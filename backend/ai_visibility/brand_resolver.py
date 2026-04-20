"""Resolve brand name from NLP entities or user override."""
from .schema import BrandInfo, BrandExtractionError

SALIENCE_THRESHOLD = 0.3

AMBIGUITY_LENGTH_THRESHOLD = 3

# Lowercased tokens that collide with unrelated named entities in AI response
# corpora. Mostly name particles (Van Gogh, Ludwig van Beethoven, Mies van
# der Rohe) and generic English words that users sometimes paste instead of
# a real brand.
AMBIGUOUS_COMMON_WORDS = frozenset({
    # Name particles / articles that appear as standalone 4+ char words
    "your", "this", "that", "them", "they",
    # Generic nouns people paste when unsure what to type
    "home", "work", "team", "test", "demo", "site", "page", "data",
    "name", "user", "info", "main", "news", "brand", "company",
    "business", "website", "service", "product", "client", "customer",
})


def check_brand_ambiguity(brand: str) -> str | None:
    """Return an advisory warning if the brand token is likely to produce
    noisy results, or None if it looks safe.

    This is intentionally non-blocking: short acronyms (IBM, HP, NIO) and
    generic words can be legitimate brands, and exposing the collision is
    itself strategic signal — it tells the brand exactly how much their
    name blurs with unrelated entities in AI responses. The UI shows this
    warning and lets the user proceed anyway.
    """
    s = (brand or "").strip()
    if not s:
        return None  # empty input is handled separately by the caller
    if len(s) <= AMBIGUITY_LENGTH_THRESHOLD:
        return (
            f"'{s}' is a short token ({len(s)} character"
            f"{'s' if len(s) != 1 else ''}). Short acronyms often match "
            "unrelated entities in AI response corpora (e.g. 'VAN' matches "
            "Van Gogh, Beethoven, Van Halen). Results may include noise — "
            "this can itself reveal positioning conflicts worth addressing."
        )
    if s.lower() in AMBIGUOUS_COMMON_WORDS:
        return (
            f"'{s}' is a generic word that may collide with unrelated "
            "entities in AI response corpora. Results may include noise."
        )
    return None


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
