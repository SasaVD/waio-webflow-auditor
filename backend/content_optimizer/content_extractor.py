"""Content extraction for competitor pages using Trafilatura."""
import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_USER_AGENTS = [
    # Chrome 125 on macOS
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    # Firefox 128 on Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
        "Gecko/20100101 Firefox/128.0"
    ),
]


async def _fetch_html(url: str, user_agent: str, timeout: float) -> str | None:
    """Fetch raw HTML via httpx."""
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True
        ) as client:
            resp = await client.get(url, headers={"User-Agent": user_agent})
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.debug(f"httpx fetch failed for {url}: {e}")
        return None


def _extract_text(html: str) -> str:
    """Extract clean text from HTML using Trafilatura (sync)."""
    import trafilatura

    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
        favor_precision=True,
    )
    return text or ""


async def _playwright_fetch(url: str, timeout: float) -> str | None:
    """Fallback: fetch page HTML via headless Chromium (handles JS-rendered sites)."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=int(timeout * 1000),
                )
                # Extra settle time for JS-rendered content
                await page.wait_for_timeout(2000)
                html = await page.content()
                return html
            finally:
                await browser.close()
    except Exception as e:
        logger.debug(f"Playwright fetch failed for {url}: {e}")
        return None


async def extract_content_from_urls(
    urls: list[str],
    timeout: float = 15.0,
) -> list[dict]:
    """Fetch and extract main content from multiple URLs concurrently.

    Returns list of {url, text, word_count, success, error}.

    Extraction strategy per URL (three attempts):
    1. httpx with Chrome UA → Trafilatura
    2. httpx with Firefox UA → Trafilatura  (if attempt 1 yields <200 words)
    3. Playwright headless Chromium → Trafilatura  (if still <200 words)
    """
    http_sem = asyncio.Semaphore(5)  # max 5 concurrent httpx fetches
    pw_sem = asyncio.Semaphore(3)  # max 3 concurrent Playwright instances

    async def extract_one(url: str) -> dict:
        best_text = ""

        try:
            # --- Attempt 1: Chrome UA ---
            async with http_sem:
                html = await _fetch_html(url, _USER_AGENTS[0], timeout)
                if html:
                    best_text = _extract_text(html)

                # --- Attempt 2: Firefox UA (only if first was weak) ---
                if len(best_text.split()) < 200:
                    html2 = await _fetch_html(url, _USER_AGENTS[1], timeout)
                    if html2:
                        text2 = _extract_text(html2)
                        if len(text2.split()) > len(best_text.split()):
                            best_text = text2

            # --- Attempt 3: Playwright fallback (outside httpx semaphore) ---
            if len(best_text.split()) < 200:
                async with pw_sem:
                    html3 = await _playwright_fetch(url, timeout=20.0)
                    if html3:
                        text3 = _extract_text(html3)
                        if len(text3.split()) > len(best_text.split()):
                            best_text = text3

        except Exception as e:
            logger.warning(f"Content extraction failed for {url}: {e}")
            return {
                "url": url,
                "text": "",
                "word_count": 0,
                "success": False,
                "error": str(e)[:200],
            }

        if not best_text or len(best_text.split()) < 50:
            return {
                "url": url,
                "text": "",
                "word_count": 0,
                "success": False,
                "error": "Insufficient content extracted after all attempts",
            }

        word_count = len(best_text.split())
        return {
            "url": url,
            "text": best_text,
            "word_count": word_count,
            "success": True,
            "error": None,
        }

    results = await asyncio.gather(*[extract_one(url) for url in urls])
    successful = sum(1 for r in results if r["success"])
    logger.info(
        f"Content extraction: {successful}/{len(urls)} URLs extracted successfully"
    )
    return list(results)
