"""Tests for the Google NLP client text preparation (BUG-2).

These lock in the _prepare_text behavior that terminates unpunctuated
lines so Google NLP's PLAIN_TEXT tokenizer treats block boundaries as
sentence boundaries. Regressions here re-introduce the "Webflow
Webflow" stutter observed on shadowdigital.cc.
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google_nlp_client import _prepare_text  # noqa: E402


def test_prepare_text_terminates_unpunctuated_lines():
    """The exact shadowdigital.cc homepage pattern: heading followed
    by a paragraph whose first word repeats the heading's last token.
    After _prepare_text the heading must end with a period so Google
    NLP sees two sentences instead of merging 'Webflow Webflow' into
    one entity."""
    src = "About Webflow\nWebflow is a no-code development tool"
    expected = "About Webflow.\nWebflow is a no-code development tool."
    assert _prepare_text(src) == expected


def test_prepare_text_preserves_already_terminated_lines():
    """Lines that already end in terminal punctuation must pass
    through untouched. Covers '.' plus the other four terminators in
    the _TERMINAL regex ('!', '?', ':', ';')."""
    src = "Hello world.\nThis is fine."
    assert _prepare_text(src) == src

    # All five terminators the regex accepts
    for terminator in [".", "!", "?", ":", ";"]:
        line = f"A line{terminator}"
        assert _prepare_text(line) == line, (
            f"Line ending in {terminator!r} should be unchanged"
        )

    # Mixed content — some lines terminated, some not
    src_mixed = "Heading one\nSentence two.\nHeading three\nSentence four!"
    expected_mixed = "Heading one.\nSentence two.\nHeading three.\nSentence four!"
    assert _prepare_text(src_mixed) == expected_mixed


def test_prepare_text_handles_empty_lines_and_whitespace():
    """Blank and whitespace-only lines between content blocks must
    stay blank — we only add periods to lines that have content.
    Otherwise we'd inject '.' into empty paragraph breaks, which
    might confuse Google NLP's sentence segmenter more than it
    helps."""
    src = "Heading\n\n  \nParagraph"
    expected = "Heading.\n\n\nParagraph."
    assert _prepare_text(src) == expected

    # Trailing whitespace on content lines is also stripped before
    # the terminator is appended — no "Heading  ." artifacts.
    src_trailing = "Heading   \nParagraph"
    expected_trailing = "Heading.\nParagraph."
    assert _prepare_text(src_trailing) == expected_trailing
