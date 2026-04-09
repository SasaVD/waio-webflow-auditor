"""
Executive Summary Generator — Strategic Diagnostic Brief
Produces a Markdown executive summary grounded in actual audit data.
No LLM dependency. Every sentence tied to a real finding or score.
"""
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


# ─── Section generators ───


def _section_strategic_context(report: dict, scores: Dict[str, int]) -> str:
    """Section 1: Outcome-first business framing. 2–3 sentences."""
    url = report.get("url", "this site")
    overall = report.get("overall_score", 0)
    nlp = _get_nlp(report)

    # Identify the primary growth levers based on what's weak
    gaps: List[str] = []
    if scores.get("structured_data", 100) < 65 or scores.get("semantic_html", 100) < 65:
        gaps.append("how search engines discover and present this site in results")
    if scores.get("aeo_content", 100) < 65 or scores.get("rag_readiness", 100) < 65:
        gaps.append("visibility in AI-generated answers and recommendations")
    if scores.get("internal_linking", 100) < 65:
        gaps.append("how effectively the site's own content drives visitors toward key pages")
    if scores.get("accessibility", 100) < 65:
        gaps.append("the breadth of audience the site can reach")
    if nlp and nlp.get("entities") and len(nlp.get("entities", [])) < 5:
        gaps.append("the range of topics Google associates with this domain")

    lines = ["## Strategic Context\n"]

    if overall >= 75 and len(gaps) <= 1:
        lines.append(
            f"**{url}** has a strong technical foundation across most audit dimensions. "
            f"The primary opportunity is refinement rather than remediation — "
            f"targeted improvements in {gaps[0] if gaps else 'a few specific areas'} "
            f"would further strengthen the site's competitive position."
        )
    elif gaps:
        opening = (
            f"This audit identifies specific gaps in {gaps[0]}"
            + (f" and {gaps[1]}" if len(gaps) > 1 else "")
            + f" for **{url}**."
        )
        lines.append(opening)
        lines.append(
            "Addressing these would improve the quality of organic traffic, "
            "reduce reliance on paid channels, and position the site for visibility "
            "in AI-generated recommendations — an increasingly significant source of "
            "qualified discovery."
        )
    else:
        lines.append(
            f"**{url}** demonstrates solid optimization across the audit dimensions. "
            f"The opportunities identified below are refinements that would "
            f"further strengthen search visibility and AI discoverability."
        )

    return "\n".join(lines)


def _section_roi_projection(report: dict, scores: Dict[str, int]) -> str:
    """Section 2: Data-grounded business case with conservative projections."""
    overall = report.get("overall_score", 0)
    crawl_stats = report.get("crawl_stats")
    page_count = crawl_stats.get("pages_crawled", 0) if crawl_stats else 0
    weak_keys = _weak(scores)

    if not weak_keys:
        return (
            "## Business Case\n\n"
            "All pillars are performing above threshold. Continued optimization "
            "will help maintain competitive position as AI search evolves."
        )

    lines = ["## Business Case\n"]

    # Baseline context
    baseline_parts = [f"an overall score of {overall}/100"]
    if page_count > 0:
        baseline_parts.append(f"{page_count:,} pages crawled")
    baseline_parts.append(f"{len(weak_keys)} pillars below target threshold")
    lines.append(
        f"Based on a current baseline of {', '.join(baseline_parts)}, "
        f"the following projections are modeled — not guaranteed — and are "
        f"contingent on implementation scope and timeline.\n"
    )

    # Traffic growth range
    if overall < 40:
        traffic_range = "30–60%"
    elif overall < 65:
        traffic_range = "15–35%"
    else:
        traffic_range = "5–15%"
    lines.append(
        f"- **Organic traffic growth potential:** {traffic_range} improvement range, "
        f"contingent on implementation scope and timeline"
    )

    # Lead/pipeline impact — only for sites with enough pages
    if page_count > 50:
        lines.append(
            f"- **Pipeline impact:** If organic traffic increases by {traffic_range}, "
            f"and current conversion rates hold, this represents a proportional "
            f"increase in monthly inquiries from organic channels"
        )

    # Efficiency gains
    js_score = scores.get("js_bloat", 100)
    data_score = scores.get("data_integrity", 100)
    a11y_score = scores.get("accessibility", 100)
    if js_score < 65 or data_score < 65:
        parts = []
        if js_score < 65:
            parts.append("reduced wasted crawl budget from performance improvements")
        if data_score < 65:
            parts.append("more accurate analytics data for decision-making")
        lines.append(f"- **Efficiency gains:** {' and '.join(parts)}")
    if a11y_score < 65:
        lines.append(
            "- **Audience expansion:** Accessibility improvements would extend "
            "reach to users who rely on assistive technologies"
        )

    return "\n".join(lines)


