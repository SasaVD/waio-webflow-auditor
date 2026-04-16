"""AI Visibility orchestrator — calls pipeline stages in order."""
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from dataforseo_client import DataForSEOClient
from .schema import BrandExtractionError
from .brand_resolver import resolve_brand
from .competitor_resolver import resolve_competitors, normalize_domain
from .prompts import build_prompts
from .mentions_fetcher import fetch_mentions
from .responses_fetcher import fetch_responses
from .sov_calculator import calculate_sov
from .cost_tracker import CostTracker

logger = logging.getLogger(__name__)


def _resolve_status(engine_results: dict) -> str:
    """Determine overall status from per-engine results."""
    oks = sum(1 for r in engine_results.values() if r.status == "ok")
    if oks == len(engine_results):
        return "ok"
    if oks >= 1:
        return "partial"
    return "failed"


async def run_ai_visibility_analysis(
    audit_id: str,
    brand_override: str | None = None,
) -> None:
    """Run the full AI Visibility pipeline and write results to the audit report.

    This is designed to be called via asyncio.create_task() — it manages its
    own DB writes and error handling. Returns None; results go to report_json.
    """
    # Import DB functions here to avoid circular imports at module level
    from db_router import get_audit_by_id, update_audit_report

    start = time.monotonic()

    try:
        # Load the audit record
        audit = await get_audit_by_id(audit_id)
        if not audit:
            logger.error(f"AI Visibility: audit {audit_id} not found")
            return

        report = audit.get("report_json") or {}
        nlp_data = report.get("nlp_analysis") or {}
        nlp_entities = nlp_data.get("entities") or []

        # Check for existing override in DB
        # The brand_override param takes precedence (from recompute request),
        # but we also check the report for a previously saved override
        if not brand_override:
            existing_viz = report.get("ai_visibility") or {}
            if existing_viz.get("brand_name_source") == "override":
                brand_override = existing_viz.get("brand_name")

        # Stage 1: Resolve brand
        try:
            brand_info = resolve_brand(brand_override, nlp_entities)
        except BrandExtractionError as e:
            logger.warning(f"AI Visibility: brand extraction failed for {audit_id}: {e}")
            await update_audit_report(audit_id, {
                "ai_visibility": {
                    "last_computed_at": datetime.now(timezone.utc).isoformat(),
                    "last_computed_status": "failed",
                    "error": str(e),
                }
            })
            return

        # Stage 2: Resolve competitors
        competitor_urls = report.get("competitor_urls") or []
        # Also check the PremiumAuditRequest competitor_urls stored in competitive_data
        competitive_data = report.get("competitive_data")
        competitors = resolve_competitors(
            competitor_urls=competitor_urls,
            competitive_data=competitive_data,
            co_mention_domains=None,  # Tier 3 populated after mentions fetch
        )

        # Stage 3: Build prompts
        detected_industry = nlp_data.get("detected_industry")
        top_entity = nlp_data.get("primary_entity")
        prompts = build_prompts(detected_industry, top_entity, brand_info.name)

        # Stage 4-6: DataForSEO calls
        cost_tracker = CostTracker()
        dfs_client = DataForSEOClient()

        try:
            # Stage 4: Fetch LLM Mentions (pre-indexed database)
            mentions = await fetch_mentions(dfs_client, brand_info.name, cost_tracker)

            # If no competitors yet, try tier 3 (co-mentions) — not implemented in Phase 1
            # Tier 3 would scan mentions data for co-mentioned domains

            # Stage 5: Fetch LLM Responses (live queries)
            responses = await fetch_responses(dfs_client, prompts, brand_info.name, cost_tracker)

            # Stage 6: Compute SOV (from cross_aggregated, if competitors available)
            sov = None
            if competitors.domains:
                # Extract brand domain from audit URL
                from urllib.parse import urlparse
                parsed_url = urlparse(audit.get("url", ""))
                brand_domain = normalize_domain(parsed_url.hostname or "")

                all_brands = [brand_domain] + competitors.domains
                cross_data = await dfs_client.llm_mentions_cross_aggregated(all_brands)
                cost_tracker.add(cross_data.get("money_spent"))
                sov = calculate_sov(cross_data, brand_domain, competitors.domains)
        finally:
            await dfs_client.close()

        # Assemble the result blob
        duration = round(time.monotonic() - start, 1)
        this_run_cost = round(cost_tracker.total, 4)
        status = _resolve_status(responses.engines)

        blob: dict[str, Any] = {
            "last_computed_at": datetime.now(timezone.utc).isoformat(),
            "last_computed_status": status,
            "run_count": (report.get("ai_visibility", {}).get("run_count", 0) or 0) + 1,
            "brand_name": brand_info.name,
            "brand_name_source": brand_info.source,
            "detected_industry": detected_industry,
            "competitors": competitors.to_dict(),
            "mentions_database": mentions.to_dict(),
            "live_test": {
                "prompts_used": [p.to_dict() for p in prompts],
                "engines": responses.to_dict()["engines"],
            },
            "cost_usd": this_run_cost,
            "duration_seconds": duration,
        }

        if sov:
            blob["share_of_voice"] = sov.to_dict()

        # Calculate cumulative cost
        existing_cumulative = report.get("ai_visibility", {}).get("cumulative_cost_usd", 0) or 0
        blob["cumulative_cost_usd"] = round(existing_cumulative + this_run_cost, 4)

        # Write to report
        await update_audit_report(audit_id, {"ai_visibility": blob})

        # Update tracking columns
        try:
            from db_postgres import get_pool
            pool = await get_pool()
            if not isinstance(audit_id, uuid.UUID):
                audit_id_uuid = uuid.UUID(str(audit_id))
            else:
                audit_id_uuid = audit_id
            async with pool.acquire() as conn:
                await conn.execute(
                    """UPDATE audits SET
                        ai_visibility_cumulative_cost_usd = ai_visibility_cumulative_cost_usd + $1,
                        ai_visibility_run_count = ai_visibility_run_count + 1,
                        last_ai_visibility_run_at = NOW(),
                        brand_name_override = $2
                    WHERE id = $3""",
                    this_run_cost,
                    brand_info.name if brand_info.source == "override" else None,
                    audit_id_uuid,
                )
        except Exception as e:
            logger.warning(f"AI Visibility: failed to update tracking columns: {e}")

        logger.info(
            f"AI Visibility complete for {audit_id}: "
            f"status={status}, cost=${this_run_cost:.2f}, "
            f"duration={duration}s, engines={len(responses.engines)}"
        )

    except Exception as e:
        logger.exception(f"AI Visibility pipeline failed for {audit_id}")
        try:
            await update_audit_report(audit_id, {
                "ai_visibility": {
                    "last_computed_at": datetime.now(timezone.utc).isoformat(),
                    "last_computed_status": "failed",
                    "error": f"Pipeline error: {type(e).__name__}: {str(e)[:500]}",
                }
            })
        except Exception:
            pass
