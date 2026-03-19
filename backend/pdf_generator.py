"""
PDF Report Generator for WAIO Audit Tool.
Converts the audit report JSON into a branded PDF using fpdf2 (pure Python).
"""
from fpdf import FPDF
from datetime import datetime

PILLAR_META = {
    "semantic_html": "Semantic HTML",
    "structured_data": "Structured Data",
    "aeo_content": "AEO Content",
    "css_quality": "CSS Quality",
    "js_bloat": "JS Bloat",
    "accessibility": "Accessibility",
}

SEV_COLORS = {
    "critical": (220, 38, 38),
    "high": (234, 88, 12),
    "medium": (161, 98, 7),
}


def _score_color(label: str):
    l = label.lower()
    if l == "excellent": return (34, 197, 94)
    if l == "good": return (132, 204, 22)
    if l == "needs improvement": return (234, 179, 8)
    if l == "poor": return (249, 115, 22)
    return (239, 68, 68)


class AuditPDF(FPDF):
    def header(self):
        self.set_fill_color(26, 26, 46)
        self.rect(0, 0, 210, 28, 'F')
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.set_xy(12, 8)
        self.cell(0, 6, "WAIO Audit Engine", new_x="LMARGIN")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(139, 139, 158)
        self.set_xy(12, 16)
        self.cell(0, 5, "BY VEZA DIGITAL", new_x="LMARGIN")
        self.ln(20)

    def footer(self):
        self.set_y(-18)
        self.set_draw_color(229, 231, 235)
        self.line(12, self.get_y(), 198, self.get_y())
        self.ln(4)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(156, 163, 175)
        self.cell(0, 4, "WAIO Audit Engine  |  Deterministic, evidence-based Webflow analysis  |  vezadigital.com", align="C")


def _safe(text) -> str:
    if text is None:
        return ""
    return str(text).encode('latin-1', 'replace').decode('latin-1')


def _section_header(pdf, title):
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(26, 26, 46)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(229, 231, 235)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.ln(3)


