"""
Content profile auditor.
Sprint 4D: Two-layer content intelligence combining deterministic analysis
with Google NLP entity intelligence.

Deterministic layer (no API):
- Reading level (Flesch-Kincaid)
- Vocabulary type analysis
- Funnel stage detection

Google NLP layer (v1 API):
- Entity analysis with salience scores
- Entity focus alignment (H1/title vs. primary entity)
- Site entity map
- Brand/competitor sentiment (selective, key pages only)

Two-layer intelligence:
- TF-IDF reveals vocabulary gaps (which terms competitors use)
- Entity analysis reveals semantic gaps (which concepts Google associates)
- Cross-reference: TF-IDF gaps that are also Google entities = highest priority
"""
import logging
import re
import math
from collections import Counter
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# ── Readability (Flesch-Kincaid) ──────────────────────────────────


def _count_syllables(word: str) -> int:
    """Count syllables in a word using a simple heuristic."""
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    # Remove trailing silent 'e'
    if word.endswith("e"):
        word = word[:-1]
    count = len(re.findall(r"[aeiouy]+", word))
    return max(count, 1)


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    sentences = re.split(r"[.!?]+", text)
    return [s.strip() for s in sentences if s.strip() and len(s.split()) >= 3]


def _split_words(text: str) -> List[str]:
    """Split text into words."""
    return [w for w in re.findall(r"[a-zA-Z]+", text) if len(w) > 1]


def compute_flesch_kincaid(text: str) -> Dict[str, Any]:
    """Compute Flesch-Kincaid readability metrics.

    Returns:
        Dict with grade_level, reading_ease, and interpretation.
    """
    words = _split_words(text)
    sentences = _split_sentences(text)

    if not words or not sentences:
        return {"grade_level": None, "reading_ease": None, "interpretation": "Insufficient text"}

    total_words = len(words)
    total_sentences = len(sentences)
    total_syllables = sum(_count_syllables(w) for w in words)

    # Flesch-Kincaid Grade Level
    grade_level = (
        0.39 * (total_words / total_sentences)
        + 11.8 * (total_syllables / total_words)
        - 15.59
    )

    # Flesch Reading Ease
    reading_ease = (
        206.835
        - 1.015 * (total_words / total_sentences)
        - 84.6 * (total_syllables / total_words)
    )

    grade_level = max(0, round(grade_level, 1))
    reading_ease = max(0, min(100, round(reading_ease, 1)))

    if reading_ease >= 80:
        interpretation = "Easy to read (Grade 6)"
    elif reading_ease >= 60:
        interpretation = "Standard (Grade 7-8)"
    elif reading_ease >= 40:
        interpretation = "Somewhat difficult (Grade 9-12)"
    elif reading_ease >= 20:
        interpretation = "Difficult (College level)"
    else:
        interpretation = "Very difficult (Graduate level)"

    return {
        "grade_level": grade_level,
        "reading_ease": reading_ease,
        "total_words": total_words,
        "total_sentences": total_sentences,
        "avg_words_per_sentence": round(total_words / total_sentences, 1),
        "avg_syllables_per_word": round(total_syllables / total_words, 2),
        "interpretation": interpretation,
    }


# ── Vocabulary Type Analysis ──────────────────────────────────────


POWER_WORDS = {
    "free", "new", "proven", "guaranteed", "exclusive", "limited", "instant",
    "premium", "breakthrough", "revolutionary", "ultimate", "essential",
    "powerful", "secret", "advanced", "professional", "expert",
}

CTA_WORDS = {
    "buy", "subscribe", "download", "register", "sign up", "get started",
    "try", "learn more", "discover", "explore", "join", "request",
    "contact", "call", "schedule", "book", "order", "start",
}

TECHNICAL_WORDS = {
    "algorithm", "api", "architecture", "bandwidth", "cache", "compiler",
    "database", "deployment", "encryption", "framework", "infrastructure",
    "integration", "latency", "middleware", "optimization", "protocol",
    "repository", "scalability", "throughput", "virtualization",
}


def analyze_vocabulary(text: str) -> Dict[str, Any]:
    """Analyze vocabulary composition and characteristics."""
    words = _split_words(text)
    if not words:
        return {"power_word_count": 0, "cta_count": 0, "technical_count": 0,
                "unique_word_ratio": 0.0, "avg_word_length": 0.0}

    lower_words = [w.lower() for w in words]
    word_set = set(lower_words)

    power_count = len(word_set & POWER_WORDS)
    cta_count = len(word_set & CTA_WORDS)
    technical_count = len(word_set & TECHNICAL_WORDS)

    unique_ratio = len(word_set) / len(lower_words)
    avg_length = sum(len(w) for w in words) / len(words)

    return {
        "power_word_count": power_count,
        "cta_count": cta_count,
        "technical_count": technical_count,
        "unique_word_ratio": round(unique_ratio, 3),
        "avg_word_length": round(avg_length, 2),
        "total_unique_words": len(word_set),
    }


