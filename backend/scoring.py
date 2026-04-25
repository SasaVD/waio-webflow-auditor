from typing import Dict, Any, Optional

# Canonical weights per pillar. MUST sum to 1.0.
# When a pillar scan fails we drop its weight and renormalize over the covered
# pillars (Option A). See compile_scores() for the full coverage model.
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

# If fewer than this fraction of weighted pillars scanned successfully, suppress
# the overall score entirely rather than renormalize over a non-representative
# subset. Option A above; Option C (suppress) below.
MIN_COVERAGE_FOR_SCORE = 0.70

# Workstream D4: scan_status values that mean "this pillar's analysis did not
# complete successfully". calculate_score(findings=[]) returns 100 by design
# (no deductions), but for non-ok pillars there were no findings to BEGIN with
# — the auditor never ran or was bot-blocked. Forcing score=0 on these
# pillars stops every downstream consumer (exec summary, PDF tiles, dashboard
# cards) from reading a confidently-wrong "perfect" pillar score. See the
# zeroing loop in compile_scores below for the full rationale.
NON_OK_STATUSES = {"failed", "incomplete", "bot_challenged"}


def calculate_score(findings: list[Dict[str, Any]]) -> int:
    score = 100.0
    
    criticals = [f for f in findings if f.get('severity') == 'critical']
    highs = [f for f in findings if f.get('severity') == 'high']
    mediums = [f for f in findings if f.get('severity') == 'medium']
    
    for i, _ in enumerate(criticals):
        score -= max(5.0, 18.0 - (i * 4.0))
    
    for i, _ in enumerate(highs):
        score -= max(3.0, 10.0 - (i * 2.0))
    
    for i, _ in enumerate(mediums):
        score -= max(1.0, 4.0 - (i * 0.5))
    
    medium_total = sum(max(1.0, 4.0 - (i * 0.5)) for i in range(len(mediums)))
    if medium_total > 20:
        score = 100.0
        for i, _ in enumerate(criticals):
            score -= max(5.0, 18.0 - (i * 4.0))
        for i, _ in enumerate(highs):
            score -= max(3.0, 10.0 - (i * 2.0))
        score -= min(20.0, medium_total)
    
    return max(0, int(round(score)))

def get_label(score: int) -> str:
    if score >= 90: return "Excellent"
    if score >= 75: return "Good"
    if score >= 55: return "Needs Improvement"
    if score >= 35: return "Poor"
    return "Critical"

