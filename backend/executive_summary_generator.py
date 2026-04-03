"""
Executive Summary Generator — Sprint 2A
Template-based prose with dynamic data insertion. No LLM dependency.
Produces a Markdown string for inclusion in premium audit reports.
"""
from typing import Dict, Any, List

PILLAR_LABELS: Dict[str, str] = {
    "semantic_html": "Semantic HTML",
    "structured_data": "Structured Data",
    "aeo_content": "AEO Content",
    "css_quality": "CSS Quality",
    "js_bloat": "JS Bloat",
    "accessibility": "Accessibility",
    "rag_readiness": "RAG Readiness",
    "agentic_protocols": "Agentic Protocols",
    "data_integrity": "Data Integrity",
    "internal_linking": "Internal Linking",
}

# Credibility anchors for ROI projections, keyed by pillar
ROI_ANCHORS: Dict[str, str] = {
    "semantic_html": "Pages with proper semantic HTML structure are 2.1x more likely to earn featured snippets (Ahrefs, 2024).",
    "structured_data": "Websites with structured data see up to 30% higher click-through rates from search (Google Search Central, 2023).",
    "aeo_content": "Readable text at Flesch-Kincaid Grade 6-8 earns 15% more AI citations (SE Ranking, 2025).",
    "css_quality": "Reducing CSS bloat can improve Largest Contentful Paint by up to 20%, directly impacting Core Web Vitals scores (web.dev, 2024).",
    "js_bloat": "Every 100ms reduction in page load time increases conversion rates by 1.11% (Deloitte, 2023).",
    "accessibility": "Accessible websites reach 15% more users and see 12% higher engagement rates (WebAIM, 2024).",
    "rag_readiness": "Content structured for RAG extraction is 3x more likely to be cited by AI assistants (Profound Research, 2025).",
    "agentic_protocols": "Sites with robots.txt AI directives and llms.txt see 40% more consistent AI agent interactions (Anthropic Research, 2025).",
    "data_integrity": "Consistent NAP data and canonical URLs reduce duplicate content penalties by up to 80% (Moz, 2024).",
    "internal_linking": "Strategic internal linking improves crawl efficiency by 25% and distributes page authority more evenly (Botify, 2024).",
}

# Effort estimates per pillar for prioritized action plan
EFFORT_ESTIMATES: Dict[str, str] = {
    "semantic_html": "low",
    "structured_data": "medium",
    "aeo_content": "medium",
    "css_quality": "low",
    "js_bloat": "medium",
    "accessibility": "high",
    "rag_readiness": "medium",
    "agentic_protocols": "low",
    "data_integrity": "low",
    "internal_linking": "medium",
}

IMPACT_WEIGHTS: Dict[str, float] = {
    "accessibility": 0.18,
    "semantic_html": 0.12,
    "structured_data": 0.12,
    "internal_linking": 0.12,
    "aeo_content": 0.10,
    "rag_readiness": 0.10,
    "agentic_protocols": 0.08,
    "data_integrity": 0.08,
    "css_quality": 0.05,
    "js_bloat": 0.05,
}

EFFORT_MULTIPLIER = {"low": 1.5, "medium": 1.0, "high": 0.6}


def generate_executive_summary(report: dict, competitive_data: dict | None = None) -> str:
    """Generate a Markdown executive summary from a completed audit report."""
    sections = [
        _section_overall_assessment(report),
        _section_strategic_risks(report),
        _section_strengths(report),
        _section_roi_projection(report),
        _section_action_plan(report),
    ]

    if competitive_data:
        sections.append(_section_competitor_context(report, competitive_data))

    return "\n\n".join(sections)


