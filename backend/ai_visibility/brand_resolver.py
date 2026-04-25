"""Resolve brand name from NLP entities or user override.

Workstream D2 (2026-04-24) hardens the override path with a 3-layer
validation pipeline. Motivating incident: sched.com 2026-04-23, where the
user typed ``"Event Management Software"`` (a category phrase, not a
brand) into the override field and AI Visibility happily counted every
category mention in any prompt response as a brand mention. New layered
priority for the override path:

    Layer 1 — KG MID primary
        Run Google NLP ``analyzeEntities`` on the brand override string.
        If any returned entity has a Knowledge Graph MID or a Wikipedia
        URL, the override is a real proper-noun brand → ``source="kg_mid"``.

    Layer 2 — Category-leaf rejection
        Still while NLP is available: detect when the override looks like
        a generic category leaf (e.g. "Event Management Software", "Web
        Design Services"). When the NLP response shows no proper-noun
        signal AND the surface form matches a category-suffix heuristic,
        raise ``BrandExtractionError``. Caller writes
        ``last_computed_status="needs_brand_confirmation"`` to the report
        and prompts the user to refine the brand string.

    Layer 3 — Curated list
        Lowercased exact-match lookup against
        ``ai_visibility/curated_brands.py``. Used for legitimate brands
        that don't have a strong KG presence (e.g. "Veza Digital").
        ``source="curated_list"``.

    Layer 4 — Unverified fallback
        Override accepted as-is. ``source="override_unverified"``. UI
        shows an advisory because we couldn't confirm the string is a
        real brand. This is the lowest-confidence path but it preserves
        the prior "always honor user input" behavior for cases where
        Google NLP isn't configured (``GOOGLE_API_KEY`` unset) or all
        upstream checks misfire.

When ``nlp_client`` is ``None`` (no NLP available) or its
``analyze_entities`` call raises, layers 1-2 are skipped — we go straight
to layer 3 → layer 4. We never raise ``BrandExtractionError`` from the
absence of NLP — silent fallback to "override_unverified" is the correct
graceful degradation. (Logging once at INFO so on-call can see the
degraded path was taken.)

Implementation note on category-leaf detection: we picked the
``analyze_entities``-only path rather than a separate ``classify_text``
call because (a) classify_text requires ≥20 tokens and brand strings are
typically 1-5 words, so it would fail validation or be unreliable; (b)
one API call instead of two; (c) the absence of KG metadata on the
entity returned for a category phrase is already the strongest signal.
The category-suffix heuristic (``_looks_like_category_leaf``) closes the
loop — multi-word strings ending in generic category tokens (software,
services, platform, etc.) without any KG hit get rejected.
"""
import logging

from .schema import BrandInfo, BrandExtractionError
from .curated_brands import CURATED_BRANDS

logger = logging.getLogger(__name__)

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