def generate_pdf(report: dict) -> bytes:
    """Generate a branded PDF from the audit report dict. Returns PDF bytes."""
    pdf = AuditPDF()
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_page()

    url = report.get("url", "Unknown")
    timestamp = report.get("audit_timestamp", "")
    try:
        ts_display = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%b %d, %Y %I:%M %p UTC")
    except Exception:
        ts_display = timestamp

    overall_score = report.get("overall_score", 0)
    overall_label = report.get("overall_label", "N/A")
    summary = report.get("summary", {})
    x_start = 12

    # -- URL + timestamp --
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(26, 26, 46)
    pdf.cell(0, 7, _safe(url), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(156, 163, 175)
    pdf.cell(0, 5, _safe(ts_display), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # -- Overall score box --
    sc = _score_color(overall_label)
    y_start = pdf.get_y()

    pdf.set_fill_color(26, 26, 46)
    pdf.rect(x_start, y_start, 40, 30, 'F')
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*sc)
    pdf.set_xy(x_start, y_start + 3)
    pdf.cell(40, 12, str(overall_score), align="C")
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(x_start, y_start + 16)
    pdf.cell(40, 5, _safe(overall_label.upper()), align="C")
    pdf.set_font("Helvetica", "", 6)
    pdf.set_text_color(139, 139, 158)
    pdf.set_xy(x_start, y_start + 22)
    pdf.cell(40, 5, "Overall Health Score", align="C")

    # -- Stats next to score --
    stats = [
        ("Total Issues", summary.get("total_findings", 0), (55, 65, 81)),
        ("Critical", summary.get("critical", 0), SEV_COLORS["critical"]),
        ("High", summary.get("high", 0), SEV_COLORS["high"]),
        ("Medium", summary.get("medium", 0), SEV_COLORS["medium"]),
    ]

    stat_x = x_start + 46
    stat_w = 30
    for label, val, color in stats:
        pdf.set_fill_color(248, 249, 250)
        pdf.rect(stat_x, y_start, stat_w, 30, 'F')
        pdf.set_font("Helvetica", "B", 6)
        pdf.set_text_color(107, 114, 128)
        pdf.set_xy(stat_x, y_start + 3)
        pdf.cell(stat_w, 4, label.upper(), align="C")
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*color)
        pdf.set_xy(stat_x, y_start + 10)
        pdf.cell(stat_w, 10, str(val), align="C")
        stat_x += stat_w + 4

    pdf.set_xy(x_start, y_start + 34)

    # -- Pillar score cards --
    pdf.ln(2)
    pillar_y = pdf.get_y()
    pillar_x = x_start
    pw = 28.5
    for key, cat in report.get("categories", {}).items():
        cat_label = PILLAR_META.get(key, key)
        score = cat.get("score", 0)
        rating = cat.get("label", "N/A")
        color = _score_color(rating)
        pdf.set_fill_color(248, 249, 250)
        pdf.rect(pillar_x, pillar_y, pw, 22, 'F')
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*color)
        pdf.set_xy(pillar_x, pillar_y + 2)
        pdf.cell(pw, 8, str(score), align="C")
        pdf.set_font("Helvetica", "B", 6)
        pdf.set_text_color(55, 65, 81)
        pdf.set_xy(pillar_x, pillar_y + 10)
        pdf.cell(pw, 4, _safe(cat_label), align="C")
        pdf.set_font("Helvetica", "", 5)
        pdf.set_text_color(*color)
        pdf.set_xy(pillar_x, pillar_y + 15)
        pdf.cell(pw, 4, _safe(rating.upper()), align="C")
        pillar_x += pw + 2.5

    pdf.set_xy(x_start, pillar_y + 28)

    # -- Top Priorities --
    _section_header(pdf, "Top Priorities")
    for i, p in enumerate(summary.get("top_priorities", []), 1):
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(234, 88, 12)
        pdf.cell(8, 5, f"{i}.")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(55, 65, 81)
        pdf.multi_cell(0, 5, _safe(p), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    # -- What's Working Well --
    positives = report.get("positive_findings", [])
    if positives:
        pdf.ln(2)
        _section_header(pdf, "What's Working Well")
        for p in positives[:8]:
            text = p.get("text", p) if isinstance(p, dict) else p
            anchor = p.get("credibility_anchor") if isinstance(p, dict) else None
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(22, 101, 52)
            pdf.multi_cell(0, 5, _safe(f"  {text}"), new_x="LMARGIN", new_y="NEXT")
            if anchor:
                pdf.set_font("Helvetica", "I", 7)
                pdf.set_text_color(107, 114, 128)
                pdf.multi_cell(0, 4, _safe(f"     {anchor}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

    # -- Detailed Findings --
    pdf.ln(2)
    _section_header(pdf, "Detailed Findings")

    for cat_key, cat_val in report.get("categories", {}).items():
        cat_label = PILLAR_META.get(cat_key, cat_key)
        findings = []
        for chk in (cat_val.get("checks") or {}).values():
            if isinstance(chk, dict) and "findings" in chk:
                findings.extend(chk["findings"])
        if not findings:
            continue

        findings.sort(key=lambda f: {"critical": 0, "high": 1, "medium": 2}.get(f.get("severity", ""), 3))

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(26, 26, 46)
        pdf.cell(0, 7, _safe(f"{cat_label} ({len(findings)} issues)"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        for f in findings:
            sev = f.get("severity", "medium")
            colors = SEV_COLORS.get(sev, SEV_COLORS["medium"])

            if pdf.get_y() > 255:
                pdf.add_page()

            # Severity label
            pdf.set_font("Helvetica", "B", 6)
            pdf.set_text_color(*colors)
            pdf.cell(0, 4, sev.upper(), new_x="LMARGIN", new_y="NEXT")

            # Description
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(26, 26, 46)
            pdf.multi_cell(0, 5, _safe(f.get("description", "")), new_x="LMARGIN", new_y="NEXT")

            # Recommendation
            rec = f.get("recommendation", "")
            if rec:
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(75, 85, 99)
                pdf.multi_cell(0, 4, _safe(f"Recommendation: {rec}"), new_x="LMARGIN", new_y="NEXT")

            # Credibility anchor
            anchor = f.get("credibility_anchor")
            if anchor:
                pdf.set_font("Helvetica", "I", 6)
                pdf.set_text_color(67, 56, 202)
                pdf.multi_cell(0, 4, _safe(f"Why this matters: {anchor}"), new_x="LMARGIN", new_y="NEXT")

            pdf.ln(4)

        pdf.ln(2)

    return pdf.output()
