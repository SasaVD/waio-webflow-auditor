"""TOC must list sections with data and page-number placeholders."""
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
        "executive_summary": "## Overview\n\nHello world.",
        "categories": {
            **{k: {"score": 70, "label": "Good"} for k in [
                "semantic_html", "structured_data", "aeo_content", "css_quality",
                "js_bloat", "rag_readiness", "agentic_protocols",
                "data_integrity", "internal_linking",
            ]},
            "accessibility": {
                "score": 55,
                "label": "Needs Improvement",
                "checks": {
                    "color_contrast": {
                        "findings": [
                            {
                                "severity": "high",
                                "description": "Low-contrast text fails WCAG AA.",
                                "recommendation": "Increase contrast ratio.",
                                "credibility_anchor": "WCAG 2.1 AA requires ≥ 4.5:1.",
                            }
                        ]
                    }
                },
            },
        },
        "tipr_analysis": {
            "summary": {"total_pages": 10, "stars": 1, "hoarders": 4, "wasters": 2, "dead_weight": 3},
            "pages": [],
            "recommendations": [],
        },
        "nlp_analysis": {
            "top_entities": [{"name": "Example", "type": "ORGANIZATION", "salience": 0.5, "mentions_count": 5}],
            "detected_industry": "/Business",
        },
        "ai_visibility": {
            "brand_name": "Example",
            "brand_name_source": "nlp",
            "live_test": {"engines": {}, "prompts_used": []},
            "mentions_database": {"total": 0},
        },
        "content_optimizer": {
            "analyses": {
                "kw1": {
                    "status": "ok",
                    "url": "https://example.com/services",
                    "keyword": "example",
                    "result": {
                        "target_url": "https://example.com/services",
                        "summary": {
                            "content_gap_score": 70,
                            "recommendations_count": {"add": 5, "increase": 2, "reduce": 1, "remove": 0},
                        },
                        "terms": [],
                    },
                }
            }
        },
        "semantic_clusters": {"clusters": [{"theme": "x", "size": 5, "keywords": []}], "n_clusters": 1},
    }


def test_toc_page_rendered_between_cover_and_exec():
    html = _render_html(_full_report())
    toc_marker = html.find("Contents")
    exec_marker = html.find("<!-- 2. EXECUTIVE SUMMARY")
    assert toc_marker > 0
    assert toc_marker < exec_marker


def test_toc_lists_all_available_sections():
    html = _render_html(_full_report())
    toc_start = html.find("<!-- TOC")
    toc_end = html.find("<!-- 2. EXECUTIVE SUMMARY")
    assert toc_start > 0
    block = html[toc_start:toc_end]
    for label in [
        "Executive Summary",
        "10-Pillar Scorecard",
        "Link Intelligence",
        "Content Intelligence",
        "AI Visibility Report",
        "Content Optimizer",
        "Topic Clusters",
        "Priority Action Items",
        "Methodology",
    ]:
        assert label in block, f"TOC missing '{label}'"


def test_toc_omits_sections_without_data():
    report = _full_report()
    del report["tipr_analysis"]
    del report["content_optimizer"]
    del report["semantic_clusters"]
    html = _render_html(report)
    toc_start = html.find("<!-- TOC")
    toc_end = html.find("<!-- 2. EXECUTIVE SUMMARY")
    block = html[toc_start:toc_end]
    assert "Executive Summary" in block
    assert "Link Intelligence" not in block
    assert "Content Optimizer" not in block
    assert "Topic Clusters" not in block


def test_toc_entries_link_to_section_anchors():
    html = _render_html(_full_report())
    assert 'id="sec-exec"' in html
    assert 'id="sec-pillars"' in html
    toc_start = html.find("<!-- TOC")
    toc_end = html.find("<!-- 2. EXECUTIVE SUMMARY")
    block = html[toc_start:toc_end]
    assert 'href="#sec-exec"' in block
    assert 'href="#sec-pillars"' in block
