"""Tests for _filter_entities covering edge cases + Belt Creative regressions."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pdf_export_generator as pdf_mod


def test_filter_drops_low_salience_other_entities():
    """OTHER entities with salience < 0.10 must be dropped in default pass."""
    raw = [
        {"name": "Belt Creative", "type": "ORGANIZATION", "salience": 0.45, "mentions_count": 12},
        {"name": "Projects", "type": "OTHER", "salience": 0.069, "mentions_count": 3},
        {"name": "word", "type": "OTHER", "salience": 0.052, "mentions_count": 2},
        {"name": "web experiences", "type": "OTHER", "salience": 0.051, "mentions_count": 1},
        {"name": "HubSpot", "type": "ORGANIZATION", "salience": 0.15, "mentions_count": 8},
        {"name": "Miami", "type": "LOCATION", "salience": 0.08, "mentions_count": 4},
        {"name": "New York", "type": "LOCATION", "salience": 0.12, "mentions_count": 6},
    ]
    out = pdf_mod._filter_entities(raw)
    names = {e["name"] for e in out}
    # Kept: high-salience regardless of type
    assert "Belt Creative" in names
    assert "HubSpot" in names
    assert "New York" in names
    assert "Miami" in names  # LOCATION ≥ 0.04 is kept
    # Dropped: OTHER entries below 0.10
    assert "Projects" not in names
    assert "word" not in names
    assert "web experiences" not in names


def test_filter_handles_lowercase_type():
    """Type field may be 'Other' or 'other' — filter should normalize."""
    raw = [
        {"name": "Belt Creative", "type": "ORGANIZATION", "salience": 0.45, "mentions_count": 12},
        {"name": "X", "type": "other", "salience": 0.08, "mentions_count": 2},
        {"name": "Y", "type": "Other", "salience": 0.06, "mentions_count": 2},
    ]
    out = pdf_mod._filter_entities(raw)
    names = {e["name"] for e in out}
    assert "X" not in names
    assert "Y" not in names


def test_filter_handles_missing_type_as_other():
    """Entity with no type field must be treated as OTHER (strict threshold)."""
    raw = [
        {"name": "Belt Creative", "type": "ORGANIZATION", "salience": 0.45, "mentions_count": 12},
        {"name": "Mystery", "salience": 0.06, "mentions_count": 2},  # no type
        {"name": "SolidEntity", "type": "ORGANIZATION", "salience": 0.20, "mentions_count": 8},
    ]
    out = pdf_mod._filter_entities(raw)
    names = {e["name"] for e in out}
    assert "Mystery" not in names
    assert "Belt Creative" in names
    assert "SolidEntity" in names


def test_filter_caps_at_ten():
    """Filter must return at most 10 entities."""
    raw = [
        {"name": f"Brand-{i}", "type": "ORGANIZATION", "salience": 0.5 - i * 0.01, "mentions_count": 20 - i}
        for i in range(20)
    ]
    out = pdf_mod._filter_entities(raw)
    assert len(out) == 10


def test_filter_relaxes_threshold_when_less_than_five_survive():
    """Relax pass: if default yields < 5, drop to 0.02 salience for non-OTHER
    but keep OTHER at 0.10 minimum."""
    raw = [
        {"name": "A", "type": "ORGANIZATION", "salience": 0.03, "mentions_count": 1},
        {"name": "B", "type": "PERSON", "salience": 0.025, "mentions_count": 1},
        {"name": "C", "type": "LOCATION", "salience": 0.022, "mentions_count": 1},
        {"name": "D", "type": "EVENT", "salience": 0.028, "mentions_count": 1},
        {"name": "TrashOther", "type": "OTHER", "salience": 0.05, "mentions_count": 1},
    ]
    out = pdf_mod._filter_entities(raw)
    names = {e["name"] for e in out}
    assert "A" in names and "B" in names and "C" in names and "D" in names
    # OTHER still requires ≥0.10 even in relaxed mode
    assert "TrashOther" not in names


def test_filter_humanizes_type_labels():
    """type strings must be humanized in output."""
    raw = [
        {"name": "Belt Creative", "type": "ORGANIZATION", "salience": 0.45, "mentions_count": 12},
        {"name": "Apple", "type": "CONSUMER_GOOD", "salience": 0.20, "mentions_count": 5},
        {"name": "Campaign", "type": "EVENT", "salience": 0.18, "mentions_count": 4},
    ]
    out = pdf_mod._filter_entities(raw)
    by_name = {e["name"]: e for e in out}
    assert by_name["Belt Creative"]["type"] == "Organization"
    # Per user spec CONSUMER_GOOD => "Product"
    assert by_name["Apple"]["type"] == "Product"
    assert by_name["Campaign"]["type"] == "Event"