# ── Funnel Stage Detection ───────────────────────────────────────


TOFU_SIGNALS = {
    "what is", "how to", "guide", "tutorial", "introduction", "beginner",
    "overview", "learn", "understand", "basics", "101", "explained",
    "tips", "best practices", "examples", "definition",
}

MOFU_SIGNALS = {
    "comparison", "vs", "versus", "review", "alternative", "best",
    "top", "features", "benefits", "case study", "whitepaper",
    "template", "checklist", "webinar", "demo", "solution",
}

BOFU_SIGNALS = {
    "pricing", "buy", "purchase", "discount", "free trial", "get started",
    "sign up", "request demo", "contact sales", "quote", "order",
    "subscribe", "plan", "package", "coupon", "deal",
}


def detect_funnel_stage(text: str, url: str = "") -> Dict[str, Any]:
    """Detect the marketing funnel stage of a page.

    Returns:
        Dict with stage (tofu/mofu/bofu), confidence, and signal counts.
    """
    lower_text = text.lower()
    lower_url = url.lower()

    tofu_count = sum(1 for s in TOFU_SIGNALS if s in lower_text or s in lower_url)
    mofu_count = sum(1 for s in MOFU_SIGNALS if s in lower_text or s in lower_url)
    bofu_count = sum(1 for s in BOFU_SIGNALS if s in lower_text or s in lower_url)

    total = tofu_count + mofu_count + bofu_count
    if total == 0:
        return {"stage": "unknown", "confidence": 0.0,
                "tofu_signals": 0, "mofu_signals": 0, "bofu_signals": 0}

    scores = {"tofu": tofu_count, "mofu": mofu_count, "bofu": bofu_count}
    stage = max(scores, key=scores.get)  # type: ignore[arg-type]
    confidence = scores[stage] / total

    return {
        "stage": stage,
        "confidence": round(confidence, 3),
        "tofu_signals": tofu_count,
        "mofu_signals": mofu_count,
        "bofu_signals": bofu_count,
    }


# ── Content Profile (Full Page Analysis) ─────────────────────────


@dataclass
class ContentProfile:
    url: str
    readability: Dict[str, Any]
    vocabulary: Dict[str, Any]
    funnel_stage: Dict[str, Any]
    # NLP entity data (populated by Sprint 4D NLP pipeline)
    primary_entity: str | None = None
    primary_entity_salience: float | None = None
    entity_focus_aligned: bool | None = None
    top_entities: List[Dict[str, Any]] = field(default_factory=list)
    # Sentiment (populated for key pages only)
    sentiment_score: float | None = None
    sentiment_magnitude: float | None = None
    entity_sentiments: List[Dict[str, Any]] = field(default_factory=list)
    # Findings
    findings: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_content_profile(
    url: str,
    clean_text: str,
    h1_text: str | None = None,
    title: str | None = None,
) -> ContentProfile:
    """Build deterministic content profile for a single page.

    NLP entity data is added separately by the NLP pipeline.

    Args:
        url: Page URL.
        clean_text: Trafilatura-extracted clean text.
        h1_text: Page H1 text (for entity focus alignment).
        title: Page title text.

    Returns:
        ContentProfile with readability, vocabulary, and funnel stage.
    """
    readability = compute_flesch_kincaid(clean_text)
    vocabulary = analyze_vocabulary(clean_text)
    funnel = detect_funnel_stage(clean_text, url)

    findings: List[Dict[str, Any]] = []

    # Readability findings
    grade = readability.get("grade_level")
    if grade is not None:
        if grade > 12:
            findings.append({
                "severity": "high",
                "description": (
                    f"Content reading level is Grade {grade} — too complex for most web audiences."
                ),
                "recommendation": (
                    "Simplify language to Grade 6-8 level. Use shorter sentences, "
                    "simpler vocabulary, and break up complex paragraphs."
                ),
                "reference": "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
                "why_it_matters": (
                    "Readable text at Flesch-Kincaid Grade 6-8 earns 15% more AI citations "
                    "(SE Ranking, 2025). Google's Helpful Content system favors accessible writing."
                ),
            })
        elif grade > 10:
            findings.append({
                "severity": "medium",
                "description": (
                    f"Content reading level is Grade {grade} — above optimal range."
                ),
                "recommendation": "Aim for Grade 6-8 reading level for maximum accessibility.",
                "reference": "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
            })

    # Word count findings
    word_count = readability.get("total_words", 0)
    if word_count < 300:
        findings.append({
            "severity": "medium",
            "description": (
                f"Thin content — only {word_count} words on this page."
            ),
            "recommendation": (
                "Pages with under 300 words often lack the depth needed to rank. "
                "Expand content to cover the topic comprehensively."
            ),
            "reference": "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
            "why_it_matters": (
                "Average word count of top-10 Google results is 1,447 words (Backlinko, 2023)."
            ),
        })

    return ContentProfile(
        url=url,
        readability=readability,
        vocabulary=vocabulary,
        funnel_stage=funnel,
        findings=findings,
    )