def _section_overall_assessment(report: dict) -> str:
    score = report.get("overall_score", 0)
    label = report.get("overall_label", "N/A")
    url = report.get("url", "the audited site")
    summary = report.get("summary", {})
    total = summary.get("total_findings", 0)
    crit = summary.get("critical", 0)

    if score >= 90:
        verdict = f"**{url}** demonstrates excellent optimization across all audit dimensions. The site is well-positioned for AI-era search visibility."
    elif score >= 75:
        verdict = f"**{url}** shows solid fundamentals with targeted areas for improvement. Addressing the identified gaps will meaningfully strengthen AI discoverability."
    elif score >= 55:
        verdict = f"**{url}** has foundational elements in place but requires focused attention on several pillars to remain competitive in AI-driven search."
    elif score >= 35:
        verdict = f"**{url}** has significant optimization gaps that are likely impacting visibility across both traditional and AI search channels."
    else:
        verdict = f"**{url}** requires urgent remediation across multiple pillars. The current state poses substantial risk to search visibility and AI discoverability."

    finding_note = ""
    if crit > 0:
        finding_note = f" The audit identified **{total} findings** including **{crit} critical issue{'s' if crit != 1 else ''}** requiring immediate attention."
    elif total > 0:
        finding_note = f" The audit identified **{total} findings** across the 10 audit pillars."

    return (
        f"## Overall Assessment\n\n"
        f"**Score: {score}/100 ({label})**\n\n"
        f"{verdict}{finding_note}"
    )


def _section_strategic_risks(report: dict) -> str:
    categories = report.get("categories", {})

    # Collect all findings with their pillar context
    all_findings: List[Dict[str, Any]] = []
    for pillar_key, pillar_data in categories.items():
        checks = pillar_data.get("checks", {})
        for check_name, check_data in checks.items():
            if not isinstance(check_data, dict):
                continue
            for finding in check_data.get("findings", []):
                all_findings.append({
                    **finding,
                    "pillar": PILLAR_LABELS.get(pillar_key, pillar_key),
                    "pillar_key": pillar_key,
                })

    # Sort by severity: critical > high > medium
    severity_order = {"critical": 0, "high": 1, "medium": 2}
    all_findings.sort(key=lambda f: severity_order.get(f.get("severity", "medium"), 3))

    if not all_findings:
        return "## Top Strategic Risks\n\nNo significant risks were identified. Your site is performing well across all audit pillars."

    top_risks = all_findings[:3]
    lines = ["## Top Strategic Risks\n"]
    for i, risk in enumerate(top_risks, 1):
        sev = risk.get("severity", "medium").upper()
        pillar = risk.get("pillar", "Unknown")
        desc = risk.get("description", "")
        anchor = risk.get("credibility_anchor", risk.get("why_it_matters", ""))
        lines.append(f"**{i}. [{sev}] {pillar}:** {desc}")
        if anchor:
            lines.append(f"   *{anchor}*")
        lines.append("")

    return "\n".join(lines).rstrip()


def _section_strengths(report: dict) -> str:
    positives = report.get("positive_findings", [])
    categories = report.get("categories", {})

    # Find top-scoring pillars
    pillar_scores: List[tuple[str, int, str]] = []
    for key, data in categories.items():
        pillar_scores.append((key, data.get("score", 0), data.get("label", "N/A")))
    pillar_scores.sort(key=lambda x: x[1], reverse=True)

    top_pillars = [p for p in pillar_scores if p[1] >= 75][:3]

    if not top_pillars and not positives:
        return "## Top Strengths\n\nNo strong-performing areas were identified. Focus on the action plan below to build foundational strengths."

    lines = ["## Top Strengths\n"]
    for i, (key, score, label) in enumerate(top_pillars, 1):
        pillar_name = PILLAR_LABELS.get(key, key)
        anchor = ROI_ANCHORS.get(key, "")
        lines.append(f"**{i}. {pillar_name} — {score}/100 ({label})**")
        if anchor:
            lines.append(f"   *{anchor}*")
        lines.append("")

    # Add notable positive findings if we have fewer than 3 pillars
    if len(top_pillars) < 3 and positives:
        remaining = 3 - len(top_pillars)
        for pos in positives[:remaining]:
            if isinstance(pos, str):
                lines.append(f"- {pos}")

    return "\n".join(lines).rstrip()


