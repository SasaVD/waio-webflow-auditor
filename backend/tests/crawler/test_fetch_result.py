"""Unit tests for FetchResult dataclass and header/cookie capture.

Verifies D1.0 refactor: fetch_page() returns a structured FetchResult carrying
html + soup + headers + cookies + status_code, so downstream bot-challenge
detection has the HTTP-layer metadata it needs.
"""
import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import crawler  # noqa: E402
from crawler import FetchResult  # noqa: E402


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_fetch_result_is_dataclass_with_expected_fields():
    r = FetchResult(html="<html></html>", soup=None, headers={"x": "y"}, cookies={"a": "b"}, status_code=200)
    assert r.html == "<html></html>"
    assert r.headers == {"x": "y"}
    assert r.cookies == {"a": "b"}
    assert r.status_code == 200


def test_fetch_result_backwards_compat_tuple_unpack():
    """Existing callers do `html, soup = await fetch_page(url)`. FetchResult
    must still support that 2-element iter-unpacking."""
    r = FetchResult(html="HTML", soup="SOUP", headers={}, cookies={}, status_code=200)
    html, soup = r
    assert html == "HTML"
    assert soup == "SOUP"


_PW_HTML = (
    "<html><body>"
    + ("<p>Real page content. </p>" * 250)  # 250 * 26 = 6500 chars, clears
    + "</body></html>"                       # fetch_page's 5000-char thin-body
)                                            # upgrade trigger at crawler.py:117


def test_fetch_page_returns_FetchResult_with_http_headers_and_cookies(monkeypatch):
    """Happy HTTP path: fetch_url returns html+headers+cookies+status and
    fetch_page assembles a FetchResult carrying all of them."""
    def fake_fetch_url(_url):
        return (
            _PW_HTML,
            {"server": "nginx", "cf-ray": "abc-def"},
            {"__cf_bm": "xyz", "session": "123"},
            200,
        )

    monkeypatch.setattr(crawler, "fetch_url", fake_fetch_url)

    result = _run(crawler.fetch_page("https://example.com/"))
    assert isinstance(result, FetchResult)
    assert "Real page content" in result.html
    assert result.soup.body is not None
    assert result.headers.get("server") == "nginx"
    assert result.headers.get("cf-ray") == "abc-def"
    assert result.cookies.get("__cf_bm") == "xyz"
    assert result.status_code == 200


def test_fetch_page_playwright_fallback_carries_headers_and_cookies(monkeypatch):
    """When HTTP fails and Playwright takes over, the FetchResult must still
    carry the headers and cookies captured from the Playwright response."""
    def http_boom(_url):
        raise Exception("403 Forbidden")

    async def fake_pw(_url, **_kwargs):
        return _PW_HTML, {"server": "cloudflare"}, {"__cf_bm": "captured"}, 403

    monkeypatch.setattr(crawler, "fetch_url", http_boom)
    monkeypatch.setattr(crawler, "fetch_page_with_playwright", fake_pw)

    result = _run(crawler.fetch_page("https://example.com/"))
    assert isinstance(result, FetchResult)
    assert result.headers.get("server") == "cloudflare"
    assert result.cookies.get("__cf_bm") == "captured"
    assert result.status_code == 403


def test_fetch_page_legacy_string_playwright_return_still_works(monkeypatch):
    """If fetch_page_with_playwright is monkeypatched to return a bare string
    (as legacy tests do), fetch_page must still produce a valid FetchResult
    with empty headers/cookies rather than crashing."""
    def http_boom(_url):
        raise Exception("net::ERR_FAILED")

    async def fake_pw_string_only(_url, **_kwargs):
        return _PW_HTML  # legacy shape

    monkeypatch.setattr(crawler, "fetch_url", http_boom)
    monkeypatch.setattr(crawler, "fetch_page_with_playwright", fake_pw_string_only)

    result = _run(crawler.fetch_page("https://example.com/"))
    assert isinstance(result, FetchResult)
    assert "Real page content" in result.html
    assert result.headers == {}
    assert result.cookies == {}


# ─────────────────────────────────────────────────────────────────────────────
# Workstream E: shared_context propagation
# ─────────────────────────────────────────────────────────────────────────────

