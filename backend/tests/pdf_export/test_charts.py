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


def test_scorecard_shows_compact_category_strip():
    """Section 03 must show the 4 weight groups as a compact strip."""
    html = _render_html(_full_report())
    start = html.find("<!-- 3. 10-PILLAR SCORECARD")
    end = html.find("<!-- 4. LINK INTELLIGENCE")
    block = html[start:end]
    assert "pillar-category-strip" in block
    for group in ("Search &amp; Discovery", "AI Readiness", "Foundations", "UX &amp; Performance"):
        assert group in block, f"Missing category chip: {group}"
    for weight in ("36%", "28%", "26%", "10%"):
        assert weight in block, f"Missing weight percentage: {weight}"


def test_scorecard_no_longer_renders_individual_pillar_cards():
    """The 10-pillar card grid is removed in favor of the bar chart + category strip."""
    html = _render_html(_full_report())
    start = html.find("<!-- 3. 10-PILLAR SCORECARD")
    end = html.find("<!-- 4. LINK INTELLIGENCE")
    block = html[start:end]
    assert 'class="pillar-card"' not in block
    assert 'class="pillar-grid' not in block


def test_pillar_chart_includes_findings_count_per_pillar():
    """Each pillar row in the bar chart must show findings count suffix."""
    report = _full_report()
    # Give accessibility 8 findings and structured_data 3 findings
    report["categories"]["accessibility"]["findings"] = [
        {"severity": "high", "description": f"f{i}"} for i in range(8)
    ]
    report["categories"]["structured_data"]["findings"] = [
        {"severity": "medium", "description": f"f{i}"} for i in range(3)
    ]
    html = _render_html(report)
    start = html.find("<!-- 3. 10-PILLAR SCORECARD")
    end = html.find("<!-- 4. LINK INTELLIGENCE")
    block = html[start:end]
    assert "8 findings" in block
    assert "3 findings" in block
    # Pillars with zero findings should render "clean" sentinel
    assert "clean" in block


def test_pillar_findings_count_falls_back_to_nested_checks():
    """When category has no top-level 'findings' list, count from checks[*].findings.
    Real stored audit reports often only nest findings under checks."""
    report = _full_report()
    # Replace accessibility with the nested-only shape
    report["categories"]["accessibility"] = {
        "score": 44, "label": "Poor",
        "checks": {
            "axe_scan": {
                "status": "fail",
                "findings": [{"severity": "high"}] * 6,
            },
            "focus_styles": {
                "status": "fail",
                "findings": [{"severity": "medium"}],
            },
            "touch_targets": {
                "status": "fail",
                "findings": [{"severity": "medium"}],
            },
        },
    }
    html = _render_html(report)
    start = html.find("<!-- 3. 10-PILLAR SCORECARD")
    end = html.find("<!-- 4. LINK INTELLIGENCE")
    block = html[start:end]
    # 6 + 1 + 1 = 8 total findings across checks
    assert "8 findings" in block


def test_tipr_rewrites_awkward_zero_outbound_phrasing():
    """Reason text with 'links out to 0 pages' must read naturally."""
    reason = "**/news** receives 30 inbound links but only links out to 0 pages. It's accumulating authority."
    out = pdf_mod._rewrite_zero_outbound_phrases(reason)
    assert "only links out to 0 pages" not in out
    assert "has no outbound internal links" in out


def test_tipr_rewrites_preserve_nonzero_counts():
    """The rewriter must NOT touch non-zero outbound phrasings."""
    reason = "/hub links out to 12 pages and has 12 outbound links"
    out = pdf_mod._rewrite_zero_outbound_phrases(reason)
    assert "links out to 12 pages" in out
    assert "12 outbound links" in out


def test_gap_bar_height_is_visible_in_pdf():
    """Gap bar must have non-trivial height so WeasyPrint renders it reliably."""
    html = _render_html(_full_report())
    # CSS style definitions must specify at least 12pt height for the bar
    assert "height: 12pt" in html


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


