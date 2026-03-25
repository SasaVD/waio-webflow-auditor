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
    try:
        # Wrap the synchronous requests.get call in a thread to keep the loop free
        html_content = await asyncio.to_thread(fetch_url, url)
    except Exception as e:
        logger.error(f"HTTP attempt failed for {url}: {e}")
        raise ValueError(f"Failed to fetch {url}: {str(e)}")

    soup = BeautifulSoup(html_content, 'lxml')
    body = soup.body

    # Check if minimal content (indicator of JS-rendered SPA)
    if not body or len(body.text.strip()) < 100 or len(html_content) < 5000:
        logger.info(f"Minimal content detected for {url}, falling back to Playwright...")
        html_content = await fetch_page_with_playwright(url)
        soup = BeautifulSoup(html_content, 'lxml')

    return html_content, soup

async def fetch_page_with_playwright(url: str) -> str:
    browser = await get_browser()
    if not browser:
        raise ValueError("Critical error: Playwright browser could not be initialized.")
        
    # Create a new context for isolation (cookies, cache)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=15000)
        html_content = await page.content()
        return html_content
    except Exception as e:
        logger.error(f"Playwright attempt failed for {url}: {e}")
        raise ValueError(f"Failed to fetch {url} via Playwright: {e}")
    finally:
        await context.close()
