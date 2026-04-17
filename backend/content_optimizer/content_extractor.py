"""Content extraction for competitor pages using Trafilatura."""
import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


async def extract_content_from_urls(
    urls: list[str],
    timeout: float = 15.0,
) -> list[dict]:
    """Fetch and extract main content from multiple URLs concurrently.

    Returns list of {url, text, word_count, success, error}.
    Uses Trafilatura for boilerplate removal (nav, footer, sidebar stripped).
    """
    sem = asyncio.Semaphore(5)  # max 5 concurrent fetches

    async def extract_one(url: str) -> dict:
        async with sem:
            try:
                async with httpx.AsyncClient(
                    timeout=timeout, follow_redirects=True
                ) as client:
                    resp = await client.get(
                        url,
                        headers={"User-Agent": "WAIO-Auditor/1.0"},
                    )
                    resp.raise_for_status()
                    html = resp.text

                import trafilatura
                text = trafilatura.extract(
                    html,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=False,
                    favor_precision=True,
                )

                if not text or len(text.split()) < 50:
                    return {
                        "url": url,
                        "text": "",
                        "word_count": 0,
                        "success": False,
                        "error": "Insufficient content extracted",
                    }

                word_count = len(text.split())
                return {
                    "url": url,
                    "text": text,
                    "word_count": word_count,
                    "success": True,
                    "error": None,
                }

            except Exception as e:
                logger.warning(f"Content extraction failed for {url}: {e}")
                return {
                    "url": url,
                    "text": "",
                    "word_count": 0,
                    "success": False,
                    "error": str(e)[:200],
                }

    results = await asyncio.gather(*[extract_one(url) for url in urls])
    successful = sum(1 for r in results if r["success"])
    logger.info(
        f"Content extraction: {successful}/{len(urls)} URLs extracted successfully"
    )
    return list(results)