def compile_scores(
    html_res: dict,
    sd_res: dict,
    aeo_res: dict,
    css_js_res: dict,
    a11y_res: dict,
    rag_res: dict,
    agent_res: dict,
    data_res: dict,
    internal_linking_res: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if internal_linking_res is None:
        internal_linking_res = {}
    
    html_score = calculate_score(html_res.get("findings", []))
    sd_score = calculate_score(sd_res.get("findings", []))
    aeo_score = calculate_score(aeo_res.get("findings", []))
    css_js_score = calculate_score(css_js_res.get("findings", []))
    a11y_score = calculate_score(a11y_res.get("findings", []))
    rag_score = calculate_score(rag_res.get("findings", []))
    agent_score = calculate_score(agent_res.get("findings", []))
    data_score = calculate_score(data_res.get("findings", []))
    il_score = calculate_score(internal_linking_res.get("findings", []))
    # Semantic HTML (20%), Structured Data (20%), AEO Content (15%), CSS Quality (5%), JavaScript Bloat (5%), Accessibility (35%)
    
    # Actually wait, css_js_res contains BOTH css findings and js findings.
    # We should split findings to score CSS vs JS separately, but for now we can approximate
    # Or split them by checking the check_key.
    
    css_findings = []
    js_findings = []
    
    css_keys = ["framework_detection", "naming_consistency", "inline_styles", "external_stylesheets", "render_blocking"]
    js_keys = ["webflow_js_bloat", "third_party_scripts", "total_scripts"]

    css_js_checks = css_js_res.get("checks", {}) or {}
    for k in css_keys:
        check = css_js_checks.get(k) or {}
        if "findings" in check:
            css_findings.extend(check["findings"])

    for k in js_keys:
        check = css_js_checks.get(k) or {}
        if "findings" in check:
            js_findings.extend(check["findings"])
            
    css_score = calculate_score(css_findings)
    js_score = calculate_score(js_findings)

    # css_quality and js_bloat both come from css_js_res; if that scan fails,
    # both sub-pillars fail together.
    css_js_status = css_js_res.get("scan_status", "ok")

    scan_statuses: Dict[str, str] = {
        "semantic_html": html_res.get("scan_status", "ok"),
        "structured_data": sd_res.get("scan_status", "ok"),
        "aeo_content": aeo_res.get("scan_status", "ok"),
        "css_quality": css_js_status,
        "js_bloat": css_js_status,
        "accessibility": a11y_res.get("scan_status", "ok"),
        "rag_readiness": rag_res.get("scan_status", "ok"),
        "agentic_protocols": agent_res.get("scan_status", "ok"),
        "data_integrity": data_res.get("scan_status", "ok"),
        "internal_linking": internal_linking_res.get("scan_status", "ok"),
    }

    raw_scores: Dict[str, int] = {
        "semantic_html": html_score,
        "structured_data": sd_score,
        "aeo_content": aeo_score,
        "css_quality": css_score,
        "js_bloat": js_score,
        "accessibility": a11y_score,
        "rag_readiness": rag_score,
        "agentic_protocols": agent_score,
        "data_integrity": data_score,
        "internal_linking": il_score,
    }

    # Workstream D4: non-ok pillars score 0, not the 100 that calculate_score
    # emits when the findings list is empty. This prevents confidently-wrong
    # "perfect" scores on pillars whose auditor never ran (sched.com 2026-04-23).
    # Coverage renormalization (loop below) already excludes these from overall,
    # but the raw scores dict is consumed by exec_summary_generator, PDF tiles,
    # dashboard pillar cards, and any other code that reads scores[pillar]
    # directly without checking scan_status. 0 is a safe integer for all
    # downstream comparisons; None would require touching ~51 consumers.
    # css_quality + js_bloat both inherit css_js_status, so iterating
    # scan_statuses zeroes both sub-pillars together when css_js_res fails.
    for pillar_key, status in scan_statuses.items():
        if status in NON_OK_STATUSES:
            raw_scores[pillar_key] = 0

    # Option A: weighted average over pillars that scanned successfully.
    # covered_weight is summed from PILLAR_WEIGHTS, not pillar count — so
    # Accessibility (18%) failing alone drops coverage to 82%, not 90%.
    covered_weight = 0.0
    weighted_sum = 0.0
    for pillar, weight in PILLAR_WEIGHTS.items():
        if scan_statuses.get(pillar, "ok") == "ok":
            covered_weight += weight
            weighted_sum += raw_scores[pillar] * weight

    overall: Optional[int]
    if covered_weight < MIN_COVERAGE_FOR_SCORE:
        # Too little of the audit succeeded to produce a meaningful score.
        # Surfaced as None so the UI can render "Score unavailable" instead of
        # a misleadingly-high number derived from 2-3 pillars.
        overall = None
        overall_label = "Scan incomplete"
    else:
        overall = int(round(weighted_sum / covered_weight))
        overall_label = get_label(overall)

    # Replace single css_js finding list with split if needed for report generator.
    css_js_res['css_score'] = css_score
    css_js_res['js_score'] = js_score

    # Workstream D4: labels for non-ok pillars are "Scan incomplete", not the
    # "Critical" that get_label(0) would produce. A bot-challenged pillar isn't
    # critically broken — it just wasn't analyzed. Surface the truth.
    pillar_labels: Dict[str, str] = {}
    for pillar_key, status in scan_statuses.items():
        if status in NON_OK_STATUSES:
            pillar_labels[pillar_key] = "Scan incomplete"
        else:
            pillar_labels[pillar_key] = get_label(raw_scores[pillar_key])

    return {
        "overall_score": overall,
        "overall_label": overall_label,
        "coverage_weight": round(covered_weight, 4),
        "scan_statuses": scan_statuses,
        "scores": raw_scores,
        "labels": pillar_labels,
    }
