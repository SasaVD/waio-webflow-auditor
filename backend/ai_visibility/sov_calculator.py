"""Share of Voice calculation from LLM Mentions cross_aggregated data."""
from typing import Any

from .schema import SOVResult


def _extract_mentions_from_item(item: dict) -> int:
    """Sum mentions across all platforms for a cross-aggregated item."""
    platforms = item.get("platform", []) or []
    return sum(
        (p.get("mentions", 0) or 0) for p in platforms if isinstance(p, dict)
    )


def calculate_sov(
    cross_aggregated_data: dict[str, Any] | None,
    brand_domain: str,
    competitor_domains: list[str],
) -> SOVResult:
    """Compute Share of Voice from the cross_aggregated_metrics endpoint.

    SOV = brand_mentions / total_mentions across brand + competitors.
    Exclusively uses mentions_database data (never live_test).

    The cross_aggregated response shape:
      {"result": {"total": {...}, "items": [{key, platform: [{mentions, ...}]}]}}
    Each item's "key" is the aggregation_key (brand/competitor name).
    """
    if not cross_aggregated_data:
        return SOVResult(brand_sov=0.0, competitor_sov={}, total_mentions_analyzed=0)

    result = cross_aggregated_data.get("result") or {}
    items = result.get("items") or []
    if not items:
        return SOVResult(brand_sov=0.0, competitor_sov={}, total_mentions_analyzed=0)

    # Build key → mention count mapping
    key_counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = (item.get("key") or "").lower()
        if key:
            key_counts[key] = _extract_mentions_from_item(item)

    # Calculate totals
    brand_key = brand_domain.lower()
    brand_count = key_counts.get(brand_key, 0)

    total = brand_count
    for comp in competitor_domains:
        comp_key = comp.lower()
        total += key_counts.get(comp_key, 0)

    if total == 0:
        return SOVResult(brand_sov=0.0, competitor_sov={}, total_mentions_analyzed=0)

    brand_sov = min(brand_count / total, 1.0)

    competitor_sov: dict[str, float] = {}
    for comp in competitor_domains:
        comp_key = comp.lower()
        comp_count = key_counts.get(comp_key, 0)
        if comp_count > 0:
            competitor_sov[comp] = comp_count / total

    return SOVResult(
        brand_sov=brand_sov,
        competitor_sov=competitor_sov,
        total_mentions_analyzed=total,
    )
