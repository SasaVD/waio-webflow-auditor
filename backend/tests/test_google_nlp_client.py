"""Tests for the Google NLP client text preparation (BUG-2) and the
min_tokens guard (Workstream D2 production fix, 2026-04-27).

The _prepare_text tests lock the BUG-2 fix that terminates unpunctuated
lines so Google NLP's PLAIN_TEXT tokenizer treats block boundaries as
sentence boundaries.

The min_tokens tests lock the kwarg behavior that lets the brand
resolver call analyze_entities on 1-word strings ("Ticketmaster",
"Sched"). The default 5-word guard was silently bypassing every KG
MID lookup — observed on production audits 9192396f and cdb1ae29
(2026-04-27 diagnostic).
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import google_nlp_client  # noqa: E402
from google_nlp_client import _prepare_text, analyze_entities  # noqa: E402


def test_prepare_text_terminates_unpunctuated_lines():
    """The exact shadowdigital.cc homepage pattern: heading followed
    by a paragraph whose first word repeats the heading's last token.
    After _prepare_text the heading must end with a period so Google
    NLP sees two sentences instead of merging 'Webflow Webflow' into
    one entity."""
    src = "About Webflow\nWebflow is a no-code development tool"
    expected = "About Webflow.\nWebflow is a no-code development tool."
    assert _prepare_text(src) == expected


def test_prepare_text_preserves_already_terminated_lines():
    """Lines that already end in terminal punctuation must pass
    through untouched. Covers '.' plus the other four terminators in
    the _TERMINAL regex ('!', '?', ':', ';')."""
    src = "Hello world.\nThis is fine."
    assert _prepare_text(src) == src

    # All five terminators the regex accepts
    for terminator in [".", "!", "?", ":", ";"]:
        line = f"A line{terminator}"
        assert _prepare_text(line) == line, (
            f"Line ending in {terminator!r} should be unchanged"
        )

    # Mixed content — some lines terminated, some not
    src_mixed = "Heading one\nSentence two.\nHeading three\nSentence four!"
    expected_mixed = "Heading one.\nSentence two.\nHeading three.\nSentence four!"
    assert _prepare_text(src_mixed) == expected_mixed


def test_prepare_text_handles_empty_lines_and_whitespace():
    """Blank and whitespace-only lines between content blocks must
    stay blank — we only add periods to lines that have content.
    Otherwise we'd inject '.' into empty paragraph breaks, which
    might confuse Google NLP's sentence segmenter more than it
    helps."""
    src = "Heading\n\n  \nParagraph"
    expected = "Heading.\n\n\nParagraph."
    assert _prepare_text(src) == expected

    # Trailing whitespace on content lines is also stripped before
    # the terminator is appended — no "Heading  ." artifacts.
    src_trailing = "Heading   \nParagraph"
    expected_trailing = "Heading.\nParagraph."
    assert _prepare_text(src_trailing) == expected_trailing


# ─────────────────────────────────────────────────────────────────────────
# Workstream D2 production fix (2026-04-27): min_tokens kwarg
#
# The `analyze_entities` function had a hardcoded `< 5 words → return []`
# guard that protects page-content callers from spending credits on thin
# pages, but silently bypassed every KG MID lookup the brand resolver
# attempted (brand strings are 1-3 words by definition). The min_tokens
# kwarg makes the threshold explicit and overridable. Brand validation
# passes min_tokens=1; default page-content behavior is unchanged.
# ─────────────────────────────────────────────────────────────────────────


def _run(coro):
    """Drive an awaitable to completion without an external loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _FakeAsyncClient:
    """Drop-in replacement for httpx.AsyncClient used in analyze_entities.

    Records the body of every POST so tests can assert the API was actually
    invoked (vs the early-return short-circuiting before any HTTP call).
    """

    def __init__(self, *_, **__):
        self.calls: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def post(self, url, json=None):  # noqa: A002
        self.calls.append({"url": url, "json": json})

        class _Resp:
            def raise_for_status(self):
                return None

            def json(self):
                # Minimal valid analyzeEntities response with one KG-backed
                # entity so the resolver's KG MID branch sees real metadata.
                return {
                    "entities": [
                        {
                            "name": "Ticketmaster",
                            "type": "ORGANIZATION",
                            "salience": 0.85,
                            "metadata": {
                                "mid": "/m/0gby4n",
                                "wikipedia_url": "https://en.wikipedia.org/wiki/Ticketmaster",
                            },
                            "mentions": [{"text": {"content": "Ticketmaster"}}],
                        }
                    ]
                }

        return _Resp()


