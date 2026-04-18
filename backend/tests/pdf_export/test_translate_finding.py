"""Tests for finding translation coverage used by Priority Actions."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pdf_export_generator as pdf_mod
from executive_summary_generator import _translate_finding


def test_translate_link_name_rule():
    """link-name must translate to a plain-English sentence."""
    raw = "Axe rule 'link-name': Links must have discernible text"
    translated = _translate_finding(raw, "accessibility")
    assert translated
    assert "Axe rule" not in translated
    assert "link-name" not in translated
    # A human-readable sentence about link text / screen readers
    assert "link" in translated.lower()


def test_translate_color_contrast_still_works():
    """Regression: existing rules must still translate."""
    raw = "Axe rule 'color-contrast': ..."
    translated = _translate_finding(raw, "accessibility")
    assert "color contrast" in translated.lower()


def test_humanize_strips_axe_prefix_when_no_translation():
    """For unknown Axe rules, _humanize_finding_description strips prefix."""
    raw = "Axe rule 'unknown-rule-xyz': some raw description here"
    result = pdf_mod._humanize_finding_description(raw, "accessibility")
    assert "Axe rule" not in result
    assert "unknown-rule-xyz" not in result
    assert "some raw description" in result


def test_humanize_passes_known_rule_to_translator():
    """Known rules: _humanize returns the translator output, not raw text."""
    raw = "Axe rule 'link-name': Links must have discernible text"
    result = pdf_mod._humanize_finding_description(raw, "accessibility")
    assert "Axe rule" not in result
    assert "link-name" not in result
