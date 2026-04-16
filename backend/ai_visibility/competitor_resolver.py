"""Resolve competitor domains via 3-tier fallback."""
from urllib.parse import urlparse
from typing import Any

from .schema import CompetitorSet


def normalize_domain(url_or_domain: str | None) -> str:
    """Extract bare domain from a URL or domain string.

    Examples:
        "https://www.webflow.com/about" → "webflow.com"
        "www.example.com" → "example.com"
        "squarespace.com" → "squarespace.com"
    """
    if not url_or_domain:
        return ""
    s = url_or_domain.strip()
    if not s:
        return ""

    # Add scheme if missing so urlparse works
    if "://" not in s:
        s = f"https://{s}"

    parsed = urlparse(s)
    host = parsed.hostname or ""
    # Strip www. prefix
    if host.startswith("www."):
        host = host[4:]
    return host


def resolve_competitors(
    competitor_urls: list[str] | None,
    competitive_data: dict[str, Any] | None,
    co_mention_domains: list[str] | None,
) -> CompetitorSet:
    """3-tier competitor fallback:

    Tier 1: competitor_urls from premium audit request (user-provided)
    Tier 2: competitive_auditor rankings from report
    Tier 3: co-mention domains from LLM Mentions API
    """
    # Tier 1: User-provided competitor URLs
    if competitor_urls:
        domains = _dedupe_domains([normalize_domain(u) for u in competitor_urls])
        if domains:
            return CompetitorSet(domains=domains, source="user_provided")

    # Tier 2: Competitive auditor results
    if competitive_data:
        rankings = competitive_data.get("rankings") or []
        if rankings:
            domains = _dedupe_domains([
                normalize_domain(r.get("url", "")) for r in rankings
            ])
            if domains:
                return CompetitorSet(domains=domains, source="competitive_auditor")

    # Tier 3: Co-mention domains from LLM Mentions
    if co_mention_domains:
        domains = _dedupe_domains([normalize_domain(d) for d in co_mention_domains])
        if domains:
            return CompetitorSet(domains=domains, source="co_mentions")

    return CompetitorSet(domains=[], source="none")


def _dedupe_domains(domains: list[str]) -> list[str]:
    """Deduplicate and filter empty strings, preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for d in domains:
        if d and d not in seen:
            seen.add(d)
            result.append(d)
    return result
