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

    async def fake_pw(_url):
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

    async def fake_pw_string_only(_url):
        return _PW_HTML  # legacy shape

    monkeypatch.setattr(crawler, "fetch_url", http_boom)
    monkeypatch.setattr(crawler, "fetch_page_with_playwright", fake_pw_string_only)

    result = _run(crawler.fetch_page("https://example.com/"))
    assert isinstance(result, FetchResult)
    assert "Real page content" in result.html
    assert result.headers == {}
    assert result.cookies == {}
