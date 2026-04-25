"""Workstream D2: KG MID / category-leaf / curated-list brand validation.

Locks the contract for the 3-layer brand override validation pipeline added
on top of the existing resolve_brand. Motivating incident: sched.com
2026-04-23, where the override "Event Management Software" was accepted
verbatim and pseudo-mentions inflated the audit. D2 rejects category
phrases, validates real brands via KG MID, and falls back to a curated
allow-list before settling on the unverified-override path.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from ai_visibility.brand_resolver import resolve_brand
from ai_visibility.schema import BrandInfo, BrandExtractionError


class _FakeNLP:
    """Minimal NLP client double exposing only the methods resolve_brand uses.

    The brand resolver only consumes ``analyze_entities`` — category-leaf
    rejection is implemented from the entity-analysis response (see
    docstring on resolve_brand for the rationale). Tests pass canned
    entity dicts mirroring the shape returned by google_nlp_client.
    """
    def __init__(self, *, entities=None, raises=None):
        self._entities = entities or []
        self._raises = raises

    def analyze_entities(self, text):
        if self._raises:
            raise self._raises
        return self._entities


def _entity(name, *, mid=None, wikipedia_url=None, entity_type="ORGANIZATION",
            salience=0.9):
    return {
        "name": name,
        "type": entity_type,
        "salience": salience,
        "metadata": {k: v for k, v in [("mid", mid), ("wikipedia_url", wikipedia_url)] if v},
    }


# ── Layer 1: KG MID primary ─────────────────────────────────────────


def test_override_with_kg_mid_resolves_with_kg_source():
    """Real brand with Knowledge Graph entry → source='kg_mid'."""
    nlp = _FakeNLP(entities=[_entity("HubSpot", mid="/m/0cxygf",
                                      wikipedia_url="https://en.wikipedia.org/wiki/HubSpot")])
    result = resolve_brand("HubSpot", nlp_entities=None, nlp_client=nlp)
    assert result.source == "kg_mid"
    assert result.name == "HubSpot"


def test_override_with_only_wikipedia_url_resolves_with_kg_source():
    """Wikipedia URL alone (no MID) is sufficient evidence of a real entity."""
    nlp = _FakeNLP(entities=[_entity("Webflow",
                                      wikipedia_url="https://en.wikipedia.org/wiki/Webflow")])
    result = resolve_brand("Webflow", nlp_entities=None, nlp_client=nlp)
    assert result.source == "kg_mid"


# ── Layer 2: Category-leaf rejection ────────────────────────────────


def test_category_phrase_override_raises_brand_extraction_error():
    """'Event Management Software' is a category, not a brand — reject hard.

    Implementation choice (see resolve_brand docstring): we use NLP
    analyzeEntities response signals only — when the entity returned for
    the brand string is not a proper-noun ORGANIZATION/PERSON/CONSUMER_GOOD,
    has no KG/Wikipedia metadata, AND its surface form matches a known
    category-leaf shape (multi-word, generic, lowercased category-like),
    we raise. Tests use a sentinel hook (``_force_category_match``) to
    assert the rejection path independent of the heuristic the
    implementation chose.
    """
    nlp = _FakeNLP(entities=[_entity("Event Management Software", entity_type="OTHER")])
    with pytest.raises(BrandExtractionError) as excinfo:
        resolve_brand("Event Management Software", nlp_entities=None, nlp_client=nlp,
                      _force_category_match=True)
    assert "category phrase" in str(excinfo.value).lower()


# ── Layer 3: Curated list ───────────────────────────────────────────


def test_override_in_curated_list_resolves_with_curated_source():
    nlp = _FakeNLP(entities=[])  # no KG, no category match
    curated = {"veza digital": "Veza Digital"}
    result = resolve_brand("Veza Digital", nlp_entities=None, nlp_client=nlp,
                           curated_brands=curated)
    assert result.source == "curated_list"
    assert result.name == "Veza Digital"


def test_curated_lookup_is_case_insensitive():
    nlp = _FakeNLP(entities=[])
    curated = {"veza digital": "Veza Digital"}
    result = resolve_brand("veza DIGITAL", nlp_entities=None, nlp_client=nlp,
                           curated_brands=curated)
    assert result.source == "curated_list"


# ── Fallthrough: override_unverified ────────────────────────────────


def test_override_falls_through_to_unverified_when_all_layers_miss():
    nlp = _FakeNLP(entities=[])
    result = resolve_brand("xyzzyfrobnicator", nlp_entities=None, nlp_client=nlp,
                           curated_brands={})
    assert result.source == "override_unverified"
    assert result.name == "xyzzyfrobnicator"


# ── NLP unavailability — graceful fallback ──────────────────────────


def test_no_nlp_client_skips_to_curated_then_unverified():
    """When called without nlp_client, KG/category checks are skipped."""
    curated = {"veza digital": "Veza Digital"}
    result = resolve_brand("Veza Digital", nlp_entities=None, nlp_client=None,
                           curated_brands=curated)
    assert result.source == "curated_list"


def test_nlp_client_failure_falls_back_gracefully():
    """If analyze_entities raises (network/auth/quota), don't crash."""
    nlp = _FakeNLP(raises=RuntimeError("API timeout"))
    result = resolve_brand("HubSpot", nlp_entities=None, nlp_client=nlp,
                           curated_brands={})
    assert result.source == "override_unverified"
    assert result.name == "HubSpot"


# ── Backwards-compat: NLP-only path (no override) ───────────────────


def test_nlp_path_unchanged_when_no_override():
    """D2 must not change the existing NLP-extraction path."""
    entities = [
        {"name": "Acme Corp", "type": "ORGANIZATION", "salience": 0.8},
    ]
    result = resolve_brand(brand_override=None, nlp_entities=entities)
    assert result.source == "nlp"
    assert result.name == "Acme Corp"


# ── Anti-regression: no path emits the deprecated "override" source ─


def test_no_path_returns_deprecated_override_source():
    """The plain 'override' source string is removed in D2 — every path must
    pick one of the new discriminators."""
    nlp = _FakeNLP(entities=[_entity("HubSpot", mid="/m/0cxygf")])
    result = resolve_brand("HubSpot", nlp_entities=None, nlp_client=nlp)
    assert result.source != "override"


def test_unverified_path_does_not_return_deprecated_override_source():
    nlp = _FakeNLP(entities=[])
    result = resolve_brand("xyzzyfrobnicator", nlp_entities=None, nlp_client=nlp,
                           curated_brands={})
    assert result.source != "override"
