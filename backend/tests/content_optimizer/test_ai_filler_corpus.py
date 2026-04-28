"""Tests for the AI filler corpus is_ai_filler() / get_filler_category() helpers.

Background: a substring-containment bug ('term_lower in phrase') in the
formulaic-phrase loop caused short single-word candidates that happen to be
substrings of any formulaic phrase to be flagged as filler. Real production
audits surfaced 'bot' (substring of 'the bottom line is'), 'day' (substring
of 'at the end of the day' / 'in today's digital'), and 'digital' (substring
of 'in today's digital') as Filler-tab terms — wrong recommendations to
remove these from client pages.

Fix: drop the reverse-direction substring check. Single-word candidates
now fall through to the structural rules; multi-word candidates only
match when a formulaic phrase is genuinely embedded in them.

These test cases were locked in the polish-sweep findings doc 2026-04-27.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from content_optimizer.ai_filler_corpus import is_ai_filler, get_filler_category


# ── Single-word false positives that the bug used to trigger ─────────────

def test_bot_is_not_filler():
    """'bot' was matching because 'bot' ⊂ 'the bottom line is' (substring of
    'bottom'). Real audit on a Webflow agency surfaced 'bot' as a Filler tab
    term — wrong on a site whose product name involves bots."""
    assert is_ai_filler("bot") is False


def test_robot_is_not_filler():
    """'robot' substring-matches 'the bottom line is' the same way."""
    assert is_ai_filler("robot") is False


def test_bottom_is_not_filler():
    """Single word, not in any single-word filler set."""
    assert is_ai_filler("bottom") is False


def test_day_is_not_filler():
    """'day' was matching 'at the end of the day' (whole phrase) and
    'in today's digital' (substring of 'today's'). For an event-management
    or scheduling site, 'day' is a legitimate brand term."""
    assert is_ai_filler("day") is False


def test_today_is_not_filler():
    """'today' substring-matches 'in today's digital' / 'in today's
    fast-paced'. Legitimate term for current-events content."""
    assert is_ai_filler("today") is False


def test_friday_is_not_filler():
    """Day of week — must not match 'at the end of the day' substring."""
    assert is_ai_filler("Friday") is False


def test_digital_is_not_filler():
    """'digital' substring-matches 'in today's digital' (whole phrase ending).
    For a digital agency audit, flagging 'digital' as filler would recommend
    removing the central brand term — exactly the kind of bug a 15-year SEO
    veteran spots in 5 minutes."""
    assert is_ai_filler("digital") is False


# ── Full formulaic phrases must still match ──────────────────────────────

def test_full_formulaic_phrase_is_filler():
    assert is_ai_filler("the bottom line is") is True


def test_at_end_of_day_phrase_is_filler():
    assert is_ai_filler("at the end of the day") is True


def test_in_todays_digital_phrase_is_filler():
    assert is_ai_filler("in today's digital") is True


def test_embedded_formulaic_phrase_in_longer_term_is_filler():
    """When a candidate term embeds a full formulaic phrase as a substring,
    it's still filler. Direction preserved: phrase ⊂ candidate."""
    assert is_ai_filler("learn the bottom line is here") is True
    assert is_ai_filler("it's important to note this") is True


# ── Structural rules still work for multi-word candidates ────────────────

def test_multiword_with_trailing_filler_noun_is_filler():
    """'digital landscape' — 'landscape' is in FILLER_NOUNS, structural rule
    fires regardless of phrase matching."""
    assert is_ai_filler("digital landscape") is True


def test_multiword_with_leading_inflated_adjective_is_filler():
    """'robust solution' — 'robust' is in INFLATED_ADJECTIVES."""
    assert is_ai_filler("robust solution") is True


def test_multiword_with_leading_abstract_verb_is_filler():
    """'leverage brand' — 'leverage' is in ABSTRACT_VERBS."""
    assert is_ai_filler("leverage brand") is True


# ── Single-word filler sets still match ──────────────────────────────────

def test_known_single_word_inflated_adjective_is_filler():
    assert is_ai_filler("robust") is True
    assert is_ai_filler("seamless") is True
    assert is_ai_filler("comprehensive") is True


def test_known_single_word_abstract_verb_is_filler():
    assert is_ai_filler("leverage") is True
    assert is_ai_filler("delve") is True


def test_known_single_word_filler_noun_is_filler():
    assert is_ai_filler("landscape") is True
    assert is_ai_filler("synergy") is True


# ── get_filler_category mirrors is_ai_filler's classification ────────────

def test_get_filler_category_for_short_word_is_generic_not_formulaic():
    """Before the fix, short words returned 'formulaic_phrase' category
    via the same buggy substring check. After the fix, they fall through
    to 'generic_filler' (the safe default for terms that don't match any
    rule)."""
    assert get_filler_category("bot") == "generic_filler"
    assert get_filler_category("day") == "generic_filler"
    assert get_filler_category("digital") == "generic_filler"


def test_get_filler_category_for_full_phrase_is_formulaic():
    assert get_filler_category("the bottom line is") == "formulaic_phrase"


def test_get_filler_category_for_filler_noun_word_is_filler_noun():
    assert get_filler_category("landscape") == "filler_noun"
