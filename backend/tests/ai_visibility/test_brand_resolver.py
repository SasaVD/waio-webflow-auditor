"""Tests for AI Visibility brand resolver."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from ai_visibility.brand_resolver import resolve_brand
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
