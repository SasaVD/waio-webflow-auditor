"""Tests for AI Visibility Share of Voice calculator."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai_visibility.sov_calculator import calculate_sov
from ai_visibility.schema import SOVResult


def _make_cross_data(brand_mentions: list[tuple[str, int]]) -> dict:
    """Build cross_aggregated response matching real API shape.

    brand_mentions: list of (aggregation_key, total_mentions) tuples.
    """
    items = [
        {
            "key": key,
            "platform": [
                {"key": "google", "mentions": count, "ai_search_volume": 0, "impressions": 0},
            ],
        }
        for key, count in brand_mentions
    ]
    return {"result": {"total": {}, "items": items}}


def test_basic_sov():
    cross_data = _make_cross_data([
        ("beltcreative.com", 100),
        ("webflow.com", 300),
        ("wix.com", 200),
    ])
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
    cross_data = _make_cross_data([
        ("webflow.com", 300),
        ("wix.com", 200),
    ])
    result = calculate_sov(
        cross_aggregated_data=cross_data,
        brand_domain="beltcreative.com",
        competitor_domains=["webflow.com", "wix.com"],
    )
    assert result.brand_sov == 0.0
    assert result.total_mentions_analyzed == 500


def test_empty_data():
    result = calculate_sov(
        cross_aggregated_data={"result": {"items": []}},
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
    cross_data = _make_cross_data([
        ("beltcreative.com", 100),
    ])
    result = calculate_sov(
        cross_aggregated_data=cross_data,
        brand_domain="beltcreative.com",
        competitor_domains=[],
    )
    assert result.brand_sov == 1.0
    assert result.competitor_sov == {}
    assert result.total_mentions_analyzed == 100


def test_sov_capped_at_one():
    cross_data = _make_cross_data([
        ("beltcreative.com", 500),
    ])
    result = calculate_sov(
        cross_aggregated_data=cross_data,
        brand_domain="beltcreative.com",
        competitor_domains=["webflow.com"],
    )
    assert result.brand_sov <= 1.0


def test_multi_platform_sov():
    """Mentions from multiple platforms should be summed."""
    cross_data = {
        "result": {
            "total": {},
            "items": [
                {
                    "key": "brand.com",
                    "platform": [
                        {"key": "google", "mentions": 60, "ai_search_volume": 0, "impressions": 0},
                        {"key": "chat_gpt", "mentions": 40, "ai_search_volume": 0, "impressions": 0},
                    ],
                },
                {
                    "key": "competitor.com",
                    "platform": [
                        {"key": "google", "mentions": 100, "ai_search_volume": 0, "impressions": 0},
                    ],
                },
            ],
        }
    }
    result = calculate_sov(
        cross_aggregated_data=cross_data,
        brand_domain="brand.com",
        competitor_domains=["competitor.com"],
    )
    # brand: 60+40=100, competitor: 100, total: 200
    assert abs(result.brand_sov - 0.5) < 0.001
    assert result.total_mentions_analyzed == 200
