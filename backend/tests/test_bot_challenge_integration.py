"""Integration test: bot-challenge hook glue in perform_audit.

Unit tests for detect_bot_challenge (test_bot_detection.py) and for
compile_scores coverage (test_scoring.py) cover the pieces individually.
This test exercises the wiring in main.perform_audit end-to-end:
  - fetch_page monkeypatched to return a Cloudflare challenge page
  - auditors MUST be skipped (scan_status='bot_challenged' on all 10)
  - compile_scores MUST suppress overall_score to None
  - report['bot_challenge'] MUST carry the detection metadata

The live smoke-test against sched.com can't validate this deterministically
because Cloudflare's bot rules are non-deterministic (IP/time/random).
"""
import asyncio
import sys
from pathlib import Path

from bs4 import BeautifulSoup

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import main  # noqa: E402
from crawler import FetchResult  # noqa: E402


_CLOUDFLARE_CHALLENGE_HTML = """
<!DOCTYPE html>
<html><head><title>Just a moment...</title></head>
<body>
  <h2 id="challenge-success-text">Verifying you are human. This may take a few seconds.</h2>
</body></html>
"""
# Minimal fixture reproducing the sched.com incident signature precisely:
# only #challenge-success-text, so detection can't short-circuit on an
# earlier selector (.cf-turnstile) and the regression test locks the
# specific signal that was in audit 563145e4.


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _Req:
    """Minimal stand-in for AuditRequest (Pydantic validation not needed here)."""
    def __init__(self, url: str, tier: str = "free"):
        self.url = url
        self.tier = tier


def test_perform_audit_short_circuits_on_cloudflare_challenge(monkeypatch):
    """End-to-end: Cloudflare challenge page → all 10 pillars skipped,
    overall_score=None, bot_challenge block populated."""

    async def fake_fetch(_url, **_kwargs):
        # Workstream E: orchestrator now passes shared_context kwarg; tolerate it.
        return FetchResult(
            html=_CLOUDFLARE_CHALLENGE_HTML,
            soup=BeautifulSoup(_CLOUDFLARE_CHALLENGE_HTML, "html.parser"),
            headers={"server": "cloudflare"},
            cookies={"__cf_bm": "captured"},
            status_code=403,
        )

    monkeypatch.setattr(main, "fetch_page", fake_fetch)

    # Workstream E: orchestrator opens an audit-scoped BrowserContext via
    # get_browser().new_context(). Stub both so tests don't launch real Chromium.
    class _FakeContext:
        async def close(self):
            pass

    class _FakeBrowser:
        async def new_context(self, **_kwargs):
            return _FakeContext()

    async def _fake_get_browser():
        return _FakeBrowser()

    monkeypatch.setattr(main, "get_browser", _fake_get_browser)

    # Sentinel: any auditor firing would mean the hook failed. Replace each
    # auditor with a function that raises — if the hook is working, none run.
    def _must_not_run(*_args, **_kwargs):
        raise AssertionError("Auditor ran despite bot_challenge detection")

    for sym in [
        "run_html_audit", "run_structured_data_audit", "run_css_js_audit",
        "run_aeo_content_audit", "run_rag_readiness_audit",
        "run_agentic_protocol_audit", "run_data_integrity_audit",
        "run_internal_linking_audit",
    ]:
        monkeypatch.setattr(main, sym, _must_not_run)

    async def _must_not_run_async(*_args, **_kwargs):
        raise AssertionError("Async auditor ran despite bot_challenge detection")

    monkeypatch.setattr(main, "run_accessibility_audit", _must_not_run_async)

    # Skip the DB write — save_audit_history hits the real database.
    async def _fake_save(*_a, **_kw):
        return "test-audit-id"

    monkeypatch.setattr(main, "save_audit_history", _fake_save)

    result = _run(main.perform_audit(_Req("https://example.com", tier="free")))

    # Detection metadata
    assert result["bot_challenge"] is not None
    assert result["bot_challenge"]["detected"] is True
    assert result["bot_challenge"]["vendor"] == "cloudflare"
    # The very signal sched.com returned — regression lock.
    assert "challenge-success-text" in result["bot_challenge"]["signals"]

    # Scoring suppression
    assert result["overall_score"] is None
    assert result["overall_label"] == "Scan incomplete"
    assert result["coverage_weight"] == 0.0

    # Every pillar flagged bot_challenged
    for pillar_key, status in result["scan_statuses"].items():
        assert status == "bot_challenged", f"{pillar_key} has status={status}, expected bot_challenged"


def test_perform_audit_normal_path_unchanged_when_no_challenge(monkeypatch):
    """Negative control: real content → normal auditors run, bot_challenge=None.
    Guards against the hook false-positiving and breaking the happy path."""
    clean_html = (
        "<html><body>"
        "<header><nav>Home About</nav></header>"
        "<main><h1>Example</h1><p>" + ("Real content here. " * 50) + "</p></main>"
        "<footer>© 2026</footer>"
        "</body></html>"
    )

    async def fake_fetch(_url, **_kwargs):
        # Workstream E: orchestrator now passes shared_context kwarg; tolerate it.
        return FetchResult(
            html=clean_html,
            soup=BeautifulSoup(clean_html, "html.parser"),
            headers={},
            cookies={},
            status_code=200,
        )

    monkeypatch.setattr(main, "fetch_page", fake_fetch)

    # Workstream E: stub the audit-scoped BrowserContext lifecycle.
    class _FakeContext:
        async def close(self):
            pass

    class _FakeBrowser:
        async def new_context(self, **_kwargs):
            return _FakeContext()

    async def _fake_get_browser():
        return _FakeBrowser()

    monkeypatch.setattr(main, "get_browser", _fake_get_browser)

    async def _fake_save(*_a, **_kw):
        return "test-audit-id"

    monkeypatch.setattr(main, "save_audit_history", _fake_save)

    result = _run(main.perform_audit(_Req("https://example.com", tier="free")))

    assert result["bot_challenge"] is None
    # Overall should be a number — exact value depends on auditor results, just
    # confirm it's not suppressed.
    assert result["overall_score"] is not None
    assert isinstance(result["overall_score"], int)
    # All pillars should have scanned.
    for pillar_key, status in result["scan_statuses"].items():
        # Either "ok" (scanned successfully) or "failed" (auditor crashed on
        # this minimal fixture) — but NEVER "bot_challenged".
        assert status != "bot_challenged", f"{pillar_key} falsely flagged bot_challenged"