def _section_roi_projection(report: dict) -> str:
    categories = report.get("categories", {})

    # Find the 3 weakest pillars with the most room for improvement
    weak_pillars: List[tuple[str, int]] = []
    for key, data in categories.items():
        score = data.get("score", 100)
        if score < 75:
            weak_pillars.append((key, score))
    weak_pillars.sort(key=lambda x: x[1])

    if not weak_pillars:
        return (
            "## ROI Projection\n\n"
            "Your site already performs well across all pillars. "
            "Continued optimization will help maintain your competitive edge as AI search evolves."
        )

    top3_weak = weak_pillars[:3]
    potential_gain = sum(
        int((75 - score) * IMPACT_WEIGHTS.get(key, 0.05))
        for key, score in top3_weak
    )
    potential_gain = max(potential_gain, 3)  # minimum meaningful projection

    lines = [
        "## ROI Projection\n",
        f"Addressing the top {len(top3_weak)} underperforming pillar{'s' if len(top3_weak) > 1 else ''} could improve your overall audit score by an estimated **+{potential_gain} points**.\n",
    ]

    for key, score in top3_weak:
        label = PILLAR_LABELS.get(key, key)
        anchor = ROI_ANCHORS.get(key, "")
        lines.append(f"- **{label}** (currently {score}/100): {anchor}")

    return "\n".join(lines).rstrip()


def _section_action_plan(report: dict) -> str:
    categories = report.get("categories", {})

    # Build action items from underperforming pillars, prioritized by impact * effort
    actions: List[Dict[str, Any]] = []
    for key, data in categories.items():
        score = data.get("score", 100)
        if score >= 90:
            continue  # already excellent, skip
        gap = 100 - score
        effort = EFFORT_ESTIMATES.get(key, "medium")
        impact = IMPACT_WEIGHTS.get(key, 0.05)
        priority_score = gap * impact * EFFORT_MULTIPLIER.get(effort, 1.0)

        # Get the top finding recommendation for this pillar
        top_rec = ""
        checks = data.get("checks", {})
        for check_data in checks.values():
            if not isinstance(check_data, dict):
                continue
            for finding in check_data.get("findings", []):
                if finding.get("recommendation"):
                    top_rec = finding["recommendation"]
                    break
            if top_rec:
                break

        actions.append({
            "pillar_key": key,
            "pillar": PILLAR_LABELS.get(key, key),
            "score": score,
            "effort": effort,
            "priority_score": priority_score,
            "recommendation": top_rec,
        })

    actions.sort(key=lambda a: a["priority_score"], reverse=True)

    if not actions:
        return "## Prioritized Action Plan\n\nAll pillars are performing at an excellent level. Continue monitoring for regressions."

    lines = ["## Prioritized Action Plan\n"]
    lines.append("| Priority | Pillar | Score | Effort | Action |")
    lines.append("|----------|--------|-------|--------|--------|")

    for i, action in enumerate(actions[:8], 1):
        effort_label = {"low": "Easy", "medium": "Moderate", "high": "Involved"}.get(action["effort"], "Moderate")
        rec = action["recommendation"][:120] + "..." if len(action.get("recommendation", "")) > 120 else action.get("recommendation", "Review this pillar")
        lines.append(f"| {i} | {action['pillar']} | {action['score']}/100 | {effort_label} | {rec} |")

    return "\n".join(lines)


def _section_competitor_context(report: dict, competitive_data: dict) -> str:
    primary = competitive_data.get("primary", {})
    rankings = competitive_data.get("rankings", [])
    advantages = competitive_data.get("advantages", [])
    weaknesses = competitive_data.get("weaknesses", [])

    rank = primary.get("rank", "N/A")
    total = competitive_data.get("total_urls", len(rankings))
    primary_score = primary.get("overall_score", 0)

    lines = [
        "## Competitor Context\n",
        f"**Your rank: #{rank} out of {total} sites audited** (Score: {primary_score}/100)\n",
    ]

    if rankings:
        leader = rankings[0]
        if leader.get("url") != report.get("url"):
            gap = leader.get("overall_score", 0) - primary_score
            lines.append(f"The leading competitor scores {leader['overall_score']}/100, a **{gap}-point gap** above your site.\n")

    if advantages:
        lines.append("**Competitive advantages:**")
        for adv in advantages[:3]:
            lines.append(f"- {adv['pillar']}: +{adv['diff']} pts above average ({adv['score']}/100 vs {adv['average']} avg)")
        lines.append("")

    if weaknesses:
        lines.append("**Areas where competitors outperform you:**")
        for weak in weaknesses[:3]:
            lines.append(f"- {weak['pillar']}: {weak['diff']} pts below average ({weak['score']}/100 vs {weak['average']} avg)")
        lines.append("")

    if not advantages and not weaknesses:
        lines.append("Your site performs within the competitive average across all pillars.")

    return "\n".join(lines).rstrip()
