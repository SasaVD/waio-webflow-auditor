"""Wiring tests: confirm each of the three log paths increments the right counter.

Pairs the existing test_bot_challenge_integration.py / test_accessibility_shared_context.py
fixture pattern with observability.get_event_aggregates() assertions, so the
counter increments are locked alongside the log paths they observe.
"""
import asyncio
import sys
from pathlib import Path

from bs4 import BeautifulSoup

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import main  # noqa: E402
import observability  # noqa: E402
from crawler import FetchResult  # noqa: E402


_CLOUDFLARE_CHALLENGE_HTML = """
<!DOCTYPE html>
<html><head><title>Just a moment...</title></head>
<body><h2 id="challenge-success-text">Verifying you are human.</h2></body></html>
"""


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _Req:
    def __init__(self, url: str, tier: str = "free"):
        self.url = url
        self.tier = tier


def test_bot_challenge_detection_increments_counter(monkeypatch):
    """Cloudflare challenge → bot_challenge.detected counter increments by 1
    with vendor='cloudflare' under by_vendor."""
    observability.reset_for_test()

    async def fake_fetch(_url, **_kwargs):
        return FetchResult(
            html=_CLOUDFLARE_CHALLENGE_HTML,
            soup=BeautifulSoup(_CLOUDFLARE_CHALLENGE_HTML, "html.parser"),
            headers={"server": "cloudflare"},
            cookies={"__cf_bm": "captured"},
            status_code=403,
        )

    monkeypatch.setattr(main, "fetch_page", fake_fetch)

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

    _run(main.perform_audit(_Req("https://example.com", tier="free")))

    agg = observability.get_event_aggregates()
    assert agg.get("bot_challenge.detected", {}).get("total", 0) == 1
    assert agg["bot_challenge.detected"]["by_vendor"]["cloudflare"] == 1


def test_clean_fetch_does_not_increment_bot_challenge_counter(monkeypatch):
    """Negative control: real content → counter stays at 0. Catches the
    regression where a false-positive bot detection would inflate the metric."""
    observability.reset_for_test()

    clean_html = (
        "<html><body>"
        "<header><nav>Home About</nav></header>"
        "<main><h1>Example</h1><p>" + ("Real content here. " * 50) + "</p></main>"
        "<footer>© 2026</footer>"
        "</body></html>"
    )

    async def fake_fetch(_url, **_kwargs):
        return FetchResult(
            html=clean_html,
            soup=BeautifulSoup(clean_html, "html.parser"),
            headers={},
            cookies={},
            status_code=200,
        )

    monkeypatch.setattr(main, "fetch_page", fake_fetch)

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

    _run(main.perform_audit(_Req("https://example.com", tier="free")))

    agg = observability.get_event_aggregates()
    assert "bot_challenge.detected" not in agg or agg["bot_challenge.detected"]["total"] == 0


def test_accessibility_scan_failed_increments_counter(monkeypatch):
    """Accessibility auditor's outer except path → accessibility.scan_failed
    counter increments. The except guards page.goto + the 5 checks (line 109).
    We fake the browser stack so setup succeeds, then make page.goto raise —
    that's the production-realistic failure mode (Playwright timeout)."""
    observability.reset_for_test()

    import accessibility_auditor

    class _FakePage:
        async def goto(self, *_a, **_kw):
            raise RuntimeError("Page.goto: Timeout 15000ms exceeded")

        async def close(self):
            pass

    class _FakeContext:
        async def new_page(self):
            return _FakePage()

        async def close(self):
            pass

    class _FakeBrowser:
        async def new_context(self, **_kwargs):
            return _FakeContext()

    async def _fake_get_browser():
        return _FakeBrowser()

    monkeypatch.setattr(accessibility_auditor, "get_browser", _fake_get_browser)

    result = _run(accessibility_auditor.run_accessibility_audit("https://example.com"))

    # Precondition: auditor returned with scan_status='failed'
    assert result.get("scan_status") == "failed"
    # The error string should be propagated verbatim from the exception
    assert "Timeout" in (result.get("scan_error") or "")

    # Counter incremented
    agg = observability.get_event_aggregates()
    assert agg.get("accessibility.scan_failed", {}).get("total", 0) == 1
