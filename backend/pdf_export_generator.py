"""Branded premium PDF export for WAIO audits.

Renders a 10-section stakeholder-grade PDF using Jinja2 + WeasyPrint.
Public entrypoint: `generate_branded_pdf(report: dict) -> bytes`.

All data access is defensive — every section degrades gracefully when a
field is missing so partial audits still produce a usable PDF.
"""
from __future__ import annotations

import html as _html
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from jinja2 import Environment, select_autoescape
from weasyprint import HTML

try:
    import markdown as _markdown_lib
    _HAS_MARKDOWN_LIB = True
except ImportError:
    _HAS_MARKDOWN_LIB = False

try:
    from executive_summary_generator import _translate_finding
except ImportError:
    _translate_finding = None


# ---------------------------------------------------------------------------
# Brand colors and pillar config
# ---------------------------------------------------------------------------

ACCENT = "#2820FF"
CYAN = "#30DAFF"
GREEN = "#47CD89"
BLUE = "#0194FE"

SEVERITY_COLORS = {
    "critical": "#DC2626",
    "high": "#EF4444",
    "medium": "#F59E0B",
    "low": "#0194FE",
    "positive": "#47CD89",
}

# Pillar groups mirror the landing page weight presentation
PILLAR_GROUPS = [
    {
        "name": "Search & Discovery",
        "weight_pct": 36,
        "color": ACCENT,
        "pillars": [
            ("semantic_html", "Semantic HTML", 12),
            ("structured_data", "Structured Data", 12),
            ("internal_linking", "Internal Linking", 12),
        ],
    },
    {
        "name": "AI Readiness",
        "weight_pct": 28,
        "color": CYAN,
        "pillars": [
            ("aeo_content", "AEO Content", 10),
            ("rag_readiness", "RAG Readiness", 10),
            ("agentic_protocols", "Agentic Protocols", 8),
        ],
    },
    {
        "name": "Foundations",
        "weight_pct": 26,
        "color": GREEN,
        "pillars": [
            ("accessibility", "Accessibility", 18),
            ("data_integrity", "Data Integrity", 8),
        ],
    },
    {
        "name": "UX & Performance",
        "weight_pct": 10,
        "color": BLUE,
        "pillars": [
            ("css_quality", "CSS Quality", 5),
            ("js_bloat", "JS Performance", 5),
        ],
    },
]

PILLAR_DESCRIPTIONS = {
    "semantic_html": "Checks page structure, landmarks, and heading hierarchy against W3C HTML standards.",
    "structured_data": "Validates JSON-LD and microdata markup against Schema.org types.",
    "aeo_content": "Evaluates answer-engine readiness: snippet-worthy blocks, FAQs, and entity clarity.",
    "css_quality": "Measures styling discipline — framework adoption, naming, render blockers, inline style leakage.",
    "js_bloat": "Flags third-party and first-party JavaScript that slows crawl and Core Web Vitals.",
    "accessibility": "Runs axe-core rules against WCAG 2.1 AA, covering contrast, labels, and keyboard navigation.",
    "rag_readiness": "Assesses content extractability and structure for retrieval-augmented generation pipelines.",
    "agentic_protocols": "Checks robots.txt, llms.txt, and AI agent policy signals.",
    "data_integrity": "Validates canonical tags, hreflang, sitemaps, and indexation signals.",
    "internal_linking": "Maps link graph health, orphans, anchor quality, and link depth.",
}


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _score_color(score: int | float | None) -> str:
    """Map a 0-100 score to brand score palette."""
    if score is None:
        return "#64748B"
    s = float(score)
    if s >= 90:
        return "#16A34A"
    if s >= 75:
        return "#65A30D"
    if s >= 55:
        return "#CA8A04"
    if s >= 35:
        return "#EA580C"
    return "#DC2626"


def _severity_color(severity: str) -> str:
    return SEVERITY_COLORS.get((severity or "").lower(), "#64748B")


def _short_url(url: str, length: int = 60) -> str:
    if not url:
        return ""
    if len(url) <= length:
        return url
    return url[: length - 1] + "\u2026"


def _domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.netloc or url
    except Exception:
        return url


# ---------------------------------------------------------------------------
# SVG / chart helpers — rendered inline in the PDF as real vectors
# ---------------------------------------------------------------------------

def _render_score_ring_svg(score: int, size: int = 220) -> str:
    """Render a circular score gauge as inline SVG.

    The ring track is a soft white against the dark cover background;
    the arc sweep uses the brand-aligned score color.
    """
    try:
        s = max(0, min(100, int(score)))
    except (TypeError, ValueError):
        s = 0
    color = _score_color(s)
    if s >= 80:
        track_color = "rgba(255,255,255,0.12)"
    else:
        track_color = "rgba(255,255,255,0.10)"
    radius = 88
    circumference = 2 * 3.141592653589793 * radius
    dash = (s / 100) * circumference
    gap = circumference - dash
    return f'''<svg width="{size}pt" height="{size}pt" viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg">
      <circle cx="110" cy="110" r="{radius}" fill="none" stroke="{track_color}" stroke-width="14"/>
      <circle cx="110" cy="110" r="{radius}" fill="none" stroke="{color}" stroke-width="14"
              stroke-dasharray="{dash:.2f} {gap:.2f}" stroke-dashoffset="0"
              stroke-linecap="round" transform="rotate(-90 110 110)"/>
      <text x="110" y="108" text-anchor="middle" font-family="Plus Jakarta Sans, Inter, sans-serif"
            font-size="56" font-weight="900" fill="{color}">{s}</text>
      <text x="110" y="138" text-anchor="middle" font-family="Inter, sans-serif"
            font-size="13" fill="#94A3B8" letter-spacing="1">/ 100</text>
    </svg>'''


def _render_pillar_bar_chart_svg(pillar_groups: list[dict]) -> str:
    """Horizontal bar chart of all 10 pillar scores grouped by weight bucket.

    Color-coded green/yellow/orange/red by score bucket. Weight percentage
    is labelled beside each pillar name.
    """
    # Flatten cards in display order
    rows: list[dict] = []
    for g in pillar_groups or []:
        for p in g.get("cards") or []:
            rows.append(p)
    if not rows:
        return ""

    row_h = 30
    top_pad = 18
    bottom_pad = 18
    label_w = 220
    bar_left = label_w + 10
    bar_right_pad = 60
    total_w = 720
    bar_w = total_w - bar_left - bar_right_pad
    total_h = top_pad + bottom_pad + row_h * len(rows)

    svg_parts = [
        f'<svg width="100%" viewBox="0 0 {total_w} {total_h}" xmlns="http://www.w3.org/2000/svg" '
        'font-family="Inter, system-ui, sans-serif">'
    ]
    # Light vertical gridlines at 25/50/75/100
    for pct in (25, 50, 75, 100):
        x = bar_left + (pct / 100) * bar_w
        svg_parts.append(
            f'<line x1="{x:.1f}" y1="{top_pad}" x2="{x:.1f}" y2="{total_h - bottom_pad / 2}" '
            'stroke="#E2E8F0" stroke-width="0.5" stroke-dasharray="2,3"/>'
        )
        svg_parts.append(
            f'<text x="{x:.1f}" y="{total_h - 2}" text-anchor="middle" '
            f'font-size="9" fill="#94A3B8">{pct}</text>'
        )

    for i, p in enumerate(rows):
        y = top_pad + i * row_h
        score = int(p.get("score") or 0)
        color = p.get("color") or _score_color(score)
        label = p.get("label") or ""
        weight = p.get("weight") or 0
        bar_length = max(0.0, min(1.0, score / 100)) * bar_w

        # Pillar name label
        svg_parts.append(
            f'<text x="{label_w}" y="{y + row_h / 2 + 4}" text-anchor="end" '
            f'font-size="11" font-weight="600" fill="#0F172A">{_html.escape(label)}</text>'
        )
        # Weight suffix
        svg_parts.append(
            f'<text x="{label_w}" y="{y + row_h / 2 + 16}" text-anchor="end" '
            f'font-size="9" fill="#94A3B8">{weight}% weight</text>'
        )
        # Track
        svg_parts.append(
            f'<rect x="{bar_left}" y="{y + 6}" width="{bar_w}" height="14" '
            'rx="3" ry="3" fill="#F1F5F9"/>'
        )
        # Fill
        svg_parts.append(
            f'<rect x="{bar_left}" y="{y + 6}" width="{bar_length:.1f}" height="14" '
            f'rx="3" ry="3" fill="{color}"/>'
        )
        # Score number to the right of the bar
        svg_parts.append(
            f'<text x="{bar_left + bar_w + 8}" y="{y + 18}" '
            f'font-size="12" font-weight="700" fill="{color}">{score}</text>'
        )

    svg_parts.append("</svg>")
    return "".join(svg_parts)


