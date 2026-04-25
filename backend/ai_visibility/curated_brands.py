"""Canonical brand list for ``resolve_brand``'s tertiary fallback layer.

When a brand override is given but Google NLP ``analyzeEntities`` returns no
Knowledge Graph metadata (no MID, no Wikipedia URL), we check this curated
map before falling back to ``"override_unverified"``. Lowercased-string keys
map to canonical-cased display names.

Extend as production produces false negatives. Strict allow-list — no
implicit substring matching, no fuzzy matching. Exact lowercase match only.
"""

CURATED_BRANDS: dict[str, str] = {
    "veza digital": "Veza Digital",
    # Add real-world brands as they surface in production audits where
    # KG MID lookup fails but the string is genuinely a known brand.
}
