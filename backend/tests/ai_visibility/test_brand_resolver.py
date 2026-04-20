"""Tests for AI Visibility brand resolver."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from ai_visibility.brand_resolver import resolve_brand, validate_brand_name
from ai_visibility.schema import BrandInfo, BrandExtractionError, BrandValidationError


def test_override_always_wins():
    nlp_entities = [
        {"name": "Belt Creative", "type": "ORGANIZATION", "salience": 0.82},
        {"name": "Webflow", "type": "ORGANIZATION", "salience": 0.45},
    ]
    result = resolve_brand(
        brand_override="Veza Digital",
        nlp_entities=nlp_entities,
    )
    assert result.name == "Veza Digital"
    assert result.source == "override"
    assert result.salience is None


def test_nlp_picks_highest_salience_org():
    nlp_entities = [
        {"name": "web design", "type": "OTHER", "salience": 0.90},
        {"name": "Belt Creative", "type": "ORGANIZATION", "salience": 0.72},
        {"name": "Webflow", "type": "ORGANIZATION", "salience": 0.45},
    ]
    result = resolve_brand(brand_override=None, nlp_entities=nlp_entities)
    assert result.name == "Belt Creative"
    assert result.source == "nlp"
    assert abs(result.salience - 0.72) < 0.001


def test_nlp_ignores_low_salience_orgs():
    nlp_entities = [
        {"name": "Belt Creative", "type": "ORGANIZATION", "salience": 0.20},
        {"name": "web design", "type": "OTHER", "salience": 0.90},
    ]
    with pytest.raises(BrandExtractionError):
        resolve_brand(brand_override=None, nlp_entities=nlp_entities)


def test_no_org_entities_raises():
    nlp_entities = [
        {"name": "web design", "type": "OTHER", "salience": 0.90},
        {"name": "SEO", "type": "CONSUMER_GOOD", "salience": 0.50},
    ]
    with pytest.raises(BrandExtractionError):
        resolve_brand(brand_override=None, nlp_entities=nlp_entities)


def test_empty_entities_raises():
    with pytest.raises(BrandExtractionError):
        resolve_brand(brand_override=None, nlp_entities=[])


def test_none_entities_raises():
    with pytest.raises(BrandExtractionError):
        resolve_brand(brand_override=None, nlp_entities=None)


def test_override_empty_string_falls_through_to_nlp():
    nlp_entities = [
        {"name": "Belt Creative", "type": "ORGANIZATION", "salience": 0.72},
    ]
    result = resolve_brand(brand_override="", nlp_entities=nlp_entities)
    assert result.name == "Belt Creative"
    assert result.source == "nlp"


def test_override_whitespace_falls_through_to_nlp():
    nlp_entities = [
        {"name": "Belt Creative", "type": "ORGANIZATION", "salience": 0.72},
    ]
    result = resolve_brand(brand_override="   ", nlp_entities=nlp_entities)
    assert result.name == "Belt Creative"
    assert result.source == "nlp"


# validate_brand_name — guards against brand tokens that collide with
# common entities in AI response corpora (e.g. "VAN" → Van Gogh, Beethoven).

def test_validate_accepts_full_brand_name():
    assert validate_brand_name("Veza Network") == "Veza Network"
    assert validate_brand_name("HubSpot") == "HubSpot"
    assert validate_brand_name("Belt Creative") == "Belt Creative"


def test_validate_trims_whitespace():
    assert validate_brand_name("  Veza Network  ") == "Veza Network"


def test_validate_rejects_three_char_acronym():
    with pytest.raises(BrandValidationError, match="too short"):
        validate_brand_name("VAN")


def test_validate_rejects_two_char_acronym():
    with pytest.raises(BrandValidationError, match="too short"):
        validate_brand_name("HP")


def test_validate_rejects_single_char():
    with pytest.raises(BrandValidationError, match="too short"):
        validate_brand_name("X")


def test_validate_rejects_empty_string():
    with pytest.raises(BrandValidationError, match="too short"):
        validate_brand_name("")


def test_validate_rejects_whitespace_only():
    with pytest.raises(BrandValidationError, match="too short"):
        validate_brand_name("   ")


def test_validate_rejects_common_word():
    with pytest.raises(BrandValidationError, match="generic word"):
        validate_brand_name("website")


def test_validate_rejects_common_word_case_insensitive():
    with pytest.raises(BrandValidationError, match="generic word"):
        validate_brand_name("Company")


def test_validate_accepts_four_char_brand():
    # Legitimate 4-char brand (e.g. Nike) — above length floor, not in word list
    assert validate_brand_name("Nike") == "Nike"
