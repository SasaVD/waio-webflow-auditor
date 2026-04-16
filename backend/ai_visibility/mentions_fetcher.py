"""Fetch LLM Mentions data from DataForSEO AI Optimization API."""
import logging

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
    1. aggregated_metrics — totals by platform, sources_domain, etc.
    2. search — triggering prompts (questions that mention the brand)
    3. top_pages — most cited pages (grouped with per-platform counts)

    All calls are to the pre-indexed database (Google AI Overview + ChatGPT).
    """
    result = MentionsResult()

    # 1. Aggregated metrics
    try:
        agg = await client.llm_mentions_aggregated(brand_name)
        cost_tracker.add(agg.get("money_spent"))
        agg_result = agg.get("result", {})

        # Response shape: {total: {platform: [{key, mentions, ai_search_volume, impressions}, ...], ...}}
        total_group = agg_result.get("total", {})

        # Platform breakdown — sum across platforms for totals
        platforms = total_group.get("platform", []) or []
        for p in platforms:
            if not isinstance(p, dict):
                continue
            platform_key = p.get("key", "")
            mentions = p.get("mentions", 0) or 0
            volume = p.get("ai_search_volume", 0) or 0
            impressions_val = p.get("impressions", 0) or 0
            result.by_platform[platform_key] = mentions
            result.total += mentions
            result.ai_search_volume += volume
            result.impressions += impressions_val

        logger.info(f"LLM Mentions aggregated: total={result.total}, volume={result.ai_search_volume}")
    except Exception as e:
        logger.warning(f"LLM Mentions aggregated failed: {e}")

    # 2. Triggering prompts (search)
    try:
        search = await client.llm_mentions_search(brand_name, limit=50)
        cost_tracker.add(search.get("money_spent"))
        items = search.get("items", []) or []

        # Response shape: [{question, answer, platform, ai_search_volume, sources, ...}, ...]
        for item in items[:20]:
            if isinstance(item, dict):
                result.triggering_prompts.append({
                    "prompt": item.get("question", ""),
                    "platform": item.get("platform", ""),
                    "model_name": item.get("model_name", ""),
                    "ai_search_volume": item.get("ai_search_volume", 0) or 0,
                })
        logger.info(f"LLM Mentions search: {len(result.triggering_prompts)} prompts")
    except Exception as e:
        logger.warning(f"LLM Mentions search failed: {e}")

    # 3. Top cited pages
    try:
        pages = await client.llm_mentions_top_pages(brand_name, limit=20)
        cost_tracker.add(pages.get("money_spent"))
        items = pages.get("items", []) or []

        # Response shape: [{key: "url", platform: [{key, mentions, ...}], ...}, ...]
        for item in items:
            if isinstance(item, dict):
                page_url = item.get("key", "")
                # Sum mentions across all platforms for this page
                platforms = item.get("platform", []) or []
                total_mentions = sum(
                    (p.get("mentions", 0) or 0) for p in platforms if isinstance(p, dict)
                )
                result.top_pages.append({
                    "url": page_url,
                    "mention_count": total_mentions,
                })
        logger.info(f"LLM Mentions top pages: {len(result.top_pages)} pages")
    except Exception as e:
        logger.warning(f"LLM Mentions top pages failed: {e}")

    result.cost_usd = cost_tracker.total  # snapshot at this point
    return result
