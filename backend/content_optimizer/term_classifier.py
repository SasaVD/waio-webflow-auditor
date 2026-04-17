"""Classify WDF*IDF terms into core/semantic/auxiliary/filler categories."""
from .schema import TermAnalysis, TermClassification
from .ai_filler_corpus import is_ai_filler, get_filler_category


def classify_terms(
    terms: list[TermAnalysis],
    target_keyword: str,
    top_entities: list[str] | None = None,
) -> list[TermAnalysis]:
    """Classify each term into one of 4 categories.

    - CORE: directly contains or is contained in the target keyword
    - SEMANTIC: semantically related (NLP entity, bigram overlap, high corpus presence)
    - AUXILIARY: relevant to topic but not directly keyword-related
    - FILLER: AI-generic phrases with no SEO value
    """
    keyword_tokens = set(target_keyword.lower().split())
    keyword_bigrams = _make_bigrams(target_keyword.lower())
    entity_set = set(e.lower() for e in (top_entities or []))

    for term in terms:
        term_lower = term.term.lower()
        term_tokens = set(term_lower.split())

        # Check 1: AI filler (highest priority)
        if is_ai_filler(term_lower):
            term.classification = TermClassification.FILLER
            term.filler_category = get_filler_category(term_lower)
            continue

        # Check 2: CORE -- term shares words with keyword
        if term_tokens & keyword_tokens:
            term.classification = TermClassification.CORE
            continue
        if term_lower in target_keyword.lower() or target_keyword.lower() in term_lower:
            term.classification = TermClassification.CORE
            continue

        # Check 3: SEMANTIC -- NLP entity, bigram overlap, or high corpus signal
        if term_lower in entity_set:
            term.classification = TermClassification.SEMANTIC
            continue
        term_bigrams = _make_bigrams(term_lower)
        if term_bigrams and keyword_bigrams and term_bigrams & keyword_bigrams:
            term.classification = TermClassification.SEMANTIC
            continue
        if term.idf > 1.0 and term.docs_containing >= 4 and term.competitor_avg_frequency >= 3:
            term.classification = TermClassification.SEMANTIC
            continue

        # Check 4: Default to AUXILIARY
        term.classification = TermClassification.AUXILIARY

    return terms


def _make_bigrams(text: str) -> set[tuple[str, str]]:
    tokens = text.split()
    return set(zip(tokens, tokens[1:])) if len(tokens) > 1 else set()
