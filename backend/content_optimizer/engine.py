"""Content Optimizer orchestrator -- calls pipeline stages in order."""
import hashlib
import logging
import time
from datetime import datetime, timezone

from .serp_fetcher import fetch_serp_results
from .content_extractor import extract_content_from_urls
from .wdf_idf_calculator import run_wdf_idf_analysis
from .term_classifier import classify_terms
from .recommendation_engine import generate_recommendations
from .schema import ContentOptimizationResult, TermClassification

logger = logging.getLogger(__name__)


def analysis_key(url: str, keyword: str) -> str:
    """Short hash of url+keyword for storage key."""
    raw = f"{url}|{keyword}".encode()
    return hashlib.md5(raw).hexdigest()[:8]


async def run_content_optimization(
    audit_id: str,
    target_url: str,
    target_text: str,
    keyword: str,
    top_entities: list[str] | None = None,
    num_competitors: int = 10,
) -> None:
    """Full WDF*IDF content optimization pipeline.

    Writes results directly to report_json["content_optimizer"]["analyses"][key].
    Designed to be called via asyncio.create_task().
    """
    from db_router import get_audit_by_id, update_audit_report

    start_time = time.time()
    key = analysis_key(target_url, keyword)

    try:
        # Step 1: Fetch SERP competitors
        serp_results = await fetch_serp_results(keyword, num_results=num_competitors)
        competitor_urls = [
            r["url"] for r in serp_results if r["url"] != target_url
        ][:num_competitors]

        # Step 2: Extract content from competitors
        competitor_extractions = await extract_content_from_urls(competitor_urls)
        successful = [e for e in competitor_extractions if e["success"]]
        failed_count = len(competitor_extractions) - len(successful)
        competitor_texts = [e["text"] for e in successful]

        if len(competitor_texts) < 3:
            raise ValueError(
                f"Only {len(competitor_texts)} competitor pages could be extracted. "
                f"Need at least 3 for meaningful analysis."
            )

        # Step 3: Compute WDF*IDF
        terms = run_wdf_idf_analysis(
            target_text=target_text,
            competitor_texts=competitor_texts,
            max_terms=100,
            ngram_range=(1, 3),
        )

        # Step 4: Classify terms
        terms = classify_terms(terms, keyword, top_entities)

        # Step 5: Generate recommendations
        recommendations = generate_recommendations(terms)

        # Step 6: Prepare chart data (top 60 terms)
        chart_terms = sorted(
            terms, key=lambda t: t.competitor_avg_wdf_idf, reverse=True
        )[:60]
        chart_data = [
            {
                "term": t.term,
                "target": t.target_wdf_idf,
                "comp_max": t.competitor_max_wdf_idf,
                "comp_avg": t.competitor_avg_wdf_idf,
                "classification": t.classification.value if t.classification else "auxiliary",
            }
            for t in chart_terms
        ]

        # Summary stats
        classification_counts = {"core": 0, "semantic": 0, "auxiliary": 0, "filler": 0}
        for t in terms:
            if t.classification:
                classification_counts[t.classification.value] += 1

        important_terms = [
            t for t in terms
            if t.classification in (TermClassification.CORE, TermClassification.SEMANTIC)
        ]
        gaps = [
            t for t in important_terms
            if t.target_wdf_idf < t.competitor_avg_wdf_idf * 0.5 or t.target_frequency == 0
        ]
        content_gap_score = round(
            len(gaps) / max(len(important_terms), 1) * 100, 1
        )

        duration = round(time.time() - start_time, 1)

        result = ContentOptimizationResult(
            keyword=keyword,
            target_url=target_url,
            target_word_count=len(target_text.split()),
            competitors_analyzed=len(successful),
            competitors_failed=failed_count,
            terms=[t.to_dict() for t in terms],
            recommendations=[r.to_dict() for r in recommendations],
            chart_data=chart_data,
            summary={
                "total_terms": len(terms),
                "core_count": classification_counts["core"],
                "semantic_count": classification_counts["semantic"],
                "auxiliary_count": classification_counts["auxiliary"],
                "filler_count": classification_counts["filler"],
                "content_gap_score": content_gap_score,
                "recommendations_count": {
                    "increase": sum(1 for r in recommendations if r.type.value == "increase"),
                    "add": sum(1 for r in recommendations if r.type.value == "add"),
                    "reduce": sum(1 for r in recommendations if r.type.value == "reduce"),
                    "remove": sum(1 for r in recommendations if r.type.value == "remove"),
                },
            },
            serp_results=serp_results,
            duration_seconds=duration,
            cost_usd=0.01,
        )

        # Write to report_json
        audit = await get_audit_by_id(audit_id)
        report = (audit.get("report_json") or {}) if audit else {}
        co = report.get("content_optimizer") or {}
        analyses = co.get("analyses") or {}

        analyses[key] = {
            "url": target_url,
            "keyword": keyword,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "status": "ok",
            "result": result.to_dict(),
        }

        await update_audit_report(audit_id, {
            "content_optimizer": {"analyses": analyses}
        })

        logger.info(
            f"Content optimization complete for {target_url} [{keyword}]: "
            f"gap={content_gap_score}%, terms={len(terms)}, "
            f"recs={len(recommendations)}, duration={duration}s"
        )

    except Exception as e:
        logger.exception(f"Content optimization failed for {target_url} [{keyword}]")
        try:
            audit = await get_audit_by_id(audit_id)
            report = (audit.get("report_json") or {}) if audit else {}
            co = report.get("content_optimizer") or {}
            analyses = co.get("analyses") or {}
            analyses[key] = {
                "url": target_url,
                "keyword": keyword,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "error": f"{type(e).__name__}: {str(e)[:500]}",
            }
            await update_audit_report(audit_id, {
                "content_optimizer": {"analyses": analyses}
            })
        except Exception:
            pass
