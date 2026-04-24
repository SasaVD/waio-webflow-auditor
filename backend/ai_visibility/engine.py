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


def resolve_industry(
    *,
    target_industry: str | None,
    detected_industry: str | None,
) -> tuple[str | None, str | None]:
    """Resolve the industry + source used for AI Visibility prompt generation.

    Priority (documented contract — Workstream D3.0, do NOT add fallback layers):

      1. ``target_industry`` (user-declared, from request.target_industry or
         report_json.audit_config.target_industry)
         → returns ``(target_industry, "user_declared")``
      2. ``detected_industry`` (NLP aggregation across crawled pages)
         → returns ``(detected_industry, "nlp_detected")``
      3. Neither present
         → returns ``(None, None)`` — caller renders "Needs attention" state
         and skips prompt generation entirely.

    We deliberately do NOT fall back to a generic "business services" leaf
    when both are None. Silent fallback caused incident 2026-04-23 (sched.com
    event-management SaaS was benchmarked against Accenture / McKinsey /
    Deloitte because detected_industry was None and the fallback kicked in).

    Args:
        target_industry: User-declared override. ``None``, empty string,
            and whitespace-only are all treated as "not provided".
        detected_industry: NLP-detected classification. Same empty/whitespace
            handling as ``target_industry``.

    Returns:
        A 2-tuple ``(value, source)`` where ``source`` is one of
        ``"user_declared"``, ``"nlp_detected"``, or ``None``.
    """
    user_val = (target_industry or "").strip()
    if user_val:
        return user_val, "user_declared"

    nlp_val = (detected_industry or "").strip()
    if nlp_val:
        return nlp_val, "nlp_detected"

    return None, None