# Generic suffix tokens that almost never appear as the last word of a real
# brand. Combined with "no KG hit" + "≥2 words" this is a strong category
# signal. Curated from Google's content-classification taxonomy leaves.
_CATEGORY_LEAF_SUFFIXES = frozenset({
    "software", "services", "service", "platform", "platforms",
    "solutions", "solution", "system", "systems", "tool", "tools",
    "application", "applications", "app", "apps",
    "management", "marketing", "agency", "agencies",
    "consulting", "consultancy", "consultants",
    "company", "companies", "firm", "firms",
    "provider", "providers",
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


def _entity_has_kg_metadata(entity: dict) -> tuple[str | None, str | None]:
    """Return (kg_mid, wikipedia_url) from an analyzeEntities entity dict.

    Tolerates both the dict-shape returned by google_nlp_client (where
    ``metadata`` is nested) and the slightly flattened shape that older
    sanitizer code emits.
    """
    metadata = entity.get("metadata") or {}
    mid = metadata.get("mid") or entity.get("knowledge_graph_mid")
    wiki = metadata.get("wikipedia_url") or entity.get("wikipedia_url")
    return (mid or None, wiki or None)


def _looks_like_category_leaf(brand: str) -> bool:
    """Heuristic: does this string look like a generic category phrase?

    Triggers when (a) it's ≥2 words AND (b) the last word is a known
    category suffix (software, services, platform, etc.). This catches
    strings like "Event Management Software", "Web Design Services",
    "Marketing Automation Platform" — the exact failure mode from the
    sched.com 2026-04-23 incident.

    Genuine brands occasionally end in these tokens (e.g. "Salesforce
    Marketing Cloud"), so this heuristic is only consulted AFTER KG MID
    lookup failed. A real brand with KG metadata always wins at Layer 1.
    """
    tokens = (brand or "").strip().lower().split()
    if len(tokens) < 2:
        return False
    return tokens[-1] in _CATEGORY_LEAF_SUFFIXES


def _validate_override_with_nlp(
    brand_override: str,
    nlp_client,
    *,
    force_category_match: bool = False,
) -> BrandInfo | None:
    """Run Layers 1-2 of the override validation pipeline.

    Returns:
        BrandInfo with source="kg_mid" if Layer 1 hits.
        None if Layer 1 misses (caller falls through to Layers 3-4).

    Raises:
        BrandExtractionError if Layer 2 (category-leaf rejection) hits.

    On any exception from ``nlp_client.analyze_entities`` (network,
    auth, quota), returns None — caller falls through gracefully.
    """
    try:
        entities = nlp_client.analyze_entities(brand_override) or []
    except Exception as e:
        logger.info(
            "KG validation unavailable — skipping to curated/unverified path "
            "(reason: %s)", e,
        )
        return None

    # Layer 1: any entity with KG MID or Wikipedia URL wins.
    for entity in entities:
        kg_mid, wiki = _entity_has_kg_metadata(entity)
        if kg_mid or wiki:
            # Prefer the entity's own canonical name when available; fall back
            # to the user's input if the entity has no name field.
            canonical = entity.get("name") or brand_override.strip()
            return BrandInfo(
                name=canonical,
                source="kg_mid",
                kg_mid=kg_mid,
                wikipedia_url=wiki,
            )

    # Layer 2: category-leaf rejection.
    # Conditions: (a) explicit test hook OR (b) heuristic match. A genuine
    # brand with KG metadata already returned at Layer 1, so by this point
    # we know NLP didn't recognize the string as a real entity.
    category_match = force_category_match or _looks_like_category_leaf(brand_override)
    if category_match:
        # Try to mention which category we matched. With analyze_entities-only
        # signals, we don't have a category path — the heuristic suffix is
        # the matched signal we report.
        suffix = brand_override.strip().split()[-1].lower() if brand_override.strip() else ""
        category_descriptor = f"category leaf '{suffix}'" if suffix else "category leaf"
        raise BrandExtractionError(
            f"'{brand_override}' is a category phrase, not a brand "
            f"(matched {category_descriptor}). AI Visibility results would be "
            f"dominated by generic category mentions, not real brand signals. "
            f"Please enter your actual brand or company name."
        )

    return None


def resolve_brand(
    brand_override: str | None,
    nlp_entities: list[dict] | None,
    *,
    nlp_client=None,
    curated_brands: dict[str, str] | None = None,
    _force_category_match: bool = False,
) -> BrandInfo:
    """Extract the brand name for AI Visibility analysis.

    Override path (Workstream D2):
        Layer 1 — KG MID via ``nlp_client.analyze_entities``
        Layer 2 — category-leaf rejection (raises BrandExtractionError)
        Layer 3 — curated brand whitelist (case-insensitive lookup)
        Layer 4 — unverified fallback (lowest confidence)

    NLP path (no override):
        Highest-salience ORGANIZATION entity above SALIENCE_THRESHOLD.
        Unchanged from pre-D2 behavior.

    Raises:
        BrandExtractionError if Layer 2 rejects the override OR if no
        override is given and the NLP path can't find a usable entity.

    The new keyword-only parameters are backwards-compatible — call sites
    that don't pass them get safe defaults (no NLP validation, default
    curated list, no test hook). The pre-D2 ``"override"`` source value
    is removed; every override path now picks one of:
    ``kg_mid | curated_list | override_unverified``.
    """
    if curated_brands is None:
        curated_brands = CURATED_BRANDS

    has_override = bool(brand_override and brand_override.strip())

    if has_override:
        override_str = brand_override.strip()  # type: ignore[union-attr]

        # Layers 1-2 (require nlp_client). On any failure, returns None and
        # we fall through. Raises BrandExtractionError on category-leaf hit.
        if nlp_client is not None:
            kg_result = _validate_override_with_nlp(
                override_str,
                nlp_client,
                force_category_match=_force_category_match,
            )
            if kg_result is not None:
                return kg_result

        # Layer 3: curated list (case-insensitive lookup).
        canonical = curated_brands.get(override_str.lower())
        if canonical:
            return BrandInfo(name=canonical, source="curated_list")

        # Layer 4: unverified fallback.
        return BrandInfo(name=override_str, source="override_unverified")

    # ── NLP path (no override) — unchanged from pre-D2 behavior ─────

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
