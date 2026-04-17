"""SerpApi integration -- fetch top organic SERP results for a keyword."""
import os
import logging

import httpx

logger = logging.getLogger(__name__)

SERPAPI_BASE = "https://serpapi.com/search"


async def fetch_serp_results(
    keyword: str,
    num_results: int = 10,
    country: str = "us",
    language: str = "en",
) -> list[dict]:
    """Fetch top organic SERP results for a keyword via SerpApi.

    Returns list of {url, title, snippet, position}.
    Cost: ~$0.01 per search on paid plan, free under 250/month.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise ValueError("SERPAPI_KEY not configured")

    params = {
        "q": keyword,
        "engine": "google",
        "api_key": api_key,
        "num": num_results,
        "gl": country,
        "hl": language,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(SERPAPI_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    organic = data.get("organic_results", [])
    results = []
    for item in organic[:num_results]:
        results.append({
            "url": item.get("link", ""),
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "position": item.get("position", 0),
        })

    logger.info(f"SerpApi returned {len(results)} results for '{keyword}'")
    return results
