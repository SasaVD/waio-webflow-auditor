from datetime import datetime, timezone
from typing import Dict, Any, List, cast, Optional

def generate_report(url: str, html_res: dict, sd_res: dict, aeo_res: dict, css_js_res: dict, a11y_res: dict, rag_res: dict, agent_res: dict, data_res: dict, scores: dict, il_res: Optional[Dict[str, Any]] = None, tier: str = "free") -> Dict[str, Any]:
    # Defense-in-depth: only pull findings/positives from pillars that scanned
    # successfully. Failed pillars should produce no findings upstream (the
    # outer except in accessibility_auditor no longer synthesizes one), but
    # guard here too so Priority Action Items can't surface a raw
    # "Failed to run complete accessibility scan" error as a recommendation.
    def _ok(res: Optional[Dict[str, Any]]) -> bool:
        if not res:
            return False
        return res.get("scan_status", "ok") == "ok"

    def _findings_if_ok(res: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return res.get("findings", []) if _ok(res) else []

    def _positives_if_ok(res: Optional[Dict[str, Any]]) -> List[Any]:
        return res.get("positive_findings", []) if _ok(res) else []

    all_findings: List[Dict[str, Any]] = cast(List[Dict[str, Any]], (
        _findings_if_ok(html_res) +
        _findings_if_ok(sd_res) +
        _findings_if_ok(aeo_res) +
        _findings_if_ok(css_js_res) +
        _findings_if_ok(a11y_res) +
        _findings_if_ok(rag_res) +
        _findings_if_ok(agent_res) +
        _findings_if_ok(data_res) +
        _findings_if_ok(il_res)
    ))

    crit = sum(1 for f in all_findings if f['severity'] == 'critical')
    high = sum(1 for f in all_findings if f['severity'] == 'high')
    med = sum(1 for f in all_findings if f['severity'] == 'medium')

    raw_positive = (
        _positives_if_ok(html_res) +
        _positives_if_ok(sd_res) +
        _positives_if_ok(aeo_res) +
        _positives_if_ok(css_js_res) +
        _positives_if_ok(a11y_res) +
        _positives_if_ok(rag_res) +
        _positives_if_ok(agent_res) +
        _positives_if_ok(data_res) +
        _positives_if_ok(il_res)
    )
    # Normalize: some auditors return strings, others return dicts with "text" key
    all_positive = []
    for p in raw_positive:
        if isinstance(p, str):
            all_positive.append(p)
        elif isinstance(p, dict):
            all_positive.append(p.get("text") or p.get("message") or p.get("description") or str(p))
        else:
            all_positive.append(str(p))
    
    top_priorities = []
    # Sort findings: critical first, high second
    sorted_findings = sorted(all_findings, key=lambda x: {'critical': 0, 'high': 1, 'medium': 2}.get(x['severity'], 3))
    for f in sorted_findings[:5]:  # type: ignore
         top_priorities.append(f['recommendation'])

    scan_statuses = scores.get("scan_statuses", {}) or {}

    def _cat(pillar_key: str, res: Optional[Dict[str, Any]], checks: Dict[str, Any]) -> Dict[str, Any]:
        status = scan_statuses.get(pillar_key, "ok")
        entry: Dict[str, Any] = {
            "score": scores["scores"][pillar_key],
            "label": scores["labels"][pillar_key],
            "scan_status": status,
            "checks": checks,
        }
        if status != "ok" and res is not None:
            err = res.get("scan_error")
            if err:
                entry["scan_error"] = err
        return entry

    css_checks_all = css_js_res.get("checks", {}) if css_js_res else {}
    css_quality_checks = {k: v for k, v in css_checks_all.items() if k in ["framework_detection", "naming_consistency", "inline_styles", "external_stylesheets", "render_blocking"]}
    js_bloat_checks = {k: v for k, v in css_checks_all.items() if k in ["webflow_js_bloat", "third_party_scripts", "total_scripts"]}

    categories = {
        "semantic_html": _cat("semantic_html", html_res, html_res.get("checks", {})),
        "structured_data": _cat("structured_data", sd_res, sd_res.get("checks", {})),
        "aeo_content": _cat("aeo_content", aeo_res, aeo_res.get("checks", {})),
        "css_quality": _cat("css_quality", css_js_res, css_quality_checks),
        "js_bloat": _cat("js_bloat", css_js_res, js_bloat_checks),
        "accessibility": _cat("accessibility", a11y_res, a11y_res.get("checks", {})),
        "rag_readiness": _cat("rag_readiness", rag_res, rag_res.get("checks", {})),
        "agentic_protocols": _cat("agentic_protocols", agent_res, agent_res.get("checks", {})),
        "data_integrity": _cat("data_integrity", data_res, data_res.get("checks", {})),
    }

    if il_res:
        categories["internal_linking"] = _cat("internal_linking", il_res, il_res.get("checks", {}))

    return {
        "url": url,
        "tier": tier,
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_score": scores["overall_score"],
        "overall_label": scores["overall_label"],
        "coverage_weight": scores.get("coverage_weight", 1.0),
        "scan_statuses": scan_statuses,
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
