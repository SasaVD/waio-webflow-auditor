"""
Content extraction module.
Sprint 4A: Unified content extraction using Trafilatura with BeautifulSoup fallback.

Trafilatura extracts clean main content from any CMS (removes nav, footer, sidebar).
This clean text feeds both WDF*IDF analysis and Google NLP API.

Performance: 50-300ms per page, parallelizable.
For sites > 1,000 pages: call trafilatura.reset_caches() every 500 pages.
"""
import asyncio
import logging
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    url: str
    clean_text: str          # Main content, no boilerplate
    title: str | None
    h1_text: str | None
    meta_description: str | None
    word_count: int
    language: str | None
    extraction_method: str   # "trafilatura" or "beautifulsoup"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def extract_content(
    html_content: str,
    url: str = "",
) -> ExtractedContent:
    """Extract clean text content from HTML using Trafilatura with BS4 fallback.

    Args:
        html_content: Raw HTML string.
        url: Page URL (for logging and metadata).

    Returns:
        ExtractedContent with clean_text suitable for NLP and TF-IDF analysis.
    """
    soup = BeautifulSoup(html_content, "lxml")
    title = _get_title(soup)
    h1 = _get_h1(soup)
    meta_desc = _get_meta_description(soup)

    # Try Trafilatura first
    clean_text = _extract_with_trafilatura(html_content, url)
    method = "trafilatura"

    if not clean_text or len(clean_text.split()) < 10:
        # Fallback to BeautifulSoup manual extraction
        clean_text = _extract_with_beautifulsoup(soup)
        method = "beautifulsoup"

    # Detect language from HTML lang attribute
    lang = soup.find("html")
    language = lang.get("lang", "").split("-")[0] if lang and lang.get("lang") else None

    word_count = len(clean_text.split()) if clean_text else 0

    return ExtractedContent(
        url=url,
        clean_text=clean_text or "",
        title=title,
        h1_text=h1,
        meta_description=meta_desc,
        word_count=word_count,
        language=language,
        extraction_method=method,
    )


def _extract_with_trafilatura(html_content: str, url: str = "") -> str | None:
    """Extract main content using Trafilatura."""
    try:
        import trafilatura
        result = trafilatura.extract(
            html_content,
            url=url,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_recall=True,
        )
        return result
    except ImportError:
        logger.warning("trafilatura not installed — skipping Trafilatura extraction")
        return None
    except Exception as e:
        logger.debug(f"Trafilatura extraction failed for {url}: {e}")
        return None


def _extract_with_beautifulsoup(soup: BeautifulSoup) -> str:
    """Fallback extraction: strip nav, footer, sidebar, scripts, styles."""
    # Remove non-content elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header",
                              "aside", "noscript", "iframe"]):
        tag.decompose()

    # Try to find main content area
    main = soup.find("main") or soup.find("article") or soup.find(role="main")
    if main:
        text = main.get_text(separator=" ", strip=True)
    else:
        body = soup.find("body")
        text = body.get_text(separator=" ", strip=True) if body else soup.get_text(separator=" ", strip=True)

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_title(soup: BeautifulSoup) -> str | None:
    title_tag = soup.find("title")
    return title_tag.get_text(strip=True) if title_tag else None


def _get_h1(soup: BeautifulSoup) -> str | None:
    h1_tag = soup.find("h1")
    return h1_tag.get_text(strip=True) if h1_tag else None


def _get_meta_description(soup: BeautifulSoup) -> str | None:
    meta = soup.find("meta", attrs={"name": "description"})
    return meta.get("content", "").strip() if meta else None


async def extract_content_batch(
    pages: List[Dict[str, str]],
    concurrency: int = 10,
) -> List[ExtractedContent]:
    """Extract content from multiple pages concurrently.

    Args:
        pages: List of dicts with 'url' and 'html_content' keys.
        concurrency: Max concurrent extractions.

    Returns:
        List of ExtractedContent results.
    """
    semaphore = asyncio.Semaphore(concurrency)
    results: List[ExtractedContent] = []
    counter = 0

    async def extract_one(page: Dict[str, str], idx: int) -> ExtractedContent:
        nonlocal counter
        url = page.get("url", "")
        html = page.get("html_content", "")
        async with semaphore:
            result = await asyncio.get_event_loop().run_in_executor(
                None, extract_content, html, url
            )
            counter += 1
            # Reset Trafilatura caches every 500 pages for memory management
            if counter % 500 == 0:
                _reset_trafilatura_caches()
                logger.info(f"Content extraction progress: {counter}/{len(pages)} pages")
            return result

    tasks = [extract_one(page, i) for i, page in enumerate(pages)]
    results = list(await asyncio.gather(*tasks))

    extracted = sum(1 for r in results if r.word_count > 0)
    logger.info(f"Content extraction complete: {extracted}/{len(pages)} pages extracted")
    return results


def _reset_trafilatura_caches():
    """Reset Trafilatura internal caches to prevent memory bloat on large sites."""
    try:
        import trafilatura
        trafilatura.reset_caches()
        logger.debug("Trafilatura caches reset")
    except (ImportError, AttributeError):
        pass


async def extract_from_urls(
    urls: List[str],
    fetch_fn=None,
) -> List[ExtractedContent]:
    """Fetch and extract content from a list of URLs.

    Args:
        urls: URLs to fetch and extract.
        fetch_fn: Async function(url) -> html_content. If None, uses httpx.

    Returns:
        List of ExtractedContent results.
    """
    import httpx

    async def default_fetch(url: str) -> str:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "WAIO-Audit-Bot/1.0 (content extraction)"
            })
            resp.raise_for_status()
            return resp.text

    fetcher = fetch_fn or default_fetch
    pages: List[Dict[str, str]] = []
    for url in urls:
        try:
            html = await fetcher(url)
            pages.append({"url": url, "html_content": html})
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            pages.append({"url": url, "html_content": ""})

    return await extract_content_batch(pages)
