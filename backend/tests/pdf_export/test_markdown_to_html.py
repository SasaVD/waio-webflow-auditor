"""Tests for markdown_to_html covering GFM tables (Fix 1)."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pdf_export_generator as pdf_mod


SCORECARD_MD = """## Current State

| Category | Score | Assessment |
| --- | :---: | --- |
| Technical Foundation | 91 | Strong |
| Content Effectiveness | 74 | Needs work |
| AI Readiness | 68 | Developing |
| Site Structure | 82 | Solid |
"""


def test_markdown_to_html_renders_pipe_tables_with_library():
    """With the markdown lib installed, pipe tables must render as <table>."""
    html = pdf_mod.markdown_to_html(SCORECARD_MD)
    assert "<table>" in html
    assert "<thead>" in html
    assert "<th>Category</th>" in html
    assert "<td>Technical Foundation</td>" in html
    # No raw pipe characters should survive
    assert "| Category |" not in html
    assert "| --- |" not in html


def test_markdown_to_html_does_not_insert_br_in_table_cells():
    """nl2br must not fire inside table cells — cells must be bare text."""
    html = pdf_mod.markdown_to_html(SCORECARD_MD)
    # Between the opening of the first row and its closing </tr>, no <br>
    first_row = html.split("<tr>")[1].split("</tr>")[0]
    assert "<br" not in first_row.lower()


def test_markdown_to_html_falls_back_without_library(monkeypatch):
    """If markdown lib is unavailable, fallback parser must still render tables."""
    monkeypatch.setattr(pdf_mod, "_HAS_MARKDOWN_LIB", False)
    html = pdf_mod.markdown_to_html(SCORECARD_MD)
    assert "<table>" in html
    assert "<th>Category</th>" in html
    assert "<td>Technical Foundation</td>" in html
    assert "| Category |" not in html


def test_markdown_to_html_preserves_headings_and_lists():
    """Regression: headings and lists must still render correctly."""
    md = "## Heading\n\n- item 1\n- item 2\n"
    html = pdf_mod.markdown_to_html(md)
    assert "<h2>Heading</h2>" in html
    assert "<li>item 1</li>" in html
    assert "<li>item 2</li>" in html