def test_fetch_page_legacy_no_shared_context_unchanged(monkeypatch):
    """Existing callers without shared_context get current behavior — Playwright
    fallback is invoked exactly as before, no shared_context plumbing visible."""
    captured = {}

    def http_boom(_url):
        raise Exception("403 Forbidden")

    async def fake_pw(_url, *, shared_context=None):
        captured["shared_context"] = shared_context
        return _PW_HTML, {"server": "nginx"}, {"a": "b"}, 200

    monkeypatch.setattr(crawler, "fetch_url", http_boom)
    monkeypatch.setattr(crawler, "fetch_page_with_playwright", fake_pw)

    result = _run(crawler.fetch_page("https://example.com/"))
    assert isinstance(result, FetchResult)
    # No shared_context provided → fetch_page_with_playwright sees None.
    assert captured["shared_context"] is None


def test_fetch_page_propagates_shared_context_to_playwright_fallback(monkeypatch):
    """When fetch_page is given a shared_context, it forwards that exact
    object to fetch_page_with_playwright on the HTTP-fail fallback path."""
    sentinel_context = object()  # opaque marker — fetch_page only needs to forward
    captured = {}

    def http_boom(_url):
        raise Exception("403 Forbidden")

    async def fake_pw(_url, *, shared_context=None):
        captured["shared_context"] = shared_context
        return _PW_HTML, {}, {}, 200

    monkeypatch.setattr(crawler, "fetch_url", http_boom)
    monkeypatch.setattr(crawler, "fetch_page_with_playwright", fake_pw)

    _run(crawler.fetch_page("https://example.com/", shared_context=sentinel_context))
    assert captured["shared_context"] is sentinel_context


def test_fetch_page_propagates_shared_context_on_thin_body_upgrade(monkeypatch):
    """The thin-body upgrade path also forwards shared_context — this is where
    the homepage Playwright fetch typically lands when HTTP succeeds but the
    page is JS-rendered (the sched.com codepath)."""
    sentinel_context = object()
    captured = {}

    def thin(_url):
        return "<html><body></body></html>"  # triggers thin-body upgrade

    async def fake_pw(_url, *, shared_context=None):
        captured["shared_context"] = shared_context
        return _PW_HTML, {}, {}, 200

    monkeypatch.setattr(crawler, "fetch_url", thin)
    monkeypatch.setattr(crawler, "fetch_page_with_playwright", fake_pw)

    _run(crawler.fetch_page("https://spa.example/", shared_context=sentinel_context))
    assert captured["shared_context"] is sentinel_context


def test_fetch_page_with_playwright_does_not_close_shared_context(monkeypatch):
    """When fetch_page_with_playwright is given a shared_context, it must NOT
    close it — caller owns lifecycle. The page IS closed (it belongs to this
    fetch), but the context lives on for accessibility's later page.goto."""

    class _FakePage:
        def __init__(self):
            self.closed = False

        async def goto(self, _url, **_kwargs):
            return None  # response can be None per fetch_page_with_playwright tolerance

        async def wait_for_load_state(self, *_a, **_kw):
            pass

        async def content(self):
            return _PW_HTML

        async def close(self):
            self.closed = True

    fake_page = _FakePage()

    class _FakeContext:
        def __init__(self):
            self.close_called = False
            self.new_page_called = False

        async def new_page(self):
            self.new_page_called = True
            return fake_page

        async def cookies(self):
            return [{"name": "__cf_bm", "value": "cleared"}]

        async def close(self):
            self.close_called = True

    fake_ctx = _FakeContext()

    # Must not call get_browser() since we're providing the context directly.
    def must_not_call_get_browser():
        raise AssertionError("get_browser called despite shared_context being provided")

    monkeypatch.setattr(crawler, "get_browser", must_not_call_get_browser)

    html, headers, cookies, status = _run(
        crawler.fetch_page_with_playwright("https://example.com/", shared_context=fake_ctx)
    )

    assert html == _PW_HTML
    assert cookies == {"__cf_bm": "cleared"}
    assert fake_ctx.new_page_called, "should have called shared_context.new_page()"
    assert fake_ctx.close_called is False, "must NOT close the shared context"
    assert fake_page.closed is True, "must close the page (fetch owns it)"
