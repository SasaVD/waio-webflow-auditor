import requests
from bs4 import BeautifulSoup
import logging
from dataclasses import dataclass, field
from typing import Optional
import asyncio
from playwright.async_api import async_playwright, Browser

logger = logging.getLogger(__name__)

_playwright = None
_browser: Optional[Browser] = None


@dataclass
class FetchResult:
    """Structured result from fetch_page().

    Carries the parsed page plus the HTTP-layer metadata (headers, cookies,
    status) that downstream bot-challenge detection needs. Dataclass instead
    of tuple so future additions (redirect_chain, fetch_duration_ms) don't
    break callers.
    """
    html: str
    soup: BeautifulSoup
    headers: dict = field(default_factory=dict)
    cookies: dict = field(default_factory=dict)
    status_code: Optional[int] = None

    # Backwards-compat: allow `html, soup = await fetch_page(url)` unpacking
    # for callers not yet migrated. Raises if anyone tries to unpack >2.
    def __iter__(self):
        yield self.html
        yield self.soup

async def init_browser():
    global _playwright, _browser
    if not _playwright:
        _playwright = await async_playwright().start()
    if not _browser:
        _browser = await _playwright.chromium.launch(headless=True)

async def close_browser():
    global _playwright, _browser
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()
    _browser = None
    _playwright = None

async def get_browser() -> Browser:
    global _browser
    if not _browser:
        await init_browser()
    return _browser

def fetch_url(url: str):
    """Plain HTTP GET. Returns (html, headers_dict, cookies_dict, status_code).

    Kept as a sync helper because callers run it in an executor; returning a
    tuple keeps the executor-bridge simple while letting fetch_page assemble
    a FetchResult.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    resp_headers = {k: v for k, v in response.headers.items()}
    resp_cookies = {c.name: c.value for c in response.cookies}
    return response.text, resp_headers, resp_cookies, response.status_code


async def fetch_page(url: str) -> FetchResult:
    """
    Fetches the HTML content of a given URL. Uses an HTTP GET request (via requests).
    If the content appears to be a JS-rendered SPA (minimal content),
    falls back to rendering via Playwright to ensure all JS is executed.

    Returns a FetchResult carrying html, soup, headers, cookies, status_code
    so downstream bot-challenge detection has the full picture.
    """
    html_content = ""
    headers_out: dict = {}
    cookies_out: dict = {}
    status_code: Optional[int] = None

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, fetch_url, url)
        # fetch_url is patched in some tests to return a bare string — tolerate both.
        if isinstance(result, tuple):
            html_content, headers_out, cookies_out, status_code = result
        else:
            html_content = result
    except Exception as e:
        # Bot-protected sites (Cloudflare, Akamai, etc.) often 403 on a plain
        # requests client. A headless Chromium usually gets through, so treat
        # any HTTP-layer failure as "try Playwright" rather than aborting.
        logger.info(f"HTTP fetch failed for {url} ({e}); falling back to Playwright")
        try:
            pw_result = await fetch_page_with_playwright(url)
            if isinstance(pw_result, tuple):
                html_content, headers_out, cookies_out, status_code = pw_result
            else:
                html_content = pw_result
        except Exception as pw_err:
            raise ValueError(
                f"Failed to fetch {url}: HTTP error ({e}) and Playwright fallback failed ({pw_err})"
            ) from pw_err

    soup = BeautifulSoup(html_content, 'lxml')
    body = soup.body

    # If HTTP succeeded but content looks JS-rendered (thin body), upgrade to Playwright.
    if not body or len(body.text.strip()) < 100 or len(html_content) < 5000:
        logger.info(f"Minimal content detected for {url}, upgrading to Playwright...")
        try:
            pw_result = await fetch_page_with_playwright(url)
            if isinstance(pw_result, tuple):
                html_content, headers_out, cookies_out, status_code = pw_result
            else:
                html_content = pw_result
            soup = BeautifulSoup(html_content, 'lxml')
        except Exception as pw_err:
            logger.warning(f"Playwright upgrade failed for {url}, keeping HTTP result: {pw_err}")

    return FetchResult(
        html=html_content,
        soup=soup,
        headers=headers_out or {},
        cookies=cookies_out or {},
        status_code=status_code,
    )


async def fetch_page_with_playwright(url: str):
    """Render a page with headless Chromium.

    Returns a 4-tuple (html, headers, cookies, status_code). Tests that
    monkeypatch this function to return a bare string are still supported by
    fetch_page, which handles both shapes.
    """
    browser = await get_browser()
    if not browser:
        raise ValueError("Critical error: Playwright browser could not be initialized.")

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )
    html_content = ""
    resp_headers: dict = {}
    resp_cookies: dict = {}
    status_code: Optional[int] = None
    try:
        page = await context.new_page()
        # Use domcontentloaded + longer timeout: networkidle hangs on any site
        # with persistent analytics/sockets, and Cloudflare JS challenges need
        # time to clear. After DOM is parsed, opportunistically wait for full
        # load (for JS hydration / challenge redirect) but don't fail if it
        # times out — a parsed DOM is enough to audit.
        response = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        if response is not None:
            try:
                resp_headers = dict(response.headers or {})
            except Exception:
                resp_headers = {}
            try:
                status_code = response.status
            except Exception:
                status_code = None
        try:
            await page.wait_for_load_state("load", timeout=10000)
        except Exception as load_err:
            logger.info(f"Playwright load state not reached for {url} ({load_err}); proceeding with DOM snapshot")

        # Capture cookies BEFORE context.close() — they're discarded with the
        # context. This is the only way Cloudflare/Akamai cookie-based bot
        # detection sees __cf_bm / _abck / etc.
        try:
            cookies_list = await context.cookies()
            resp_cookies = {c.get("name", ""): c.get("value", "") for c in cookies_list if c.get("name")}
        except Exception as cookie_err:
            logger.debug(f"Could not capture cookies for {url}: {cookie_err}")
            resp_cookies = {}

        html_content = await page.content()
    except Exception as e:
        logger.error(f"Playwright attempt failed for {url}: {e}")
        # Ensure we re-raise to satisfy type checker and propagate the error
        raise ValueError(f"Failed to fetch {url} via Playwright: {e}") from e
    finally:
        await context.close()

    return html_content, resp_headers, resp_cookies, status_code
