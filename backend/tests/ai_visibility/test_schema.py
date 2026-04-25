"""Tests for AI Visibility schema dataclasses."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai_visibility.schema import (
    BrandInfo, CompetitorSet, PromptTemplate, EngineResult,
    MentionsResult, ResponsesResult, SOVResult, BrandExtractionError,
)


def test_brand_info_to_dict_with_salience():
    b = BrandInfo(name="Belt Creative", source="nlp", salience=0.71234)
    d = b.to_dict()
    assert d == {"name": "Belt Creative", "source": "nlp", "salience": 0.7123}


def test_brand_info_to_dict_without_salience():
    # Workstream D2: 'override' was replaced by the 3-layer discriminator.
    # 'override_unverified' represents the lowest-confidence override path
    # (no KG hit, not in curated list).
    b = BrandInfo(name="Belt Creative", source="override_unverified")
    d = b.to_dict()
    assert d == {"name": "Belt Creative", "source": "override_unverified"}
    assert "salience" not in d


def test_brand_info_to_dict_with_kg_metadata():
    """KG-validated overrides emit kg_mid + wikipedia_url alongside the source."""
    b = BrandInfo(
        name="HubSpot",
        source="kg_mid",
        kg_mid="/m/0cxygf",
        wikipedia_url="https://en.wikipedia.org/wiki/HubSpot",
    )
    d = b.to_dict()
    assert d["source"] == "kg_mid"
    assert d["kg_mid"] == "/m/0cxygf"
    assert d["wikipedia_url"] == "https://en.wikipedia.org/wiki/HubSpot"


def test_brand_info_to_dict_curated_omits_kg_fields():
    """Curated-list resolutions don't have KG metadata — fields stay absent."""
    b = BrandInfo(name="Veza Digital", source="curated_list")
    d = b.to_dict()
    assert d == {"name": "Veza Digital", "source": "curated_list"}


def test_competitor_set_to_dict():
    c = CompetitorSet(domains=["webflow.com", "wix.com"], source="user_provided")
    d = c.to_dict()
    assert d == {"domains": ["webflow.com", "wix.com"], "source": "user_provided"}


def test_prompt_template_to_dict():
    p = PromptTemplate(id=1, category="discovery", text="best agencies")
    d = p.to_dict()
    assert d == {"id": 1, "category": "discovery", "text": "best agencies"}


def test_engine_result_ok():
    e = EngineResult(
        status="ok", engine="chatgpt",
        responses_by_prompt={1: {"text": "..."}},
        cost_usd=0.42, brand_mentioned_in=2,
    )
    d = e.to_dict()
    assert d["status"] == "ok"
    assert d["cost_usd"] == 0.42
    assert d["brand_mentioned_in"] == 2
    assert "responses_by_prompt" in d
    assert "error" not in d


def test_engine_result_failed():
    e = EngineResult(
        status="failed", engine="perplexity",
        error="timeout after 120s", cost_usd=0.0,
    )
    d = e.to_dict()
    assert d["status"] == "failed"
    assert d["error"] == "timeout after 120s"
    assert "responses_by_prompt" not in d


def test_mentions_result_to_dict():
    m = MentionsResult(
        total=103,
        by_platform={"google_ai_overview": 69, "chatgpt": 34},
        ai_search_volume=156000,
        impressions=42300,
        top_pages=[{"url": "https://example.com", "mention_count": 12}],
        triggering_prompts=[],
        cost_usd=0.15,
    )
    d = m.to_dict()
    assert d["total"] == 103
    assert d["ai_search_volume"] == 156000
    assert "cost_usd" not in d  # cost tracked separately, not in blob


def test_responses_result_to_dict():
    r = ResponsesResult(
        engines={
            "chatgpt": EngineResult(status="ok", engine="chatgpt", cost_usd=0.42, brand_mentioned_in=2),
            "perplexity": EngineResult(status="failed", engine="perplexity", error="timeout"),
        },
        cost_usd=0.42,
    )
    d = r.to_dict()
    assert "chatgpt" in d["engines"]
    assert d["engines"]["chatgpt"]["status"] == "ok"
    assert d["engines"]["perplexity"]["status"] == "failed"


def test_sov_result_to_dict():
    s = SOVResult(
        brand_sov=0.12345,
        competitor_sov={"webflow.com": 0.34567, "wix.com": 0.28},
        total_mentions_analyzed=847,
    )
    d = s.to_dict()
    assert d["source"] == "mentions_database.cross_aggregated"
    assert d["brand_sov"] == 0.1235  # rounded to 4 decimals
    assert d["competitor_sov"]["webflow.com"] == 0.3457
    assert d["total_mentions_analyzed"] == 847


def test_sov_empty_competitors():
    s = SOVResult(brand_sov=0.0, competitor_sov={}, total_mentions_analyzed=0)
    d = s.to_dict()
    assert d["competitor_sov"] == {}


def test_brand_extraction_error_is_exception():
    assert issubclass(BrandExtractionError, Exception)