def _section_diagnosis(report: dict, scores: Dict[str, int]) -> str:
    """Section 3: Core diagnostic statements drawn from actual scores and data."""
    overall = report.get("overall_score", 0)
    tipr = _get_tipr(report)
    nlp = _get_nlp(report)
    clusters = _get_clusters(report)

    lines = ["## Audit Diagnosis\n"]

    # If high-scoring, lead with strengths
    strong_keys = _strong(scores)
    if overall >= 75 and strong_keys:
        top_names = [PILLAR_LABELS.get(k, k) for k in strong_keys[:3]]
        lines.append(
            f"The site demonstrates strong fundamentals across "
            f"{', '.join(top_names)}. "
            f"The primary opportunities lie in the areas noted below.\n"
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
            f"The site has {level} technical foundation — key signals that help search engines "
            f"and AI systems interpret content hierarchy and page purpose are incomplete."
        )

    sd_score = scores.get("structured_data", 100)
    if sd_score < 65:
        if sd_score < 30:
            word = "missing"
        elif sd_score < 50:
            word = "incomplete"
        else:
            word = "inconsistent"
        statements.append(
            f"Structured data implementation is {word}, limiting how search engines "
            f"display the site in rich results and reducing click-through rates from search."
        )

    aeo_score = scores.get("aeo_content", 100)
    rag_score = scores.get("rag_readiness", 100)
    if aeo_score < 65 and rag_score < 65:
        statements.append(
            "AI visibility is limited — content formatting and structured signals don't "
            "meet the patterns that AI systems use when selecting sources for generated answers."
        )
    elif aeo_score < 65:
        statements.append(
            "Content is reasonably well-structured for AI extraction, but lacks the "
            "answer-oriented formatting that drives inclusion in AI-generated responses."
        )

    il_score = scores.get("internal_linking", 100)
    if il_score < 65:
        statements.append(
            "Internal link structure does not clearly guide authority or user flow toward "
            "the site's most important pages, diluting the impact of existing content."
        )

    a11y_score = scores.get("accessibility", 100)
    if a11y_score < 65:
        statements.append(
            "Accessibility gaps limit the site's reach to users with assistive technologies "
            "and create compliance risk, while also signaling reduced content quality to search engines."
        )

    # TIPR-derived statements
    if tipr:
        s = tipr.get("summary", {})
        total_pages = s.get("total_pages", 0)
        orphan_count = s.get("orphan_count", 0)
        hoarder_count = s.get("hoarders", 0)

        if total_pages > 0 and orphan_count > 0:
            orphan_pct = round(orphan_count / total_pages * 100)
            if orphan_pct >= 10:
                statements.append(
                    f"{orphan_pct}% of crawled pages ({orphan_count} pages) have no internal links "
                    f"pointing to them, making them invisible to both search crawlers and "
                    f"users navigating the site."
                )

        if total_pages > 0 and hoarder_count > 0:
            hoarder_pct = round(hoarder_count / total_pages * 100)
            if hoarder_pct >= 20:
                statements.append(
                    f"A significant portion of pages ({hoarder_pct}%) accumulate link authority "
                    f"without distributing it, creating bottlenecks that prevent deeper "
                    f"content from ranking."
                )

    # NLP sentiment
    if nlp:
        sentiment = nlp.get("sentiment", {})
        magnitude = sentiment.get("magnitude", 0)
        sent_score = sentiment.get("score", 0)
        if magnitude > 1.5 and sent_score < -0.2:
            statements.append(
                "Content tone is inconsistent, with sections that may undermine "
                "trust signals that both users and AI systems rely on."
            )

    # Cluster content gaps
    if clusters:
        total_gaps = sum(
            len(c.get("content_gaps", []))
            for c in clusters.get("clusters", [])
        )
        if total_gaps > 0:
            statements.append(
                f"Topic coverage has gaps — {total_gaps} content areas identified by "
                f"the audit lack dedicated pages, representing missed opportunities "
                f"for topical authority."
            )

    # Limit to 4 most impactful statements
    for stmt in statements[:4]:
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
    if sem < 65 or sd < 65:
        risks.append(
            "Reduced visibility for high-value search queries where competitors "
            "with better technical signals are preferred"
        )

    # AI presence risk
    aeo = scores.get("aeo_content", 100)
    rag = scores.get("rag_readiness", 100)
    if aeo < 65 or rag < 65:
        risks.append(
            "Low presence in AI-generated answers, an area where early movers "
            "are establishing lasting advantage"
        )

    # Internal linking risk
    il = scores.get("internal_linking", 100)
    if il < 65:
        risks.append(
            "Existing content assets underperforming because link authority "
            "is not reaching them"
        )

    # Orphan pages risk
    if tipr:
        s = tipr.get("summary", {})
        orphans = s.get("orphan_count", 0)
        if orphans > 0:
            risks.append(
                f"{orphans} pages that cost resources to create are currently "
                f"generating zero organic traffic due to missing internal links"
            )

    # Accessibility risk
    a11y = scores.get("accessibility", 100)
    if a11y < 65:
        risks.append(
            "Potential compliance exposure and exclusion of users who rely on "
            "assistive technologies"
        )

    # Content gaps risk
    if clusters:
        total_gaps = sum(
            len(c.get("content_gaps", []))
            for c in clusters.get("clusters", [])
        )
        if total_gaps > 0:
            risks.append(
                f"Competitors capturing demand for {total_gaps} topic areas "
                f"where this site has no content presence"
            )

    if not risks:
        return ""  # Skip section entirely for high-scoring sites

    lines = ["## Key Risks\n"]
    for risk in risks[:3]:
        lines.append(f"- {risk}")

    return "\n".join(lines)


