"""Cover page must render the SVG score ring, not plain text."""
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


def test_cover_renders_svg_score_ring():
    report = {"url": "https://example.com", "overall_score": 76, "overall_label": "Good"}
    html = _render_html(report)
    # Find the cover block
    cover_end = html.find("<!-- 2. EXECUTIVE SUMMARY")
    assert cover_end > 0
    cover_block = html[:cover_end]
    # SVG present
    assert "<svg" in cover_block
    # The score number appears inside an SVG <text> element
    assert "<text" in cover_block
    assert ">76<" in cover_block


def test_cover_build_exposes_score_ring_svg():
    """_build_cover must place the pre-rendered SVG in the context."""
    ctx = pdf_mod._build_cover({"url": "https://x.com", "overall_score": 82, "overall_label": "Good"})
    assert "score_ring_svg" in ctx
    assert ctx["score_ring_svg"].lstrip().startswith("<svg")
    # Color-code matches ≥80 green range
    assert "110" in ctx["score_ring_svg"]  # viewBox anchor