def test_tipr_axis_labels_not_rotated():
    html = _render_html(_full_report())
    assert "Low Traffic" in html
    assert "High Traffic" in html
    assert "High PageRank" in html
    assert "Low PageRank" in html
    # Axis labels must not be rotated — readability requirement.
    assert "writing-mode: vertical-rl" not in html
    assert "transform: rotate(180deg)" not in html
    # X-axis labels live above the cells (row 1), Y-axis labels live in col 1.
    assert "q-axis-x-low" in html
    assert "q-axis-x-high" in html
    assert "q-axis-y-high" in html
    assert "q-axis-y-low" in html


def test_content_gap_bar_rendered_per_card():
    html = _render_html(_full_report())
    start = html.find("<!-- 7. CONTENT OPTIMIZER")
    end = html.find("<!-- 8. TOPIC CLUSTERS")
    block = html[start:end]
    assert "92%" in block
    assert "gap-bar" in block
    assert "width: 92" in block or "width:92" in block


def _co_only_report(gap_score) -> dict:
    """Minimal report with one Content Optimizer card carrying ``gap_score``.
    Used by boundary-case tests below."""
    base = _full_report()
    base["content_optimizer"] = {
        "analyses": {
            "edge": {
                "status": "ok",
                "url": "https://example.com/edge",
                "keyword": "edge case",
                "result": {
                    "summary": {
                        "content_gap_score": gap_score,
                        "recommendations_count": {"add": 0, "increase": 0, "reduce": 0, "remove": 0},
                    },
                    "terms": [],
                },
            }
        }
    }
    return base


def test_gap_bar_renders_for_zero_gap_score():
    """gap_score=0 must still produce a track + bar pair (CSS min-width
    floor keeps the bar visible). Locks against the 04-20 bug report
    "Content Optimizer visual gap bars not rendering" — empirically the
    bug no longer reproduces; this test prevents regression."""
    html = _render_html(_co_only_report(0.0))
    start = html.find("<!-- 7. CONTENT OPTIMIZER")
    end = html.find("<!-- 8. TOPIC CLUSTERS")
    block = html[start:end]
    # The container track must be present
    assert 'class="gap-bar-track"' in block
    # And the bar with width: 0(.0)% (the min-width floor handles the visual)
    assert 'class="gap-bar"' in block
    assert "width: 0" in block  # matches "width: 0%" or "width: 0.0%"


def test_gap_bar_renders_for_full_gap_score():
    """gap_score=100 must produce width at the upper bound. The engine
    emits floats via round(x, 1), so 100.0 renders as '100.0%' — accept
    either int-formatted or float-formatted output as long as it's
    bounded at 100."""
    html = _render_html(_co_only_report(100.0))
    start = html.find("<!-- 7. CONTENT OPTIMIZER")
    end = html.find("<!-- 8. TOPIC CLUSTERS")
    block = html[start:end]
    assert "100.0%" in block or "100%" in block
    assert "width: 100" in block


def test_gap_bar_preserves_float_precision():
    """gap_score=45.3 (typical post-`round(x, 1)` value from the engine)
    must render as 'width: 45.3%' — not silently coerced to int. Catches
    any regression where a future template change strips fractional
    digits and produces visibly inaccurate bars."""
    html = _render_html(_co_only_report(45.3))
    start = html.find("<!-- 7. CONTENT OPTIMIZER")
    end = html.find("<!-- 8. TOPIC CLUSTERS")
    block = html[start:end]
    assert "45.3%" in block
    assert "width: 45.3" in block or "width:45.3" in block


def test_gap_bar_track_and_bar_are_paired():
    """Every card must emit BOTH a .gap-bar-track AND a .gap-bar — the
    track without the bar would render as an empty gray rectangle (the
    visual symptom from the original 04-20 report). Counts must match."""
    html = _render_html(_full_report())
    start = html.find("<!-- 7. CONTENT OPTIMIZER")
    end = html.find("<!-- 8. TOPIC CLUSTERS")
    block = html[start:end]
    assert block.count('class="gap-bar-track"') == block.count('class="gap-bar"')
    assert block.count('class="gap-bar"') >= 1
