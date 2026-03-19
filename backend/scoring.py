from typing import Dict, Any

def calculate_score(findings: list[Dict[str, Any]]) -> int:
    score = 100
    for finding in findings:
        sev = finding.get('severity', 'medium')
        if sev == 'critical': score -= 15
        elif sev == 'high': score -= 8
        elif sev == 'medium': score -= 3
    return max(0, score)

def get_label(score: int) -> str:
    if score >= 90: return "Excellent"
    if score >= 70: return "Good"
    if score >= 50: return "Needs Improvement"
    if score >= 30: return "Poor"
    return "Critical"

def compile_scores(
    html_res: dict,
    sd_res: dict,
    aeo_res: dict,
    css_js_res: dict,
    a11y_res: dict,
    rag_res: dict,
    agent_res: dict,
    data_res: dict
) -> Dict[str, Any]:
    
    html_score = calculate_score(html_res.get("findings", []))
    sd_score = calculate_score(sd_res.get("findings", []))
    aeo_score = calculate_score(aeo_res.get("findings", []))
    css_js_score = calculate_score(css_js_res.get("findings", []))
    a11y_score = calculate_score(a11y_res.get("findings", []))
    rag_score = calculate_score(rag_res.get("findings", []))
    agent_score = calculate_score(agent_res.get("findings", []))
    data_score = calculate_score(data_res.get("findings", []))
    
    # 5.10 Scoring Model
    # Semantic HTML (20%), Structured Data (20%), AEO Content (15%), CSS Quality (5%), JavaScript Bloat (5%), Accessibility (35%)
    
    # Actually wait, css_js_res contains BOTH css findings and js findings.
    # We should split findings to score CSS vs JS separately, but for now we can approximate
    # Or split them by checking the check_key.
    
    css_findings = []
    js_findings = []
    
    css_keys = ["framework_detection", "naming_consistency", "inline_styles", "external_stylesheets", "render_blocking"]
    js_keys = ["webflow_js_bloat", "third_party_scripts", "total_scripts"]
    
    for k in css_keys:
        if "findings" in css_js_res["checks"][k]:
            css_findings.extend(css_js_res["checks"][k]["findings"])
            
    for k in js_keys:
        if "findings" in css_js_res["checks"][k]:
            js_findings.extend(css_js_res["checks"][k]["findings"])
            
    css_score = calculate_score(css_findings)
    js_score = calculate_score(js_findings)
    
    overall = (html_score * 0.15) + (sd_score * 0.15) + (aeo_score * 0.10) + (css_score * 0.05) + (js_score * 0.05) + (a11y_score * 0.20) + (rag_score * 0.10) + (agent_score * 0.10) + (data_score * 0.10)
    overall = int(round(overall))
    
    # Replace single css_js finding list with split if needed for report generator.
    css_js_res['css_score'] = css_score
    css_js_res['js_score'] = js_score
    
    return {
        "overall_score": overall,
        "overall_label": get_label(overall),
        "scores": {
            "semantic_html": html_score,
            "structured_data": sd_score,
            "aeo_content": aeo_score,
            "css_quality": css_score,
            "js_bloat": js_score,
            "accessibility": a11y_score,
            "rag_readiness": rag_score,
            "agentic_protocols": agent_score,
            "data_integrity": data_score
        },
        "labels": {
            "semantic_html": get_label(html_score),
            "structured_data": get_label(sd_score),
            "aeo_content": get_label(aeo_score),
            "css_quality": get_label(css_score),
            "js_bloat": get_label(js_score),
            "accessibility": get_label(a11y_score),
            "rag_readiness": get_label(rag_score),
            "agentic_protocols": get_label(agent_score),
            "data_integrity": get_label(data_score)
        }
    }
