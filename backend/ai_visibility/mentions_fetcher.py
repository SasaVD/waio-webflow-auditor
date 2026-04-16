"""Fetch LLM Mentions data from DataForSEO AI Optimization API."""
import logging
from typing import Any

from dataforseo_client import DataForSEOClient
from .schema import MentionsResult
from .cost_tracker import CostTracker

logger = logging.getLogger(__name__)


async def fetch_mentions(
    client: DataForSEOClient,
    brand_name: str,
    cost_tracker: CostTracker,
) -> MentionsResult:
    """Fetch all LLM Mentions data for a brand.

    Makes 3 API calls:
    1. aggregated_search_data — totals, platform breakdown, search volume
    2. search_data — triggering prompts
    3. top_pages — most cited pages

    All calls are to the pre-indexed database (Google AI Overview + ChatGPT only).
    """
    result = MentionsResult()

    # 1. Aggregated data
    try:
        agg = await client.llm_mentions_aggregated(brand_name)
        cost_tracker.add(agg.get("money_spent"))
        agg_result = agg.get("result", {})
        result.total = agg_result.get("total_count", 0) or 0
        result.ai_search_volume = agg_result.get("ai_search_volume", 0) or 0
        result.impressions = agg_result.get("impressions", 0) or 0

        # Platform breakdown from engines
        engines_data = agg_result.get("engines", {})
        if isinstance(engines_data, dict):
            for engine_key, engine_val in engines_data.items():
                if isinstance(engine_val, dict):
                    result.by_platform[engine_key] = engine_val.get("count", 0) or 0
                elif isinstance(engine_val, (int, float)):
                    result.by_platform[engine_key] = int(engine_val)

        logger.info(f"LLM Mentions aggregated: total={result.total}, volume={result.ai_search_volume}")
    except Exception as e:
        logger.warning(f"LLM Mentions aggregated failed: {e}")

    # 2. Triggering prompts
    try:
        search = await client.llm_mentions_search(brand_name, limit=50)
        cost_tracker.add(search.get("money_spent"))
        items = search.get("items", [])
        for item in items[:20]:
            if isinstance(item, dict):
                result.triggering_prompts.append({
                    "prompt": item.get("keyword", item.get("prompt", "")),
                    "mention_count": item.get("count", 0) or 0,
                    "platform": item.get("engine", ""),
                })
        logger.info(f"LLM Mentions search: {len(result.triggering_prompts)} prompts")
    except Exception as e:
        logger.warning(f"LLM Mentions search failed: {e}")

    # 3. Top cited pages
    try:
        pages = await client.llm_mentions_top_pages(brand_name, limit=20)
        cost_tracker.add(pages.get("money_spent"))
        items = pages.get("items", [])
        for item in items:
            if isinstance(item, dict):
                result.top_pages.append({
                    "url": item.get("url", ""),
                    "mention_count": item.get("count", item.get("mention_count", 0)) or 0,
                })
        logger.info(f"LLM Mentions top pages: {len(result.top_pages)} pages")
    except Exception as e:
        logger.warning(f"LLM Mentions top pages failed: {e}")

    result.cost_usd = cost_tracker.total  # snapshot at this point
    return result