def enrich_profile_with_entities(
    profile: ContentProfile,
    entity_analysis: Any,
    h1_text: str | None = None,
    title: str | None = None,
) -> ContentProfile:
    """Enrich a content profile with NLP entity analysis results.

    Args:
        profile: Existing deterministic profile.
        entity_analysis: PageEntityAnalysis from google_nlp_client.
        h1_text: Page H1 for focus alignment check.
        title: Page title for focus alignment check.

    Returns:
        ContentProfile with NLP data populated.
    """
    if not entity_analysis:
        return profile

    profile.primary_entity = entity_analysis.primary_entity
    profile.primary_entity_salience = entity_analysis.primary_entity_salience
    profile.entity_focus_aligned = entity_analysis.entity_focus_aligned
    profile.top_entities = [e.to_dict() for e in entity_analysis.entities[:10]]

    if entity_analysis.sentiment:
        profile.sentiment_score = entity_analysis.sentiment.score
        profile.sentiment_magnitude = entity_analysis.sentiment.magnitude

    if entity_analysis.entity_sentiments:
        profile.entity_sentiments = [e.to_dict() for e in entity_analysis.entity_sentiments[:10]]

    # Entity focus alignment findings
    if entity_analysis.entity_focus_aligned is False and entity_analysis.primary_entity:
        intent_text = h1_text or title or ""
        profile.findings.append({
            "severity": "high",
            "description": (
                f"Entity focus misalignment: Google sees this page as being about "
                f"'{entity_analysis.primary_entity}' (salience {entity_analysis.primary_entity_salience:.2f}) "
                f"but your H1 says '{intent_text}'."
            ),
            "recommendation": (
                f"Align your content so that '{intent_text.split()[0] if intent_text else 'your topic'}' "
                f"is the dominant entity. Increase mentions and context around your intended topic, "
                f"or update the H1 to match what the page actually covers."
            ),
            "reference": "https://developers.google.com/search/docs/appearance/title-link",
            "why_it_matters": (
                "When Google's entity analysis disagrees with your page title, "
                "it signals topic confusion. Pages with aligned entity focus rank "
                "2.3 positions higher (Surfer SEO, 2024)."
            ),
        })

    return profile


def compute_two_layer_recommendations(
    tfidf_gaps: List[Any],
    entity_map: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Cross-reference TF-IDF gap terms with NLP entity map.

    Terms that appear in BOTH TF-IDF gaps AND as Google NLP entities
    are the highest priority content recommendations.

    Args:
        tfidf_gaps: TermGap objects from WDF*IDF analysis.
        entity_map: Site entity map from build_site_entity_map().

    Returns:
        Prioritized list of content recommendations.
    """
    entity_names = {e["entity"].lower() for e in entity_map}

    high_priority: List[Dict[str, Any]] = []
    medium_priority: List[Dict[str, Any]] = []

    for gap in tfidf_gaps:
        term = gap.term if isinstance(gap, str) else getattr(gap, "term", str(gap))
        term_lower = term.lower()

        # Check if this gap term is also a Google NLP entity
        is_entity = term_lower in entity_names or any(
            term_lower in ename for ename in entity_names
        )

        entry = {
            "term": term,
            "source": "tfidf+entity" if is_entity else "tfidf",
            "competitor_score": getattr(gap, "competitor_score", 0),
            "competitor_frequency": getattr(gap, "competitor_frequency", 0),
            "is_google_entity": is_entity,
        }

        if is_entity:
            high_priority.append(entry)
        else:
            medium_priority.append(entry)

    return high_priority + medium_priority
