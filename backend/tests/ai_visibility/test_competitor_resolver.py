"""Tests for AI Visibility competitor resolver."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai_visibility.competitor_resolver import resolve_competitors, normalize_domain
from ai_visibility.schema import CompetitorSet


# --- Domain normalization ---

def test_normalize_full_url():
    assert normalize_domain("https://www.webflow.com/about") == "webflow.com"


def test_normalize_url_no_www():
    assert normalize_domain("https://wix.com/templates") == "wix.com"


def test_normalize_bare_domain():
    assert normalize_domain("squarespace.com") == "squarespace.com"


def test_normalize_with_www_no_scheme():
    assert normalize_domain("www.example.com") == "example.com"


def test_normalize_empty_string():
    assert normalize_domain("") == ""


def test_normalize_none():
    assert normalize_domain(None) == ""


# --- Competitor resolution ---

def test_tier1_user_provided():
    result = resolve_competitors(
        competitor_urls=["https://webflow.com", "https://wix.com"],
        competitive_data=None,
        co_mention_domains=None,
    )
    assert result.source == "user_provided"
    assert result.domains == ["webflow.com", "wix.com"]


def test_tier1_dedupes():
    result = resolve_competitors(
        competitor_urls=["https://webflow.com", "https://www.webflow.com/pricing"],
        competitive_data=None,
        co_mention_domains=None,
    )
    assert result.domains == ["webflow.com"]


def test_tier2_competitive_auditor():
    competitive_data = {
        "rankings": [
            {"url": "https://webflow.com", "overall_score": 85},
            {"url": "https://wix.com", "overall_score": 72},
        ]
    }
    result = resolve_competitors(
        competitor_urls=[],
        competitive_data=competitive_data,
        co_mention_domains=None,
    )
    assert result.source == "competitive_auditor"
    assert "webflow.com" in result.domains


def test_tier3_co_mentions():
    result = resolve_competitors(
        competitor_urls=[],
        competitive_data=None,
        co_mention_domains=["hubspot.com", "mailchimp.com"],
    )
    assert result.source == "co_mentions"
    assert result.domains == ["hubspot.com", "mailchimp.com"]


def test_all_empty_returns_none_source():
    result = resolve_competitors(
        competitor_urls=[],
        competitive_data=None,
        co_mention_domains=None,
    )
    assert result.source == "none"
    assert result.domains == []


def test_competitive_data_missing_rankings():
    result = resolve_competitors(
        competitor_urls=[],
        competitive_data={"some_other_key": 42},
        co_mention_domains=None,
    )
    assert result.source == "none"
    assert result.domains == []
