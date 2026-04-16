"""Resolve brand name from NLP entities or user override."""
from .schema import BrandInfo, BrandExtractionError

SALIENCE_THRESHOLD = 0.3


def resolve_brand(
    brand_override: str | None,
    nlp_entities: list[dict] | None,
) -> BrandInfo:
    """Extract the brand name for AI Visibility analysis.

    Priority:
    1. brand_override (from user confirmation modal or DB column)
    2. Highest-salience ORGANIZATION entity above threshold

    Raises BrandExtractionError if no brand can be resolved.
    """
    # Override always wins (if non-empty)
    if brand_override and brand_override.strip():
        return BrandInfo(name=brand_override.strip(), source="override")

    # Fall through to NLP extraction
    if not nlp_entities:
        raise BrandExtractionError(
            "No NLP entities available for brand extraction. "
            "Please enter a brand name manually."
        )

    # Filter to ORGANIZATION entities above salience threshold
    orgs = [
        e for e in nlp_entities
        if e.get("type") == "ORGANIZATION" and (e.get("salience", 0) or 0) >= SALIENCE_THRESHOLD
    ]

    if not orgs:
        raise BrandExtractionError(
            "No ORGANIZATION entities found with salience > 0.3. "
            "Please enter a brand name manually."
        )

    # Pick highest salience
    best = max(orgs, key=lambda e: e.get("salience", 0))
    return BrandInfo(
        name=best["name"],
        source="nlp",
        salience=best.get("salience"),
    )
