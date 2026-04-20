import requests
from bs4 import BeautifulSoup
import logging
from typing import Tuple, Optional
import asyncio
from playwright.async_api import async_playwright, Browser

logger = logging.getLogger(__name__)

_playwright = None
_browser: Optional[Browser] = None

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

def fetch_url(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.text

async def fetch_page(url: str) -> Tuple[str, BeautifulSoup]:
    """
    Fetches the HTML content of a given URL. Uses an HTTP GET request (via requests).
    If the content appears to be a JS-rendered SPA (minimal content),
    falls back to rendering via Playwright to ensure all JS is executed.
    """
    html_content = ""
    try:
        loop = asyncio.get_running_loop()
        html_content = await loop.run_in_executor(None, fetch_url, url)
    except Exception as e:
        # Bot-protected sites (Cloudflare, Akamai, etc.) often 403 on a plain
        # requests client. A headless Chromium usually gets through, so treat
        # any HTTP-layer failure as "try Playwright" rather than aborting.
        logger.info(f"HTTP fetch failed for {url} ({e}); falling back to Playwright")
        try:
            html_content = await fetch_page_with_playwright(url)
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
            html_content = await fetch_page_with_playwright(url)
            soup = BeautifulSoup(html_content, 'lxml')
        except Exception as pw_err:
            logger.warning(f"Playwright upgrade failed for {url}, keeping HTTP result: {pw_err}")

    return html_content, soup

async def fetch_page_with_playwright(url: str) -> str:
    browser = await get_browser()
    if not browser:
        raise ValueError("Critical error: Playwright browser could not be initialized.")
        
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )
    html_content = ""
    try:
        page = await context.new_page()
        # Use domcontentloaded + longer timeout: networkidle hangs on any site
        # with persistent analytics/sockets, and Cloudflare JS challenges need
        # time to clear. After DOM is parsed, opportunistically wait for full
        # load (for JS hydration / challenge redirect) but don't fail if it
        # times out — a parsed DOM is enough to audit.
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_load_state("load", timeout=10000)
        except Exception as load_err:
            logger.info(f"Playwright load state not reached for {url} ({load_err}); proceeding with DOM snapshot")
        html_content = await page.content()
    except Exception as e:
        logger.error(f"Playwright attempt failed for {url}: {e}")
        # Ensure we re-raise to satisfy type checker and propagate the error
        raise ValueError(f"Failed to fetch {url} via Playwright: {e}") from e
    finally:
        await context.close()

    return html_content