async def run_ai_visibility_analysis(
    audit_id: str,
    brand_override: str | None = None,
    target_industry: str | None = None,
) -> None:
    """Run the full AI Visibility pipeline and write results to the audit report.

    This is designed to be called via asyncio.create_task() — it manages its
    own DB writes and error handling. Returns None; results go to report_json.

    Args:
        audit_id: Audit to analyse.
        brand_override: Optional user-provided brand name override (skips NLP
            brand extraction when set).
        target_industry: Optional user-declared industry override (Workstream
            D3). Takes precedence over NLP ``detected_industry``. When both
            this and the NLP value are empty, the engine writes a
            ``last_computed_status="needs_industry_confirmation"`` blob and
            short-circuits — no prompts are generated, no DFS calls are made.
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

        from nlp_sanitizer import sanitize_entity_dicts, sanitize_entity_name

        report = audit.get("report_json") or {}
        nlp_data = report.get("nlp_analysis") or {}
        detected_industry_raw = nlp_data.get("detected_industry")
        # Defense-in-depth: sanitize before brand_resolver or build_prompts
        # see the stuttering "Webflow Webflow" artifact (BUG-3).
        nlp_entities = sanitize_entity_dicts(
            nlp_data.get("entities") or [], detected_industry_raw
        )

        # Check for existing override in DB
        # The brand_override param takes precedence (from recompute request),
        # but we also check the report for a previously saved override
        if not brand_override:
            existing_viz = report.get("ai_visibility") or {}
            if existing_viz.get("brand_name_source") == "override":
                brand_override = existing_viz.get("brand_name")

        # Workstream D3: resolve the industry through the priority ladder
        # (user_declared → nlp_detected → None). If the caller passed an
        # explicit target_industry, use it; otherwise check the stored audit
        # record for a previously-saved user target.
        if not target_industry:
            existing_viz = report.get("ai_visibility") or {}
            existing_industry = existing_viz.get("industry") or {}
            # New-shape storage (Contract 2): ai_visibility.industry.user_provided
            target_industry = (
                existing_industry.get("user_provided")
                or report.get("target_industry")
                or (report.get("audit_config") or {}).get("target_industry")
            )

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
        competitor_urls = audit.get("competitor_urls") or report.get("competitor_urls") or []
        # Also check the PremiumAuditRequest competitor_urls stored in competitive_data
        competitive_data = report.get("competitive_data")
        competitors = resolve_competitors(
            competitor_urls=competitor_urls,
            competitive_data=competitive_data,
            co_mention_domains=None,  # Tier 3 populated after mentions fetch
        )

        # Stage 3: Resolve industry + build prompts
        # Workstream D3 (Contract 5): priority user_declared → nlp_detected → None.
        # resolve_industry returns (None, None) when both inputs are empty —
        # we MUST short-circuit here and emit a "needs_industry_confirmation"
        # status rather than letting build_prompts fabricate a fallback leaf.
        industry_value, industry_source = resolve_industry(
            target_industry=target_industry,
            detected_industry=detected_industry_raw,
        )
        industry_block = {
            "value": industry_value,
            "source": industry_source,
            "user_provided": (target_industry or None) if (target_industry or "").strip() else None,
        }

        if industry_value is None:
            logger.info(
                f"AI Visibility: industry unresolved for {audit_id} "
                f"(target_industry={target_industry!r}, "
                f"detected_industry={detected_industry_raw!r}). "
                "Writing needs_industry_confirmation status and skipping prompts."
            )
            existing_viz = report.get("ai_visibility") or {}
            await update_audit_report(audit_id, {
                "ai_visibility": {
                    "last_computed_at": datetime.now(timezone.utc).isoformat(),
                    "last_computed_status": "needs_industry_confirmation",
                    "run_count": existing_viz.get("run_count", 0) or 0,
                    "brand_name": brand_info.name,
                    "brand_name_source": brand_info.source,
                    "industry": industry_block,
                    # Deprecated: keep for a release or two for backwards-compat
                    # with older dashboards that read detected_industry directly.
                    # TODO: remove after frontend fully migrated to industry.value.
                    "detected_industry": detected_industry_raw,
                    "cumulative_cost_usd": existing_viz.get("cumulative_cost_usd", 0) or 0,
                }
            })
            return

        detected_industry = industry_value  # legacy local name, used below
        # sanitize_entity_name returns None if the top_entity is pure
        # adjacent-token repetition or duplicates the industry leaf —
        # build_prompts already treats None as "fall back to industry leaf".
        top_entity = sanitize_entity_name(
            nlp_data.get("primary_entity"), detected_industry
        )
        prompts = build_prompts(detected_industry, top_entity, brand_info.name)

        # Stage 4-6: DataForSEO calls
        cost_tracker = CostTracker()
        dfs_client = DataForSEOClient()

        # Extract brand domain from audit URL (used by mentions + SOV)
        from urllib.parse import urlparse
        parsed_url = urlparse(audit.get("url", ""))
        brand_domain = normalize_domain(parsed_url.hostname or "")

        try:
            # Stage 4: Fetch LLM Mentions (pre-indexed database)
            mentions = await fetch_mentions(
                dfs_client, brand_info.name, brand_domain, cost_tracker,
            )

            # If no competitors yet, try tier 3 (co-mentions) — not implemented in Phase 1
            # Tier 3 would scan mentions data for co-mentioned domains

            # Stage 5: Fetch LLM Responses (live queries)
            responses = await fetch_responses(dfs_client, prompts, brand_info.name, cost_tracker)

            # Stage 6: Compute SOV (from cross_aggregated, if competitors available)
            sov = None
            if competitors.domains:

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
            # Workstream D3 Contract 2: resolved industry block. Frontend reads
            # industry.value + industry.source to branch between the normal
            # tile and the "Needs attention" card.
            "industry": industry_block,
            # Deprecated: retained for backwards-compat with older dashboards
            # / exports that still read detected_industry directly. Remove
            # once all readers have been migrated to ai_visibility.industry.value.
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

        # Regenerate executive summary with AI Visibility data included (Phase 3)
        try:
            from executive_summary_generator import generate_executive_summary
            refreshed = await get_audit_by_id(audit_id)
            if refreshed:
                full_rpt = refreshed.get("report_json") or {}
                if isinstance(full_rpt, str):
                    full_rpt = json.loads(full_rpt)
                competitive_data = full_rpt.get("competitive_data")
                new_summary = generate_executive_summary(full_rpt, competitive_data)
                await update_audit_report(audit_id, {"executive_summary": new_summary})
                logger.info(f"Executive summary regenerated with AI Visibility data: {len(new_summary)} chars")
        except Exception as e:
            logger.warning(f"Post-AI-Visibility summary regeneration failed (non-fatal): {e}")

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
