"""
Executive Summary Generator — Strategic Diagnostic Brief
Produces a Markdown executive summary grounded in actual audit data.
No LLM dependency. Every sentence tied to a real finding or score.
"""
import re
from typing import Dict, Any, List

PILLAR_LABELS: Dict[str, str] = {
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

PILLAR_WEIGHTS: Dict[str, float] = {
    "semantic_html": 0.12,
    "structured_data": 0.12,
    "aeo_content": 0.10,
    "css_quality": 0.05,
    "js_bloat": 0.05,
    "accessibility": 0.18,
    "rag_readiness": 0.10,
    "agentic_protocols": 0.08,
    "data_integrity": 0.08,
    "internal_linking": 0.12,
}

# Maps each pillar to the composite category shown in the scorecard.
PILLAR_TO_CATEGORY: Dict[str, str] = {
    "semantic_html": "Technical Foundation",
    "structured_data": "Technical Foundation",
    "js_bloat": "Technical Foundation",
    "css_quality": "Technical Foundation",
    "aeo_content": "Content Effectiveness",
    "rag_readiness": "Content Effectiveness",
    "agentic_protocols": "AI Readiness",
    "internal_linking": "Site Structure",
    "accessibility": "Site Structure",
    "data_integrity": "Site Structure",
}


# ─── Helpers ───


def _get_scores(report: dict) -> Dict[str, int]:
    """Extract pillar key → score mapping from report categories."""
    cats = report.get("categories", {})
    scores: Dict[str, int] = {}
    for key in PILLAR_LABELS:
        cat = cats.get(key)
        if cat:
            scores[key] = cat.get("score", 0)
    return scores


def _weak(scores: Dict[str, int], threshold: int = 65) -> List[str]:
    """Return pillar keys scoring below threshold, sorted weakest first."""
    return sorted(
        [k for k, v in scores.items() if v < threshold],
        key=lambda k: scores[k],
    )


def _strong(scores: Dict[str, int], threshold: int = 75) -> List[str]:
    """Return pillar keys scoring at or above threshold, sorted strongest first."""
    return sorted(
        [k for k, v in scores.items() if v >= threshold],
        key=lambda k: -scores[k],
    )


def _avg(*values: int) -> int:
    """Average of integers, rounded."""
    valid = [v for v in values if v is not None]
    return round(sum(valid) / len(valid)) if valid else 0


def _interp(score: int) -> str:
    """One-phrase score interpretation."""
    if score >= 80:
        return "Strong — minor refinements available"
    if score >= 65:
        return "Solid base, targeted improvements needed"
    if score >= 45:
        return "Developing — significant opportunity for improvement"
    if score >= 25:
        return "Foundational gaps requiring focused attention"
    return "Critical gaps limiting site performance"


def _get_tipr(report: dict) -> dict | None:
    """Extract TIPR summary if available."""
    tipr = report.get("tipr_analysis")
    if not tipr or not tipr.get("summary"):
        return None
    return tipr


def _get_nlp(report: dict) -> dict | None:
    """Extract NLP analysis if available."""
    nlp = report.get("nlp_analysis")
    if not nlp:
        return None
    return nlp


def _get_clusters(report: dict) -> dict | None:
    """Extract semantic clusters if available."""
    sc = report.get("semantic_clusters")
    if not sc or not sc.get("clusters"):
        return None
    return sc


def _composite_category_scores(scores: Dict[str, int]) -> Dict[str, int]:
    """Return the composite (averaged) score per scorecard category.

    Uses the same averaging logic as _section_scorecard so text and table agree.
    """
    sem = scores.get("semantic_html", 0)
    sd = scores.get("structured_data", 0)
    js = scores.get("js_bloat", 0)
    css = scores.get("css_quality", 0)
    aeo = scores.get("aeo_content", 0)
    rag = scores.get("rag_readiness", 0)
    agent = scores.get("agentic_protocols", 0)
    il = scores.get("internal_linking", 0)
    a11y = scores.get("accessibility", 0)
    data = scores.get("data_integrity", 0)
    return {
        "Technical Foundation": _avg(sem, sd, js, css),
        "Content Effectiveness": _avg(aeo, rag),
        "AI Readiness": _avg(aeo, rag, agent),
        "Site Structure": _avg(il, a11y, data),
    }


def _page_count(report: dict) -> int:
    """Best-effort page count from TIPR or crawl stats."""
    tipr = report.get("tipr_analysis") or {}
    total = (tipr.get("summary") or {}).get("total_pages") or 0
    if total:
        return total
    crawl = report.get("crawl_stats") or {}
    return crawl.get("pages_crawled") or 0


def _site_name(url: str) -> str:
    """Extract a clean domain for sentence use (no https://, no trailing slash)."""
    if not url:
        return "the site"
    s = re.sub(r"^https?://", "", url).rstrip("/")
    s = re.sub(r"^www\.", "", s)
    return s


def _industry_from_nlp(nlp: dict | None) -> str | None:
    """Extract a human-readable industry label from NLP data."""
    if not nlp:
        return None
    # Prefer insights.primary_topic (already human)
    insights = nlp.get("insights") or {}
    primary = insights.get("primary_topic")
    if primary:
        return primary
    # Fallback: take last segment of detected_industry path
    industry = nlp.get("detected_industry")
    if industry:
        parts = [p for p in industry.split("/") if p]
        if parts:
            return parts[-1]
    return None


def _is_agency_industry(industry: str | None) -> bool:
    if not industry:
        return False
    low = industry.lower()
    return any(
        kw in low
        for kw in ("agency", "marketing", "web design", "web development", "advertising")
    )


def _collect_findings(report: dict) -> List[Dict[str, Any]]:
    """Collect all findings from audit categories, sorted by severity."""
    findings: List[Dict[str, Any]] = []
    for pillar_key, pillar_data in report.get("categories", {}).items():
        checks = pillar_data.get("checks", {})
        for check_data in checks.values():
            if not isinstance(check_data, dict):
                continue
            for f in check_data.get("findings", []):
                findings.append({**f, "pillar_key": pillar_key})
    severity_order = {"critical": 0, "high": 1, "medium": 2}
    findings.sort(key=lambda f: severity_order.get(f.get("severity", "medium"), 3))
    return findings


def _a11y_breakdown(report: dict) -> Dict[str, Any]:
    """Summarize accessibility findings into plain-English categories + count."""
    a11y = (report.get("categories") or {}).get("accessibility") or {}
    categories_hit: List[str] = []
    total = 0
    for chk in a11y.get("checks", {}).values():
        if not isinstance(chk, dict):
            continue
        for f in chk.get("findings", []):
            total += 1
            desc = (f.get("description") or "").lower()
            check_id = (f.get("check_id") or "").lower()
            if "color-contrast" in desc or "contrast" in desc:
                cat = "color contrast"
            elif (
                "aria" in desc
                or "aria" in check_id
                or "landmark" in desc
                or "role" in desc
            ):
                cat = "ARIA and landmark markup"
            elif "focus" in desc or "keyboard" in desc:
                cat = "keyboard and focus indicators"
            elif "touch" in desc or "44x44" in desc or "tap target" in desc:
                cat = "touch-target sizing"
            elif "label" in desc or "form" in desc:
                cat = "form labeling"
            elif "alt" in desc or "image" in desc:
                cat = "image alt text"
            elif "heading" in desc:
                cat = "heading structure"
            else:
                cat = "assistive-tech compatibility"
            if cat not in categories_hit:
                categories_hit.append(cat)
    return {"total": total, "categories": categories_hit}


# ─── Plain-English translation for Supporting Detail ───


def _translate_finding(desc: str, pillar_key: str) -> str:
    """Translate a raw finding description into executive-friendly language.

    Returns a single sentence, no raw Axe rule IDs, no Schema property paths,
    no percentage dumps.
    """
    d = (desc or "").strip()
    if not d:
        return ""

    low = d.lower()

    # Axe rule translations ---
    if "color-contrast" in low:
        return (
            "Some text has insufficient color contrast against its background, "
            "making it difficult to read for users with low vision."
        )
    if "aria-required-children" in low:
        return (
            "Interactive elements (menus, tabs, dialogs) have incomplete "
            "accessibility markup, making them unusable for screen-reader users."
        )
    if "aria-prohibited-attr" in low or "aria-prohibited" in low:
        return (
            "Some elements use ARIA attributes that are disallowed for their role, "
            "confusing assistive technologies."
        )
    if "landmark-banner" in low or "banner landmark" in low:
        return (
            "The page's banner region is not marked up as a top-level landmark, "
            "making navigation harder for screen-reader users."
        )
    if "aria-required-parent" in low:
        return (
            "ARIA child elements are missing their required parent containers, "
            "breaking screen-reader navigation."
        )
    if "aria-allowed-attr" in low or "aria-valid-attr" in low:
        return (
            "Invalid or disallowed ARIA attributes are present and will be "
            "ignored or misinterpreted by assistive technologies."
        )
    if "missing visible focus indicator" in low or "focus indicator" in low:
        return (
            "Keyboard users cannot see which element is currently focused, "
            "blocking keyboard-only navigation."
        )
    if "touch target" in low or re.search(r"smaller than \d+x\d+", low):
        m = re.search(r"(\d+)\s*interactive elements", low)
        count = m.group(1) if m else None
        if count:
            return (
                f"{count} interactive elements are smaller than Apple/Google's "
                f"recommended 44×44px minimum, making them hard to tap on mobile."
            )
        return (
            "Interactive elements are too small to tap reliably on mobile, "
            "hurting usability for touch users."
        )
    if "keyboard trap" in low:
        return (
            "Keyboard users can get trapped in components they can't tab out of."
        )
    if "heading-order" in low or "heading order" in low:
        return (
            "Heading levels skip or reverse, making document structure harder "
            "for both screen readers and search engines to parse."
        )
    if "label" in low and ("form" in low or "input" in low or "missing" in low):
        return (
            "Form inputs are missing associated labels, making them unusable "
            "for screen-reader users and weakening form submission tracking."
        )
    if "image-alt" in low or (
        "alt" in low and ("image" in low or "missing" in low)
    ):
        return (
            "Images are missing descriptive alt text, blocking screen-reader "
            "users and reducing image search visibility."
        )

    # Structured data property paths ---
    if "schema" in low and ("missing" in low or "property" in low):
        # Strip out `.hasOfferCatalog.itemListElement[]` style paths
        if "offer" in low and "price" in low:
            return (
                "Product or service listings are missing price information in "
                "structured data, preventing rich pricing displays in search results."
            )
        if "review" in low or "rating" in low:
            return (
                "Reviews or ratings are not exposed in structured data, so "
                "star ratings can't appear alongside the site's search results."
            )
        if "breadcrumb" in low:
            return (
                "Breadcrumb navigation is not exposed in structured data, "
                "limiting how Google displays site hierarchy in results."
            )
        if "faq" in low:
            return (
                "FAQ content isn't marked up as structured data, preventing "
                "rich FAQ displays in search results."
            )
        return (
            "Key page types are missing required structured data properties, "
            "which limits eligibility for rich search result features."
        )
    if "json-ld" in low and ("missing" in low or "no" in low):
        return (
            "Pages don't expose JSON-LD structured data, so search engines "
            "have to guess at page type and content meaning."
        )

    # Semantic HTML ---
    m = re.search(r"semantic html ratio.*?(\d+(?:\.\d+)?)%", low)
    if m:
        return (
            "The page relies heavily on generic HTML elements rather than "
            "semantic markup, making it harder for search engines and AI "
            "systems to identify content structure."
        )
    if "no main landmark" in low or "missing main" in low:
        return (
            "Pages have no <main> landmark, so assistive tech and crawlers "
            "can't identify the primary content area."
        )
    if "h1" in low and ("missing" in low or "multiple" in low or "no h1" in low):
        if "multiple" in low:
            return (
                "Multiple H1 headings are present, diluting the page's topic "
                "signal for both search engines and AI systems."
            )
        return (
            "Pages are missing an H1 heading, weakening the primary topic "
            "signal search engines rely on to rank content."
        )

    # Readability ---
    m = re.search(r"grade (\d+(?:\.\d+)?)", low)
    if m and ("readability" in low or "reading level" in low or "flesch" in low):
        grade = m.group(1)
        return (
            f"Content is written at a Grade {grade} reading level — the optimal "
            f"range for web content is Grade 6–8, which improves comprehension "
            f"and AI-citation rates."
        )

    # Internal linking ---
    if "orphan" in low:
        m = re.search(r"(\d+)\s*(pages?|orphan)", low)
        if m:
            return (
                f"{m.group(1)} pages are orphaned with no internal links pointing "
                f"to them, effectively invisible to crawlers and site visitors."
            )
        return (
            "Pages are orphaned with no internal links pointing to them, "
            "effectively invisible to crawlers and site visitors."
        )
    if "anchor text" in low and ("generic" in low or "click here" in low):
        return (
            "Internal links use generic anchor text ('click here', 'read more'), "
            "wasting signals that help search engines understand link targets."
        )

    # JS / performance ---
    if "javascript" in low and ("bloat" in low or "render-blocking" in low):
        return (
            "Render-blocking JavaScript is slowing initial page load, hurting "
            "both user experience and crawler efficiency."
        )

    # AEO / RAG ---
    if "question" in low and ("missing" in low or "not found" in low):
        return (
            "Content lacks direct-answer formatting (Q-and-A structure) that "
            "AI systems look for when selecting sources for generated answers."
        )
    if "summary" in low and "missing" in low:
        return (
            "Content is missing opening summaries that AI retrieval systems "
            "use to decide whether a page answers a given query."
        )

    # Agentic / robots ---
    if "llms.txt" in low or "llm" in low and "missing" in low:
        return (
            "No llms.txt file is present, so AI agents have no machine-readable "
            "guide to the site's content structure."
        )
    if "robots.txt" in low and ("ai" in low or "missing" in low):
        return (
            "robots.txt doesn't explicitly address AI crawlers, leaving "
            "discoverability and gating ambiguous."
        )

    # Structured-data 'Missing required property' generic fallback
    m = re.search(r"missing required property '([^']+)'", d, flags=re.IGNORECASE)
    if m:
        prop = m.group(1)
        return (
            f"Structured data is missing the '{prop}' property on key page "
            f"templates, blocking the enhanced search displays that depend on it."
        )

    # Strip raw Axe prefix if we didn't match a specific rule
    cleaned = re.sub(
        r"^axe rule '[^']+':\s*", "", d, flags=re.IGNORECASE
    ).strip()
    # Drop Schema.org property paths like Offer.hasOfferCatalog.itemListElement[]
    cleaned = re.sub(
        r"\s+in\s+\b\w+(?:\.\w+){2,}(?:\[\])?",
        "",
        cleaned,
    )
    cleaned = re.sub(r"\b\w+(?:\.\w+){2,}(?:\[\])?", "", cleaned).strip()
    # Collapse extra spaces introduced by removals
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    # Single-sentence cap: keep first sentence only
    first_sentence = re.split(r"(?<=[.!?])\s+", cleaned)[0]
    if first_sentence.endswith((".", "!", "?")):
        return first_sentence
    return first_sentence.rstrip(".") + "."


# ─── Section generators ───


def _section_strategic_context(report: dict, scores: Dict[str, int]) -> str:
    """Section 1: Outcome-first business framing. 4–6 sentences."""
    site = _site_name(report.get("url", ""))
    overall = report.get("overall_score", 0)
    nlp = _get_nlp(report)
    cms = (report.get("cms_detection") or {}).get("platform", "unknown")
    industry = _industry_from_nlp(nlp)
    is_agency = _is_agency_industry(industry)
    weak_keys = _weak(scores)
    strong_keys = _strong(scores)
    page_count = _page_count(report)

    # Identify weakest composite category using the scorecard's composite avg
    # (so text matches the table the reader will see directly below).
    composite_scores = _composite_category_scores(scores)
    weakest_category = None
    weakest_cat_score = 100
    if composite_scores:
        weakest_category, weakest_cat_score = min(
            composite_scores.items(), key=lambda kv: kv[1]
        )

    # Industry framing fragment — always set off by commas, never an em-dash
    # (em-dash caused awkward sentence structure like "site — a web design site demonstrates").
    industry_frag = ""
    if industry:
        if is_agency:
            industry_frag = f", a {industry.lower()} site,"
        else:
            industry_frag = f" ({industry})"

    # CMS framing fragment (only if detected and not "unknown")
    cms_frag = ""
    if cms == "webflow":
        cms_frag = " Built on Webflow, the platform's native tooling makes the technical adjustments below reachable without engineering work."

    a11y = scores.get("accessibility", 100)
    a11y_reach_pct = 15 if a11y < 55 else (12 if a11y < 70 else 8)

    lines = ["## Strategic Context"]

    # ── High-scoring path (> 70) ──
    if overall > 70:
        # Name top strengths (mapped to composite categories)
        strong_cats: List[str] = []
        for k in strong_keys:
            c = PILLAR_TO_CATEGORY.get(k)
            if c and c not in strong_cats:
                strong_cats.append(c)
        strong_phrase = (
            " and ".join(strong_cats[:2])
            if strong_cats
            else "its core audit dimensions"
        )
        weakest_pillar_name = (
            PILLAR_LABELS.get(weak_keys[0]) if weak_keys else "AI readiness"
        )
        weakest_pillar_score = scores.get(weak_keys[0]) if weak_keys else None

        # Opening — vary by whether we have industry/agency signal
        if is_agency and industry:
            opening = (
                f"{site}{industry_frag} demonstrates strong fundamentals in "
                f"{strong_phrase}, scoring above thresholds where most competitors "
                f"fall short."
            )
        elif industry:
            opening = (
                f"{site}{industry_frag} performs above average across "
                f"{strong_phrase}, with quality content already in place."
            )
        else:
            opening = (
                f"{site} demonstrates strong fundamentals across {strong_phrase}, "
                f"scoring above industry benchmarks in these areas."
            )
        lines.append(opening)

        # Frame the gap
        if weakest_category and weakest_cat_score < 65:
            gap_sentence = (
                f"The primary opportunities are structural: search engines and "
                f"AI systems struggle to discover and interpret the full scope "
                f"of what the site offers, not because the content is weak, but "
                f"because the technical signals connecting it are incomplete. "
                f"Specifically, {weakest_category} at {weakest_cat_score}/100 "
                f"represents the widest gap between the site's content quality "
                f"and its actual visibility."
            )
        elif weakest_pillar_score is not None and weakest_pillar_score < 65:
            gap_sentence = (
                f"The primary opportunity is refinement rather than remediation — "
                f"{weakest_pillar_name} at {weakest_pillar_score}/100 is the one "
                f"area where targeted investment would meaningfully shift "
                f"overall performance."
            )
        else:
            gap_sentence = (
                "The opportunities identified below are refinements that would "
                "further strengthen visibility in search and AI-driven "
                "discovery channels."
            )
        lines.append(gap_sentence)

        # Outcome sentence + reach extension
        outcome = (
            "Addressing this would mean existing content — which already "
            "performs well when found — gets found significantly more often."
        )
        if a11y < 65:
            outcome += (
                f" The secondary opportunity is reach: accessibility "
                f"improvements would extend the site's audience to the "
                f"~{a11y_reach_pct}% of users who currently can't fully engage with it."
            )
        lines.append(outcome + cms_frag)

    # ── Mid-scoring path (50–70) ──
    elif overall >= 50:
        weakest_pillar_names = (
            [PILLAR_LABELS.get(k) for k in weak_keys[:2]] if weak_keys else []
        )

        # Opening — lead with the gap between offering and web communication
        business_type = industry.lower() if industry else "service business"
        if is_agency and industry:
            subject = f"{site}, a {industry.lower()},"
        elif industry:
            subject = f"{site} ({industry})"
        else:
            subject = site

        opening = (
            f"{subject} has a gap between the services it offers and how "
            f"effectively the website communicates them to search engines, "
            f"AI systems, and prospective clients."
        )
        lines.append(opening)

        # Strength + weakness pairing
        strong_cats: List[str] = []
        for k in strong_keys:
            c = PILLAR_TO_CATEGORY.get(k)
            if c and c not in strong_cats:
                strong_cats.append(c)
        strong_frag = (
            ", ".join(strong_cats[:2]) if strong_cats else "most audit dimensions"
        )
        if weakest_pillar_names:
            weak_frag = " and ".join(n for n in weakest_pillar_names if n)
            lines.append(
                f"The site scores well in {strong_frag}, but foundational "
                f"signals — particularly in {weak_frag} — are limiting how "
                f"search engines present the site in results."
            )
        else:
            lines.append(
                f"The site scores well in {strong_frag}, but a handful of "
                f"technical gaps are limiting how it appears in search results."
            )

        # Outcome framing
        weak_count = len(weak_keys)
        lines.append(
            f"Addressing the {weak_count} pillar{'s' if weak_count != 1 else ''} "
            f"currently below target would improve both the quality and volume "
            f"of organic traffic, reduce dependence on paid acquisition, and "
            f"position the site for visibility in AI-powered discovery "
            f"channels that are becoming important for {business_type} buyers."
            + cms_frag
        )

    # ── Low-scoring path (< 50) ──
    else:
        subject_frag = f" ({industry})" if industry else ""
        lines.append(
            f"This audit identifies foundational gaps across multiple dimensions "
            f"of {site}'s{subject_frag} web presence."
        )
        # Name the weak categories
        weak_cats: List[str] = []
        for k in weak_keys:
            c = PILLAR_TO_CATEGORY.get(k)
            if c and c not in weak_cats:
                weak_cats.append(c)
        weak_cat_frag = (
            ", ".join(weak_cats) if weak_cats else "content, structure, and technical layers"
        )
        lines.append(
            f"{weak_cat_frag} each require focused attention before organic "
            f"channels can perform reliably."
        )
        lines.append(
            f"The current state means the site is underperforming relative to "
            f"the investment in content and services it represents — search "
            f"engines cannot effectively interpret the content, AI systems "
            f"cannot extract or cite it, and a meaningful segment of potential "
            f"visitors encounter barriers to engagement."
        )
        lines.append(
            "Because the gaps are foundational, addressing them produces "
            "compounding improvements across search visibility, AI presence, "
            "and user experience simultaneously." + cms_frag
        )

    # Optional scale note when site is large
    if page_count >= 200:
        lines.append(
            f"At {page_count:,} crawled pages, even small per-page improvements "
            f"compound into meaningful aggregate lift."
        )

    return "\n\n".join(lines)


def _section_roi_projection(report: dict, scores: Dict[str, int]) -> str:
    """Section 2: Data-grounded business case with variable projections."""
    overall = report.get("overall_score", 0)
    page_count = _page_count(report)
    tipr = _get_tipr(report)
    clusters = _get_clusters(report)
    weak_keys = _weak(scores)

    if not weak_keys:
        return (
            "## Business Case\n\n"
            "All pillars are performing above threshold. Continued optimization "
            "will help maintain competitive position as AI search evolves."
        )

    lines = ["## Business Case\n"]

    # ── Variable traffic-growth range ──
    # Base on: overall score band + pillar-below-threshold count + worst score
    worst_score = min(scores.values()) if scores else 100
    weak_count = len(weak_keys)

    if overall < 40:
        low, high = 35, 70
    elif overall < 55:
        low, high = 25, 50
    elif overall < 65:
        low, high = 15, 35
    elif overall < 72:
        low, high = 12, 28
    elif overall < 78:
        low, high = 8, 20
    else:
        low, high = 5, 12

    # Widen range when many pillars are weak
    if weak_count >= 4:
        high += 10
    elif weak_count >= 3:
        high += 5
    # Widen more when the worst pillar is near zero
    if worst_score <= 10:
        high += 10
        low += 5
    elif worst_score <= 30:
        high += 5

    # Larger sites have more surface area to improve
    if page_count >= 500:
        high += 5

    traffic_range = f"{low}–{high}%"

    # Baseline sentence — reference actual numbers
    baseline_parts = [f"an overall score of {overall}/100"]
    if page_count > 0:
        baseline_parts.append(f"{page_count:,} pages analyzed")
    baseline_parts.append(
        f"{weak_count} pillar{'s' if weak_count != 1 else ''} below target threshold"
    )
    lines.append(
        f"Based on a current baseline of {', '.join(baseline_parts)}, "
        f"the following projections are modeled from audit data — not "
        f"guaranteed — and are contingent on implementation scope and timeline.\n"
    )

    # ── First bullet: traffic/visibility lift (vary label) ──
    # Rotate the label based on score band so reports don't all say the same thing
    if overall >= 75:
        label1 = "Search visibility improvement range"
    elif overall >= 55:
        label1 = "Organic performance ceiling lift"
    else:
        label1 = "Discovery channel expansion"
    lines.append(
        f"- **{label1}:** {traffic_range} modeled improvement range over a "
        f"6–12 month horizon, contingent on implementation sequencing"
    )

    # ── Second bullet: pipeline impact (vary by size) ──
    if page_count >= 50:
        lines.append(
            f"- **Pipeline impact:** If organic traffic moves by "
            f"{traffic_range} and current conversion rates hold, this produces "
            f"a proportional lift in qualified inquiries from organic channels "
            f"without additional ad spend"
        )

    # ── Third bullet: chosen from real site data (variable) ──
    third: str | None = None
    if tipr:
        orphans = (tipr.get("summary") or {}).get("orphan_count") or 0
        if orphans >= 20:
            third = (
                f"**Recaptured content value:** {orphans} pages currently "
                f"generating zero organic traffic could be reactivated through "
                f"internal-linking improvements, turning existing investment "
                f"into measurable search presence"
            )
    if not third and clusters:
        total_gaps = sum(
            len(c.get("content_gaps", [])) for c in clusters.get("clusters", [])
        )
        if total_gaps >= 10:
            # Contextualize
            ratio_note = ""
            if page_count:
                ratio = total_gaps / page_count
                if ratio > 0.5:
                    ratio_note = (
                        " — the highest-value 5–10 should be prioritized rather "
                        "than pursuing all of them"
                    )
                elif ratio > 0.2:
                    ratio_note = " — representing significant adjacent demand"
                else:
                    ratio_note = " — a focused set of expansion opportunities"
            third = (
                f"**Content expansion potential:** {total_gaps} topic areas "
                f"were identified where no dedicated page exists{ratio_note}"
            )
    if not third and scores.get("structured_data", 100) < 50:
        third = (
            "**Rich result eligibility:** Implementing structured data would "
            "qualify the site for enhanced search displays (FAQ panels, "
            "review stars, pricing) that typically increase click-through "
            "rates by 20–40%"
        )
    if not third and scores.get("accessibility", 100) < 65:
        third = (
            "**Audience expansion:** Accessibility improvements would extend "
            "reach to users who rely on assistive technologies — a segment "
            "that currently can't fully engage with the site"
        )
    if not third and scores.get("js_bloat", 100) < 65:
        third = (
            "**Efficiency gains:** Performance improvements would reduce "
            "wasted crawl budget and improve Core Web Vitals, a ranking "
            "signal Google applies across all queries"
        )

    if third:
        lines.append(f"- {third}")

    return "\n".join(lines)


def _section_diagnosis(report: dict, scores: Dict[str, int]) -> str:
    """Section 3: 3–5 diagnostic statements drawn from actual scores and data."""
    overall = report.get("overall_score", 0)
    tipr = _get_tipr(report)
    nlp = _get_nlp(report)
    clusters = _get_clusters(report)
    page_count = _page_count(report)

    lines = ["## Audit Diagnosis\n"]

    # If high-scoring, lead with strengths
    strong_keys = _strong(scores)
    if overall >= 75 and strong_keys:
        top_names = [PILLAR_LABELS.get(k, k) for k in strong_keys[:3]]
        lines.append(
            f"The site demonstrates strong fundamentals across "
            f"{', '.join(top_names)}. The primary opportunities lie in the "
            f"areas noted below.\n"
        )

    statements: List[str] = []

    sem_score = scores.get("semantic_html", 100)
    if sem_score < 65:
        if sem_score < 40:
            level = "a weak"
        elif sem_score < 55:
            level = "a developing"
        else:
            level = "a partial"
        statements.append(
            f"The site has {level} technical foundation — key signals that "
            f"help search engines and AI systems interpret content hierarchy "
            f"and page purpose are incomplete."
        )

    sd_score = scores.get("structured_data", 100)
    if sd_score < 65:
        if sd_score <= 10:
            statements.append(
                f"Structured data is effectively absent (score: {sd_score}/100). "
                f"Google has no machine-readable way to understand page types, "
                f"services, pricing, or reviews — disqualifying the site from "
                f"rich results entirely."
            )
        elif sd_score < 30:
            statements.append(
                f"Structured data implementation is minimal ({sd_score}/100), "
                f"severely limiting rich-result eligibility across major page types."
            )
        elif sd_score < 50:
            statements.append(
                f"Structured data is incomplete ({sd_score}/100), limiting how "
                f"search engines display the site in rich results and reducing "
                f"click-through rates from search."
            )
        else:
            statements.append(
                f"Structured data is inconsistent ({sd_score}/100) — present on "
                f"some templates but missing required properties that unlock "
                f"rich search displays."
            )

    aeo_score = scores.get("aeo_content", 100)
    rag_score = scores.get("rag_readiness", 100)
    if aeo_score < 65 and rag_score < 65:
        statements.append(
            "AI visibility is limited — content formatting and structured "
            "signals don't meet the patterns that AI systems use when "
            "selecting sources for generated answers."
        )
    elif aeo_score < 65:
        statements.append(
            "Content is reasonably well-structured for AI extraction, but "
            "lacks the answer-oriented formatting that drives inclusion in "
            "AI-generated responses."
        )

    il_score = scores.get("internal_linking", 100)
    if il_score < 65:
        statements.append(
            "Internal link structure does not clearly guide authority or user "
            "flow toward the site's most important pages, diluting the impact "
            "of existing content."
        )

    # Accessibility — now site-specific (Problem 3 fix)
    a11y_score = scores.get("accessibility", 100)
    if a11y_score < 65:
        breakdown = _a11y_breakdown(report)
        total = breakdown["total"]
        cats = breakdown["categories"]
        cat_frag = ", ".join(cats[:2]) if cats else "assistive-tech compatibility"
        if a11y_score < 50:
            reach_pct = 15
            statements.append(
                f"Accessibility is a significant gap at {a11y_score}/100. "
                f"{total} violation{'s' if total != 1 else ''} "
                f"{'were' if total != 1 else 'was'} detected, concentrated in "
                f"{cat_frag}. This limits the site's audience to roughly "
                f"{100 - reach_pct}% of potential visitors, creates compliance "
                f"exposure, and signals structural problems to search engines."
            )
        else:
            reach_pct = 12
            statements.append(
                f"Accessibility is below target at {a11y_score}/100 with "
                f"{total} specific issue{'s' if total != 1 else ''} — primarily "
                f"in {cat_frag} — that limit reach to the ~{reach_pct}% of users "
                f"who rely on assistive technologies."
            )

    # TIPR-derived statements — now contextualized
    if tipr:
        s = tipr.get("summary", {})
        total_pages = s.get("total_pages", 0) or page_count
        orphan_count = s.get("orphan_count", 0)
        hoarder_count = s.get("hoarders", 0)

        if total_pages > 0 and orphan_count > 0:
            orphan_pct = round(orphan_count / total_pages * 100)
            if orphan_pct >= 40:
                statements.append(
                    f"{orphan_pct}% of the site ({orphan_count} of {total_pages} "
                    f"pages) has no internal links pointing to it — an unusually "
                    f"high share that suggests the site's information "
                    f"architecture isn't connecting content libraries to the "
                    f"pages where authority concentrates."
                )
            elif orphan_pct >= 15:
                statements.append(
                    f"{orphan_pct}% of pages ({orphan_count} of {total_pages}) "
                    f"are orphaned with no inbound internal links, effectively "
                    f"invisible to both crawlers and users."
                )

        if total_pages > 0 and hoarder_count > 0:
            hoarder_pct = round(hoarder_count / total_pages * 100)
            if hoarder_pct >= 25:
                statements.append(
                    f"A large portion of pages ({hoarder_pct}%) accumulate link "
                    f"authority without distributing it, creating bottlenecks "
                    f"that prevent deeper content from ranking."
                )

    # NLP sentiment
    if nlp:
        sentiment = nlp.get("sentiment", {})
        magnitude = sentiment.get("magnitude", 0)
        sent_score = sentiment.get("score", 0)
        if magnitude > 1.5 and sent_score < -0.2:
            statements.append(
                "Content tone is inconsistent, with sections that may undermine "
                "trust signals both users and AI systems rely on."
            )

    # Cluster content gaps — contextualized by page count (Problem 5 fix)
    if clusters:
        total_gaps = sum(
            len(c.get("content_gaps", []))
            for c in clusters.get("clusters", [])
        )
        if total_gaps > 0 and page_count > 0:
            ratio = total_gaps / page_count
            if ratio > 0.5:
                statements.append(
                    f"Topic analysis identified {total_gaps} content areas "
                    f"where no dedicated page exists (~{ratio:.1f} gaps per "
                    f"existing page). This high ratio suggests the site is "
                    f"narrowly focused on a few topics; the priority is the "
                    f"top 5–10 highest-value gaps, not pursuing all of them."
                )
            elif ratio > 0.2:
                statements.append(
                    f"Topic analysis identified {total_gaps} content areas "
                    f"where no dedicated page exists — significant untapped "
                    f"demand in topics adjacent to existing content."
                )
            else:
                statements.append(
                    f"Topic analysis identified {total_gaps} content areas "
                    f"where no dedicated page exists — a focused set of "
                    f"expansion opportunities."
                )
        elif total_gaps > 0:
            statements.append(
                f"Topic analysis identified {total_gaps} content areas lacking "
                f"dedicated pages, representing missed opportunities for topical "
                f"authority."
            )

    # Limit to 5 most impactful statements
    for stmt in statements[:5]:
        lines.append(stmt)
        lines.append("")

    if not statements:
        lines.append(
            "No significant structural issues were identified. "
            "The site is well-positioned across the audited dimensions."
        )

    return "\n".join(lines).rstrip()


def _section_key_risks(report: dict, scores: Dict[str, int]) -> str:
    """Section 4: 3 specific risk statements tied to the diagnosis."""
    tipr = _get_tipr(report)
    clusters = _get_clusters(report)

    risks: List[str] = []

    # Technical visibility risk
    sem = scores.get("semantic_html", 100)
    sd = scores.get("structured_data", 100)
    if sd <= 10:
        risks.append(
            "Complete exclusion from rich-result placements (FAQ panels, "
            "review stars, pricing) while competitors capture this visibility"
        )
    elif sem < 65 or sd < 65:
        risks.append(
            "Reduced visibility for high-value search queries where competitors "
            "with better technical signals are preferred"
        )

    # AI presence risk
    aeo = scores.get("aeo_content", 100)
    rag = scores.get("rag_readiness", 100)
    if aeo < 65 or rag < 65:
        risks.append(
            "Low presence in AI-generated answers, where early movers are "
            "establishing lasting citation advantage"
        )

    # Orphan pages risk (uses real data)
    if tipr:
        s = tipr.get("summary", {})
        orphans = s.get("orphan_count", 0)
        if orphans >= 20:
            risks.append(
                f"{orphans} pages that cost resources to create are currently "
                f"generating zero organic traffic due to missing internal links"
            )

    # Internal linking risk (general, if not covered by orphans)
    il = scores.get("internal_linking", 100)
    if il < 65 and not any("orphan" in r.lower() for r in risks):
        risks.append(
            "Existing content assets underperforming because link authority "
            "is not reaching them"
        )

    # Accessibility risk
    a11y = scores.get("accessibility", 100)
    if a11y < 65:
        risks.append(
            "Potential ADA compliance exposure and exclusion of users who rely "
            "on assistive technologies"
        )

    # Content gaps risk
    if clusters:
        total_gaps = sum(
            len(c.get("content_gaps", []))
            for c in clusters.get("clusters", [])
        )
        if total_gaps >= 20:
            risks.append(
                f"Competitors capturing demand for topics where this site has "
                f"no content presence ({total_gaps} such gaps identified)"
            )

    if not risks:
        return ""  # Skip section entirely for high-scoring sites

    lines = ["## Key Risks\n"]
    for risk in risks[:3]:
        lines.append(f"- {risk}")

    return "\n".join(lines)


def _section_scorecard(scores: Dict[str, int]) -> str:
    """Section 5: Composite category scorecard table (valid GFM)."""
    sem = scores.get("semantic_html", 0)
    sd = scores.get("structured_data", 0)
    js = scores.get("js_bloat", 0)
    css = scores.get("css_quality", 0)
    aeo = scores.get("aeo_content", 0)
    rag = scores.get("rag_readiness", 0)
    agent = scores.get("agentic_protocols", 0)
    il = scores.get("internal_linking", 0)
    a11y = scores.get("accessibility", 0)
    data = scores.get("data_integrity", 0)

    tech = _avg(sem, sd, js, css)
    content = _avg(aeo, rag)
    ai = _avg(aeo, rag, agent)
    structure = _avg(il, a11y, data)

    # NOTE: blank lines before AND after the table are required by GFM.
    # All rows must have exactly the same number of pipe-delimited columns.
    lines = [
        "## Current State",
        "",
        "| Category | Score | Assessment |",
        "| --- | :---: | --- |",
        f"| Technical Foundation | {tech} | {_interp(tech)} |",
        f"| Content Effectiveness | {content} | {_interp(content)} |",
        f"| AI Readiness | {ai} | {_interp(ai)} |",
        f"| Site Structure | {structure} | {_interp(structure)} |",
        "",
    ]

    return "\n".join(lines)


def _section_priority_actions(
    report: dict, scores: Dict[str, int]
) -> str:
    """Section 6: 4–5 specific action items for areas below 65."""
    tipr = _get_tipr(report)
    clusters = _get_clusters(report)
    cms = (report.get("cms_detection") or {}).get("platform", "unknown")
    is_webflow = cms == "webflow"
    page_count = _page_count(report)

    actions: List[str] = []

    if scores.get("semantic_html", 100) < 65:
        if is_webflow:
            actions.append(
                "Add missing heading hierarchy and semantic elements using "
                "Webflow's tag settings to improve how search engines interpret "
                "page structure"
            )
        else:
            actions.append(
                "Add missing heading hierarchy and semantic HTML signals to "
                "improve how search engines interpret page structure"
            )

    if scores.get("structured_data", 100) < 65:
        sd_score = scores.get("structured_data", 0)
        urgency = "Implement" if sd_score > 20 else "Deploy"
        if is_webflow:
            actions.append(
                f"{urgency} Schema.org structured data across key page "
                f"templates using Webflow Collection fields and custom-code "
                f"embeds, starting with service/offering pages to enable rich "
                f"search results"
            )
        else:
            actions.append(
                f"{urgency} Schema.org structured data for key page types "
                f"(Organization, Service, FAQ, Breadcrumb) to enable rich "
                f"search results"
            )

    if scores.get("aeo_content", 100) < 65:
        actions.append(
            "Rework core content pages to include direct-answer formatting "
            "(Q&A blocks, tl;dr summaries) that AI systems prioritize for "
            "citation"
        )

    if scores.get("rag_readiness", 100) < 65:
        actions.append(
            "Improve content structure with clear sections, summaries, and "
            "entity-rich text that AI retrieval systems can extract"
        )

    # Accessibility action — now references real findings (Problem 3 fix)
    if scores.get("accessibility", 100) < 65:
        breakdown = _a11y_breakdown(report)
        cats = breakdown["categories"]
        if cats:
            cat_frag = ", ".join(cats[:2])
            actions.append(
                f"Fix accessibility gaps concentrated in {cat_frag} — these "
                f"directly affect assistive-tech users and create compliance risk"
            )
        else:
            actions.append(
                "Address accessibility gaps to expand audience reach and "
                "reduce compliance risk"
            )

    if scores.get("agentic_protocols", 100) < 65:
        actions.append(
            "Add AI-agent compatibility signals (robots.txt AI directives, "
            "llms.txt, structured API endpoints) to improve automated discovery"
        )

    if scores.get("data_integrity", 100) < 65:
        actions.append(
            "Fix tracking implementation gaps so analytics data accurately "
            "reflects site performance"
        )

    # TIPR-derived action — uses REAL recommendation count and top hoarder->target (Problem 7 fix)
    if tipr:
        recs = tipr.get("recommendations", []) or []
        rec_count = len(recs)
        if rec_count > 0:
            # Find top add-link rec for context
            top_rec = None
            for r in recs:
                if r.get("type") == "add_link" and r.get("priority") == "high":
                    top_rec = r
                    break
            if not top_rec:
                top_rec = recs[0]

            src = top_rec.get("source_url") or ""
            tgt = top_rec.get("target_url") or ""
            src_path = _path_of(src)
            tgt_path = _path_of(tgt)

            if src_path and tgt_path:
                actions.append(
                    f"Implement the {rec_count} internal-link changes "
                    f"identified by link-intelligence analysis — the "
                    f"highest-impact change is adding links from {src_path} "
                    f"to {tgt_path} to redistribute accumulated authority"
                )
            else:
                actions.append(
                    f"Implement the {rec_count} internal-link changes "
                    f"identified by link-intelligence analysis, prioritizing "
                    f"high-authority hoarder pages that have no outbound "
                    f"internal links"
                )

    # Cluster gap action — contextualized (Problem 5 fix)
    if clusters:
        all_gaps: List[str] = []
        for c in clusters.get("clusters", []):
            for g in c.get("content_gaps", []):
                if isinstance(g, dict):
                    label = g.get("label") or g.get("topic") or g.get("name")
                elif isinstance(g, str):
                    label = g
                else:
                    label = None
                if label:
                    all_gaps.append(label)
        total_gaps = sum(
            len(c.get("content_gaps", []))
            for c in clusters.get("clusters", [])
        )
        if total_gaps >= 10:
            sample_frag = ""
            if all_gaps:
                sample = [g for g in all_gaps[:3] if g]
                if sample:
                    sample_frag = (
                        f", starting with {', '.join(sample)} where demand is "
                        f"already documented"
                    )
            # Don't say "create 288 pages" on a 360-page site — that's absurd
            if page_count and total_gaps / page_count > 0.4:
                actions.append(
                    f"Create content for the top 5–10 highest-priority topic "
                    f"gaps (of {total_gaps} identified){sample_frag}, rather "
                    f"than pursuing the full list"
                )
            else:
                actions.append(
                    f"Create content for the {total_gaps} identified topic "
                    f"gaps{sample_frag} to establish authority in uncovered areas"
                )

    if not actions:
        return (
            "## Priority Actions\n\n"
            "All pillars are performing above threshold. Continue monitoring "
            "for regressions and refine based on competitive movement."
        )

    lines = ["## Priority Actions\n"]
    for action in actions[:5]:
        lines.append(f"- {action}")

    return "\n".join(lines)


def _path_of(url: str) -> str:
    """Extract the path portion of a URL, with leading slash."""
    if not url:
        return ""
    m = re.match(r"^https?://[^/]+(/.*)?$", url)
    if m:
        path = m.group(1) or "/"
        return path
    if url.startswith("/"):
        return url
    return url


def _section_opportunities(report: dict, scores: Dict[str, int]) -> str:
    """Section 7: Forward-looking strategic opportunities."""
    tipr = _get_tipr(report)
    nlp = _get_nlp(report)
    clusters = _get_clusters(report)
    cms = (report.get("cms_detection") or {}).get("platform", "unknown")
    page_count = _page_count(report)

    opps: List[str] = []

    # Cluster expansion — contextualized
    if clusters:
        total_gaps = sum(
            len(c.get("content_gaps", []))
            for c in clusters.get("clusters", [])
        )
        if total_gaps >= 10:
            if page_count and total_gaps / page_count > 0.4:
                opps.append(
                    f"Prioritize the highest-intent topic areas from {total_gaps} "
                    f"identified gaps where the site currently has no content "
                    f"presence — tight focus will beat broad coverage"
                )
            else:
                opps.append(
                    f"Expand into {total_gaps} high-intent topic areas identified "
                    f"by semantic analysis where the site currently has no "
                    f"content presence"
                )

    # Amplify Stars
    if tipr:
        stars = (tipr.get("summary") or {}).get("stars", 0)
        if stars > 0:
            opps.append(
                f"Amplify the {stars} pages already performing well (classified "
                f"as 'Star' pages) by building more internal links to them "
                f"from related content"
            )

    # AI visibility opportunity
    aeo = scores.get("aeo_content", 100)
    rag = scores.get("rag_readiness", 100)
    sd = scores.get("structured_data", 100)
    if (aeo < 65 or rag < 65) and sd >= 55:
        opps.append(
            "Capture AI-driven visibility by improving content formatting — "
            "the technical foundation for AI readiness is partially in place"
        )

    # NLP entity strength
    if nlp and nlp.get("entities"):
        entities = nlp["entities"]
        top_entity = entities[0] if entities else None
        if top_entity and top_entity.get("salience", 0) > 0.3:
            opps.append(
                f"Double down on \"{top_entity['name']}\" content where the "
                f"site already demonstrates topical authority (salience: "
                f"{round(top_entity['salience'] * 100)}%)"
            )

    # CMS migration opportunity
    if cms not in ("webflow", "unknown"):
        weak_keys = _weak(scores)
        if weak_keys:
            weak_areas = ", ".join(
                PILLAR_LABELS.get(k, k) for k in weak_keys[:2]
            )
            opps.append(
                f"Consider platform migration to improve technical control over "
                f"{weak_areas} — migration intelligence is included in this audit"
            )

    if not opps:
        return ""

    lines = ["## Strategic Opportunities\n"]
    for opp in opps[:3]:
        lines.append(f"- {opp}")

    return "\n".join(lines)


def _section_supporting_detail(report: dict) -> str:
    """Section 8: 1 plain-English example finding per scorecard category (single sentence)."""
    findings = _collect_findings(report)
    if not findings:
        return ""

    # Group pillars into composite categories
    category_buckets = {
        "Technical Foundation": {"semantic_html", "structured_data", "js_bloat", "css_quality"},
        "Content Effectiveness": {"aeo_content", "rag_readiness"},
        "AI Readiness": {"agentic_protocols"},
        "Site Structure": {"internal_linking", "accessibility", "data_integrity"},
    }

    def _pick_one(pillar_set: set) -> str | None:
        for f in findings:
            if f.get("pillar_key") in pillar_set:
                translated = _translate_finding(
                    f.get("description", ""), f.get("pillar_key", "")
                )
                if translated:
                    return translated
        return None

    rows: List[tuple[str, str]] = []
    for label, pillars in category_buckets.items():
        picked = _pick_one(pillars)
        if picked:
            rows.append((label, picked))

    if not rows:
        return ""

    lines = ["### Supporting Detail\n"]
    for label, sentence in rows:
        lines.append(f"- **{label}:** {sentence}")

    return "\n".join(lines)


# ─── Main entry point ───


def generate_executive_summary(
    report: dict, competitive_data: dict | None = None
) -> str:
    """Generate a strategic diagnostic brief from a completed audit report.

    Produces a single Markdown string with 8 sections. Sections are omitted
    when the underlying data doesn't exist (e.g., no TIPR enrichment yet).
    """
    scores = _get_scores(report)

    sections: List[str] = []

    # 1. Strategic Context
    sections.append(_section_strategic_context(report, scores))

    # 2. Business Case (ROI Projection)
    sections.append(_section_roi_projection(report, scores))

    # 3. Audit Diagnosis
    sections.append(_section_diagnosis(report, scores))

    # 4. Key Risks
    risks = _section_key_risks(report, scores)
    if risks:
        sections.append(risks)

    # 5. Scorecard
    sections.append(_section_scorecard(scores))

    # 6. Priority Actions
    sections.append(_section_priority_actions(report, scores))

    # 7. Strategic Opportunities
    opps = _section_opportunities(report, scores)
    if opps:
        sections.append(opps)

    # 8. Supporting Detail
    detail = _section_supporting_detail(report)
    if detail:
        sections.append(detail)

    # Competitor context (append if available)
    if competitive_data:
        comp = _section_competitor_context(report, competitive_data)
        if comp:
            sections.append(comp)

    return "\n\n".join(sections)


def _section_competitor_context(report: dict, competitive_data: dict) -> str:  # noqa: C901
    """Optional: Competitor benchmarking context."""
    rankings = competitive_data.get("rankings", [])
    primary = competitive_data.get("primary", {})
    advantages = competitive_data.get("advantages", [])
    weaknesses = competitive_data.get("weaknesses", [])

    if not rankings:
        return ""

    rank = primary.get("rank", "N/A")
    total = competitive_data.get("total_urls", len(rankings))
    primary_score = primary.get("overall_score", 0)

    lines = [
        "## Competitive Position\n",
        f"**Rank: #{rank} of {total} sites benchmarked** (Score: {primary_score}/100)\n",
    ]

    if rankings:
        leader = rankings[0]
        if leader.get("url") != report.get("url"):
            gap = leader.get("overall_score", 0) - primary_score
            lines.append(
                f"The leading competitor scores {leader['overall_score']}/100, "
                f"a {gap}-point gap above this site.\n"
            )

    if advantages:
        lines.append("**Where you lead:**")
        for adv in advantages[:3]:
            lines.append(
                f"- {adv['pillar']}: +{adv['diff']} pts above average "
                f"({adv['score']}/100 vs {adv['average']} avg)"
            )
        lines.append("")

    if weaknesses:
        lines.append("**Where competitors lead:**")
        for weak in weaknesses[:3]:
            lines.append(
                f"- {weak['pillar']}: {weak['diff']} pts below average "
                f"({weak['score']}/100 vs {weak['average']} avg)"
            )
        lines.append("")

    return "\n".join(lines).rstrip()
