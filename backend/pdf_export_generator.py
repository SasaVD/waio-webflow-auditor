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
# Minimal, safe markdown -> HTML converter
# ---------------------------------------------------------------------------

_BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*")


def _render_inline(text: str) -> str:
    """Escape then replace **bold**."""
    escaped = _html.escape(text)
    return _BOLD_RE.sub(r"<strong>\1</strong>", escaped)


def markdown_to_html(md: str) -> str:
    """Tiny markdown converter.

    Handles:
      - ## and ### headings
      - blank-line-separated paragraphs
      - unordered lists (- or *)
      - ordered lists (1. 2. ...)
      - **bold** inline
    """
    if not md:
        return ""

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

    para_buf: list[str] = []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Blank line -> flush paragraph
        if not stripped:
            flush_paragraph(para_buf)
            i += 1
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
    """TIPR summary, top pages, and top recommendations."""
    link_analysis = report.get("link_analysis") or {}
    tipr = link_analysis.get("tipr_analysis") or {}

    if not tipr:
        return {"available": False}

    summary = tipr.get("summary") or {}
    pages = tipr.get("pages") or []
    recs = tipr.get("recommendations") or []

    # Top 10 pages by TIPR rank (already sorted best-first by engine)
    top_pages = []
    for p in pages[:10]:
        top_pages.append({
            "url": _short_url(p.get("url", ""), 60),
            "classification": (p.get("classification") or "").replace("_", " ").title(),
            "class_color": {
                "star": GREEN,
                "hoarder": "#F59E0B",
                "waster": BLUE,
                "dead weight": "#94A3B8",
                "dead_weight": "#94A3B8",
            }.get((p.get("classification") or "").lower(), "#64748B"),
            "inbound": p.get("inbound_count") or 0,
            "outbound": p.get("outbound_count") or 0,
            "score": round(p.get("pagerank_score") or 0, 1),
        })

    top_recs = []
    for r in recs[:10]:
        top_recs.append({
            "source": _short_url(r.get("source_url", ""), 45),
            "target": _short_url(r.get("target_url", ""), 45),
            "reason": r.get("reason") or "",
            "priority": (r.get("priority") or "").title(),
            "priority_color": {
                "High": SEVERITY_COLORS["high"],
                "Medium": SEVERITY_COLORS["medium"],
                "Low": SEVERITY_COLORS["low"],
            }.get((r.get("priority") or "").title(), "#64748B"),
        })

    return {
        "available": True,
        "total_pages": summary.get("total_pages") or len(pages),
        "stars": summary.get("stars") or 0,
        "hoarders": summary.get("hoarders") or 0,
        "wasters": summary.get("wasters") or 0,
        "dead_weight": summary.get("dead_weight") or 0,
        "orphan_count": summary.get("orphan_count") or 0,
        "top_pages": top_pages,
        "top_recs": top_recs,
    }


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
                slot = agg.setdefault(name, {"name": name, "salience_sum": 0.0, "count": 0, "type": e.get("type") or e.get("entity_type") or ""})
                slot["salience_sum"] += sal
                slot["count"] += 1
        entities = sorted(
            ({"name": v["name"], "salience": round(v["salience_sum"], 3), "frequency": v["count"], "type": v["type"]}
             for v in agg.values()),
            key=lambda e: (e["salience"], e["frequency"]),
            reverse=True,
        )[:10]
    else:
        entities = []
        for e in raw_entities[:10]:
            if not isinstance(e, dict):
                continue
            entities.append({
                "name": e.get("name", ""),
                "salience": round(float(e.get("salience") or 0), 3),
                "frequency": e.get("mentions_count") or e.get("frequency") or 0,
                "type": e.get("type") or e.get("entity_type") or "",
            })

    return {
        "available": bool(industry or entities),
        "industry": industry,
        "industry_confidence": round(industry_conf, 2) if isinstance(industry_conf, (int, float)) else None,
        "entities": entities,
    }


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

    zero_state = total_mentions == 0 and len(platforms) > 0

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
                aggregated.append({
                    "severity": sev.title(),
                    "severity_color": _severity_color(sev),
                    "pillar": pillar_label,
                    "check": check_name.replace("_", " ").title(),
                    "description": f.get("description") or "",
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
