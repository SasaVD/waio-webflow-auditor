"""
Competitive AI-Readiness Auditor.
Runs the full audit pipeline concurrently on a primary URL and up to 4 competitors,
then ranks by overall score, identifies advantages/weaknesses, and computes pillar averages.
"""
import asyncio
import logging
from typing import List, Dict, Any

from crawler import fetch_page
from html_auditor import run_html_audit
from structured_data_auditor import run_structured_data_audit
from css_js_auditor import run_css_js_audit
from accessibility_auditor import run_accessibility_audit
from aeo_content_auditor import run_aeo_content_audit
from rag_readiness_auditor import run_rag_readiness_audit
from agentic_protocol_auditor import run_agentic_protocol_audit
from data_integrity_auditor import run_data_integrity_audit
from internal_linking_auditor import run_internal_linking_audit
from scoring import compile_scores
from report_generator import generate_report

logger = logging.getLogger(__name__)

PILLAR_KEYS = [
    "semantic_html", "structured_data", "aeo_content", "css_quality",
    "js_bloat", "accessibility", "rag_readiness", "agentic_protocols", 
    "data_integrity", "internal_linking"
]

PILLAR_LABELS = {
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


async def audit_single_url(url: str) -> Dict[str, Any]:
    """Run the full 10-pillar audit on a single URL and return scores + report."""
    try:
        html_content, soup = await fetch_page(url)
        html_res = run_html_audit(soup, html_content)
        sd_res = run_structured_data_audit(html_content, url)
        css_js_res = run_css_js_audit(soup, html_content)
        aeo_res = run_aeo_content_audit(soup, html_content)
        rag_res = run_rag_readiness_audit(soup, html_content)
        agent_res = run_agentic_protocol_audit(soup, html_content, url)
        data_res = run_data_integrity_audit(soup, html_content)
        il_res = run_internal_linking_audit(soup, html_content, url, site_data=None)
        a11y_res = await run_accessibility_audit(url)

        scores_all = compile_scores(html_res, sd_res, aeo_res, css_js_res, a11y_res, rag_res, agent_res, data_res, il_res)
        scores = scores_all.get("scores", {})
        report = generate_report(url, html_res, sd_res, aeo_res, css_js_res, a11y_res, rag_res, agent_res, data_res, scores_all, il_res)

        return {
            "url": url,
            "overall_score": scores_all.get("overall_score", 0),
            "overall_label": scores_all.get("overall_label", "N/A"),
            "pillar_scores": {k: scores.get(k, 0) for k in PILLAR_KEYS},
            "report": report,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Competitive audit failed for {url}: {e}")
        return {
            "url": url,
            "overall_score": 0,
            "overall_label": "Error",
            "pillar_scores": {k: 0 for k in PILLAR_KEYS},
            "report": None,
            "error": str(e),
        }


async def run_competitive_audit(primary_url: str, competitor_urls: List[str]) -> Dict[str, Any]:
    """
    Run audits concurrently on primary + competitors, rank them, and identify
    advantages/weaknesses for the primary URL.
    """
    all_urls = [primary_url] + competitor_urls[:4]
    logger.info(f"Running competitive audit: primary={primary_url}, competitors={competitor_urls[:4]}")

    # Run all audits concurrently
    results = await asyncio.gather(*[audit_single_url(url) for url in all_urls])

    # Sort by score descending and assign rank
    ranked = sorted(results, key=lambda r: r["overall_score"], reverse=True)
    for i, r in enumerate(ranked):
        r["rank"] = i + 1

    # Compute pillar averages across all URLs
    pillar_averages: Dict[str, float] = {}
    for key in PILLAR_KEYS:
        scores_for_pillar = [r["pillar_scores"].get(key, 0) for r in results]
        pillar_averages[key] = round(sum(scores_for_pillar) / len(scores_for_pillar), 1) if scores_for_pillar else 0

    # Find primary result
    primary_result = next((r for r in ranked if r["url"] == primary_url), ranked[0])

    # Advantages: pillars where primary is ≥10 pts above average
    advantages = []
    weaknesses = []
    for key in PILLAR_KEYS:
        primary_score = primary_result["pillar_scores"].get(key, 0)
        avg = pillar_averages.get(key, 0)
        diff = round(primary_score - avg, 1)
        if diff >= 10:
            advantages.append({"pillar": PILLAR_LABELS.get(key, key), "key": key, "score": primary_score, "average": avg, "diff": diff})
        elif diff <= -10:
            weaknesses.append({"pillar": PILLAR_LABELS.get(key, key), "key": key, "score": primary_score, "average": avg, "diff": diff})

    return {
        "is_competitive": True,
        "primary_url": primary_url,
        "primary": primary_result,
        "rankings": ranked,
        "pillar_averages": pillar_averages,
        "pillar_labels": PILLAR_LABELS,
        "advantages": advantages,
        "weaknesses": weaknesses,
        "total_urls": len(all_urls),
    }