def _section_scorecard(scores: Dict[str, int]) -> str:
    """Section 5: Composite category scorecard table."""
    sem = scores.get("semantic_html", 0)
    sd = scores.get("structured_data", 0)
    js = scores.get("js_bloat", 0)
    aeo = scores.get("aeo_content", 0)
    rag = scores.get("rag_readiness", 0)
    agent = scores.get("agentic_protocols", 0)
    il = scores.get("internal_linking", 0)
    a11y = scores.get("accessibility", 0)
    data = scores.get("data_integrity", 0)

    tech = _avg(sem, sd, js)
    content = _avg(aeo, rag)
    ai = _avg(aeo, rag, agent)
    structure = _avg(il, a11y, data)

    lines = [
        "## Current State\n",
        "| Category | Score | Assessment |",
        "|----------|:-----:|------------|",
        f"| Technical Foundation | {tech} | {_interp(tech)} |",
        f"| Content Effectiveness | {content} | {_interp(content)} |",
        f"| AI Readiness | {ai} | {_interp(ai)} |",
        f"| Site Structure | {structure} | {_interp(structure)} |",
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

    actions: List[str] = []

    if scores.get("semantic_html", 100) < 65:
        if is_webflow:
            actions.append(
                "Add missing heading hierarchy and semantic elements using Webflow's "
                "tag settings to improve how search engines interpret page structure"
            )
        else:
            actions.append(
                "Add missing heading hierarchy and semantic HTML signals "
                "to improve how search engines interpret page structure"
            )

    if scores.get("structured_data", 100) < 65:
        if is_webflow:
            actions.append(
                "Implement structured data markup using Webflow Collection fields "
                "and custom code embeds to enable rich search results"
            )
        else:
            actions.append(
                "Implement structured data markup (Schema.org) for key page types "
                "to enable rich search results"
            )

    if scores.get("aeo_content", 100) < 65:
        actions.append(
            "Rework core content pages to include direct-answer formatting "
            "that AI systems prioritize for citation"
        )

    if scores.get("rag_readiness", 100) < 65:
        actions.append(
            "Improve content structure with clear sections, summaries, and "
            "entity-rich text that AI retrieval systems can extract"
        )

    if scores.get("internal_linking", 100) < 65:
        action = "Restructure internal links to direct authority toward high-priority pages"
        if tipr:
            top_hoarders = tipr.get("summary", {}).get("top_hoarders", [])
            if top_hoarders:
                action += " — starting with pages that hold disproportionate link equity"
        actions.append(action)

    if scores.get("accessibility", 100) < 65:
        # Pull top 2 specific a11y findings
        a11y_findings = []
        a11y_cat = report.get("categories", {}).get("accessibility", {})
        for chk in a11y_cat.get("checks", {}).values():
            if isinstance(chk, dict):
                for f in chk.get("findings", []):
                    if f.get("severity") in ("critical", "high"):
                        desc = f.get("description", "")
                        if len(desc) > 60:
                            desc = desc[:57] + "..."
                        a11y_findings.append(desc)
        if a11y_findings:
            specifics = " and ".join(a11y_findings[:2])
            actions.append(
                f"Address accessibility gaps including {specifics} "
                f"to expand audience reach"
            )
        else:
            actions.append(
                "Address accessibility gaps to expand audience reach and "
                "reduce compliance risk"
            )

    if scores.get("agentic_protocols", 100) < 65:
        actions.append(
            "Add AI agent compatibility signals (robots.txt AI directives, "
            "llms.txt, structured API endpoints) to improve automated discovery"
        )

    if scores.get("data_integrity", 100) < 65:
        actions.append(
            "Fix tracking implementation gaps to ensure analytics data "
            "accurately reflects site performance"
        )

    # TIPR-derived actions
    if tipr:
        rec_count = len(tipr.get("recommendations", []))
        if rec_count > 0:
            # Find dominant recommendation group
            groups: Dict[str, int] = {}
            for r in tipr.get("recommendations", []):
                g = r.get("group", "general")
                groups[g] = groups.get(g, 0) + 1
            top_group = max(groups, key=groups.get) if groups else "general"
            actions.append(
                f"Implement {rec_count} internal link changes identified by link "
                f"intelligence analysis, prioritizing {top_group.replace('_', ' ')} actions"
            )

    # Cluster gap actions
    if clusters:
        total_gaps = sum(
            len(c.get("content_gaps", []))
            for c in clusters.get("clusters", [])
        )
        if total_gaps > 0:
            actions.append(
                f"Create content for {total_gaps} identified topic gaps to "
                f"establish authority in uncovered service areas"
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


def _section_opportunities(report: dict, scores: Dict[str, int]) -> str:
    """Section 7: Forward-looking strategic opportunities."""
    tipr = _get_tipr(report)
    nlp = _get_nlp(report)
    clusters = _get_clusters(report)
    cms = (report.get("cms_detection") or {}).get("platform", "unknown")

    opps: List[str] = []

    # Cluster expansion
    if clusters:
        total_gaps = sum(
            len(c.get("content_gaps", []))
            for c in clusters.get("clusters", [])
        )
        if total_gaps > 0:
            opps.append(
                f"Expand into {total_gaps} high-intent topic areas identified by "
                f"semantic analysis where the site currently has no content presence"
            )

    # Amplify Stars
    if tipr:
        stars = tipr.get("summary", {}).get("stars", 0)
        if stars > 0:
            opps.append(
                f"Amplify the {stars} pages already performing well (classified as "
                f"'Star' pages) by building more internal links to them from related content"
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
        # Find entity types with high salience
        top_entity = entities[0] if entities else None
        if top_entity and top_entity.get("salience", 0) > 0.3:
            opps.append(
                f"Double down on \"{top_entity['name']}\" content where the site "
                f"already demonstrates topical authority (salience: "
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


def _section_supporting_detail(report: dict, scores: Dict[str, int]) -> str:
    """Section 8: 1–2 example findings per scorecard category."""
    findings = _collect_findings(report)
    if not findings:
        return ""

    # Group findings by composite category
    tech_pillars = {"semantic_html", "structured_data", "js_bloat", "css_quality"}
    content_pillars = {"aeo_content", "rag_readiness"}
    ai_pillars = {"aeo_content", "rag_readiness", "agentic_protocols"}
    structure_pillars = {"internal_linking", "accessibility", "data_integrity"}

    def _pick(pillar_set: set, count: int = 2) -> List[str]:
        out = []
        for f in findings:
            if f.get("pillar_key") in pillar_set:
                desc = f.get("description", "")
                if desc and desc not in out:
                    out.append(desc)
                if len(out) >= count:
                    break
        return out

    tech_examples = _pick(tech_pillars)
    content_examples = _pick(content_pillars)
    ai_examples = _pick(ai_pillars - content_pillars)  # avoid duplicates
    structure_examples = _pick(structure_pillars)

    has_any = tech_examples or content_examples or ai_examples or structure_examples
    if not has_any:
        return ""

    lines = ["### Supporting Detail\n"]

    if tech_examples:
        joined = " · ".join(tech_examples[:2])
        lines.append(f"- **Technical Foundation:** {joined}")
    if content_examples:
        joined = " · ".join(content_examples[:2])
        lines.append(f"- **Content Effectiveness:** {joined}")
    if ai_examples:
        joined = " · ".join(ai_examples[:2])
        lines.append(f"- **AI Readiness:** {joined}")
    if structure_examples:
        joined = " · ".join(structure_examples[:2])
        lines.append(f"- **Site Structure:** {joined}")

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
    detail = _section_supporting_detail(report, scores)
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
