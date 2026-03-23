from datetime import datetime, timezone
from typing import Dict, Any, List, cast, Optional

def generate_report(url: str, html_res: dict, sd_res: dict, aeo_res: dict, css_js_res: dict, a11y_res: dict, rag_res: dict, agent_res: dict, data_res: dict, scores: dict, il_res: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    all_findings: List[Dict[str, Any]] = cast(List[Dict[str, Any]], (
        html_res.get("findings", []) + 
        sd_res.get("findings", []) + 
        aeo_res.get("findings", []) +
        css_js_res.get("findings", []) + 
        a11y_res.get("findings", []) +
        rag_res.get("findings", []) +
        agent_res.get("findings", []) +
        data_res.get("findings", []) +
        il_res.get("findings", []) if il_res else []
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
        data_res.get("positive_findings", []) +
        (il_res.get("positive_findings", []) if il_res else [])
    )
    
    top_priorities = []
    # Sort findings: critical first, high second
    sorted_findings = sorted(all_findings, key=lambda x: {'critical': 0, 'high': 1, 'medium': 2}.get(x['severity'], 3))
    for f in sorted_findings[:5]:  # type: ignore
         top_priorities.append(f['recommendation'])

    categories = {
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
    }

    if il_res:
        categories["internal_linking"] = {
            "score": scores["scores"]["internal_linking"],
            "label": scores["labels"]["internal_linking"],
            "checks": il_res.get("checks", {})
        }

    return {
        "url": url,
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_score": scores["overall_score"],
        "overall_label": scores["overall_label"],
        "categories": categories,
        "positive_findings": all_positive,
        "summary": {
            "total_findings": len(all_findings),
            "critical": crit,
            "high": high,
            "medium": med,
            "top_priorities": top_priorities
        }
    }

def generate_site_report(start_url: str, page_audits: List[Dict[str, Any]], job_id: str = "") -> Dict[str, Any]:
    if not page_audits:
        return {"error": "No pages successfully crawled."}
        
    avg_score = sum(p["scores"]["overall_score"] for p in page_audits) / len(page_audits)
    
    final_label = "critical"
    if avg_score >= 90:
        final_label = "excellent"
    elif avg_score >= 80:
        final_label = "good"
    elif avg_score >= 60:
        final_label = "needs improvement"
    elif avg_score >= 40:
        final_label = "poor"
        
    detailed_reports = []
    for p in page_audits:
        rep = generate_report(
            p["url"], p.get("html_res",{}), p.get("sd_res",{}), p.get("aeo_res",{}), 
            p.get("css_js_res",{}), p.get("a11y_res",{}), p.get("rag_res",{}), 
            p.get("agent_res",{}), p.get("data_res",{}), p.get("scores",{}), p.get("il_res")
        )
        detailed_reports.append(rep)
        
    return {
        "url": start_url,
        "is_site_audit": True,
        "job_id": job_id,
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "pages_crawled": len(page_audits),
        "overall_score": int(avg_score),
        "overall_label": final_label,
        "pages": [
            {
                "url": p["url"],
                "overall_score": p["scores"]["overall_score"],
                "overall_label": p["scores"]["overall_label"]
            } for p in page_audits
        ],
        "detailed_reports": detailed_reports
    }