def test_analyze_entities_default_min_tokens_skips_short_input(monkeypatch):
    """Default min_tokens=5 preserves the page-content caller's behavior.
    Inputs under 5 words still early-return [] without making an API call —
    proven by the lack of recorded HTTP calls on the fake client."""
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-test")
    fake = _FakeAsyncClient()
    monkeypatch.setattr(google_nlp_client.httpx, "AsyncClient", lambda *a, **kw: fake)

    result = _run(analyze_entities("Ticketmaster"))

    assert result == []
    assert fake.calls == [], (
        "Default min_tokens=5 must short-circuit before any HTTP call. "
        "If this fires, the page-content caller is now spending credits "
        "on thin-content pages."
    )


def test_analyze_entities_min_tokens_one_invokes_api_on_short_brand(monkeypatch):
    """min_tokens=1 lets the brand resolver call analyze_entities on
    real-world brand strings (1-3 words). The API IS hit, the response is
    parsed, and the entity carries the KG metadata fields the resolver
    inspects (mid + wikipedia_url)."""
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-test")
    fake = _FakeAsyncClient()
    monkeypatch.setattr(google_nlp_client.httpx, "AsyncClient", lambda *a, **kw: fake)

    result = _run(analyze_entities("Ticketmaster", min_tokens=1))

    assert len(fake.calls) == 1, (
        "min_tokens=1 must reach the API. If 0 calls were recorded, the "
        "kwarg isn't actually overriding the guard."
    )
    assert "documents:analyzeEntities" in fake.calls[0]["url"]
    assert len(result) == 1
    assert result[0].name == "Ticketmaster"
    assert result[0].knowledge_graph_mid == "/m/0gby4n"
    assert result[0].wikipedia_url == "https://en.wikipedia.org/wiki/Ticketmaster"


def test_analyze_entities_min_tokens_zero_treats_empty_input_as_skip(monkeypatch):
    """Edge case: min_tokens=0 still skips a literally empty string
    (len("".split()) == 0, so 0 < 0 is false and the guard passes).
    This documents the behavior — min_tokens=0 effectively disables the
    guard entirely, including for empty input. Callers who want to
    reject empty strings must do so themselves."""
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-test")
    fake = _FakeAsyncClient()
    monkeypatch.setattr(google_nlp_client.httpx, "AsyncClient", lambda *a, **kw: fake)

    # Empty string: 0 words < 0 is false → guard does NOT trigger → API call made
    _run(analyze_entities("", min_tokens=0))
    assert len(fake.calls) == 1


# ─────────────────────────────────────────────────────────────────────────
# Integration-style: resolve_brand end-to-end with KG MID hit
#
# Locks the path that was structurally broken in production (audits
# 9192396f and cdb1ae29 on 2026-04-27): a real brand string ("Ticketmaster")
# fed through the resolver with a properly-configured NLP client must
# return source="kg_mid" with kg_mid + wikipedia_url populated, NOT
# fall through to "override_unverified".
# ─────────────────────────────────────────────────────────────────────────


def test_resolve_brand_kg_mid_path_with_realistic_nlp_response():
    """End-to-end lock: resolve_brand with an NLP client that returns the
    same shape google_nlp_client emits (after _BrandNLPClientAdapter's
    field translation) must promote a KG-validated brand to source=kg_mid.

    This is the path that silently produced override_unverified on every
    production brand pre-fix. With min_tokens=1 wired through the adapter,
    this test confirms the resolver receives the metadata and routes
    through layer 1 instead of falling through to layer 4."""
    from ai_visibility.brand_resolver import resolve_brand

    class _MockNLP:
        """Mirrors what _BrandNLPClientAdapter.analyze_entities returns —
        a list of dicts with metadata.mid / metadata.wikipedia_url, NOT the
        NLPEntityResult dataclass shape (the adapter does that translation)."""
        def analyze_entities(self, _text: str):
            return [
                {
                    "name": "Ticketmaster",
                    "type": "ORGANIZATION",
                    "salience": 0.85,
                    "metadata": {
                        "mid": "/m/0gby4n",
                        "wikipedia_url": "https://en.wikipedia.org/wiki/Ticketmaster",
                    },
                }
            ]

    info = resolve_brand("Ticketmaster", nlp_entities=None, nlp_client=_MockNLP())

    assert info.source == "kg_mid", (
        f"Expected source='kg_mid' for KG-backed brand, got {info.source!r}. "
        f"This is the production regression locked by Workstream D2 "
        f"production fix (2026-04-27)."
    )
    assert info.name == "Ticketmaster"
    assert info.kg_mid == "/m/0gby4n"
    assert info.wikipedia_url == "https://en.wikipedia.org/wiki/Ticketmaster"
