from datetime import datetime, timezone
from typing import Dict, Any, List, cast

def generate_report(url: str, html_res: dict, sd_res: dict, aeo_res: dict, css_js_res: dict, a11y_res: dict, rag_res: dict, agent_res: dict, data_res: dict, scores: dict) -> Dict[str, Any]:
    all_findings: List[Dict[str, Any]] = cast(List[Dict[str, Any]], (
        html_res.get("findings", []) + 
        sd_res.get("findings", []) + 
        aeo_res.get("findings", []) +
        css_js_res.get("findings", []) + 
        a11y_res.get("findings", []) +
        rag_res.get("findings", []) +
        agent_res.get("findings", []) +
        data_res.get("findings", [])
    ))
    
    crit = sum(1 for f in all_findings if f['severity'] == 'critical')
    high = sum(1 for f in all_findings if f['severity'] == 'high')
    med = sum(1 for f in all_findings if f['severity'] == 'medium')
    
    all_positive = (
        html_res.get("positive_findings", []) +
        sd_res.get("positive_findings", []) +
        aeo_res.get("positive_findings", []) +
        css_js_res.get("positive_findings", []) +
        a11y_res.get("positive_findings", []) +
        rag_res.get("positive_findings", []) +
        agent_res.get("positive_findings", []) +
        data_res.get("positive_findings", [])
    )
    
    top_priorities = []
    # Sort findings: critical first, high second
    sorted_findings = sorted(all_findings, key=lambda x: {'critical': 0, 'high': 1, 'medium': 2}.get(x['severity'], 3))
    for f in sorted_findings[:5]:  # type: ignore
         top_priorities.append(f['recommendation'])

    return {
        "url": url,
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_score": scores["overall_score"],
        "overall_label": scores["overall_label"],
        "categories": {
            "semantic_html": {
                "score": scores["scores"]["semantic_html"],
                "label": scores["labels"]["semantic_html"],
                "checks": html_res.get("checks", {})
            },
            "structured_data": {
                "score": scores["scores"]["structured_data"],
                "label": scores["labels"]["structured_data"],
                "checks": sd_res.get("checks", {})
            },
            "aeo_content": {
                "score": scores["scores"]["aeo_content"],
                "label": scores["labels"]["aeo_content"],
                "checks": aeo_res.get("checks", {})
            },
            "css_quality": {
                "score": scores["scores"]["css_quality"],
                "label": scores["labels"]["css_quality"],
                "checks": {k: v for k, v in css_js_res.get("checks", {}).items() if k in ["framework_detection", "naming_consistency", "inline_styles", "external_stylesheets", "render_blocking"]}
            },
            "js_bloat": {
                "score": scores["scores"]["js_bloat"],
                "label": scores["labels"]["js_bloat"],
                "checks": {k: v for k, v in css_js_res.get("checks", {}).items() if k in ["webflow_js_bloat", "third_party_scripts", "total_scripts"]}
            },
            "accessibility": {
                "score": scores["scores"]["accessibility"],
                "label": scores["labels"]["accessibility"],
                "checks": a11y_res.get("checks", {})
            },
            "rag_readiness": {
                "score": scores["scores"]["rag_readiness"],
                "label": scores["labels"]["rag_readiness"],
                "checks": rag_res.get("checks", {})
            },
            "agentic_protocols": {
                "score": scores["scores"]["agentic_protocols"],
                "label": scores["labels"]["agentic_protocols"],
                "checks": agent_res.get("checks", {})
            },
            "data_integrity": {
                "score": scores["scores"]["data_integrity"],
                "label": scores["labels"]["data_integrity"],
                "checks": data_res.get("checks", {})
            }
        },
        "positive_findings": all_positive,
        "summary": {
            "total_findings": len(all_findings),
            "critical": crit,
            "high": high,
            "medium": med,
            "top_priorities": top_priorities
        }
    }
