"""Share of Voice calculation from LLM Mentions cross_aggregated data."""
from typing import Any

from .schema import SOVResult


def calculate_sov(
    cross_aggregated_data: dict[str, Any] | None,
    brand_domain: str,
    competitor_domains: list[str],
) -> SOVResult:
    """Compute Share of Voice from the cross_aggregated_metrics endpoint.

    SOV = brand_mentions / total_mentions across brand + competitors.
    Exclusively uses mentions_database data (never live_test).
    """
    if not cross_aggregated_data:
        return SOVResult(brand_sov=0.0, competitor_sov={}, total_mentions_analyzed=0)

    items = cross_aggregated_data.get("items") or []
    if not items:
        return SOVResult(brand_sov=0.0, competitor_sov={}, total_mentions_analyzed=0)

    # Build domain → count mapping
    domain_counts: dict[str, int] = {}
    for item in items:
        keyword = (item.get("keyword") or "").lower()
        count = item.get("count", 0) or 0
        if keyword:
            domain_counts[keyword] = domain_counts.get(keyword, 0) + count

    # Calculate totals
    brand_key = brand_domain.lower()
    brand_count = domain_counts.get(brand_key, 0)

    total = brand_count
    competitor_sov: dict[str, float] = {}
    for comp in competitor_domains:
        comp_key = comp.lower()
        comp_count = domain_counts.get(comp_key, 0)
        total += comp_count

    if total == 0:
        return SOVResult(brand_sov=0.0, competitor_sov={}, total_mentions_analyzed=0)

    brand_sov = min(brand_count / total, 1.0)

    for comp in competitor_domains:
        comp_key = comp.lower()
        comp_count = domain_counts.get(comp_key, 0)
        if comp_count > 0:
            competitor_sov[comp] = comp_count / total

    return SOVResult(
        brand_sov=brand_sov,
        competitor_sov=competitor_sov,
        total_mentions_analyzed=total,
    )
