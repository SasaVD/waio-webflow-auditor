"""Resolve brand name from NLP entities or user override."""
from .schema import BrandInfo, BrandExtractionError, BrandValidationError

SALIENCE_THRESHOLD = 0.3

MIN_BRAND_LENGTH = 4

# Lowercased tokens that collide with unrelated named entities in AI response
# corpora. Mostly name particles (Van Gogh, Ludwig van Beethoven, Mies van
# der Rohe) and generic English words that users sometimes paste instead of
# a real brand. Length check above catches <4 chars, so entries here are
# the >=4 char common words worth blocking explicitly.
AMBIGUOUS_COMMON_WORDS = frozenset({
    # Name particles / articles that appear as standalone 4+ char words
    "your", "this", "that", "them", "they",
    # Generic nouns people paste when unsure what to type
    "home", "work", "team", "test", "demo", "site", "page", "data",
    "name", "user", "info", "main", "news", "brand", "company",
    "business", "website", "service", "product", "client", "customer",
})


def validate_brand_name(brand: str) -> str:
    """Validate a user-supplied brand name before running AI Visibility.

    Returns the trimmed brand name on success.
    Raises BrandValidationError with a user-facing message on failure.
    """
    s = (brand or "").strip()
    if len(s) <= 3:
        raise BrandValidationError(
            f"Brand name '{s}' is too short ({len(s)} character"
            f"{'s' if len(s) != 1 else ''}). "
            "Use the full brand name (e.g. 'Veza Network' not 'VAN') — "
            "short acronyms match unrelated entities in AI response corpora "
            "(Van Gogh, Beethoven, etc.) and return junk data."
        )
    if s.lower() in AMBIGUOUS_COMMON_WORDS:
        raise BrandValidationError(
            f"'{s}' is a generic word that collides with unrelated entities "
            "in AI response corpora. Use the full brand name instead."
        )
    return s


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
