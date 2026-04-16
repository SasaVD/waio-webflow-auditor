"""Tests for AI Visibility Share of Voice calculator."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai_visibility.sov_calculator import calculate_sov
from ai_visibility.schema import SOVResult


def test_basic_sov():
    cross_data = {
        "items": [
            {"keyword": "beltcreative.com", "count": 100},
            {"keyword": "webflow.com", "count": 300},
            {"keyword": "wix.com", "count": 200},
        ]
    }
    result = calculate_sov(
        cross_aggregated_data=cross_data,
        brand_domain="beltcreative.com",
        competitor_domains=["webflow.com", "wix.com"],
    )
    assert isinstance(result, SOVResult)
    assert abs(result.brand_sov - 100 / 600) < 0.001
    assert abs(result.competitor_sov["webflow.com"] - 300 / 600) < 0.001
    assert abs(result.competitor_sov["wix.com"] - 200 / 600) < 0.001
    assert result.total_mentions_analyzed == 600


def test_brand_not_in_data():
    cross_data = {
        "items": [
            {"keyword": "webflow.com", "count": 300},
            {"keyword": "wix.com", "count": 200},
        ]
    }
    result = calculate_sov(
        cross_aggregated_data=cross_data,
        brand_domain="beltcreative.com",
        competitor_domains=["webflow.com", "wix.com"],
    )
    assert result.brand_sov == 0.0
    assert result.total_mentions_analyzed == 500


def test_empty_data():
    result = calculate_sov(
        cross_aggregated_data={"items": []},
        brand_domain="beltcreative.com",
        competitor_domains=["webflow.com"],
    )
    assert result.brand_sov == 0.0
    assert result.competitor_sov == {}
    assert result.total_mentions_analyzed == 0


def test_none_data():
    result = calculate_sov(
        cross_aggregated_data=None,
        brand_domain="beltcreative.com",
        competitor_domains=["webflow.com"],
    )
    assert result.brand_sov == 0.0
    assert result.total_mentions_analyzed == 0


def test_no_competitors():
    cross_data = {
        "items": [
            {"keyword": "beltcreative.com", "count": 100},
        ]
    }
    result = calculate_sov(
        cross_aggregated_data=cross_data,
        brand_domain="beltcreative.com",
        competitor_domains=[],
    )
    assert result.brand_sov == 1.0
    assert result.competitor_sov == {}
    assert result.total_mentions_analyzed == 100


def test_sov_capped_at_one():
    cross_data = {
        "items": [
            {"keyword": "beltcreative.com", "count": 500},
        ]
    }
    result = calculate_sov(
        cross_aggregated_data=cross_data,
        brand_domain="beltcreative.com",
        competitor_domains=["webflow.com"],
    )
    assert result.brand_sov <= 1.0
