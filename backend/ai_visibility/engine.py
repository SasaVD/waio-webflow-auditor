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

# Workstream D2: the four post-D2 source values that all represent a user
# override (as opposed to NLP auto-extraction). Legacy persisted blobs may
# still carry the pre-D2 ``"override"`` string, so we accept that too when
# reading from DB.
_OVERRIDE_SOURCE_VALUES = frozenset({
    "kg_mid", "curated_list", "override_unverified", "override",
})


class _BrandNLPClientAdapter:
    """Adapter that exposes ``analyze_entities`` as a sync-callable method.

    ``backend/google_nlp_client.py`` exposes module-level *async* functions
    (``analyze_entities``, ``classify_text``). The brand resolver expects a
    duck-typed object with a sync ``analyze_entities(text)`` method (it's
    called from ``resolve_brand`` which is itself sync). This adapter
    bridges the two — running the async coroutine to completion via
    ``asyncio.run``. Cost is one ~1-unit NLP call per brand override
    validation (~$0.001), so the blocking call is acceptable in the
    AI Visibility orchestrator's async context.
    """
    def __init__(self):
        import google_nlp_client  # type: ignore[import-not-found]
        self._mod = google_nlp_client

    def analyze_entities(self, text: str):
        import asyncio
        coro = self._mod.analyze_entities(text)
        # We're inside an already-running event loop (run_ai_visibility_analysis
        # is an async function). asyncio.run() can't be used from a running
        # loop. We use loop-aware execution: schedule on a fresh event loop
        # in a background thread to avoid the "running loop" reentrancy issue.
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # We're inside the live loop — run the coroutine in a fresh loop
            # in a worker thread. This keeps resolve_brand's sync interface
            # while still consuming the async google_nlp_client.
            import concurrent.futures
            def _runner():
                return asyncio.run(coro)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_runner)
                results = future.result(timeout=35)
        else:
            results = asyncio.run(coro)
        # Convert dataclass results to plain dicts that the resolver
        # understands (matching the test fakes' shape). The resolver reads
        # entity.metadata.mid / metadata.wikipedia_url; map fields back.
        return [
            {
                "name": e.name,
                "type": e.entity_type,
                "salience": e.salience,
                "metadata": {
                    k: v for k, v in [
                        ("mid", e.knowledge_graph_mid),
                        ("wikipedia_url", e.wikipedia_url),
                    ] if v
                },
            }
            for e in (results or [])
        ]


def _build_brand_nlp_client():
    """Construct a brand-validation NLP client, or None if NLP isn't configured.

    Returns None when ``GOOGLE_API_KEY`` is unset so the resolver gracefully
    falls through to the curated-list / override_unverified path. Any other
    construction error also returns None — never raises into the caller.
    """
    try:
        import google_nlp_client  # type: ignore[import-not-found]
        if not google_nlp_client.is_configured():
            return None
        return _BrandNLPClientAdapter()
    except Exception as e:  # pragma: no cover — defensive
        logger.info(
            "Brand NLP client unavailable — skipping KG validation (%s)", e,
        )
        return None


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
        # but we also check the report for a previously saved override.
        # Workstream D2 split "override" into {kg_mid, curated_list,
        # override_unverified} — any of those (plus the legacy literal
        # "override" for old records) means the user provided this string.
        if not brand_override:
            existing_viz = report.get("ai_visibility") or {}
            if existing_viz.get("brand_name_source") in _OVERRIDE_SOURCE_VALUES:
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
        # Workstream D2: validate user-provided overrides via Google NLP's
        # KG MID metadata, then category-leaf rejection, then a curated
        # whitelist, before falling through to "override_unverified".
        # nlp_client is a thin adapter exposing analyze_entities — when
        # GOOGLE_API_KEY isn't configured the resolver gracefully skips
        # layers 1-2 and falls straight to the curated/unverified path.
        nlp_client = _build_brand_nlp_client()
        try:
            brand_info = resolve_brand(
                brand_override,
                nlp_entities,
                nlp_client=nlp_client,
            )
        except BrandExtractionError as e:
            # Differentiate the two error shapes:
            #   - User provided an override but it was rejected as a category
            #     phrase → "needs_brand_confirmation" (mirror D3's industry
            #     gate). Frontend renders a "refine your brand" card.
            #   - No override AND no usable NLP entities → legacy "failed"
            #     status (existing behavior preserved for the auto-extract
            #     path; the recompute UI handles this with its own prompt).
            had_override = bool(brand_override and brand_override.strip())
            existing_viz = report.get("ai_visibility") or {}
            blob: dict[str, Any] = {
                "last_computed_at": datetime.now(timezone.utc).isoformat(),
                "run_count": existing_viz.get("run_count", 0) or 0,
                "cumulative_cost_usd": existing_viz.get("cumulative_cost_usd", 0) or 0,
            }
            if had_override:
                logger.warning(
                    f"AI Visibility: brand override rejected for {audit_id}: {e}"
                )
                blob["last_computed_status"] = "needs_brand_confirmation"
                blob["brand_validation_warning"] = str(e)
                # Echo the rejected user input so the frontend can pre-fill
                # the modal with what they typed.
                blob["brand_name"] = brand_override.strip()  # type: ignore[union-attr]
            else:
                logger.warning(
                    f"AI Visibility: brand extraction failed for {audit_id}: {e}"
                )
                blob["last_computed_status"] = "failed"
                blob["error"] = str(e)
            await update_audit_report(audit_id, {"ai_visibility": blob})
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
                    # D2: any of the three override-discriminator values means
                    # the user supplied this brand string; persist their input.
                    brand_info.name if brand_info.source in _OVERRIDE_SOURCE_VALUES else None,
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
