"""Regression: bot-protected sites that 403 the plain HTTP client must fall
back to Playwright instead of aborting the audit (e.g. loungelizard.com)."""
import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import crawler  # noqa: E402


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


_PW_HTML = (
    "<html><body>"
    + ("<p>Real browser rendered content for Lounge Lizard.</p>" * 50)
    + "</body></html>"
)


def test_http_403_falls_back_to_playwright(monkeypatch):
    """When requests.get raises (e.g. 403 Forbidden), we must try Playwright
    instead of failing the entire audit."""
    def boom(_url):
        raise Exception("403 Client Error: Forbidden for url: https://www.loungelizard.com/")

    async def fake_pw(_url):
        return _PW_HTML

    monkeypatch.setattr(crawler, "fetch_url", boom)
    monkeypatch.setattr(crawler, "fetch_page_with_playwright", fake_pw)

    html, soup = _run(crawler.fetch_page("https://www.loungelizard.com/"))
    assert "Real browser rendered content" in html
    assert soup.body is not None


def test_both_paths_fail_raises_informative_error(monkeypatch):
    """If Playwright also fails, the ValueError must name both errors."""
    def http_boom(_url):
        raise Exception("403 Forbidden")

    async def pw_boom(_url):
        raise Exception("net::ERR_TIMED_OUT")

    monkeypatch.setattr(crawler, "fetch_url", http_boom)
    monkeypatch.setattr(crawler, "fetch_page_with_playwright", pw_boom)

    with pytest.raises(ValueError) as exc:
        _run(crawler.fetch_page("https://www.loungelizard.com/"))
    msg = str(exc.value)
    assert "403" in msg
    assert "ERR_TIMED_OUT" in msg or "Playwright" in msg


def test_thin_http_response_upgrades_to_playwright(monkeypatch):
    """Existing behavior preserved: thin HTTP body triggers Playwright upgrade."""
    def thin(_url):
        return "<html><body></body></html>"

    async def fake_pw(_url):
        return _PW_HTML

    monkeypatch.setattr(crawler, "fetch_url", thin)
    monkeypatch.setattr(crawler, "fetch_page_with_playwright", fake_pw)

    html, _soup = _run(crawler.fetch_page("https://spa.example/"))
    assert "Real browser rendered content" in html


def test_thin_http_and_failed_playwright_keeps_http_result(monkeypatch):
    """If the HTTP fetch succeeded but looked thin AND Playwright upgrade
    fails, we keep the HTTP body rather than throwing — partial signal beats
    no audit at all."""
    def thin(_url):
        return "<html><body></body></html>"

    async def pw_boom(_url):
        raise Exception("browser crashed")

    monkeypatch.setattr(crawler, "fetch_url", thin)
    monkeypatch.setattr(crawler, "fetch_page_with_playwright", pw_boom)

    html, _soup = _run(crawler.fetch_page("https://spa.example/"))
    assert html == "<html><body></body></html>"
