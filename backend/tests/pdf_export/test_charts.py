"""Tests for Fix 5 charts: pillar bar, TIPR quadrant, content gap bar."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pdf_export_generator as pdf_mod


def _render_html(report: dict) -> str:
    ctx = pdf_mod._prepare_context(report or {})
    template = pdf_mod._jinja_env.from_string(pdf_mod._TEMPLATE)
    return template.render(**ctx)


def _full_report() -> dict:
    return {
        "url": "https://example.com",
        "overall_score": 72,
        "overall_label": "Good",
        "categories": {
            "semantic_html": {"score": 85, "label": "Excellent"},
            "structured_data": {"score": 72, "label": "Good"},
            "aeo_content": {"score": 68, "label": "Needs Improvement"},
            "css_quality": {"score": 80, "label": "Good"},
            "js_bloat": {"score": 55, "label": "Needs Improvement"},
            "accessibility": {"score": 45, "label": "Poor"},
            "rag_readiness": {"score": 78, "label": "Good"},
            "agentic_protocols": {"score": 90, "label": "Excellent"},
            "data_integrity": {"score": 88, "label": "Excellent"},
            "internal_linking": {"score": 62, "label": "Needs Improvement"},
        },
        "tipr_analysis": {
            "summary": {
                "total_pages": 171, "stars": 4, "hoarders": 64,
                "wasters": 0, "dead_weight": 103, "orphan_count": 12,
            },
            "pages": [],
            "recommendations": [],
        },
        "content_optimizer": {
            "analyses": {
                "kw1": {
                    "status": "ok",
                    "url": "https://example.com/services",
                    "keyword": "web design miami",
                    "result": {
                        "target_url": "https://example.com/services",
                        "summary": {
                            "content_gap_score": 92,
                            "recommendations_count": {"add": 18, "increase": 4, "reduce": 2, "remove": 1},
                        },
                        "terms": [],
                    },
                }
            }
        },
    }


def test_pillar_chart_svg_renders_in_section_03():
    html = _render_html(_full_report())
    start = html.find("<!-- 3. 10-PILLAR SCORECARD")
    end = html.find("<!-- 4. LINK INTELLIGENCE")
    assert start > 0 and end > start
    block = html[start:end]
    assert "<svg" in block
    assert ">85<" in block or "85" in block


def test_tipr_quadrant_grid_rendered():
    html = _render_html(_full_report())
    start = html.find("<!-- 4. LINK INTELLIGENCE")
    end = html.find("<!-- 5. CONTENT INTELLIGENCE")
    block = html[start:end]
    assert "Stars" in block
    assert "Hoarders" in block
    assert "Wasters" in block
    assert "Dead Weight" in block
    assert "4" in block
    assert "64" in block
    assert "103" in block
    assert "tipr-quadrant" in block


def test_content_gap_bar_rendered_per_card():
    html = _render_html(_full_report())
    start = html.find("<!-- 7. CONTENT OPTIMIZER")
    end = html.find("<!-- 8. TOPIC CLUSTERS")
    block = html[start:end]
    assert "92%" in block
    assert "gap-bar" in block
    assert "width: 92" in block or "width:92" in block
