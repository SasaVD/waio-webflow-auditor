"""
AI Filler Phrase Corpus v1.0
Curated from empirical research on LLM-generated text patterns.
Organized by category for classification and reporting.
"""

# Category: ABSTRACT_VERB -- vague action words AI overuses
ABSTRACT_VERBS = {
    "delve", "leverage", "utilize", "harness", "streamline", "underscore",
    "navigate", "foster", "bolster", "spearhead", "empower", "catalyze",
    "synergize", "optimize", "facilitate", "encompass", "revolutionize",
    "supercharge", "turbocharge", "elevate", "amplify",
}

# Category: INFLATED_ADJECTIVE -- unnecessarily dramatic modifiers
INFLATED_ADJECTIVES = {
    "pivotal", "robust", "innovative", "seamless", "cutting-edge",
    "comprehensive", "multifaceted", "holistic", "groundbreaking",
    "game-changing", "transformative", "unparalleled", "state-of-the-art",
    "top-notch", "best-in-class", "world-class", "bespoke",
    "ever-evolving", "dynamic", "nuanced",
}

# Category: FILLER_NOUN -- abstract nouns with no concrete meaning
FILLER_NOUNS = {
    "landscape", "realm", "tapestry", "synergy", "testament", "underpinnings",
    "journey", "paradigm", "ecosystem", "bedrock", "cornerstone",
    "linchpin", "catalyst", "nexus", "blueprint",
}

# Category: FORMULAIC_PHRASE -- multi-word patterns
FORMULAIC_PHRASES = [
    "it's important to note",
    "it's worth noting",
    "in today's digital",
    "in today's fast-paced",
    "in today's competitive",
    "in an era of",
    "at the end of the day",
    "the bottom line is",
    "embark on a journey",
    "a testament to",
    "serves as a reminder",
    "it goes without saying",
    "needless to say",
    "plays a crucial role",
    "plays a pivotal role",
    "at its core",
    "when it comes to",
    "in the realm of",
    "stands out as",
    "takes center stage",
    "is no exception",
    "look no further",
    "without further ado",
    "the world of",
    "dive into",
    "deep dive",
    "let's explore",
    "in conclusion",
    "to sum up",
    "in summary",
    "as we move forward",
    "moving forward",
]

# Compile all single-word fillers
ALL_SINGLE_WORD_FILLERS = ABSTRACT_VERBS | INFLATED_ADJECTIVES | FILLER_NOUNS

# Category lookup for reporting
_CATEGORY_MAP: dict[str, str] = {}
for _word in ABSTRACT_VERBS:
    _CATEGORY_MAP[_word] = "abstract_verb"
for _word in INFLATED_ADJECTIVES:
    _CATEGORY_MAP[_word] = "inflated_adjective"
for _word in FILLER_NOUNS:
    _CATEGORY_MAP[_word] = "filler_noun"


def is_ai_filler(term: str) -> bool:
    """Check if a term is an AI filler word or phrase.

    Handles the fact that the WDF*IDF tokenizer strips hyphens, so
    "game-changing" arrives here as "game changing".  We re-hyphenate
    and check both forms.
    """
    term_lower = term.lower().strip()

    # Direct single-word match
    if term_lower in ALL_SINGLE_WORD_FILLERS:
        return True

    # Re-hyphenated form (tokenizer converts "game-changing" → "game changing")
    if " " in term_lower:
        hyphenated = term_lower.replace(" ", "-")
        if hyphenated in ALL_SINGLE_WORD_FILLERS:
            return True

    # Formulaic phrase match
    for phrase in FORMULAIC_PHRASES:
        if phrase in term_lower or term_lower in phrase:
            return True

    # Multi-word structural checks
    words = term_lower.split()
    if len(words) >= 2:
        # Trailing filler noun: "digital landscape", "innovation tapestry"
        if words[-1] in FILLER_NOUNS:
            return True
        # Leading inflated adjective: "robust solution", "bespoke design"
        if words[0] in INFLATED_ADJECTIVES:
            return True
        # Leading abstract verb: "leverage brand", "harness technology"
        if words[0] in ABSTRACT_VERBS:
            return True

    return False


def get_filler_category(term: str) -> str:
    """Return the filler category for a term."""
    term_lower = term.lower().strip()
    if term_lower in _CATEGORY_MAP:
        return _CATEGORY_MAP[term_lower]
    # Re-hyphenated form
    if " " in term_lower:
        hyphenated = term_lower.replace(" ", "-")
        if hyphenated in _CATEGORY_MAP:
            return _CATEGORY_MAP[hyphenated]
    for phrase in FORMULAIC_PHRASES:
        if phrase in term_lower or term_lower in phrase:
            return "formulaic_phrase"
    words = term_lower.split()
    if len(words) >= 2:
        if words[-1] in FILLER_NOUNS:
            return "filler_noun"
        if words[0] in INFLATED_ADJECTIVES:
            return "inflated_adjective"
        if words[0] in ABSTRACT_VERBS:
            return "abstract_verb"
    return "generic_filler"