# ---------------------------------------------------------------------------
# Minimal, safe markdown -> HTML converter
# ---------------------------------------------------------------------------

_BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*")


def _render_inline(text: str) -> str:
    """Escape then replace **bold**."""
    escaped = _html.escape(text)
    return _BOLD_RE.sub(r"<strong>\1</strong>", escaped)


def markdown_to_html(md: str) -> str:
    """Markdown converter for the executive summary.

    Uses python-markdown with the `tables` and `fenced_code` extensions
    when available so GFM pipe-tables render as real HTML tables. Falls
    back to a minimal in-module converter when the library is missing
    (keeps local dev unblocked without the extra dep).
    """
    if not md:
        return ""

    if _HAS_MARKDOWN_LIB:
        return _markdown_lib.markdown(
            md,
            extensions=["tables", "fenced_code"],
            output_format="html5",
        )

    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)

    def flush_paragraph(buffer: list[str]) -> None:
        if not buffer:
            return
        text = " ".join(s.strip() for s in buffer if s.strip())
        if text:
            out.append(f"<p>{_render_inline(text)}</p>")
        buffer.clear()

    def _is_table_row(s: str) -> bool:
        return s.startswith("|") and s.endswith("|") and s.count("|") >= 2

    def _is_table_sep(s: str) -> bool:
        # "| --- | :---: | --- |" — cells of only dashes/colons/spaces
        if not _is_table_row(s):
            return False
        cells = [c.strip() for c in s.strip("|").split("|")]
        return all(re.fullmatch(r":?-{3,}:?", c) for c in cells) and bool(cells)

    def _split_row(s: str) -> list[str]:
        return [c.strip() for c in s.strip("|").split("|")]

    para_buf: list[str] = []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Blank line -> flush paragraph
        if not stripped:
            flush_paragraph(para_buf)
            i += 1
            continue

        # GFM pipe table: header | separator | body-rows
        if (
            _is_table_row(stripped)
            and i + 1 < n
            and _is_table_sep(lines[i + 1].strip())
        ):
            flush_paragraph(para_buf)
            headers = _split_row(stripped)
            i += 2  # skip header + separator
            body_rows: list[list[str]] = []
            while i < n and _is_table_row(lines[i].strip()):
                body_rows.append(_split_row(lines[i].strip()))
                i += 1
            table_parts = ["<table>", "<thead><tr>"]
            for h in headers:
                table_parts.append(f"<th>{_render_inline(h)}</th>")
            table_parts.append("</tr></thead><tbody>")
            for row in body_rows:
                table_parts.append("<tr>")
                for cell in row:
                    table_parts.append(f"<td>{_render_inline(cell)}</td>")
                table_parts.append("</tr>")
            table_parts.append("</tbody></table>")
            out.append("".join(table_parts))
            continue

        # Heading ###
        if stripped.startswith("### "):
            flush_paragraph(para_buf)
            out.append(f"<h3>{_render_inline(stripped[4:].strip())}</h3>")
            i += 1
            continue

        # Heading ##
        if stripped.startswith("## "):
            flush_paragraph(para_buf)
            out.append(f"<h2>{_render_inline(stripped[3:].strip())}</h2>")
            i += 1
            continue

        # Unordered list
        if re.match(r"^[-*]\s+", stripped):
            flush_paragraph(para_buf)
            items: list[str] = []
            while i < n:
                m = re.match(r"^[-*]\s+(.*)$", lines[i].strip())
                if not m:
                    break
                items.append(f"<li>{_render_inline(m.group(1).strip())}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph(para_buf)
            items = []
            while i < n:
                m = re.match(r"^\d+\.\s+(.*)$", lines[i].strip())
                if not m:
                    break
                items.append(f"<li>{_render_inline(m.group(1).strip())}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        # Paragraph continuation
        para_buf.append(stripped)
        i += 1

    flush_paragraph(para_buf)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Section context builders
# ---------------------------------------------------------------------------

def _build_cover(report: dict) -> dict:
    url = report.get("url") or report.get("primary_url") or ""
    overall_score = report.get("overall_score") or 0
    overall_label = report.get("overall_label") or "Unscored"
    cms = (
        report.get("detected_cms")
        or report.get("cms_detection", {}).get("platform")
        or "Unknown CMS"
    )
    tier = (report.get("tier") or "free").capitalize()

    # Timestamp
    ts_raw = report.get("created_at") or report.get("timestamp") or ""
    try:
        if ts_raw:
            dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            ts = dt.strftime("%B %d, %Y")
        else:
            ts = datetime.utcnow().strftime("%B %d, %Y")
    except Exception:
        ts = datetime.utcnow().strftime("%B %d, %Y")

    return {
        "url": url,
        "domain": _domain(url),
        "overall_score": overall_score,
        "overall_label": overall_label,
        "overall_color": _score_color(overall_score),
        "cms": cms,
        "tier": tier,
        "timestamp": ts,
    }


def _build_pillars(report: dict) -> list[dict]:
    """Build per-group pillar rows for the 10-pillar scorecard."""
    categories = report.get("categories") or {}
    result: list[dict] = []
    for group in PILLAR_GROUPS:
        pillar_cards = []
        for key, label, weight in group["pillars"]:
            cat = categories.get(key) or {}
            score = cat.get("score") if cat.get("score") is not None else None
            score_int = int(score) if isinstance(score, (int, float)) else 0
            pillar_cards.append({
                "key": key,
                "label": label,
                "weight": weight,
                "score": score_int,
                "label_text": cat.get("label") or "Not scored",
                "color": _score_color(score_int),
                "initial": label[:1],
            })
        result.append({
            "name": group["name"],
            "weight_pct": group["weight_pct"],
            "color": group["color"],
            "cards": pillar_cards,
        })
    return result


def _build_tipr(report: dict) -> dict:
    """TIPR summary, top pages, and top recommendations.

    TIPR data lives at the TOP LEVEL of the report as `tipr_analysis`,
    not nested under `link_analysis`. Total pages and orphan counts are
    derived from the pages list (the summary dict only carries the
    quadrant counts).
    """
    tipr = report.get("tipr_analysis") or {}
    # Legacy fallback in case an older report shape nested it
    if not tipr:
        tipr = (report.get("link_analysis") or {}).get("tipr_analysis") or {}

    if not tipr:
        return {"available": False}

    summary = tipr.get("summary") or {}
    pages = tipr.get("pages") or []
    recs = tipr.get("recommendations") or []

    # Derive totals that the engine's summary block doesn't include directly
    total_pages = summary.get("total_pages") or len(pages)
    orphan_count = summary.get("orphan_count")
    if orphan_count is None:
        orphan_count = sum(
            1 for p in pages
            if isinstance(p, dict)
            and (p.get("click_depth") == -1 or (p.get("inbound_count") or 0) == 0)
        )

    # Top 10 pages by TIPR rank
    sorted_pages = sorted(
        [p for p in pages if isinstance(p, dict)],
        key=lambda p: p.get("tipr_rank") if isinstance(p.get("tipr_rank"), (int, float)) else 999999,
    )
    top_pages = []
    for p in sorted_pages[:10]:
        classification = (p.get("classification") or "").lower()
        top_pages.append({
            "url": _short_url(p.get("url", ""), 60),
            "classification": classification.replace("_", " ").title(),
            "class_color": {
                "star": GREEN,
                "hoarder": "#F59E0B",
                "waster": BLUE,
                "dead weight": "#94A3B8",
                "dead_weight": "#94A3B8",
            }.get(classification, "#64748B"),
            "inbound": p.get("inbound_count") or 0,
            "outbound": p.get("outbound_count") or 0,
            "score": round(p.get("tipr_score") or p.get("pagerank_score") or 0, 1),
        })

    # Sort recs by priority (high > medium > low) then cap at 10
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    sorted_recs = sorted(
        [r for r in recs if isinstance(r, dict)],
        key=lambda r: priority_rank.get((r.get("priority") or "").lower(), 3),
    )
    top_recs = []
    for r in sorted_recs[:10]:
        priority = (r.get("priority") or "").lower()
        # Strip markdown bold from reason — WeasyPrint will render the escaped text
        reason_clean = re.sub(r"\*\*([^*]+?)\*\*", r"\1", r.get("reason") or "")
        top_recs.append({
            "source": _short_url(r.get("source_url", ""), 45),
            "target": _short_url(r.get("target_url", ""), 45),
            "reason": reason_clean,
            "priority": priority.title(),
            "priority_color": {
                "high": SEVERITY_COLORS["high"],
                "medium": SEVERITY_COLORS["medium"],
                "low": SEVERITY_COLORS["low"],
            }.get(priority, "#64748B"),
            "impact": r.get("expected_impact") or "",
        })

    stars = int(summary.get("stars") or 0)
    hoarders = int(summary.get("hoarders") or 0)
    wasters = int(summary.get("wasters") or 0)
    dead_weight = int(summary.get("dead_weight") or 0)

    def _pct(n: int) -> int:
        return round((n / total_pages) * 100) if total_pages else 0

    return {
        "available": True,
        "total_pages": total_pages,
        "stars": stars,
        "stars_pct": _pct(stars),
        "hoarders": hoarders,
        "hoarders_pct": _pct(hoarders),
        "wasters": wasters,
        "wasters_pct": _pct(wasters),
        "dead_weight": dead_weight,
        "dead_weight_pct": _pct(dead_weight),
        "orphan_count": orphan_count,
        "orphan_pct": _pct(orphan_count),
        "top_pages": top_pages,
        "top_recs": top_recs,
    }


_ENTITY_TYPE_LABELS = {
    "ORGANIZATION": "Organization",
    "PERSON": "Person",
    "LOCATION": "Location",
    "EVENT": "Event",
    "WORK_OF_ART": "Creative Work",
    "CONSUMER_GOOD": "Product",
    "PRICE": "Price",
    "DATE": "Date",
    "NUMBER": "Number",
    "PHONE_NUMBER": "Phone",
    "ADDRESS": "Address",
    "OTHER": "Topic",
}


def _humanize_entity_type(raw_type: str) -> str:
    if not raw_type:
        return ""
    return _ENTITY_TYPE_LABELS.get(raw_type.upper(), raw_type.replace("_", " ").title())


def _filter_entities(raw_entities: list[dict]) -> list[dict]:
    """Filter low-value entities and humanize types.

    Drops entries with salience < 0.04 and type=="OTHER" entries below 0.10.
    Entities with no type field are treated as OTHER.
    If fewer than 5 survive, relaxes the non-OTHER threshold to 0.02 but
    holds the OTHER bar at 0.10 so generic noise words don't flood back in.
    """
    def _normalize_type(e: dict) -> str:
        raw_type = e.get("type") or e.get("entity_type") or ""
        return (raw_type or "OTHER").upper()

    def _pick(threshold: float, other_threshold: float) -> list[dict]:
        out: list[dict] = []
        for e in raw_entities:
            if not isinstance(e, dict):
                continue
            sal = float(e.get("salience") or 0)
            etype = _normalize_type(e)
            if sal < threshold:
                continue
            if etype == "OTHER" and sal < other_threshold:
                continue
            out.append({
                "name": e.get("name", ""),
                "salience": round(sal, 3),
                "frequency": e.get("mentions_count") or e.get("frequency") or 0,
                "type": _humanize_entity_type(etype),
            })
        return out[:10]

    entities = _pick(0.04, 0.10)
    if len(entities) < 5:
        # Relax non-OTHER threshold only — OTHER stays strict
        entities = _pick(0.02, 0.10)
    return entities


def _build_content_intel(report: dict) -> dict:
    """Content intelligence: industry, NLP category, top site-wide entities."""
    nlp = report.get("nlp_analysis") or {}
    industry = (
        report.get("detected_industry")
        or nlp.get("detected_industry")
        or nlp.get("primary_category")
        or None
    )
    industry_conf = (
        report.get("detected_industry_confidence")
        or nlp.get("industry_confidence")
        or None
    )

    # Collect entities: prefer nlp.top_entities, else aggregate from page_entities
    raw_entities = nlp.get("top_entities") or nlp.get("entities") or []
    if not raw_entities:
        page_entities = report.get("page_entities") or {}
        agg: dict[str, dict] = {}
        for url, ents in page_entities.items():
            if not isinstance(ents, list):
                continue
            for e in ents:
                if not isinstance(e, dict):
                    continue
                name = (e.get("name") or "").strip()
                if not name:
                    continue
                sal = float(e.get("salience") or 0)
                slot = agg.setdefault(name, {"name": name, "salience": 0.0, "mentions_count": 0, "type": e.get("type") or e.get("entity_type") or ""})
                slot["salience"] += sal
                slot["mentions_count"] += 1
        raw_entities = sorted(
            agg.values(),
            key=lambda e: (e["salience"], e["mentions_count"]),
            reverse=True,
        )

    entities = _filter_entities(raw_entities)

    return {
        "available": bool(industry or entities),
        "industry": industry,
        "industry_confidence": round(industry_conf, 2) if isinstance(industry_conf, (int, float)) else None,
        "entities": entities,
    }


_BRAND_BOLD_RE = re.compile(r"\*\*([^*\n]{2,60}?)\*\*")
_BRAND_NUMBERED_RE = re.compile(r"\*\*\s*\d+\.\s+([^*\n]{2,60}?)\*\*")
_BRAND_STOPWORDS = {
    # Generic headings / section labels that appear as bold markdown
    "full-service agencies", "boutique/specialized agencies", "what to consider",
    "key features", "pricing", "overview", "summary", "pros", "cons",
    "strengths", "weaknesses", "notes", "conclusion", "introduction",
    "top agencies comparison", "key strengths", "notable mentions",
    "recommendation", "recommendations", "our pick",
    # Common section words that slip through markdown bolding
    "agency", "company", "companies", "services", "price", "rating",
    "review", "reviews", "source", "sources", "note", "notes",
    "specialties", "specialty", "founded", "headquarters", "category",
    "minimum project size", "average hourly rate",
}


def _clean_brand_candidate(raw: str) -> str:
    """Strip leading numbering, trailing punctuation, inline roles, etc."""
    s = raw.strip()
    # Strip leading "1. ", "2. "
    s = re.sub(r"^\s*\d+[.)]\s+", "", s)
    # Strip trailing punctuation and leading/trailing whitespace
    s = s.strip(" -–—:;.,()[]")
    # Drop trailing parenthetical descriptions
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    return s


def _extract_discovery_brands(engines: dict, own_brand: str, max_brands: int = 15) -> list[dict]:
    """Extract brand names from AI responses to discovery prompts.

    LLM responses routinely bold brand names using `**Brand**` markdown.
    We walk every engine's `responses_by_prompt`, collect bold matches
    from discovery-category responses (prompt IDs 1-3), filter generic
    headings, and return the top N by mention count.
    """
    if not isinstance(engines, dict):
        return []
    own_lower = (own_brand or "").strip().lower()
    counts: dict[str, int] = {}
    for engine_data in engines.values():
        if not isinstance(engine_data, dict):
            continue
        rbp = engine_data.get("responses_by_prompt") or {}
        if not isinstance(rbp, dict):
            continue
        for prompt_id, resp in rbp.items():
            # ID 4 is reputation prompt — excluded from "brands in your category"
            try:
                if int(str(prompt_id)) == 4:
                    continue
            except (TypeError, ValueError):
                pass
            text = ""
            if isinstance(resp, dict):
                text = resp.get("text") or ""
            elif isinstance(resp, str):
                text = resp
            if not text:
                continue
            # Combine both regex patterns to catch numbered + free-form bolds
            candidates = set(_BRAND_BOLD_RE.findall(text))
            for raw in candidates:
                name = _clean_brand_candidate(raw)
                if not name:
                    continue
                lower = name.lower()
                if lower == own_lower:
                    continue
                if lower in _BRAND_STOPWORDS:
                    continue
                # Skip obvious non-brand headings (long phrases with common words only)
                if len(name) > 50 or len(name) < 2:
                    continue
                # Must contain at least one letter
                if not re.search(r"[A-Za-z]", name):
                    continue
                counts[name] = counts.get(name, 0) + 1

    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:max_brands]
    return [{"name": n, "count": c} for n, c in ranked]


def _build_ai_visibility(report: dict) -> dict:
    viz = report.get("ai_visibility") or {}
    if not viz or not viz.get("brand_name"):
        return {"available": False}

    brand = viz.get("brand_name") or ""
    source = viz.get("brand_name_source") or "nlp"
    live = viz.get("live_test") or {}
    engines = live.get("engines") or {}

    # Platforms: normalize common aliases
    platform_labels = {
        "chatgpt": "ChatGPT",
        "claude": "Claude",
        "perplexity": "Perplexity",
        "gemini": "Gemini",
        "google_ai_overview": "Google AI Overview",
        "ai_overview": "Google AI Overview",
    }

    platforms = []
    total_mentions = 0
    for engine_key, erdata in engines.items():
        if not isinstance(erdata, dict):
            continue
        label = platform_labels.get(engine_key, engine_key.replace("_", " ").title())
        mentioned_in = int(erdata.get("brand_mentioned_in") or 0)
        status = erdata.get("status") or "unknown"
        total_mentions += mentioned_in
        platforms.append({
            "name": label,
            "mentions": mentioned_in,
            "status": status,
            "status_color": GREEN if status == "ok" else "#94A3B8",
        })

    # Share of Voice
    sov = viz.get("share_of_voice") or {}
    sov_rows: list[dict] = []
    if sov:
        brand_sov = float(sov.get("brand_sov") or 0) * 100
        sov_rows.append({
            "name": brand,
            "is_brand": True,
            "pct": round(brand_sov, 1),
            "mentions": sov.get("total_mentions_analyzed") or 0,
        })
        for comp_name, comp_pct in (sov.get("competitor_sov") or {}).items():
            sov_rows.append({
                "name": comp_name,
                "is_brand": False,
                "pct": round(float(comp_pct or 0) * 100, 1),
                "mentions": None,
            })
        sov_rows.sort(key=lambda r: r["pct"], reverse=True)

    # Prompts
    prompts_used = live.get("prompts_used") or []
    prompt_rows = []
    for p in prompts_used[:10]:
        if not isinstance(p, dict):
            continue
        prompt_rows.append({
            "id": p.get("id"),
            "category": (p.get("category") or "").title(),
            "text": p.get("text") or "",
        })

    # Competitive brand intelligence: who DOES get cited in discovery prompts
    discovery_brands = _extract_discovery_brands(engines, brand)

    # Status framing + estimated reach from mentions_database
    mentions_db = viz.get("mentions_database") or {}
    total_db_mentions = int(mentions_db.get("total") or 0)
    ai_search_volume = int(mentions_db.get("ai_search_volume") or 0)
    impressions = int(mentions_db.get("impressions") or 0)

    zero_state = total_mentions == 0 and total_db_mentions == 0 and len(platforms) > 0

    if zero_state:
        status_headline = "Untapped AI discovery channel"
        status_body = (
            f"{brand} is not yet appearing in AI-generated responses for "
            "category searches. This represents an untapped channel — "
            "competitors who establish AI visibility now build compounding advantage."
        )
    elif total_db_mentions > 0:
        reach_parts = []
        if ai_search_volume:
            reach_parts.append(f"{ai_search_volume:,} monthly AI searches")
        if impressions:
            reach_parts.append(f"{impressions:,} impressions tracked")
        reach = " · ".join(reach_parts) if reach_parts else "tracked impressions pending"
        status_headline = f"{total_db_mentions} AI responses cite {brand}"
        status_body = (
            f"Your brand appears in {total_db_mentions} AI-generated responses "
            f"({reach})."
        )
    else:
        status_headline = "Category reputation only"
        status_body = (
            f"{brand} is returned when directly queried, but is not cited in "
            "discovery prompts — where buyers compare options without naming brands."
        )

    return {
        "available": True,
        "brand": brand,
        "brand_source": source.replace("_", " "),
        "platforms": platforms,
        "total_mentions": total_mentions,
        "zero_state": zero_state,
        "sov_rows": sov_rows,
        "has_sov": bool(sov_rows),
        "prompts": prompt_rows,
        "discovery_brands": discovery_brands,
        "status_headline": status_headline,
        "status_body": status_body,
    }


def _build_content_optimizer(report: dict) -> dict:
    co = report.get("content_optimizer") or {}
    analyses_dict = co.get("analyses") or {}

    cards: list[dict] = []
    for key, entry in analyses_dict.items():
        if not isinstance(entry, dict) or entry.get("status") != "ok":
            continue
        result = entry.get("result") or {}
        summary = result.get("summary") or {}
        rec_counts = summary.get("recommendations_count") or {}
        terms = result.get("terms") or []

        missing_core = []
        for t in terms:
            if not isinstance(t, dict):
                continue
            rec = t.get("recommendation")
            if isinstance(rec, dict) and rec.get("type") == "add":
                classif = rec.get("classification") or t.get("classification")
                if classif in ("core", "semantic"):
                    missing_core.append({
                        "term": t.get("term"),
                        "priority": round(float(rec.get("priority") or 0), 2),
                    })
        missing_core.sort(key=lambda m: m["priority"], reverse=True)
        missing_core = missing_core[:10]

        gap_score = summary.get("content_gap_score") or 0
        cards.append({
            "url": _short_url(entry.get("url") or result.get("target_url") or "", 70),
            "keyword": entry.get("keyword") or result.get("keyword") or "",
            "gap_score": gap_score,
            "gap_color": _score_color(100 - gap_score),
            "add": rec_counts.get("add") or 0,
            "increase": rec_counts.get("increase") or 0,
            "reduce": rec_counts.get("reduce") or 0,
            "remove": rec_counts.get("remove") or 0,
            "missing_core": missing_core,
        })

    return {"available": bool(cards), "cards": cards}


def _build_clusters(report: dict) -> dict:
    sc = report.get("semantic_clusters") or {}
    if not sc:
        return {"available": False}

    clusters_raw = sc.get("clusters") or []
    cluster_rows: list[dict] = []
    gaps_rows: list[dict] = []
    total_pages = 0

    for c in clusters_raw:
        if not isinstance(c, dict):
            continue
        size = c.get("size") or len(c.get("pages") or [])
        total_pages += size
        pillar = c.get("pillar") or {}
        pillar_url = pillar.get("url") if isinstance(pillar, dict) else None
        top_ents = c.get("top_entities") or []
        top_terms = []
        for item in top_ents[:3]:
            if isinstance(item, (list, tuple)) and item:
                top_terms.append(str(item[0]))
            elif isinstance(item, dict):
                top_terms.append(item.get("name") or item.get("term") or "")

        row = {
            "name": c.get("label") or f"Cluster {c.get('id', '?')}",
            "size": size,
            "pillar": _short_url(pillar_url or "", 50) if pillar_url else "—",
            "has_pillar": bool(pillar_url),
            "top_terms": ", ".join(t for t in top_terms if t) or "—",
            "health_pct": (c.get("link_health") or {}).get("health_pct") or 0,
        }
        cluster_rows.append(row)
        if not pillar_url:
            gaps_rows.append(row)

    avg_size = (total_pages / len(cluster_rows)) if cluster_rows else 0

    return {
        "available": True,
        "total_clusters": len(cluster_rows),
        "avg_pages": round(avg_size, 1),
        "silhouette": sc.get("silhouette_score"),
        "quality": (sc.get("quality") or "").title(),
        "cluster_rows": cluster_rows,
        "gaps_rows": gaps_rows,
    }


_AXE_RULE_PREFIX_RE = re.compile(r"^axe rule '([^']+)':\s*", re.IGNORECASE)
_SCHEMA_PATH_RE = re.compile(r"\b\w+(?:\.\w+){2,}(?:\[\])?")


def _humanize_finding_description(raw: str, pillar_key: str) -> str:
    """Translate a raw finding description into an executive-friendly sentence.

    Uses the canonical translator from executive_summary_generator when
    available so the PDF text matches the on-dashboard summary wording.
    Falls back to stripping the `Axe rule '<id>':` prefix and any trailing
    Schema.org property paths.
    """
    desc = (raw or "").strip()
    if not desc:
        return ""
    if _translate_finding is not None:
        try:
            translated = _translate_finding(desc, pillar_key)
            if translated:
                return translated
        except Exception:
            pass
    # Fallback: strip raw Axe prefix and schema property paths
    cleaned = _AXE_RULE_PREFIX_RE.sub("", desc).strip()
    cleaned = _SCHEMA_PATH_RE.sub("", cleaned).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned or desc


def _build_priority_actions(report: dict) -> list[dict]:
    """Aggregate critical+high findings across all pillars, sorted by severity."""
    categories = report.get("categories") or {}
    aggregated: list[dict] = []

    pillar_labels = {
        "semantic_html": "Semantic HTML",
        "structured_data": "Structured Data",
        "aeo_content": "AEO Content",
        "css_quality": "CSS Quality",
        "js_bloat": "JS Performance",
        "accessibility": "Accessibility",
        "rag_readiness": "RAG Readiness",
        "agentic_protocols": "Agentic Protocols",
        "data_integrity": "Data Integrity",
        "internal_linking": "Internal Linking",
    }

    for pillar_key, cat in categories.items():
        if not isinstance(cat, dict):
            continue
        pillar_label = pillar_labels.get(pillar_key, pillar_key.replace("_", " ").title())
        checks = cat.get("checks") or {}
        for check_name, check in checks.items():
            if not isinstance(check, dict):
                continue
            findings = check.get("findings") or []
            for f in findings:
                if not isinstance(f, dict):
                    continue
                sev = (f.get("severity") or "").lower()
                if sev not in ("critical", "high"):
                    continue
                raw_desc = f.get("description") or ""
                description = _humanize_finding_description(raw_desc, pillar_key)
                aggregated.append({
                    "severity": sev.title(),
                    "severity_color": _severity_color(sev),
                    "pillar": pillar_label,
                    "check": check_name.replace("_", " ").title(),
                    "description": description,
                    "recommendation": f.get("recommendation") or "",
                    "credibility": f.get("credibility_anchor") or f.get("why_it_matters") or "",
                    "sev_rank": 0 if sev == "critical" else 1,
                })

    aggregated.sort(key=lambda x: x["sev_rank"])
    return aggregated[:15]


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

def _prepare_context(report: dict) -> dict:
    """Shape the report dict into the template's expected structure."""
    summary_md = report.get("executive_summary") or ""
    exec_html = markdown_to_html(summary_md) if summary_md else ""

    ctx = {
        "cover": _build_cover(report),
        "exec_html": exec_html,
        "has_exec": bool(exec_html),
        "pillar_groups": _build_pillars(report),
        "pillar_descriptions": PILLAR_DESCRIPTIONS,
        "tipr": _build_tipr(report),
        "content_intel": _build_content_intel(report),
        "ai_visibility": _build_ai_visibility(report),
        "content_optimizer": _build_content_optimizer(report),
        "clusters": _build_clusters(report),
        "priority_actions": _build_priority_actions(report),
        "current_year": datetime.utcnow().year,
        "accent": ACCENT,
        "cyan": CYAN,
        "green": GREEN,
        "blue": BLUE,
    }
    return ctx


# ---------------------------------------------------------------------------
# Jinja2 template
# ---------------------------------------------------------------------------

_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>WAIO Branded Intelligence Report — {{ cover.domain }}</title>
<style>
  @page {
    size: A4;
    margin: 18mm 16mm 20mm 16mm;
    @bottom-left {
      content: "WAIO Audit Engine — by Veza Digital";
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 8.5pt;
      color: #64748B;
    }
    @bottom-center {
      content: "{{ cover.domain }}";
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 8.5pt;
      color: #64748B;
    }
    @bottom-right {
      content: "Page " counter(page) " of " counter(pages);
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 8.5pt;
      color: #64748B;
    }
  }
  @page cover {
    margin: 0;
    @bottom-left { content: ""; }
    @bottom-center { content: ""; }
    @bottom-right { content: ""; }
  }

  * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }

  html, body {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    font-size: 10.5pt;
    color: #0F172A;
    line-height: 1.55;
    margin: 0;
    padding: 0;
  }

  h1, h2, h3, h4 {
    font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
    font-weight: 800;
    letter-spacing: -0.015em;
    margin: 0;
    color: #0F172A;
  }

  h2 {
    font-size: 22pt;
    margin-bottom: 10pt;
    page-break-after: avoid;
  }
  h3 {
    font-size: 13pt;
    margin: 14pt 0 6pt 0;
    page-break-after: avoid;
  }
  p { margin: 0 0 8pt 0; }
  strong { color: #0F172A; font-weight: 700; }
  em { color: #64748B; font-style: italic; }

  .muted { color: #64748B; }
  .tiny { font-size: 8.5pt; }
  .small { font-size: 9.5pt; }
  .mono { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 9pt; }

  .page { page-break-before: always; }
  .first-page { page-break-before: avoid; }

  /* ───── Cover ───── */
  .cover {
    page: cover;
    page-break-after: always;
    height: 297mm;
    width: 210mm;
    background: linear-gradient(160deg, #0D121C 0%, #151B28 55%, #1A2235 100%);
    color: #F1F5F9;
    padding: 22mm 18mm;
    position: relative;
  }
  .cover::before {
    content: "";
    position: absolute;
    top: -80px; right: -80px;
    width: 360px; height: 360px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(40,32,255,0.55) 0%, rgba(40,32,255,0) 70%);
  }
  .cover::after {
    content: "";
    position: absolute;
    bottom: -120px; left: -120px;
    width: 420px; height: 420px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(48,218,255,0.25) 0%, rgba(48,218,255,0) 70%);
  }
  .cover-content { position: relative; z-index: 1; }
  .wordmark {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 900;
    letter-spacing: -0.04em;
    font-size: 36pt;
    color: #FFFFFF;
  }
  .wordmark .dot { color: {{ accent }}; }
  .eyebrow {
    display: inline-block;
    margin-top: 28pt;
    padding: 5pt 12pt;
    background: rgba(40,32,255,0.22);
    border: 1px solid rgba(40,32,255,0.55);
    border-radius: 999px;
    color: #C7D2FE;
    font-size: 9pt;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .cover-url {
    margin-top: 22pt;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 28pt;
    font-weight: 800;
    color: #FFFFFF;
    word-break: break-all;
    line-height: 1.15;
  }
  .cover-meta-row {
    margin-top: 16pt;
    display: flex;
    gap: 8pt;
    flex-wrap: wrap;
  }
  .cover-chip {
    display: inline-block;
    padding: 5pt 11pt;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8pt;
    font-size: 9pt;
    color: #F1F5F9;
    letter-spacing: 0.02em;
  }
  .cover-chip.premium {
    background: rgba(40,32,255,0.25);
    border-color: rgba(40,32,255,0.55);
    color: #FFFFFF;
    font-weight: 600;
  }
  .cover-score-card {
    margin-top: 42pt;
    display: flex;
    align-items: center;
    gap: 24pt;
    padding: 24pt;
    border-radius: 18pt;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.10);
  }
  .score-circle {
    width: 120pt;
    height: 120pt;
    border-radius: 50%;
    background: conic-gradient({{ cover.overall_color }} 0% {{ cover.overall_score }}%, rgba(255,255,255,0.08) {{ cover.overall_score }}% 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .score-inner {
    width: 94pt;
    height: 94pt;
    background: #0D121C;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }
  .score-num {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 34pt;
    font-weight: 900;
    color: {{ cover.overall_color }};
    line-height: 1;
  }
  .score-of { font-size: 9pt; color: #94A3B8; margin-top: 2pt; }
  .score-label-block { color: #F1F5F9; }
  .score-label-block .eyebrow-plain {
    font-size: 8.5pt;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 4pt;
  }
  .score-label-block .big {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 24pt;
    font-weight: 800;
    color: {{ cover.overall_color }};
  }

  .trust-bar {
    position: absolute;
    bottom: 22mm;
    left: 18mm;
    right: 18mm;
    padding-top: 12pt;
    border-top: 1px solid rgba(255,255,255,0.12);
    text-align: center;
    color: #94A3B8;
    font-size: 9pt;
    letter-spacing: 0.05em;
  }

  /* ───── Section header ───── */
  .section-eyebrow {
    display: inline-block;
    color: {{ accent }};
    font-size: 8.5pt;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 4pt;
  }
  .section-divider {
    height: 2pt;
    width: 48pt;
    background: {{ accent }};
    margin: 6pt 0 16pt 0;
    border-radius: 2pt;
  }
  .lede {
    font-size: 11pt;
    color: #475569;
    margin-bottom: 14pt;
  }

  /* ───── Tables ───── */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 10pt 0 12pt 0;
    font-size: 9.5pt;
    page-break-inside: auto;
  }
  th {
    text-align: left;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 700;
    font-size: 8.5pt;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 8pt 10pt;
    border-bottom: 1.5pt solid #E2E8F0;
  }
  td {
    padding: 8pt 10pt;
    border-bottom: 1px solid #F1F5F9;
    vertical-align: top;
  }
  tr { page-break-inside: avoid; }

  .pill {
    display: inline-block;
    padding: 2pt 8pt;
    border-radius: 999px;
    font-size: 8pt;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: 0.04em;
  }

  /* ───── Pillar scorecard ───── */
  .group-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 10pt 14pt;
    border-radius: 10pt;
    margin-top: 14pt;
    margin-bottom: 10pt;
    background: #F8FAFC;
    border-left: 4pt solid var(--group-color);
  }
  .group-header .gname {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 13pt;
    font-weight: 800;
    color: #0F172A;
  }
  .group-header .gweight {
    font-size: 10pt;
    color: #64748B;
    font-weight: 600;
  }
  .pillar-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10pt;
  }
  .pillar-grid.two-col { grid-template-columns: 1fr 1fr; }
  .pillar-card {
    padding: 12pt;
    border: 1px solid #E2E8F0;
    border-radius: 10pt;
    background: #FFFFFF;
  }
  .pillar-head {
    display: flex;
    align-items: center;
    gap: 8pt;
    margin-bottom: 8pt;
  }
  .pillar-initial {
    width: 26pt; height: 26pt;
    border-radius: 50%;
    background: #EEF2FF;
    color: {{ accent }};
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 800;
    font-size: 12pt;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }
  .pillar-name { font-weight: 700; font-size: 10pt; color: #0F172A; }
  .pillar-weight { font-size: 8pt; color: #94A3B8; }
  .pillar-score {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 24pt;
    font-weight: 800;
  }
  .pillar-status {
    font-size: 8.5pt;
    color: #64748B;
    margin-bottom: 6pt;
  }
  .pillar-bar {
    height: 5pt;
    background: #F1F5F9;
    border-radius: 3pt;
    overflow: hidden;
  }
  .pillar-fill { height: 100%; border-radius: 3pt; }

  /* ───── KPI strip ───── */
  .kpi-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10pt;
    margin-bottom: 14pt;
  }
  .kpi {
    padding: 12pt;
    border: 1px solid #E2E8F0;
    border-radius: 10pt;
    background: #F8FAFC;
  }
  .kpi .k-value {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 20pt;
    font-weight: 800;
    color: #0F172A;
  }
  .kpi .k-label {
    font-size: 8.5pt;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 3pt;
  }

  /* ───── Finding card ───── */
  .action {
    padding: 12pt 14pt;
    border-left: 4pt solid var(--action-color);
    background: #F8FAFC;
    border-radius: 0 10pt 10pt 0;
    margin-bottom: 10pt;
    page-break-inside: avoid;
  }
  .action-head {
    display: flex;
    gap: 8pt;
    align-items: center;
    margin-bottom: 4pt;
  }
  .action-pillar {
    font-size: 9pt;
    color: #64748B;
    font-weight: 600;
  }
  .action-desc { font-weight: 700; color: #0F172A; margin-bottom: 4pt; }
  .action-rec { font-size: 10pt; color: #334155; margin-bottom: 4pt; }
  .action-cred { font-size: 9pt; font-style: italic; color: #64748B; }

  /* ───── Info box ───── */
  .infobox {
    padding: 12pt 14pt;
    border-radius: 10pt;
    background: #EEF2FF;
    border: 1px solid rgba(40,32,255,0.25);
    color: #1E1B4B;
    margin-bottom: 12pt;
  }
  .infobox.warn {
    background: #FEF3C7;
    border-color: #F59E0B;
    color: #78350F;
  }
  .infobox .title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 800;
    margin-bottom: 4pt;
    font-size: 11pt;
  }

  .exec ul, .exec ol { padding-left: 18pt; margin: 6pt 0 10pt 0; }
  .exec li { margin-bottom: 3pt; }
  .exec h2 { font-size: 14pt; margin-top: 14pt; }
  .exec h3 { font-size: 12pt; margin-top: 12pt; color: {{ accent }}; }
  .exec table {
    width: 100%;
    border-collapse: collapse;
    margin: 12pt 0;
    font-size: 10pt;
  }
  .exec th, .exec td {
    border: 1px solid #E2E8F0;
    padding: 6pt 8pt;
    text-align: left;
    vertical-align: top;
  }
  .exec th {
    background: #F8FAFC;
    font-weight: 600;
    color: #0F172A;
  }
  .exec tbody tr:nth-child(even) td {
    background: #FAFBFC;
  }

  .badge {
    display: inline-block;
    padding: 2pt 8pt;
    border-radius: 6pt;
    font-size: 8pt;
    font-weight: 700;
    background: #EEF2FF;
    color: {{ accent }};
    letter-spacing: 0.04em;
  }

  .footer-sig {
    margin-top: 20pt;
    padding-top: 10pt;
    border-top: 1px solid #E2E8F0;
    color: #64748B;
    font-size: 9pt;
  }

  /* ───── Optimizer card ───── */
  .opt-card {
    padding: 14pt;
    border: 1px solid #E2E8F0;
    border-radius: 12pt;
    margin-bottom: 12pt;
    page-break-inside: avoid;
    background: #FFFFFF;
  }
  .opt-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10pt;
    gap: 12pt;
  }
  .opt-url { font-weight: 700; color: #0F172A; font-size: 10pt; word-break: break-all; }
  .opt-kw { font-size: 9pt; color: #64748B; margin-top: 2pt; }
  .opt-gap {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 22pt;
    font-weight: 800;
    text-align: right;
    flex-shrink: 0;
  }
  .opt-gap .lab { display: block; font-size: 8pt; color: #94A3B8; letter-spacing: 0.05em; text-transform: uppercase; }
  .opt-counts {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8pt;
    margin: 10pt 0;
  }
  .opt-counts .cell {
    padding: 8pt;
    background: #F8FAFC;
    border-radius: 8pt;
    text-align: center;
  }
  .opt-counts .num { font-weight: 800; font-size: 14pt; font-family: 'Plus Jakarta Sans', sans-serif; }
  .opt-counts .lab { font-size: 8pt; color: #64748B; text-transform: uppercase; letter-spacing: 0.04em; }

  .chip-list .chip {
    display: inline-block;
    padding: 3pt 9pt;
    border-radius: 999px;
    background: #EEF2FF;
    color: {{ accent }};
    margin: 2pt 4pt 2pt 0;
    font-size: 9pt;
    font-weight: 600;
  }
</style>
</head>
<body>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- 1. COVER -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="cover">
  <div class="cover-content">
    <div class="wordmark">WAIO<span class="dot">.</span></div>
    <div class="eyebrow">Branded Intelligence Report</div>
    <div class="cover-url">{{ cover.url or cover.domain or "—" }}</div>
    <div class="cover-meta-row">
      <span class="cover-chip">{{ cover.cms }}</span>
      <span class="cover-chip">{{ cover.timestamp }}</span>
      <span class="cover-chip premium">{{ cover.tier }}</span>
    </div>

    <div class="cover-score-card">
      <div class="score-circle">
        <div class="score-inner">
          <div class="score-num">{{ cover.overall_score }}</div>
          <div class="score-of">/ 100</div>
        </div>
      </div>
      <div class="score-label-block">
        <div class="eyebrow-plain">Overall Audit Score</div>
        <div class="big">{{ cover.overall_label }}</div>
        <div class="small muted" style="margin-top: 6pt;">10 deterministic pillars · evidence-based scoring</div>
      </div>
    </div>
  </div>
  <div class="trust-bar">
    Validated against W3C · WCAG 2.1 · Schema.org · Google Web Vitals
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- 2. EXECUTIVE SUMMARY -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="page">
  <div class="section-eyebrow">Section 02</div>
  <h2>Executive Summary</h2>
  <div class="section-divider"></div>
  <p class="lede">A narrative walk-through of strategic context, diagnosis, and priority actions — translated from the raw audit data by the WAIO summary engine.</p>

  <div class="exec">
    {% if has_exec %}
      {{ exec_html | safe }}
    {% else %}
      <p class="muted">Executive summary not yet generated for this audit. Trigger the summary regeneration endpoint once enrichment (link intelligence + AI visibility) completes.</p>
    {% endif %}
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- 3. 10-PILLAR SCORECARD -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="page">
  <div class="section-eyebrow">Section 03</div>
  <h2>10-Pillar Scorecard</h2>
  <div class="section-divider"></div>
  <p class="lede">Every pillar is a deterministic check against published standards. Groups below match the WAIO weighting model.</p>

  {% for group in pillar_groups %}
    <div class="group-header" style="--group-color: {{ group.color }};">
      <div class="gname">{{ group.name }}</div>
      <div class="gweight">{{ group.weight_pct }}% of overall score</div>
    </div>
    <div class="pillar-grid {% if group.cards|length == 2 %}two-col{% endif %}">
      {% for p in group.cards %}
        <div class="pillar-card">
          <div class="pillar-head">
            <div class="pillar-initial" style="background: {{ p.color }}22; color: {{ p.color }};">{{ p.initial }}</div>
            <div>
              <div class="pillar-name">{{ p.label }}</div>
              <div class="pillar-weight">{{ p.weight }}% weight</div>
            </div>
          </div>
          <div class="pillar-score" style="color: {{ p.color }};">{{ p.score }}</div>
          <div class="pillar-status">{{ p.label_text }}</div>
          <div class="pillar-bar">
            <div class="pillar-fill" style="width: {{ p.score }}%; background: {{ p.color }};"></div>
          </div>
        </div>
      {% endfor %}
    </div>
  {% endfor %}
</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- 4. LINK INTELLIGENCE (TIPR) -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="page">
  <div class="section-eyebrow">Section 04</div>
  <h2>Link Intelligence — TIPR Analysis</h2>
  <div class="section-divider"></div>
  <p class="lede">True Internal PageRank (TIPR) ranks every page by authority flow and discovery depth, then classifies each into a quadrant.</p>

  {% if not tipr.available %}
    <div class="infobox warn">
      <div class="title">TIPR not yet computed</div>
      <div>Run enrichment (DataForSEO crawl → link graph rebuild) to populate per-page authority scores and link recommendations.</div>
    </div>
  {% else %}
    <div class="kpi-strip">
      <div class="kpi"><div class="k-value">{{ tipr.total_pages }}</div><div class="k-label">Pages scored</div></div>
      <div class="kpi"><div class="k-value" style="color: {{ green }};">{{ tipr.stars }}</div><div class="k-label">Stars</div></div>
      <div class="kpi"><div class="k-value" style="color: #F59E0B;">{{ tipr.hoarders }}</div><div class="k-label">Hoarders</div></div>
      <div class="kpi"><div class="k-value" style="color: #94A3B8;">{{ tipr.orphan_count }}</div><div class="k-label">Orphans</div></div>
    </div>

    <h3>Top 10 Pages by TIPR Score</h3>
    <table>
      <thead>
        <tr><th>URL</th><th>Class</th><th style="text-align:right;">Inbound</th><th style="text-align:right;">Outbound</th><th style="text-align:right;">Score</th></tr>
      </thead>
      <tbody>
        {% for p in tipr.top_pages %}
          <tr>
            <td class="mono">{{ p.url }}</td>
            <td><span class="pill" style="background: {{ p.class_color }};">{{ p.classification }}</span></td>
            <td style="text-align:right;">{{ p.inbound }}</td>
            <td style="text-align:right;">{{ p.outbound }}</td>
            <td style="text-align:right;"><strong>{{ p.score }}</strong></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>

    {% if tipr.top_recs %}
      <h3>Top 10 Interlinking Recommendations</h3>
      <table>
        <thead>
          <tr><th>Priority</th><th>From</th><th>To</th><th>Reason</th></tr>
        </thead>
        <tbody>
          {% for r in tipr.top_recs %}
            <tr>
              <td><span class="pill" style="background: {{ r.priority_color }};">{{ r.priority }}</span></td>
              <td class="mono tiny">{{ r.source }}</td>
              <td class="mono tiny">{{ r.target }}</td>
              <td class="small">{{ r.reason }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    {% endif %}
  {% endif %}
</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- 5. CONTENT INTELLIGENCE -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="page">
  <div class="section-eyebrow">Section 05</div>
  <h2>Content Intelligence</h2>
  <div class="section-divider"></div>
  <p class="lede">These are the entities Google's own NLP models associate with your site — powered by the Cloud Natural Language API.</p>

  {% if not content_intel.available %}
    <div class="infobox warn">
      <div class="title">NLP enrichment not computed</div>
      <div>Google NLP classification + entity analysis have not yet been run for this audit.</div>
    </div>
  {% else %}
    {% if content_intel.industry %}
      <div class="infobox">
        <div class="title">Detected Industry</div>
        <div>
          <strong>{{ content_intel.industry }}</strong>
          {% if content_intel.industry_confidence %}
            <span class="muted small"> · confidence {{ content_intel.industry_confidence }}</span>
          {% endif %}
        </div>
      </div>
    {% endif %}

    {% if content_intel.entities %}
      <h3>Top Site-Wide Entities</h3>
      <table>
        <thead>
          <tr><th>#</th><th>Entity</th><th>Type</th><th style="text-align:right;">Salience</th><th style="text-align:right;">Frequency</th></tr>
        </thead>
        <tbody>
          {% for e in content_intel.entities %}
            <tr>
              <td class="muted">{{ loop.index }}</td>
              <td><strong>{{ e.name }}</strong></td>
              <td class="tiny muted">{{ e.type }}</td>
              <td style="text-align:right;">{{ e.salience }}</td>
              <td style="text-align:right;">{{ e.frequency }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    {% endif %}
  {% endif %}
</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- 6. AI VISIBILITY -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="page">
  <div class="section-eyebrow">Section 06</div>
  <h2>AI Visibility Report</h2>
  <div class="section-divider"></div>
  <p class="lede">How your brand appears in answers from ChatGPT, Claude, Perplexity, Gemini, and Google AI Overview.</p>

  {% if not ai_visibility.available %}
    <div class="infobox warn">
      <div class="title">AI Visibility not computed</div>
      <div>Run the AI Visibility analysis to benchmark your brand against competitors across five LLM platforms.</div>
    </div>
  {% else %}
    <div class="infobox">
      <div class="title">Brand: {{ ai_visibility.brand }}</div>
      <div class="small">Source: {{ ai_visibility.brand_source }}</div>
    </div>

    <h3>Platforms Tested</h3>
    <table>
      <thead>
        <tr><th>Platform</th><th>Status</th><th style="text-align:right;">Prompts with Brand Mention</th></tr>
      </thead>
      <tbody>
        {% for p in ai_visibility.platforms %}
          <tr>
            <td><strong>{{ p.name }}</strong></td>
            <td><span class="pill" style="background: {{ p.status_color }};">{{ p.status|upper }}</span></td>
            <td style="text-align:right;"><strong>{{ p.mentions }}</strong></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>

    {% if ai_visibility.zero_state %}
      <div class="infobox warn">
        <div class="title">Zero-citation opportunity</div>
        <div>Zero AI citations across 5 platforms means every competitor who gets cited is stealing discovery demand that could be yours. The priority actions in Section 9 target the exact prompts to win.</div>
      </div>
    {% endif %}

    {% if ai_visibility.has_sov %}
      <h3>Share of Voice</h3>
      <table>
        <thead>
          <tr><th>Brand</th><th style="text-align:right;">Share %</th><th style="text-align:right;">Mentions analyzed</th></tr>
        </thead>
        <tbody>
          {% for r in ai_visibility.sov_rows %}
            <tr>
              <td>{% if r.is_brand %}<strong style="color: {{ accent }};">{{ r.name }}</strong> <span class="badge">You</span>{% else %}{{ r.name }}{% endif %}</td>
              <td style="text-align:right;"><strong>{{ r.pct }}%</strong></td>
              <td style="text-align:right;" class="muted">{{ r.mentions if r.mentions is not none else "—" }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    {% endif %}

    {% if ai_visibility.prompts %}
      <h3>Top Discovery Prompts Tested</h3>
      <table>
        <thead>
          <tr><th>#</th><th>Category</th><th>Prompt</th></tr>
        </thead>
        <tbody>
          {% for p in ai_visibility.prompts %}
            <tr>
              <td class="muted">{{ p.id }}</td>
              <td><span class="badge">{{ p.category }}</span></td>
              <td class="small">{{ p.text }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    {% endif %}
  {% endif %}
</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- 7. CONTENT OPTIMIZER -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="page">
  <div class="section-eyebrow">Section 07</div>
  <h2>Content Optimizer Summaries</h2>
  <div class="section-divider"></div>
  <p class="lede">WDF*IDF-driven content gap analysis for each optimized page.</p>

  {% if not content_optimizer.available %}
    <div class="infobox warn">
      <div class="title">No content optimization analyses found</div>
      <div>Run the Content Optimizer from the dashboard (Content → Optimizer) to generate per-page term gap analysis vs. top-ranking competitors.</div>
    </div>
  {% else %}
    {% for c in content_optimizer.cards %}
      <div class="opt-card">
        <div class="opt-header">
          <div>
            <div class="opt-url">{{ c.url }}</div>
            <div class="opt-kw">Keyword: <strong>{{ c.keyword }}</strong></div>
          </div>
          <div class="opt-gap" style="color: {{ c.gap_color }};">
            {{ c.gap_score }}%
            <span class="lab">Content gap</span>
          </div>
        </div>
        <div class="opt-counts">
          <div class="cell"><div class="num" style="color: {{ green }};">{{ c.add }}</div><div class="lab">Add</div></div>
          <div class="cell"><div class="num" style="color: {{ blue }};">{{ c.increase }}</div><div class="lab">Increase</div></div>
          <div class="cell"><div class="num" style="color: #F59E0B;">{{ c.reduce }}</div><div class="lab">Reduce</div></div>
          <div class="cell"><div class="num" style="color: #DC2626;">{{ c.remove }}</div><div class="lab">Remove</div></div>
        </div>
        {% if c.missing_core %}
          <div class="small muted" style="margin-bottom: 4pt;"><strong style="color: #0F172A;">Top missing core terms:</strong></div>
          <div class="chip-list">
            {% for m in c.missing_core %}<span class="chip">{{ m.term }}</span>{% endfor %}
          </div>
        {% endif %}
      </div>
    {% endfor %}
  {% endif %}
</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- 8. TOPIC CLUSTERS -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="page">
  <div class="section-eyebrow">Section 08</div>
  <h2>Topic Clusters</h2>
  <div class="section-divider"></div>
  <p class="lede">Semantic clusters discovered across your site, ranked by link-health and size.</p>

  {% if not clusters.available %}
    <div class="infobox warn">
      <div class="title">Clustering not available</div>
      <div>Semantic clusters require at least 10 crawled pages with entity or content data. Re-run enrichment once more pages are indexed.</div>
    </div>
  {% else %}
    <div class="kpi-strip">
      <div class="kpi"><div class="k-value">{{ clusters.total_clusters }}</div><div class="k-label">Clusters</div></div>
      <div class="kpi"><div class="k-value">{{ clusters.avg_pages }}</div><div class="k-label">Avg pages / cluster</div></div>
      <div class="kpi"><div class="k-value">{{ clusters.silhouette if clusters.silhouette is not none else "—" }}</div><div class="k-label">Silhouette score</div></div>
      <div class="kpi"><div class="k-value">{{ clusters.quality or "—" }}</div><div class="k-label">Quality</div></div>
    </div>

    <h3>All Clusters</h3>
    <table>
      <thead>
        <tr><th>Cluster</th><th style="text-align:right;">Pages</th><th>Pillar page</th><th>Top terms</th><th style="text-align:right;">Link Health</th></tr>
      </thead>
      <tbody>
        {% for c in clusters.cluster_rows %}
          <tr>
            <td><strong>{{ c.name }}</strong></td>
            <td style="text-align:right;">{{ c.size }}</td>
            <td class="mono tiny">{{ c.pillar }}</td>
            <td class="small">{{ c.top_terms }}</td>
            <td style="text-align:right;">{{ c.health_pct }}%</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>

    {% if clusters.gaps_rows %}
      <h3>Content Gap: Clusters Without a Pillar</h3>
      <table>
        <thead>
          <tr><th>Cluster</th><th style="text-align:right;">Orphaned Pages</th><th>Top terms</th></tr>
        </thead>
        <tbody>
          {% for c in clusters.gaps_rows %}
            <tr>
              <td><strong>{{ c.name }}</strong></td>
              <td style="text-align:right;">{{ c.size }}</td>
              <td class="small">{{ c.top_terms }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    {% endif %}
  {% endif %}
</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- 9. PRIORITY ACTIONS -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="page">
  <div class="section-eyebrow">Section 09</div>
  <h2>Priority Action Items</h2>
  <div class="section-divider"></div>
  <p class="lede">Top critical and high-severity findings across all 10 pillars, sorted by impact. Every action cites a verified standard.</p>

  {% if not priority_actions %}
    <div class="infobox">
      <div class="title">No critical or high-severity findings</div>
      <div>Site scores well on the weighted pillars. Review the full findings list in the dashboard for medium-severity refinements.</div>
    </div>
  {% else %}
    {% for a in priority_actions %}
      <div class="action" style="--action-color: {{ a.severity_color }};">
        <div class="action-head">
          <span class="pill" style="background: {{ a.severity_color }};">{{ a.severity }}</span>
          <span class="action-pillar">{{ a.pillar }} · {{ a.check }}</span>
        </div>
        <div class="action-desc">{{ a.description }}</div>
        {% if a.recommendation %}<div class="action-rec">{{ a.recommendation }}</div>{% endif %}
        {% if a.credibility %}<div class="action-cred">{{ a.credibility }}</div>{% endif %}
      </div>
    {% endfor %}
  {% endif %}
</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- 10. METHODOLOGY -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="page">
  <div class="section-eyebrow">Section 10</div>
  <h2>Methodology</h2>
  <div class="section-divider"></div>
  <p class="lede">Zero AI guessing. Every pillar is a reproducible check against verified standards.</p>

  <h3>The 10 Deterministic Pillars</h3>
  <table>
    <thead><tr><th>Pillar</th><th>What it audits</th></tr></thead>
    <tbody>
      {% for key, desc in pillar_descriptions.items() %}
        <tr>
          <td><strong>{{ key.replace("_", " ").title() }}</strong></td>
          <td class="small">{{ desc }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>

  <h3>Scoring Weights</h3>
  <p>Weights reflect how each pillar affects real-world SEO and AI discovery outcomes. Accessibility carries the highest weight (18%) because WCAG failures cascade into SEO, legal, and conversion risk. Link architecture, semantic HTML, and structured data each carry 12% because they directly control crawlability and machine understanding.</p>

  <h3>Credibility Anchors</h3>
  <p>Every finding cites a primary source:</p>
  <ul>
    <li><strong>W3C</strong> — HTML Living Standard, validator rulesets</li>
    <li><strong>WCAG 2.1</strong> — Web Content Accessibility Guidelines (via axe-core)</li>
    <li><strong>Schema.org</strong> — official JSON-LD type definitions</li>
    <li><strong>Google Web Vitals</strong> — LCP, INP, CLS thresholds and documentation</li>
    <li><strong>Google Search Central</strong> — crawling, rendering, and indexing guidance</li>
  </ul>

  <div class="infobox">
    <div class="title">Zero AI guessing</div>
    <div>None of the 10 pillars calls an LLM. AI enrichment layers (NLP entities, AI Visibility) are separate from the deterministic pillars that drive the overall score — and are clearly labeled as such throughout this report.</div>
  </div>

  <div class="footer-sig">
    Veza Digital · WAIO Audit Engine · {{ current_year }}
  </div>
</div>

</body>
</html>
"""


_jinja_env = Environment(
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def generate_branded_pdf(report: dict[str, Any]) -> bytes:
    """Render a 10-section branded premium audit PDF. Returns PDF bytes."""
    ctx = _prepare_context(report or {})
    template = _jinja_env.from_string(_TEMPLATE)
    html_string = template.render(**ctx)
    pdf_bytes = HTML(string=html_string).write_pdf()
    return pdf_bytes
