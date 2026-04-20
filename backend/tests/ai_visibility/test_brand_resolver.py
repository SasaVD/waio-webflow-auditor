"""Tests for AI Visibility brand resolver."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from ai_visibility.brand_resolver import resolve_brand, check_brand_ambiguity
from ai_visibility.schema import BrandInfo, BrandExtractionError


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


# check_brand_ambiguity — advisory warning, never raises. Short acronyms
# (IBM, NIO, HP) and generic words can be legitimate brands and exposing
# the collision is itself strategic signal, so we warn but don't block.

def test_ambiguity_none_for_full_brand_name():
    assert check_brand_ambiguity("Veza Network") is None
    assert check_brand_ambiguity("HubSpot") is None
    assert check_brand_ambiguity("Belt Creative") is None


def test_ambiguity_none_for_empty_input():
    # Empty string isn't "ambiguous" — it's invalid input, handled elsewhere.
    assert check_brand_ambiguity("") is None
    assert check_brand_ambiguity("   ") is None


def test_ambiguity_warns_on_three_char_acronym():
    warning = check_brand_ambiguity("VAN")
    assert warning is not None
    assert "short token" in warning
    assert "VAN" in warning


def test_ambiguity_warns_on_two_char_acronym():
    warning = check_brand_ambiguity("HP")
    assert warning is not None
    assert "short token" in warning


def test_ambiguity_warns_on_single_char():
    warning = check_brand_ambiguity("X")
    assert warning is not None
    assert "1 character" in warning


def test_ambiguity_warns_on_common_word():
    warning = check_brand_ambiguity("website")
    assert warning is not None
    assert "generic word" in warning


def test_ambiguity_warns_on_common_word_case_insensitive():
    warning = check_brand_ambiguity("Company")
    assert warning is not None
    assert "generic word" in warning


def test_ambiguity_none_for_four_char_brand():
    # Legitimate 4-char brand — above threshold, not in word list
    assert check_brand_ambiguity("Nike") is None
