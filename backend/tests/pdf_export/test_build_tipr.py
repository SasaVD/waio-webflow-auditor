"""Tests for _build_tipr covering both storage locations and available flag."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pdf_export_generator as pdf_mod


def _make_tipr_payload() -> dict:
    return {
        "summary": {
            "total_pages": 171,
            "stars": 4,
            "hoarders": 64,
            "wasters": 0,
            "dead_weight": 103,
            "orphan_count": 12,
        },
        "pages": [
            {
                "url": "https://example.com/",
                "tipr_rank": 1,
                "tipr_score": 88.2,
                "inbound_count": 15,
                "outbound_count": 8,
                "classification": "star",
            },
            {
                "url": "https://example.com/blog",
                "tipr_rank": 2,
                "tipr_score": 71.4,
                "inbound_count": 3,
                "outbound_count": 12,
                "classification": "hoarder",
            },
        ],
        "recommendations": [
            {
                "source_url": "https://example.com/",
                "target_url": "https://example.com/blog",
                "reason": "**Strong hub** should link to buried content",
                "priority": "high",
                "expected_impact": "+8 ranks",
            }
        ],
    }


def test_build_tipr_reads_top_level_key():
    """Primary path: data at report['tipr_analysis']."""
    report = {"tipr_analysis": _make_tipr_payload()}
    result = pdf_mod._build_tipr(report)
    assert result["available"] is True
    assert result["total_pages"] == 171
    assert result["stars"] == 4
    assert result["hoarders"] == 64
    assert result["dead_weight"] == 103
    assert result["orphan_count"] == 12
    assert len(result["top_pages"]) == 2
    assert len(result["top_recs"]) == 1
    # Markdown bold must be stripped from recommendation reason
    assert "**" not in result["top_recs"][0]["reason"]


def test_build_tipr_reads_legacy_nested_location():
    """Fallback: older reports nest it under link_analysis."""
    report = {"link_analysis": {"tipr_analysis": _make_tipr_payload()}}
    result = pdf_mod._build_tipr(report)
    assert result["available"] is True
    assert result["total_pages"] == 171


def test_build_tipr_unavailable_when_missing():
    """Empty report returns available: False."""
    result = pdf_mod._build_tipr({})
    assert result == {"available": False}


def test_build_tipr_includes_wasters_and_dead_weight_pct():
    """Fix 5 Chart 2 needs wasters and dead_weight with percentages."""
    report = {"tipr_analysis": _make_tipr_payload()}
    result = pdf_mod._build_tipr(report)
    for key in ("stars_pct", "hoarders_pct", "wasters_pct", "dead_weight_pct"):
        assert key in result, f"missing {key}"
    assert result["wasters_pct"] == 0
    # 103 / 171 = ~60.23%
    assert 60 <= result["dead_weight_pct"] <= 61
