"""Tests verifying the AI Visibility section renders competitive brands + status."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pdf_export_generator as pdf_mod


def _render_html(report: dict) -> str:
    """Render just the template HTML (skip WeasyPrint) for fast assertion."""
    ctx = pdf_mod._prepare_context(report or {})
    template = pdf_mod._jinja_env.from_string(pdf_mod._TEMPLATE)
    return template.render(**ctx)


def _minimal_report_zero_state() -> dict:
    """Belt Creative shape: 4/4 reputation, 0 discovery mentions."""
    return {
        "url": "https://beltcreative.com",
        "overall_score": 62,
        "overall_label": "Needs Improvement",
        "ai_visibility": {
            "brand_name": "Belt Creative",
            "brand_name_source": "nlp",
            "live_test": {
                "engines": {
                    "chatgpt": {
                        "brand_mentioned_in": 0,
                        "status": "ok",
                        "responses_by_prompt": {
                            "1": {"text": "Top agencies include **Lounge Lizard**, **Huge**, **Clay**."},
                            "2": {"text": "Consider **Blue Fountain Media** and **Clay**."},
                            "3": {"text": "**Big Drop Inc** stands out."},
                            "4": {"text": "Belt Creative is a Miami agency."},  # reputation — excluded
                        },
                    },
                    "perplexity": {
                        "brand_mentioned_in": 0,
                        "status": "ok",
                        "responses_by_prompt": {
                            "1": {"text": "**Lounge Lizard** and **Huge** are strong picks."},
                        },
                    },
                },
                "prompts_used": [
                    {"id": 1, "category": "discovery", "text": "Top web design agencies in Miami?"},
                ],
            },
            "mentions_database": {"total": 0, "ai_search_volume": 0, "impressions": 0},
        },
    }


def test_template_renders_discovery_brands_section():
    html = _render_html(_minimal_report_zero_state())
    # Heading identifying the competitive-brands subsection
    assert "Brands Appearing in Your Category" in html
    # Competitor brands from the fixture
    assert "Lounge Lizard" in html
    assert "Huge" in html
    assert "Clay" in html
    assert "Blue Fountain Media" in html
    # Each brand should have a count badge next to it
    assert "×" in html or "mentions" in html.lower()


def test_template_renders_zero_state_status():
    html = _render_html(_minimal_report_zero_state())
    # Zero-state headline + body from _build_ai_visibility
    assert "Untapped AI discovery channel" in html


def test_template_excludes_own_brand_from_discovery_list():
    """Own brand must never appear in the discovery brands table."""
    report = _minimal_report_zero_state()
    # Add a response that mentions Belt Creative in a discovery prompt
    report["ai_visibility"]["live_test"]["engines"]["chatgpt"]["responses_by_prompt"]["1"]["text"] = (
        "Top agencies include **Belt Creative**, **Huge**, **Clay**."
    )
    html = _render_html(report)
    idx = html.find("Brands Appearing in Your Category")
    assert idx > 0
    block = html[idx:idx + 3000]
    assert "Huge" in block
    assert "Clay" in block
    # Own brand excluded by _extract_discovery_brands
    assert "<td>Belt Creative</td>" not in block


def test_template_omits_section_when_no_discovery_brands():
    """If every engine is empty, don't render the competitive-brands section."""
    report = _minimal_report_zero_state()
    # Wipe all responses
    for eng in report["ai_visibility"]["live_test"]["engines"].values():
        eng["responses_by_prompt"] = {}
    html = _render_html(report)
    assert "Brands Appearing in Your Category" not in html
