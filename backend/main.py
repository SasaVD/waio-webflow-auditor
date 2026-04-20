import logging
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Body, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import os
import asyncio

from crawler import fetch_page, close_browser
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
from executive_summary_generator import generate_executive_summary
from webflow_fixes import get_fix, get_all_fixes, match_fixes_to_findings
from generic_fixes import match_generic_fixes_to_findings
from pdf_generator import generate_pdf
from pdf_export_generator import generate_branded_pdf
from md_generator import generate_markdown
from email_sender import send_report_email
from db_router import (init_db, close_db, create_job, get_job_status, get_single_page_audit,
                       save_audit_history, update_audit_report, get_audit_history,
                       get_audit_by_id, list_all_audits,
                       create_schedule, get_schedules, update_schedule, delete_schedule,
                       save_dataforseo_task, update_dataforseo_task,
                       get_dataforseo_task, get_dataforseo_task_by_audit,
                       save_google_tokens, get_google_tokens, list_google_tokens,
                       delete_google_tokens,
                       save_link_graph_edges, get_link_graph_data,
                       save_page_content_batch, save_cms_detection,
                       save_industry_detection,
                       get_page_content_for_audit,
                       save_migration_assessment, get_migration_assessment,
                       get_user_by_email, has_any_admin, create_user)
from auth import get_current_user, hash_password
from auth_routes import router as auth_router
from site_crawler import run_site_crawl
from scheduler import scheduler_loop
from competitive_auditor import run_competitive_audit
from dataforseo_client import DataForSEOClient, DataForSEOError, is_configured as is_dataforseo_configured
from google_auth import (
    is_configured as is_google_configured,
    get_auth_url, exchange_code, encrypt_token, decrypt_token,
    gsc_list_sites, gsc_get_all_pages, gsc_list_sitemaps,
    ga4_list_properties, ga4_get_traffic_by_page,
)
from link_graph_auditor import build_link_graph
from cms_detector import detect_cms
from content_extractor import extract_content
from content_profile_auditor import build_content_profile
from cms_migration_auditor import run_migration_assessment
from wdf_idf_auditor import run_wdf_idf_analysis
from interlinking_auditor import find_interlinking_opportunities
from tipr_engine import run_tipr_analysis
from topic_clustering_engine import run_topic_clustering, prepare_pages_from_report
from link_data_export import generate_link_data_excel, generate_link_data_csv_zip
from knowledge_base_generator import generate_knowledge_base, export_jsonl_bytes
from ai_visibility import run_ai_visibility_analysis
from ai_visibility.brand_resolver import resolve_brand
from ai_visibility.schema import BrandExtractionError
from google_nlp_client import (
    classify_text as nlp_classify_text,
    analyze_entities as nlp_analyze_entities,
    analyze_sentiment as nlp_analyze_sentiment,
    is_configured as is_nlp_configured,
)
import cross_audit_queries
import json
import re
import uuid
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WAIO Webflow Audit Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register auth routes
app.include_router(auth_router)

class AuditRequest(BaseModel):
    url: HttpUrl
    tier: str = "free"

class MultiAuditRequest(BaseModel):
    url: HttpUrl
    max_pages: int = 5
    tier: str = "free"

class PremiumAuditRequest(BaseModel):
    url: HttpUrl
    competitor_urls: list[str] = []
    gsc_property: str | None = None
    target_keyword: str | None = None
    max_pages: int = 2000
    nlp_classification: bool = True
    nlp_entity_analysis: bool = True
    nlp_sentiment: bool = False
    ai_visibility_opt_in: bool = True
    brand_name: str | None = None

class ExportRequest(BaseModel):
    report: dict

class SendReportRequest(BaseModel):
    email: str
    report: dict

class ScheduleRequest(BaseModel):
    url: str
    email: str
    frequency: str = "weekly"
    max_pages: int = 1

class ScheduleUpdateRequest(BaseModel):
    enabled: bool | None = None
    frequency: str | None = None
    email: str | None = None

class CompetitiveRequest(BaseModel):
    primary_url: str
    competitor_urls: List[str] = []

class PageAuditRequest(BaseModel):
    url: str
    parent_audit_id: str | None = None

@app.on_event("startup")
async def startup_event():
    await init_db()
    # Seed admin account from env vars if no admin exists
    try:
        admin_exists = await has_any_admin()
        if not admin_exists:
            admin_email = os.environ.get("ADMIN_EMAIL")
            admin_password = os.environ.get("ADMIN_PASSWORD")
            if admin_email and admin_password:
                existing = await get_user_by_email(admin_email.lower())
                if not existing:
                    hashed = hash_password(admin_password)
                    logger.info(f"Admin password hash: length={len(hashed)}, prefix={hashed[:7]}")
                    await create_user(
                        email=admin_email.lower(),
                        password_hash=hashed,
                        name="Admin",
                        role="admin",
                    )
                    logger.info(f"Admin account seeded: {admin_email}")
    except Exception as e:
        logger.warning(f"Admin seeding failed (non-fatal): {e}")
    asyncio.create_task(scheduler_loop())

@app.on_event("shutdown")
async def shutdown_event():
    await close_browser()
    await close_db()

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/audit")
async def perform_audit(request: AuditRequest):
    url = str(request.url)
    tier = request.tier if request.tier in ("free", "premium") else "free"
    logger.info(f"Starting {tier} audit for {url}")
    try:
        html_content, soup = await fetch_page(url)

        # Run the 10 deterministic pillars (always, regardless of tier)
        logger.info(f"Running HTML audit for {url}")
        html_res = run_html_audit(soup, html_content)

        logger.info(f"Running Structured Data audit for {url}")
        sd_res = run_structured_data_audit(html_content, url)

        logger.info(f"Running CSS/JS audit for {url}")
        css_js_res = run_css_js_audit(soup, html_content)

        logger.info(f"Running AEO content audit for {url}")
        aeo_res = run_aeo_content_audit(soup, html_content)

        logger.info(f"Running RAG Readiness audit for {url}")
        rag_res = run_rag_readiness_audit(soup, html_content)

        logger.info(f"Running Agentic Protocol audit for {url}")
        agent_res = run_agentic_protocol_audit(soup, html_content, url)

        logger.info(f"Running Data Integrity audit for {url}")
        data_res = run_data_integrity_audit(soup, html_content)

        logger.info(f"Running Internal Linking audit for {url}")
        il_res = run_internal_linking_audit(soup, html_content, str(request.url), site_data=None)

        logger.info(f"Running Accessibility audit for {url}")
        a11y_res = await run_accessibility_audit(url)

        logger.info("Compiling scores and report")
        scores = compile_scores(html_res, sd_res, aeo_res, css_js_res, a11y_res, rag_res, agent_res, data_res, il_res)
        report = generate_report(url, html_res, sd_res, aeo_res, css_js_res, a11y_res, rag_res, agent_res, data_res, scores, il_res, tier=tier)

        # Premium modules will be added in later sprints (executive summary, fix KB, etc.)

        # Auto-save to audit history
        audit_id = await save_audit_history(url, "single", report.get("overall_score", 0), report.get("overall_label", "N/A"), report, tier=tier)
        report["audit_id"] = str(audit_id)

        return report

    except Exception as e:
        logger.error(f"Audit failed for {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")

@app.post("/api/audit/multi")
async def perform_multi_audit(request: MultiAuditRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    url_str = str(request.url)
    
    await create_job(job_id)
    background_tasks.add_task(run_site_crawl, job_id, url_str, request.max_pages)
    
    return {"job_id": job_id, "status": "running", "url": url_str}

@app.post("/api/audit/competitive")
async def perform_competitive_audit(request: CompetitiveRequest):
    primary = request.primary_url.strip()
    if not primary.startswith('http'):
        primary = 'https://' + primary
    competitors = [c.strip() if c.strip().startswith('http') else 'https://' + c.strip() for c in request.competitor_urls[:4] if c.strip()]
    
    logger.info(f"Starting competitive audit: primary={primary}, competitors={competitors}")
    try:
        result = await run_competitive_audit(primary, competitors)
        
        # Auto-save primary to history
        p = result.get("primary", {})
        audit_id = await save_audit_history(primary, "competitive", p.get("overall_score", 0), p.get("overall_label", "N/A"), result)
        result["audit_id"] = str(audit_id)

        return result
    except Exception as e:
        logger.error(f"Competitive audit failed: {e}")
        raise HTTPException(status_code=500, detail=f"Competitive audit failed: {str(e)}")

@app.post("/api/audit/premium")
async def perform_premium_audit(request: PremiumAuditRequest, user=Depends(get_current_user)):
    """Premium audit endpoint — requires authentication.
    Runs the full 10-pillar audit plus premium modules."""
    url = str(request.url)
    audit_id = uuid.uuid4()
    logger.info("=== PREMIUM AUDIT START ===")
    logger.info(f"URL: {url}, audit_id={audit_id}")
    logger.info(f"Config: DataForSEO={is_dataforseo_configured()}, NLP={is_nlp_configured()}, competitors={len(request.competitor_urls)}")
    try:
        html_content, soup = await fetch_page(url)
        logger.info(f"Page fetched: {len(html_content)} bytes")

        # ── Phase 1: 10-pillar deterministic audit (always runs) ──
        html_res = run_html_audit(soup, html_content)
        sd_res = run_structured_data_audit(html_content, url)
        css_js_res = run_css_js_audit(soup, html_content)
        aeo_res = run_aeo_content_audit(soup, html_content)
        rag_res = run_rag_readiness_audit(soup, html_content)
        agent_res = run_agentic_protocol_audit(soup, html_content, url)
        data_res = run_data_integrity_audit(soup, html_content)
        il_res = run_internal_linking_audit(soup, html_content, url, site_data=None)
        a11y_res = await run_accessibility_audit(url)

        scores = compile_scores(html_res, sd_res, aeo_res, css_js_res, a11y_res, rag_res, agent_res, data_res, il_res)
        report = generate_report(url, html_res, sd_res, aeo_res, css_js_res, a11y_res, rag_res, agent_res, data_res, scores, il_res, tier="premium")
        logger.info(f"10-pillar audit complete: score={report.get('overall_score')}")

        # ── Initialize all premium keys with null defaults ──
        # Frontend checks these keys; null = "not available", missing = crash
        report["executive_summary"] = None
        report["webflow_fixes"] = None
        report["competitive_data"] = None
        report["cms_detection"] = None
        report["content_profile"] = None
        report["wdf_idf"] = None
        report["migration_assessment"] = None
        report["nlp_analysis"] = None
        report["link_analysis"] = None
        report["crawl_stats"] = None
        report["crawl_status"] = "not_configured"
        report["crawl_task_id"] = None

        # ── Phase 2: Premium modules (each wrapped in try/except) ──

        # Sprint 2C: Competitor benchmarking
        competitive_data = None
        if request.competitor_urls:
            try:
                logger.info(f"Running competitor benchmarking against {len(request.competitor_urls)} URLs")
                competitive_data = await run_competitive_audit(url, request.competitor_urls)
                report["competitive_data"] = competitive_data
                logger.info(f"Competitor benchmark complete: {len(competitive_data.get('rankings', []))} ranked")
            except Exception as e:
                logger.warning(f"Competitor benchmarking failed (non-fatal): {e}")

        # Sprint 2A: Executive summary (with competitor context if available)
        try:
            report["executive_summary"] = generate_executive_summary(report, competitive_data)
            logger.info(f"Executive summary generated: {len(report['executive_summary'])} chars")
        except Exception as e:
            logger.warning(f"Executive summary failed (non-fatal): {e}")

        # Sprint 3F: CMS detection on homepage HTML (zero-cost) — run before fix matching
        try:
            parsed = urlparse(url)
            domain = parsed.hostname or parsed.netloc
            cms_result = await detect_cms(html_content, response_headers=None, domain=domain)
            report["cms_detection"] = cms_result.to_dict()
            logger.info(f"CMS detected: {cms_result.platform} (confidence={cms_result.confidence})")
        except Exception as e:
            logger.warning(f"CMS detection failed (non-fatal): {e}")

        # Sprint 2B + CMS-aware fix instructions
        try:
            detected_cms = (report.get("cms_detection") or {}).get("platform", "unknown")
            if detected_cms == "webflow":
                report["webflow_fixes"] = match_fixes_to_findings(report)
            else:
                report["webflow_fixes"] = match_generic_fixes_to_findings(report)
            fix_count = len(report["webflow_fixes"]) if report["webflow_fixes"] else 0
            logger.info(f"Fix instructions matched ({detected_cms}): {fix_count} fixes")
        except Exception as e:
            logger.warning(f"Fix matching failed (non-fatal): {e}")

        # Sprint 4A: Content extraction on homepage (Trafilatura)
        extracted = None
        try:
            extracted = extract_content(html_content, url)
            report["content_profile"] = build_content_profile(
                url, extracted.clean_text, extracted.h1_text, extracted.title,
            ).to_dict()
            logger.info(f"Content extracted: {extracted.word_count} words via {extracted.extraction_method}")
        except Exception as e:
            logger.warning(f"Content extraction failed (non-fatal): {e}")

        # Sprint 3E: Google NLP analysis on homepage (if configured)
        if is_nlp_configured() and request.nlp_classification and extracted and extracted.clean_text:
            nlp_data: dict = {}
            # Classification
            try:
                categories = await nlp_classify_text(extracted.clean_text)
                if categories:
                    primary = categories[0]
                    nlp_data["detected_industry"] = primary.category
                    nlp_data["industry_confidence"] = primary.confidence
                    nlp_data["all_categories"] = [
                        {"category": c.category, "confidence": c.confidence}
                        for c in categories
                    ]
                    logger.info(f"NLP classification: {primary.category} ({primary.confidence:.2f})")
                else:
                    logger.info("NLP classification returned no categories (text too short?)")
            except Exception as e:
                logger.warning(f"NLP classification failed (non-fatal): {e}")

            # Entity analysis
            if request.nlp_entity_analysis:
                try:
                    entities = await nlp_analyze_entities(extracted.clean_text)
                    if entities:
                        nlp_data["entities"] = [
                            {
                                "name": ent.name,
                                "type": ent.entity_type,
                                "salience": round(ent.salience, 4),
                                "wikipedia_url": ent.wikipedia_url,
                                "mentions_count": ent.mentions_count,
                            }
                            for ent in entities[:30]
                        ]
                        top = entities[0]
                        nlp_data["primary_entity"] = top.name
                        nlp_data["primary_entity_salience"] = round(top.salience, 4)

                        # Entity type distribution
                        type_counts: dict[str, int] = {}
                        for ent in entities:
                            type_counts[ent.entity_type] = type_counts.get(ent.entity_type, 0) + 1
                        nlp_data["entity_type_distribution"] = type_counts

                        # Entity focus alignment (does primary entity match H1/title?)
                        if extracted.h1_text or extracted.title:
                            title_text = (extracted.h1_text or extracted.title or "").lower()
                            nlp_data["entity_focus_aligned"] = (
                                top.name.lower() in title_text
                                or any(w in title_text for w in top.name.lower().split() if len(w) > 3)
                            )

                        logger.info(f"NLP entities: {len(entities)} found, primary={top.name} ({top.salience:.2f})")
                    else:
                        logger.info("NLP entity analysis returned no entities")
                except Exception as e:
                    logger.warning(f"NLP entity analysis failed (non-fatal): {e}")

            # Sentiment analysis
            try:
                sentiment = await nlp_analyze_sentiment(extracted.clean_text)
                score = sentiment.score
                magnitude = sentiment.magnitude
                # Human-readable interpretation
                if score <= -0.5:
                    tone = "Negative / Critical"
                elif score <= -0.1:
                    tone = "Slightly Negative / Cautious"
                elif score <= 0.1:
                    tone = "Neutral / Factual"
                elif score <= 0.5:
                    tone = "Slightly Positive / Encouraging"
                else:
                    tone = "Positive / Enthusiastic"
                nlp_data["sentiment"] = {
                    "score": round(score, 3),
                    "magnitude": round(magnitude, 3),
                    "tone": tone,
                }
                logger.info(f"NLP sentiment: score={score:.2f}, magnitude={magnitude:.2f}, tone={tone}")
            except Exception as e:
                logger.warning(f"NLP sentiment analysis failed (non-fatal): {e}")

            # Content stats
            nlp_data["content_stats"] = {
                "word_count": extracted.word_count,
                "language": extracted.language,
                "extracted_via": extracted.extraction_method,
            }

            # Derived insights
            try:
                insights: dict = {}
                if nlp_data.get("detected_industry"):
                    parts = nlp_data["detected_industry"].strip("/").split("/")
                    insights["primary_topic"] = parts[-1] if parts else nlp_data["detected_industry"]
                    insights["topic_confidence"] = nlp_data.get("industry_confidence", 0)
                if nlp_data.get("entity_type_distribution"):
                    dominant_type = max(nlp_data["entity_type_distribution"], key=nlp_data["entity_type_distribution"].get)
                    insights["entity_focus"] = dominant_type.lower().replace("_", " ")
                if nlp_data.get("sentiment"):
                    insights["content_tone"] = nlp_data["sentiment"]["tone"]
                if nlp_data.get("entities"):
                    unique_types = len(nlp_data.get("entity_type_distribution", {}))
                    insights["entity_diversity_score"] = round(min(unique_types / 8.0, 1.0), 2)
                    insights["top_keyword_entities"] = [
                        e["name"] for e in nlp_data["entities"][:8]
                        if e["type"] in ("OTHER", "CONSUMER_GOOD", "WORK_OF_ART", "ORGANIZATION")
                    ][:5]

                # SEO alignment check
                conf = nlp_data.get("industry_confidence", 0)
                aligned = nlp_data.get("entity_focus_aligned")
                if conf >= 0.7 and aligned is True:
                    insights["seo_alignment"] = "strong"
                elif conf >= 0.5 or aligned is True:
                    insights["seo_alignment"] = "moderate"
                else:
                    insights["seo_alignment"] = "weak"

                nlp_data["insights"] = insights
            except Exception as e:
                logger.warning(f"NLP insights derivation failed (non-fatal): {e}")

            if nlp_data:
                report["nlp_analysis"] = nlp_data

        # Sprint 4B: WDF*IDF gap analysis (if keyword or competitors provided)
        if request.target_keyword or request.competitor_urls:
            try:
                target_text = extracted.clean_text if extracted else ""
                if target_text and len(target_text.split()) > 20:
                    wdf_result = await run_wdf_idf_analysis(
                        target_url=url,
                        target_text=target_text,
                        competitor_urls=request.competitor_urls or None,
                        target_keyword=request.target_keyword,
                    )
                    report["wdf_idf"] = wdf_result.to_dict()
                    logger.info(f"WDF*IDF: coverage={wdf_result.coverage_score}%, {len(wdf_result.gap_terms)} gaps")
                else:
                    logger.info("WDF*IDF skipped: insufficient extracted text")
            except Exception as e:
                logger.warning(f"WDF*IDF analysis failed (non-fatal): {e}")

        # Sprint 4E: CMS migration assessment (any detected platform except webflow/unknown)
        detected_platform = (report.get("cms_detection") or {}).get("platform", "unknown")
        if detected_platform not in ("webflow", "unknown"):
            try:
                all_findings = []
                for cat_data in report.get("categories", {}).values():
                    for chk in (cat_data.get("checks") or {}).values():
                        all_findings.extend(chk.get("findings") or [])
                migration = run_migration_assessment(
                    source_cms=detected_platform,
                    total_pages=request.max_pages,
                    audit_findings=all_findings,
                )
                report["migration_assessment"] = migration.to_dict()
                from cms_migration_auditor import CMS_TIER
                cms_tier = CMS_TIER.get(detected_platform, 3)
                logger.info(f"Migration assessment (tier {cms_tier}): {detected_platform} -> webflow")
            except Exception as e:
                logger.warning(f"Migration assessment failed (non-fatal): {e}")

        # Sprint 3A: Submit DataForSEO site-wide crawl (async — runs in background)
        if is_dataforseo_configured():
            try:
                app_base = os.environ.get("APP_BASE_URL", "").rstrip("/")
                dfs_client = DataForSEOClient()
                pingback_url = f"{app_base}/api/dataforseo/pingback?task_id=$id" if app_base else None
                task_result = await dfs_client.create_task(
                    url,
                    max_crawl_pages=request.max_pages,
                    pingback_url=pingback_url,
                    tag=str(audit_id),
                )
                await dfs_client.close()
                report["crawl_task_id"] = task_result["task_id"]
                report["crawl_status"] = "crawling"
                report["enrichment_status"] = "polling"
                report["enrichment_progress"] = "Site crawl submitted, waiting for results..."
                report["max_pages_requested"] = request.max_pages
                logger.info(f"DataForSEO task submitted: {task_result['task_id']} for {url}")
            except Exception as e:
                logger.warning(f"DataForSEO task submission failed (non-fatal): {e}")
                report["crawl_status"] = "unavailable"
                report["enrichment_status"] = "failed"
                report["enrichment_progress"] = "Crawl service unavailable"

        # ── Phase 3: Persist to database ──
        audit_type = "competitive" if competitive_data else "single"

        # Log final report keys for debugging
        premium_keys = ["executive_summary", "webflow_fixes", "competitive_data",
                        "cms_detection", "content_profile", "wdf_idf", "nlp_analysis",
                        "link_analysis", "crawl_stats", "migration_assessment"]
        populated = [k for k in premium_keys if report.get(k) is not None]
        logger.info(f"Premium data populated: {populated}")

        # Persist AI Visibility opt-in state for the background enrichment task
        report["ai_visibility_opt_in"] = request.ai_visibility_opt_in
        if request.brand_name:
            report["ai_visibility_brand_name"] = request.brand_name

        await save_audit_history(
            url, audit_type,
            report.get("overall_score", 0), report.get("overall_label", "N/A"),
            report, tier="premium", audit_id=audit_id,
        )

        # Persist CMS detection to database
        if report.get("cms_detection") and report["cms_detection"].get("platform") != "unknown":
            try:
                cms = report["cms_detection"]
                await save_cms_detection(
                    audit_id, cms["platform"], cms.get("version"),
                    cms["confidence"], cms["detection_method"],
                    cms.get("technologies", []),
                )
            except Exception as e:
                logger.warning(f"Failed to save CMS detection: {e}")

        # Persist migration assessment to database
        if report.get("migration_assessment"):
            try:
                await save_migration_assessment(
                    audit_id, json.dumps(report["migration_assessment"]),
                )
            except Exception as e:
                logger.warning(f"Failed to save migration assessment: {e}")

        # Save DataForSEO task record after audit is persisted (needs audit_id FK)
        if report.get("crawl_task_id"):
            try:
                await save_dataforseo_task(
                    report["crawl_task_id"], audit_id, url, request.max_pages,
                )
            except Exception as e:
                logger.warning(f"Failed to save DataForSEO task record: {e}")

            # Launch background polling task to fetch crawl results when ready.
            # This is the PRIMARY mechanism — the pingback is a bonus accelerator.
            asyncio.create_task(
                _poll_and_enrich_crawl(report["crawl_task_id"], str(audit_id))
            )
            logger.info(f"Background poller launched for DataForSEO task {report['crawl_task_id']}")

        report["audit_id"] = str(audit_id)
        logger.info("=== PREMIUM AUDIT COMPLETE ===")
        return report

    except Exception as e:
        logger.error(f"Premium audit failed for {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Premium audit failed: {str(e)}")

@app.get("/api/audit/status/{job_id}")
async def get_audit_status(job_id: str):
    status_data = await get_job_status(job_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Job not found")
    return status_data

@app.get("/api/audit/page/{job_id}")
async def fetch_single_page_audit(job_id: str, url: str):
    data = await get_single_page_audit(job_id, url)
    if not data:
        raise HTTPException(status_code=404, detail="Page report not found for this job and URL")
    
    # Transform raw audit data into the formatted report structure
    # that the AuditReport frontend component expects
    scores = data.get("scores", {})
    report = generate_report(
        url,
        data.get("html_res", {}),
        data.get("sd_res", {}),
        data.get("aeo_res", {}),
        data.get("css_js_res", {}),
        data.get("a11y_res", {}),
        data.get("rag_res", {}),
        data.get("agent_res", {}),
        data.get("data_res", {}),
        scores,
        data.get("il_res")
    )
    return report

# --- History & Schedule Endpoints ---

@app.get("/api/history")
async def get_history(url: str):
    history = await get_audit_history(url)
    return {"url": url, "history": history}


@app.get("/api/audit/report/{audit_id}")
async def get_audit_report(audit_id: str):
    """Retrieve a saved audit report by ID."""
    record = await get_audit_by_id(audit_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit not found")
    # Return the full report JSON directly (same shape the frontend expects)
    report = record["report_json"]
    report["audit_id"] = record["id"]

    # Lazy TIPR computation: if link graph exists but TIPR wasn't computed
    # (covers audits enriched before TIPR code was deployed)
    if not report.get("tipr_analysis"):
        graph_data = (report.get("link_analysis") or {}).get("graph")
        if graph_data and graph_data.get("links"):
            try:
                tipr_result = run_tipr_analysis(
                    graph_data=graph_data,
                    nlp_analysis=report.get("nlp_analysis"),
                    max_recommendations=50,
                )
                if tipr_result:
                    report["tipr_analysis"] = tipr_result
                    await update_audit_report(audit_id, {"tipr_analysis": tipr_result})
                    logger.info(
                        f"Lazy TIPR computed for audit {audit_id}: "
                        f"{tipr_result['summary']['total_pages']} pages scored"
                    )
            except Exception as e:
                logger.warning(f"Lazy TIPR computation failed for {audit_id}: {e}")

    # Lazy semantic clustering: if link graph exists but clusters weren't computed
    if not report.get("semantic_clusters"):
        graph_data = (report.get("link_analysis") or {}).get("graph")
        if graph_data and graph_data.get("nodes") and len(graph_data["nodes"]) >= 20:
            try:
                # Run entity extraction if NLP is configured and not already done
                updates: dict = {}
                if is_nlp_configured() and not report.get("page_entities"):
                    page_entities = await _extract_page_entities(
                        graph_data=graph_data,
                        tipr_analysis=report.get("tipr_analysis"),
                        homepage_url=report.get("url", ""),
                        existing_entities=None,
                        max_pages=25,
                    )
                    if page_entities:
                        report["page_entities"] = page_entities
                        updates["page_entities"] = page_entities

                cluster_pages, cluster_links = prepare_pages_from_report(report)
                if cluster_pages:
                    sc_result = run_topic_clustering(
                        pages=cluster_pages,
                        links=cluster_links,
                    )
                    if sc_result:
                        report["semantic_clusters"] = sc_result
                        updates["semantic_clusters"] = sc_result
                        logger.info(
                            f"Lazy semantic clustering for audit {audit_id}: "
                            f"{sc_result['n_clusters']} clusters"
                        )
                if updates:
                    await update_audit_report(audit_id, updates)
            except Exception as e:
                logger.warning(f"Lazy semantic clustering failed for {audit_id}: {e}")

    return report


@app.post("/api/audit/{audit_id}/recompute-tipr")
async def recompute_tipr(audit_id: str):
    """One-time admin endpoint: clear cached tipr_analysis so the lazy
    computation in get_audit_report re-runs with the latest TIPR engine."""
    record = await get_audit_by_id(audit_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit not found")
    report = record["report_json"]
    if "tipr_analysis" not in report:
        return {"status": "noop", "message": "No cached tipr_analysis to clear"}
    # Must delete key and write full report back — update_audit_report does a
    # merge so it can't remove keys.
    del report["tipr_analysis"]
    import uuid as _uuid
    import db_postgres as _db_pg
    _aid = _uuid.UUID(str(audit_id))
    pool = await _db_pg.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE audits SET report_json = $1 WHERE id = $2",
            json.dumps(report), _aid,
        )
    return {"status": "cleared", "message": "tipr_analysis removed — will recompute on next load"}


@app.post("/api/audit/{audit_id}/recompute-clusters")
async def recompute_clusters(audit_id: str):
    """Admin endpoint: clear cached semantic_clusters and page_entities
    so lazy computation re-runs with the latest clustering engine."""
    record = await get_audit_by_id(audit_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit not found")
    report = record["report_json"]
    cleared = []
    if "semantic_clusters" in report:
        del report["semantic_clusters"]
        cleared.append("semantic_clusters")
    if "page_entities" in report:
        del report["page_entities"]
        cleared.append("page_entities")
    if not cleared:
        return {"status": "noop", "message": "No cached clustering data to clear"}
    import uuid as _uuid
    import db_postgres as _db_pg
    _aid = _uuid.UUID(str(audit_id))
    pool = await _db_pg.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE audits SET report_json = $1 WHERE id = $2",
            json.dumps(report), _aid,
        )
    return {"status": "cleared", "message": f"Cleared {', '.join(cleared)} — will recompute on next load"}


@app.post("/api/audit/{audit_id}/recompute-summary")
async def recompute_summary(audit_id: str):
    """Admin endpoint: regenerate executive summary using the latest generator
    and whatever enrichment data is currently available in the report."""
    record = await get_audit_by_id(audit_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit not found")
    report = record["report_json"]
    if isinstance(report, str):
        report = json.loads(report)
    competitive_data = report.get("competitive_data")
    new_summary = generate_executive_summary(report, competitive_data)
    report["executive_summary"] = new_summary
    import uuid as _uuid
    import db_postgres as _db_pg
    _aid = _uuid.UUID(str(audit_id))
    pool = await _db_pg.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE audits SET report_json = $1 WHERE id = $2",
            json.dumps(report), _aid,
        )
    return {
        "status": "regenerated",
        "length": len(new_summary),
        "message": "Executive summary regenerated with current enrichment data",
    }


@app.get("/api/audit/enrichment-status/{audit_id}")
async def get_enrichment_status(audit_id: str):
    """Lightweight endpoint to poll enrichment progress.
    Returns only status fields — no full report fetch."""
    record = await get_audit_by_id(audit_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit not found")
    report = record["report_json"]
    if isinstance(report, str):
        report = json.loads(report)
    link_analysis = report.get("link_analysis") or {}
    has_graph = bool(link_analysis.get("graph", {}).get("nodes"))
    has_clusters = bool(link_analysis.get("clusters"))
    has_semantic_clusters = bool(report.get("semantic_clusters"))
    return {
        "enrichment_status": report.get("enrichment_status", "complete"),
        "enrichment_progress": report.get("enrichment_progress", ""),
        "has_link_graph": has_graph,
        "has_topic_clusters": has_clusters,
        "has_semantic_clusters": has_semantic_clusters,
    }


@app.post("/api/audit/{audit_id}/refresh-enrichment")
async def refresh_enrichment(audit_id: str, background_tasks: BackgroundTasks):
    """Manual refresh — checks DataForSEO status and triggers enrichment if ready.
    Useful after the background poller has timed out."""
    record = await get_audit_by_id(audit_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit not found")
    report = record["report_json"]
    if isinstance(report, str):
        report = json.loads(report)

    # Already complete — nothing to do
    if report.get("enrichment_status") == "complete":
        return {"enrichment_status": "complete", "message": "Enrichment already complete."}

    task_id = report.get("crawl_task_id")
    if not task_id:
        return {"enrichment_status": report.get("enrichment_status", "failed"),
                "message": "No crawl task associated with this audit."}

    if not is_dataforseo_configured():
        return {"enrichment_status": "failed", "message": "DataForSEO not configured."}

    try:
        dfs_client = DataForSEOClient()
        summary = await dfs_client.get_summary(task_id)
        crawl_progress = summary.get("crawl_progress", "unknown")
        pages_crawled = summary.get("pages_crawled", 0)
        pages_count = summary.get("pages_count", 0)

        if crawl_progress == "finished":
            # Crawl is done — trigger enrichment in background
            await update_audit_report(audit_id, {
                "enrichment_status": "polling",
                "enrichment_progress": "Crawl complete. Building link graph and topic clusters...",
            })
            await update_dataforseo_task(task_id, status="completed", summary=summary)
            background_tasks.add_task(
                _enrich_report_from_crawl, task_id, dfs_client, summary
            )
            return {"enrichment_status": "polling",
                    "message": "Crawl finished! Processing results now..."}
        else:
            await dfs_client.close()
            progress_msg = f"Still crawling... {pages_crawled}/{pages_count} pages"
            await update_audit_report(audit_id, {
                "enrichment_status": "timed_out",
                "enrichment_progress": progress_msg,
            })
            return {"enrichment_status": "timed_out",
                    "message": progress_msg}
    except Exception as e:
        logger.warning(f"Manual refresh failed for audit {audit_id}: {e}")
        return {"enrichment_status": "timed_out",
                "message": f"Could not check crawl status: {str(e)}"}


# --- Per-Page Audit Endpoints (Part 2) ---

# Simple in-memory concurrency limiter per parent audit
_page_audit_semaphores: dict[str, asyncio.Semaphore] = {}


@app.post("/api/audit/page")
async def run_page_audit(request: PageAuditRequest):
    """Run the 10-pillar single-page audit on any URL.
    Optionally links the result to a parent premium audit."""
    url = request.url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    parent_id = request.parent_audit_id

    # Verify parent audit exists if provided
    if parent_id:
        parent = await get_audit_by_id(parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent audit not found")

    # Rate limit: max 5 concurrent page audits per parent
    if parent_id:
        if parent_id not in _page_audit_semaphores:
            _page_audit_semaphores[parent_id] = asyncio.Semaphore(5)
        sem = _page_audit_semaphores[parent_id]
        if sem.locked():
            # Check if all 5 slots are taken
            raise HTTPException(
                status_code=429,
                detail="Maximum 5 concurrent page audits. Please wait for one to finish.",
            )
    else:
        sem = None

    async def _run():
        logger.info(f"Starting page audit for {url} (parent={parent_id})")
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

            scores = compile_scores(
                html_res, sd_res, aeo_res, css_js_res, a11y_res,
                rag_res, agent_res, data_res, il_res,
            )
            report = generate_report(
                url, html_res, sd_res, aeo_res, css_js_res, a11y_res,
                rag_res, agent_res, data_res, scores, il_res, tier="page",
            )

            # Save as a separate audit record with tier="page"
            audit_id = await save_audit_history(
                url, "page",
                report.get("overall_score", 0),
                report.get("overall_label", "N/A"),
                report, tier="page",
            )
            report["audit_id"] = str(audit_id)
            report["parent_audit_id"] = parent_id

            # Also store the page audit reference in the parent's report_json
            if parent_id:
                try:
                    parent_record = await get_audit_by_id(parent_id)
                    if parent_record and parent_record.get("report_json"):
                        rj = parent_record["report_json"]
                        if isinstance(rj, str):
                            rj = json.loads(rj)
                        page_audits = rj.get("page_audits", {})
                        page_audits[url] = {
                            "audit_id": str(audit_id),
                            "score": report.get("overall_score", 0),
                            "label": report.get("overall_label", "N/A"),
                            "timestamp": report.get("timestamp", ""),
                        }
                        await update_audit_report(parent_id, {"page_audits": page_audits})
                except Exception as e:
                    logger.warning(f"Failed to save page audit ref to parent (non-fatal): {e}")

            logger.info(f"Page audit complete for {url}: score={report.get('overall_score', 0)}")
            return report

        except Exception as e:
            logger.error(f"Page audit failed for {url}: {e}")
            raise HTTPException(status_code=500, detail=f"Page audit failed: {str(e)}")

    if sem:
        async with sem:
            return await _run()
    return await _run()


@app.get("/api/audit/{parent_audit_id}/page-audit")
async def get_page_audit(parent_audit_id: str, url: str):
    """Retrieve page audit results for a specific URL under a parent audit.
    Returns 404 if no page audit has been run for this URL yet."""
    parent = await get_audit_by_id(parent_audit_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent audit not found")

    rj = parent["report_json"]
    if isinstance(rj, str):
        rj = json.loads(rj)

    page_audits = rj.get("page_audits", {})
    ref = page_audits.get(url)
    if not ref or not ref.get("audit_id"):
        raise HTTPException(status_code=404, detail="No page audit found for this URL")

    # Fetch the full page audit report
    page_record = await get_audit_by_id(ref["audit_id"])
    if not page_record:
        raise HTTPException(status_code=404, detail="Page audit record not found")

    report = page_record["report_json"]
    if isinstance(report, str):
        report = json.loads(report)
    report["audit_id"] = ref["audit_id"]
    report["parent_audit_id"] = parent_audit_id
    return report


@app.get("/api/audit/{parent_audit_id}/page-audits")
async def list_page_audits(parent_audit_id: str):
    """List all page audits that have been run under a parent audit."""
    parent = await get_audit_by_id(parent_audit_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent audit not found")

    rj = parent["report_json"]
    if isinstance(rj, str):
        rj = json.loads(rj)

    return {"page_audits": rj.get("page_audits", {})}


@app.get("/api/audits")
async def get_all_audits(
    limit: int = 100, offset: int = 0,
    user=Depends(get_current_user),
):
    """List all audits. Requires authentication."""
    audits = await list_all_audits(limit=limit, offset=offset)
    return {"audits": audits, "total": len(audits)}


@app.post("/api/schedules")
async def create_new_schedule(request: ScheduleRequest):
    schedule_id = await create_schedule(request.url, request.email, request.frequency, request.max_pages)
    return {"id": schedule_id, "status": "created"}

@app.get("/api/schedules")
async def list_schedules():
    schedules = await get_schedules()
    return {"schedules": schedules}

@app.put("/api/schedules/{schedule_id}")
async def update_existing_schedule(schedule_id: int, request: ScheduleUpdateRequest):
    await update_schedule(schedule_id, enabled=request.enabled, frequency=request.frequency, email=request.email)
    return {"id": schedule_id, "status": "updated"}

@app.delete("/api/schedules/{schedule_id}")
async def delete_existing_schedule(schedule_id: int):
    await delete_schedule(schedule_id)
    return {"id": schedule_id, "status": "deleted"}

# --- Webflow Fix Knowledge Base ---

@app.get("/api/fixes")
async def list_fixes():
    """List all available Webflow fix instructions."""
    return {"fixes": get_all_fixes()}

@app.get("/api/fixes/{finding_pattern}")
async def get_fix_for_finding(finding_pattern: str):
    """Get Webflow fix instructions for a specific finding pattern."""
    fix = get_fix(finding_pattern)
    if not fix:
        raise HTTPException(status_code=404, detail=f"No fix found for pattern: {finding_pattern}")
    return fix

# --- DataForSEO Crawl Endpoints (Sprint 3A) ---


def _poll_interval(attempt: int) -> int:
    """Progressive poll intervals: fast at start, slower over time.
    Polls 1-10: 15s, polls 11-30: 20s, polls 31-60: 30s.
    Total: ~25 minutes of polling before timeout."""
    if attempt <= 10:
        return 15
    if attempt <= 30:
        return 20
    return 30


async def _poll_and_enrich_crawl(task_id: str, audit_id: str):
    """Poll DataForSEO summary until crawl completes, then enrich the audit report.

    This is the PRIMARY mechanism for collecting crawl results. The pingback
    endpoint is a bonus accelerator — if it fires first, `update_dataforseo_task`
    will already have status='completed' and this poller will skip straight to
    enrichment on its next iteration.
    """
    max_attempts = 60  # progressive intervals totalling ~25 minutes
    for attempt in range(1, max_attempts + 1):
        await asyncio.sleep(_poll_interval(attempt))

        try:
            # Check if the pingback already handled this task
            task_record = await get_dataforseo_task(task_id)
            if task_record and task_record.get("status") == "completed":
                logger.info(
                    f"DataForSEO task {task_id} already completed (likely via pingback), "
                    "checking if enrichment already ran..."
                )
                # Check if the audit report already has link_analysis
                audit = await get_audit_by_id(audit_id)
                if audit and audit.get("report_json"):
                    rj = audit["report_json"]
                    if isinstance(rj, str):
                        rj = json.loads(rj)
                    if rj.get("link_analysis") and rj.get("crawl_status") == "completed":
                        logger.info(f"Audit {audit_id} already enriched, poller exiting")
                        return
                # Pingback marked it completed but enrichment didn't run — do it now
                dfs_client = DataForSEOClient()
                summary = await dfs_client.get_summary(task_id)
                await _enrich_report_from_crawl(task_id, dfs_client, summary)
                return

            # Poll DataForSEO for crawl progress
            dfs_client = DataForSEOClient()
            summary = await dfs_client.get_summary(task_id)
            await dfs_client.close()

            crawl_progress = summary.get("crawl_progress", "unknown")
            pages_crawled = summary.get("pages_crawled", 0)
            pages_count = summary.get("pages_count", 0)
            logger.info(
                f"DataForSEO poll {attempt}/{max_attempts}: task={task_id} "
                f"progress={crawl_progress} pages={pages_crawled}/{pages_count}"
            )

            # Build informative progress message
            if crawl_progress == "in_progress" and pages_crawled > 0:
                progress_msg = f"Crawling site... {pages_crawled}/{pages_count} pages discovered (poll {attempt}/{max_attempts})"
            elif attempt > 10 and pages_crawled == 0:
                progress_msg = f"Waiting for crawler to start... This can take a few minutes for larger sites. (poll {attempt}/{max_attempts})"
            else:
                progress_msg = f"Crawling site... {pages_crawled}/{pages_count} pages (poll {attempt}/{max_attempts})"

            await update_audit_report(audit_id, {
                "enrichment_status": "polling",
                "enrichment_progress": progress_msg,
            })

            if crawl_progress == "finished":
                await update_audit_report(audit_id, {
                    "enrichment_status": "polling",
                    "enrichment_progress": "Crawl complete. Building link graph and topic clusters...",
                })
                await update_dataforseo_task(task_id, status="completed", summary=summary)
                dfs_client = DataForSEOClient()
                await _enrich_report_from_crawl(task_id, dfs_client, summary)
                return

        except Exception as e:
            logger.warning(f"DataForSEO poll error (attempt {attempt}): {e}")

    # Timed out — use "timed_out" status (not "failed") so frontend can distinguish
    logger.warning(
        f"DataForSEO crawl timed out after {max_attempts} polls for task {task_id}, "
        f"audit {audit_id}. Results can still arrive via pingback or manual refresh."
    )
    await update_audit_report(audit_id, {
        "enrichment_status": "timed_out",
        "enrichment_progress": "Crawl is still running. Data will appear when it completes. Try refreshing in a few minutes.",
    })


@app.get("/api/dataforseo/pingback")
async def dataforseo_pingback(task_id: str, background_tasks: BackgroundTasks):
    """Webhook called by DataForSEO when a crawl task finishes.
    The $id in the pingback URL gets replaced with the actual task_id."""
    logger.info(f"DataForSEO pingback received for task {task_id}")
    try:
        dfs_client = DataForSEOClient()
        summary = await dfs_client.get_summary(task_id)

        crawl_progress = summary.get("crawl_progress", "unknown")
        status = "completed" if crawl_progress == "finished" else "failed"

        await update_dataforseo_task(task_id, status=status, summary=summary)
        logger.info(
            f"DataForSEO task {task_id} marked {status}: "
            f"{summary.get('pages_count', 0)} pages, "
            f"{summary.get('internal_links_count', 0)} internal links"
        )

        # If crawl completed, check if the poller already enriched, then enrich if not
        if status == "completed":
            # Check if enrichment already happened (from the polling task)
            task_record = await get_dataforseo_task(task_id)
            audit_id = task_record.get("audit_id") if task_record else None
            already_enriched = False
            if audit_id:
                audit = await get_audit_by_id(audit_id)
                if audit and audit.get("report_json"):
                    rj = audit["report_json"]
                    if isinstance(rj, str):
                        rj = json.loads(rj)
                    already_enriched = bool(rj.get("link_analysis") and rj.get("crawl_status") == "completed")

            if already_enriched:
                logger.info(f"Pingback: audit {audit_id} already enriched by poller, skipping")
                await dfs_client.close()
            else:
                background_tasks.add_task(
                    _enrich_report_from_crawl, task_id, dfs_client, summary
                )
        else:
            await dfs_client.close()
    except DataForSEOError as e:
        logger.error(f"DataForSEO pingback processing failed: {e}")
        await update_dataforseo_task(task_id, status="failed")
    except Exception as e:
        logger.error(f"Unexpected error in DataForSEO pingback: {e}")

    return {"status": "ok"}


async def _extract_page_entities(
    graph_data: dict,
    tipr_analysis: dict | None,
    homepage_url: str,
    existing_entities: dict | None = None,
    max_pages: int = 25,
) -> dict:
    """Extract NLP entities from top pages for better topic clustering.

    Selects pages by importance (PageRank, click depth, hub status) and
    runs Google NLP analyzeEntities on Trafilatura-extracted content.

    Returns dict of url -> {entities: [...], analyzed_at: "..."}.
    Budget: ~25 NLP API calls (75 units, well within 5K free tier).
    """
    import httpx
    from datetime import datetime, timezone

    # If we already have enough entity data, skip
    if existing_entities and len(existing_entities) >= max_pages:
        logger.info(f"Page entities already exist ({len(existing_entities)} pages), skipping extraction")
        return existing_entities

    nodes = graph_data.get("nodes", [])
    if not nodes:
        return {}

    # Build TIPR lookup for PageRank scores
    tipr_pages = (tipr_analysis or {}).get("pages", [])
    tipr_map = {p["url"]: p for p in tipr_pages if isinstance(p, dict)}

    # Score each page for importance
    scored_pages = []
    seen_prefixes: set[str] = set()
    homepage_norm = homepage_url.rstrip("/").lower()

    for node in nodes:
        url = node.get("id", "")
        if not url:
            continue

        tipr = tipr_map.get(url, {})
        pr_score = tipr.get("pagerank_score", 0) or 0
        click_depth = node.get("depth", 99)
        if click_depth is None or click_depth < 0:
            click_depth = 99
        inbound = node.get("inbound", 0) or 0

        # URL prefix for directory representation
        parsed = urlparse(url)
        segments = [s for s in parsed.path.strip("/").split("/") if s]
        prefix = segments[0] if segments else "/"

        is_homepage = url.rstrip("/").lower() == homepage_norm
        is_depth1 = click_depth == 1
        is_new_prefix = prefix not in seen_prefixes

        # Importance score (higher = more important)
        importance = (
            (100.0 if is_homepage else 0) +
            pr_score * 0.5 +
            (30.0 if is_depth1 else 0) +
            (15.0 if is_new_prefix else 0) +
            inbound * 0.3 +
            max(0, 10.0 - click_depth * 2.0)
        )

        scored_pages.append({
            "url": url,
            "importance": importance,
            "prefix": prefix,
            "title": node.get("label", ""),
        })
        if is_new_prefix:
            seen_prefixes.add(prefix)

    # Sort by importance, take top N
    scored_pages.sort(key=lambda p: p["importance"], reverse=True)
    selected_urls = [p["url"] for p in scored_pages[:max_pages]]

    logger.info(f"Selected {len(selected_urls)} pages for NLP entity extraction")

    # Fetch HTML and extract content, then run NLP
    page_entities: dict = dict(existing_entities or {})
    analyzed_count = 0

    for i, url in enumerate(selected_urls):
        # Skip if already analyzed
        if url in page_entities and page_entities[url].get("entities"):
            continue

        try:
            # Fetch HTML
            async with httpx.AsyncClient(
                timeout=15.0, follow_redirects=True
            ) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "WAIO-Audit-Bot/1.0 (content extraction)"
                })
                resp.raise_for_status()
                html = resp.text

            # Extract clean text via Trafilatura
            extracted = extract_content(html, url)
            if not extracted.clean_text or len(extracted.clean_text.split()) < 30:
                logger.debug(f"Insufficient content for NLP on {url}")
                continue

            # Run Google NLP entity analysis
            entities = await nlp_analyze_entities(extracted.clean_text)
            if entities:
                page_entities[url] = {
                    "entities": [
                        {
                            "name": e.name,
                            "type": e.entity_type,
                            "salience": round(e.salience, 4),
                            "wikipedia_url": e.wikipedia_url,
                            "mentions_count": e.mentions_count,
                        }
                        for e in entities[:20]
                    ],
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                }
                analyzed_count += 1
                logger.info(
                    f"Entity extraction ({analyzed_count}/{len(selected_urls)}): "
                    f"{url} — {len(entities)} entities, primary={entities[0].name}"
                )
        except Exception as e:
            logger.debug(f"Entity extraction failed for {url}: {e}")

    logger.info(f"Page entity extraction complete: {analyzed_count} new pages analyzed, {len(page_entities)} total")
    return page_entities


def _extract_lightweight_entities(title: str, url: str) -> list[dict]:
    """Extract pseudo-entities from title + URL for pages without NLP data.

    Uses simple heuristics: title-case words that aren't common English words,
    plus URL path segment tokens. Not as accurate as Google NLP but gives
    every page some entity signal for clustering.
    """
    COMMON_WORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "this", "that", "these",
        "those", "it", "its", "from", "how", "what", "why", "when", "where",
        "who", "which", "your", "our", "my", "his", "her", "their", "all",
        "each", "every", "both", "few", "more", "most", "other", "some", "such",
        "no", "not", "only", "own", "same", "so", "than", "too", "very",
        "about", "home", "page", "blog", "post", "article", "new", "best",
        "top", "free", "guide", "ultimate", "complete", "step", "tips",
        "get", "use", "using", "make", "one", "two", "three", "first",
    }

    entities = []
    seen = set()

    # Extract from title: multi-word capitalized phrases and significant words
    if title:
        # Find capitalized phrases (2+ words that look like proper nouns/names)
        words = title.split()
        i = 0
        while i < len(words):
            # Look for sequences of capitalized words
            if words[i][0:1].isupper() and words[i].lower() not in COMMON_WORDS and len(words[i]) > 2:
                phrase = [words[i]]
                j = i + 1
                while j < len(words) and words[j][0:1].isupper() and words[j].lower() not in COMMON_WORDS:
                    phrase.append(words[j])
                    j += 1
                name = " ".join(phrase)
                name_lower = name.lower()
                if name_lower not in seen and len(name) > 2:
                    entities.append({
                        "name": name,
                        "type": "INFERRED",
                        "salience": 0.15 if len(phrase) > 1 else 0.08,
                    })
                    seen.add(name_lower)
                i = j
            else:
                # Single significant word
                w = words[i]
                wl = w.lower().strip(".,!?:;()[]{}\"'")
                if wl not in COMMON_WORDS and len(wl) > 3 and wl not in seen:
                    entities.append({
                        "name": wl.title(),
                        "type": "INFERRED",
                        "salience": 0.05,
                    })
                    seen.add(wl)
                i += 1

    # Extract from URL path segments
    parsed = urlparse(url)
    segments = [s for s in parsed.path.strip("/").split("/") if s]
    for seg in segments:
        tokens = re.split(r"[-_.]", seg)
        for tok in tokens:
            tok_lower = tok.lower()
            if tok_lower not in COMMON_WORDS and len(tok_lower) > 3 and tok_lower not in seen:
                entities.append({
                    "name": tok_lower.title(),
                    "type": "INFERRED",
                    "salience": 0.03,
                })
                seen.add(tok_lower)

    return entities[:10]


async def _enrich_report_from_crawl(
    task_id: str, dfs_client: DataForSEOClient, summary: dict
):
    """Background task: fetch DataForSEO pages/links, build link graph,
    and merge enriched data into the saved audit report."""
    try:
        # Find the audit_id associated with this task
        task_record = await get_dataforseo_task(task_id)
        if not task_record or not task_record.get("audit_id"):
            logger.warning(f"No audit_id found for DataForSEO task {task_id}, skipping enrichment")
            await dfs_client.close()
            return
        audit_id = task_record["audit_id"]

        # Look up the audit to get the homepage URL
        audit_record = await get_audit_by_id(audit_id)
        if not audit_record:
            logger.warning(f"Audit {audit_id} not found for enrichment")
            await dfs_client.close()
            return
        homepage_url = audit_record["url"]

        logger.info(f"Enriching audit {audit_id} with DataForSEO crawl data from task {task_id}")

        # Fetch all pages and links from DataForSEO (GET endpoints are FREE)
        pages_data = await dfs_client.get_all_pages(task_id)
        links_data = await dfs_client.get_all_links(task_id)
        await dfs_client.close()

        logger.info(f"Fetched {len(pages_data)} pages, {len(links_data)} links from DataForSEO")

        # Short-circuit: DataForSEO crawled 0 pages. Almost always means the
        # site blocked DataForSEO's crawler (Cloudflare / bot protection). All
        # the downstream analysis (link graph, TIPR, clustering) needs at least
        # one page to produce anything useful, so skip it and give the user an
        # actionable message instead of the generic "try again" failure.
        if not pages_data and not links_data:
            logger.warning(
                f"DataForSEO returned 0 pages for task {task_id} — likely bot-protected site"
            )
            await update_audit_report(audit_id, {
                "crawl_status": "no_data",
                "crawl_stats": {
                    "pages_crawled": summary.get("pages_crawled", 0),
                    "pages_discovered": summary.get("pages_count", 0),
                    "internal_links": 0,
                    "external_links": 0,
                    "broken_links": 0,
                    "broken_resources": 0,
                },
                "enrichment_status": "no_data",
                "enrichment_progress": (
                    "Site-wide crawl returned no pages — the site likely blocks automated "
                    "crawlers (Cloudflare or similar). The single-page audit still succeeded; "
                    "Link Graph, Link Intelligence, and Topic Clusters require a multi-page "
                    "crawl and are unavailable for this site."
                ),
            })
            return

        # Build crawl_stats
        crawl_stats = {
            "pages_crawled": summary.get("pages_crawled", 0),
            "pages_discovered": summary.get("pages_count", 0),
            "internal_links": summary.get("internal_links_count", 0),
            "external_links": summary.get("external_links_count", 0),
            "broken_links": summary.get("broken_links", 0),
            "broken_resources": summary.get("broken_resources", 0),
        }

        # Build link graph + topic clusters using link_graph_auditor
        link_analysis = build_link_graph(
            pages_data=pages_data,
            links_data=links_data,
            homepage_url=homepage_url,
        )

        # Run TIPR analysis on the link graph
        tipr_analysis = None
        graph_data = link_analysis.get("graph")
        if graph_data and graph_data.get("links"):
            try:
                # Pull NLP data from existing report for content relevance scoring
                existing_report = audit_record.get("report_json") or {}
                nlp_data = existing_report.get("nlp_analysis")
                tipr_analysis = run_tipr_analysis(
                    graph_data=graph_data,
                    nlp_analysis=nlp_data,
                    max_recommendations=50,
                )
                if tipr_analysis:
                    logger.info(
                        f"TIPR analysis complete: {tipr_analysis['summary']['total_pages']} pages, "
                        f"{len(tipr_analysis['recommendations'])} recommendations"
                    )
            except Exception as e:
                logger.warning(f"TIPR analysis failed (non-fatal): {e}", exc_info=True)

        # Multi-page NLP entity extraction for better clustering
        page_entities: dict = {}
        existing_report = audit_record.get("report_json") or {}
        if is_nlp_configured() and graph_data and graph_data.get("nodes"):
            try:
                page_entities = await _extract_page_entities(
                    graph_data=graph_data,
                    tipr_analysis=tipr_analysis,
                    homepage_url=homepage_url,
                    existing_entities=existing_report.get("page_entities") or {},
                    max_pages=25,
                )
                logger.info(f"Page entity extraction: {len(page_entities)} pages analyzed")
            except Exception as e:
                logger.warning(f"Page entity extraction failed (non-fatal): {e}", exc_info=True)

        # Run semantic topic clustering on the enriched data
        semantic_clusters = None
        try:
            cluster_pages, cluster_links = prepare_pages_from_report({
                **existing_report,
                "link_analysis": link_analysis,
                "tipr_analysis": tipr_analysis,
                "page_entities": page_entities,
            })
            if cluster_pages:
                semantic_clusters = run_topic_clustering(
                    pages=cluster_pages,
                    links=cluster_links,
                )
                if semantic_clusters:
                    logger.info(
                        f"Semantic clustering complete: {semantic_clusters['n_clusters']} clusters, "
                        f"silhouette={semantic_clusters['silhouette_score']:.3f}"
                    )
        except Exception as e:
            logger.warning(f"Semantic topic clustering failed (non-fatal): {e}", exc_info=True)

        # Merge enriched data into the saved report
        report_updates = {
            "crawl_status": "completed",
            "crawl_stats": crawl_stats,
            "link_analysis": link_analysis,
            "tipr_analysis": tipr_analysis,
            "semantic_clusters": semantic_clusters,
            "page_entities": page_entities if page_entities else None,
            "enrichment_status": "complete",
            "enrichment_progress": "Complete",
        }

        await update_audit_report(audit_id, report_updates)
        logger.info(
            f"Audit {audit_id} enriched: "
            f"{len(link_analysis.get('graph', {}).get('nodes', []))} graph nodes, "
            f"{len(link_analysis.get('clusters', []))} clusters"
        )

        # Regenerate executive summary now that TIPR + clusters are available
        try:
            enriched_record = await get_audit_by_id(audit_id)
            if enriched_record:
                full_report = enriched_record["report_json"]
                if isinstance(full_report, str):
                    full_report = json.loads(full_report)
                competitive_data = full_report.get("competitive_data")
                new_summary = generate_executive_summary(full_report, competitive_data)
                await update_audit_report(audit_id, {"executive_summary": new_summary})
                logger.info(f"Executive summary regenerated post-enrichment: {len(new_summary)} chars")
        except Exception as e:
            logger.warning(f"Post-enrichment summary regeneration failed (non-fatal): {e}")

        # ── Spawn AI Visibility as a sibling task (Phase 3) ──
        try:
            enriched_for_aiv = await get_audit_by_id(audit_id)
            if enriched_for_aiv:
                aiv_rpt = enriched_for_aiv.get("report_json") or {}
                if isinstance(aiv_rpt, str):
                    aiv_rpt = json.loads(aiv_rpt)
                if aiv_rpt.get("ai_visibility_opt_in"):
                    brand_override = aiv_rpt.get("ai_visibility_brand_name")
                    asyncio.create_task(
                        run_ai_visibility_analysis(
                            audit_id=str(audit_id),
                            brand_override=brand_override,
                        )
                    )
                    logger.info(f"AI Visibility sibling task launched for audit {audit_id}")
        except Exception as e:
            logger.warning(f"Failed to launch AI Visibility sibling task (non-fatal): {e}")

        # Also persist link graph edges to the dedicated table
        try:
            edges = []
            for link in links_data:
                if isinstance(link, dict):
                    edges.append({
                        "source_url": link.get("page_from", ""),
                        "target_url": link.get("page_to", ""),
                        "anchor_text": link.get("anchor", ""),
                        "is_nofollow": link.get("dofollow", True) is False,
                    })
            if edges:
                await save_link_graph_edges(audit_id, edges)
                logger.info(f"Saved {len(edges)} link graph edges for audit {audit_id}")
        except Exception as e:
            logger.warning(f"Failed to save link graph edges (non-fatal): {e}")

    except Exception as e:
        logger.error(f"Report enrichment failed for task {task_id}: {e}", exc_info=True)
        # Mark enrichment as failed so the frontend stops polling
        try:
            task_record = await get_dataforseo_task(task_id)
            if task_record and task_record.get("audit_id"):
                await update_audit_report(task_record["audit_id"], {
                    "enrichment_status": "failed",
                    "enrichment_progress": "Report enrichment failed. Please try again.",
                })
        except Exception:
            pass
        try:
            await dfs_client.close()
        except Exception:
            pass


@app.get("/api/audit/crawl-status/{task_id}")
async def get_crawl_status(task_id: str):
    """Check the status of a DataForSEO crawl task.
    Used by the frontend to poll for crawl completion."""
    # First check our local DB
    task = await get_dataforseo_task(task_id)
    if task:
        return {
            "task_id": task["task_id"],
            "status": task["status"],
            "pages_crawled": task["pages_crawled"],
            "pages_count": task["pages_count"],
            "internal_links_count": task["internal_links_count"],
            "external_links_count": task["external_links_count"],
            "broken_links": task["broken_links"],
            "created_at": task["created_at"],
            "completed_at": task["completed_at"],
        }

    # If not in DB yet, try querying DataForSEO directly
    if not is_dataforseo_configured():
        raise HTTPException(status_code=404, detail="Task not found and DataForSEO not configured")

    try:
        dfs_client = DataForSEOClient()
        summary = await dfs_client.get_summary(task_id)
        await dfs_client.close()
        return {
            "task_id": task_id,
            "status": "crawling" if summary.get("crawl_progress") != "finished" else "completed",
            "pages_crawled": summary.get("pages_crawled", 0),
            "pages_count": summary.get("pages_count", 0),
            "internal_links_count": summary.get("internal_links_count", 0),
            "external_links_count": summary.get("external_links_count", 0),
            "broken_links": summary.get("broken_links", 0),
            "created_at": None,
            "completed_at": None,
        }
    except DataForSEOError as e:
        raise HTTPException(status_code=502, detail=f"DataForSEO query failed: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check crawl status: {str(e)}")


# --- Google OAuth Endpoints (Sprint 3B) ---

@app.get("/api/auth/google")
async def google_auth_start(property_url: str | None = None):
    """Initiate Google OAuth flow. Returns the consent URL to redirect the user to.
    Optional property_url is carried through as state to associate tokens after callback."""
    if not is_google_configured():
        raise HTTPException(status_code=501, detail="Google OAuth not configured (missing GOOGLE_CLIENT_ID/SECRET)")

    app_base = os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{app_base}/api/auth/google/callback"
    state = property_url or ""
    auth_url = get_auth_url(redirect_uri, state=state)
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@app.get("/api/auth/google/callback")
async def google_auth_callback(code: str, state: str = ""):
    """OAuth callback — exchange code for tokens, discover properties, store encrypted."""
    if not is_google_configured():
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    app_base = os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{app_base}/api/auth/google/callback"

    try:
        token_data = await exchange_code(code, redirect_uri)
    except Exception as e:
        logger.error(f"Google OAuth exchange failed: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth code exchange failed: {str(e)}")

    # Discover GSC sites and GA4 properties
    gsc_sites: list = []
    ga4_properties: list = []
    try:
        gsc_sites = await gsc_list_sites(token_data)
    except Exception as e:
        logger.warning(f"Failed to list GSC sites: {e}")
    try:
        ga4_properties = await ga4_list_properties(token_data)
    except Exception as e:
        logger.warning(f"Failed to list GA4 properties: {e}")

    # If caller specified a property_url in state, store tokens for it
    property_url = state.strip() if state else None
    if property_url:
        encrypted = encrypt_token(token_data)
        await save_google_tokens(
            property_url=property_url,
            encrypted_tokens=encrypted,
            scopes=token_data.get("scope"),
        )

    # Return a simple HTML page that posts a message back to the opener window
    # and the discovered properties for the frontend to handle
    result = {
        "success": True,
        "gsc_sites": gsc_sites,
        "ga4_properties": ga4_properties,
        "stored_for": property_url,
    }

    # If opened in a popup, close it and notify parent; otherwise return JSON
    html_content = f"""<!DOCTYPE html><html><body>
    <p>Google account connected successfully. You can close this window.</p>
    <script>
    if (window.opener) {{
        window.opener.postMessage({json.dumps(result)}, '*');
        window.close();
    }}
    </script></body></html>"""

    from fastapi.responses import HTMLResponse as HTMLResp
    return HTMLResp(content=html_content)


@app.post("/api/auth/google/connect")
async def google_auth_connect(
    property_url: str = Body(...),
    ga4_property_id: str | None = Body(None),
    tokens: dict = Body(...),
):
    """Store tokens for a specific GSC property after the user selects it in the frontend."""
    encrypted = encrypt_token(tokens)
    await save_google_tokens(
        property_url=property_url,
        encrypted_tokens=encrypted,
        ga4_property_id=ga4_property_id,
        scopes=tokens.get("scope"),
    )
    return {"status": "connected", "property_url": property_url}


@app.get("/api/auth/google/status")
async def google_auth_status(property_url: str | None = None):
    """Check if Google OAuth tokens exist. If property_url given, check that specific one."""
    if property_url:
        record = await get_google_tokens(property_url)
        return {
            "connected": record is not None,
            "property_url": property_url,
            "ga4_property_id": record.get("ga4_property_id") if record else None,
            "email": record.get("email") if record else None,
            "updated_at": record.get("updated_at") if record else None,
        }
    # List all connected properties
    all_tokens = await list_google_tokens()
    return {
        "connected": len(all_tokens) > 0,
        "properties": all_tokens,
    }


@app.delete("/api/auth/google/{property_url:path}")
async def google_auth_disconnect(property_url: str):
    """Disconnect (delete tokens for) a GSC property."""
    await delete_google_tokens(property_url)
    return {"status": "disconnected", "property_url": property_url}


@app.get("/api/gsc/sites")
async def get_gsc_sites(property_url: str):
    """List GSC sites accessible with stored tokens for a given property."""
    record = await get_google_tokens(property_url)
    if not record:
        raise HTTPException(status_code=404, detail="No tokens found for this property")
    token_data = decrypt_token(record["encrypted_tokens"])
    sites = await gsc_list_sites(token_data)
    return {"sites": sites}


@app.get("/api/gsc/pages")
async def get_gsc_pages(
    property_url: str,
    start_date: str = "2025-01-01",
    end_date: str = "2026-03-31",
):
    """Get all indexed pages for a GSC property with impressions/clicks data."""
    record = await get_google_tokens(property_url)
    if not record:
        raise HTTPException(status_code=404, detail="No tokens found for this property")
    token_data = decrypt_token(record["encrypted_tokens"])
    pages = await gsc_get_all_pages(token_data, property_url, start_date, end_date)
    return {"property_url": property_url, "total_pages": len(pages), "pages": pages}


@app.get("/api/gsc/sitemaps")
async def get_gsc_sitemaps(property_url: str):
    """List sitemaps for a GSC property."""
    record = await get_google_tokens(property_url)
    if not record:
        raise HTTPException(status_code=404, detail="No tokens found for this property")
    token_data = decrypt_token(record["encrypted_tokens"])
    sitemaps = await gsc_list_sitemaps(token_data, property_url)
    return {"property_url": property_url, "sitemaps": sitemaps}


@app.get("/api/ga4/traffic")
async def get_ga4_traffic(
    property_url: str,
    start_date: str = "90daysAgo",
    end_date: str = "today",
):
    """Get organic traffic per landing page from GA4."""
    record = await get_google_tokens(property_url)
    if not record:
        raise HTTPException(status_code=404, detail="No tokens found for this property")
    if not record.get("ga4_property_id"):
        raise HTTPException(status_code=400, detail="No GA4 property linked for this GSC property")
    token_data = decrypt_token(record["encrypted_tokens"])
    traffic = await ga4_get_traffic_by_page(
        token_data, record["ga4_property_id"], start_date, end_date
    )
    return {
        "property_url": property_url,
        "ga4_property_id": record["ga4_property_id"],
        "total_pages": len(traffic),
        "pages": traffic,
    }


# --- Link Graph & CMS Endpoints (Sprint 3C-F) ---

@app.get("/api/audit/link-graph/{audit_id}")
async def get_audit_link_graph(audit_id: str):
    """Return the link graph data for D3 visualization.
    Prefers the full link_analysis from report_json (has stats, orphans, hubs, clusters).
    Falls back to reconstructing from link_graph + page_content DB tables."""
    # Primary source: link_analysis stored in report_json by _enrich_report_from_crawl
    audit = await get_audit_by_id(audit_id)
    if audit and audit.get("report_json"):
        rj = audit["report_json"]
        if isinstance(rj, str):
            rj = json.loads(rj)
        link_analysis = rj.get("link_analysis")
        if link_analysis and link_analysis.get("graph", {}).get("nodes"):
            return link_analysis

    # Fallback: reconstruct from DB tables (limited format — no stats/hubs)
    data = await get_link_graph_data(audit_id)
    if not data:
        raise HTTPException(status_code=404, detail="Link graph data not available yet. It will appear after the site crawl completes.")

    # Wrap in the format the LinkGraph component expects
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    for node in nodes:
        node.setdefault("cluster", -1)
        node.setdefault("inbound", 0)
        node.setdefault("outbound", 0)
    return {
        "graph": {"nodes": nodes, "links": links},
        "stats": {
            "total_pages": len(nodes),
            "total_internal_links": len(links),
            "total_edges": len(links),
            "avg_inbound_links": round(len(links) / max(len(nodes), 1), 1),
            "max_depth": max((n.get("depth") or 0 for n in nodes), default=0),
            "homepage_inbound": 0,
        },
        "orphans": {
            "orphan_count": sum(1 for n in nodes if n.get("is_orphan")),
            "total_known_urls": len(nodes),
            "crawled_count": len(nodes),
        },
        "hubs": [],
        "clusters": [],
    }


@app.get("/api/audit/clusters/{audit_id}")
async def get_audit_clusters(audit_id: str):
    """Return topic cluster data for an audit."""
    # Primary source: link_analysis in report_json
    audit = await get_audit_by_id(audit_id)
    if audit and audit.get("report_json"):
        rj = audit["report_json"]
        if isinstance(rj, str):
            rj = json.loads(rj)
        link_analysis = rj.get("link_analysis")
        if link_analysis:
            return {
                "audit_id": audit_id,
                "clusters": link_analysis.get("clusters", []),
                "industry": link_analysis.get("industry", {}),
            }

    # Fallback: DB tables
    data = await get_link_graph_data(audit_id)
    if not data:
        raise HTTPException(status_code=404, detail="No link graph data found for this audit")
    return {
        "audit_id": audit_id,
        "clusters": data.get("clusters", []),
        "industry": data.get("industry", {}),
    }


@app.get("/api/audit/cms/{audit_id}")
async def get_audit_cms(audit_id: str):
    """Return CMS detection result for an audit."""
    graph_data = await get_link_graph_data(audit_id)
    if graph_data and graph_data.get("cms_detection"):
        return graph_data["cms_detection"]
    raise HTTPException(status_code=404, detail="CMS detection data not found for this audit")


@app.post("/api/audit/process-crawl/{audit_id}")
async def process_crawl_results(audit_id: str, background_tasks: BackgroundTasks):
    """Process completed DataForSEO crawl results: build link graph, detect clusters,
    run NLP classification, and persist everything.
    Called after DataForSEO pingback confirms crawl completion."""
    task = await get_dataforseo_task_by_audit(audit_id)
    if not task:
        raise HTTPException(status_code=404, detail="No DataForSEO task found for this audit")
    if task["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Crawl not yet completed (status: {task['status']})")

    task_id = task["task_id"]
    target_url = task["target_url"]

    async def _process():
        try:
            dfs_client = DataForSEOClient()
            pages_data = await dfs_client.get_all_pages(task_id)
            links_data = await dfs_client.get_all_links(task_id)
            await dfs_client.close()

            logger.info(f"Processing crawl for audit {audit_id}: {len(pages_data)} pages, {len(links_data)} links")

            # Build link graph analysis
            graph_result = build_link_graph(
                pages_data=pages_data,
                links_data=links_data,
                homepage_url=target_url,
            )

            # Save link graph edges to DB
            edges_for_db = [
                {
                    "source_url": e["source"],
                    "target_url": e["target"],
                    "anchor_text": e.get("anchor", ""),
                    "is_nofollow": e.get("is_nofollow", False),
                    "link_position": e.get("link_type", ""),
                }
                for e in graph_result["graph"]["links"][:50000]
            ]
            await save_link_graph_edges(audit_id, edges_for_db)

            # Save page content batch
            page_content_batch = [
                {
                    "url": node["id"],
                    "title": node.get("label", ""),
                    "click_depth": node.get("depth"),
                    "is_orphan": node.get("is_orphan", False),
                }
                for node in graph_result["graph"]["nodes"]
            ]
            await save_page_content_batch(audit_id, page_content_batch)

            # Save industry detection if available
            industry = graph_result.get("industry", {})
            if industry.get("detected_industry"):
                await save_industry_detection(
                    audit_id,
                    industry["detected_industry"],
                    industry["confidence"],
                    industry.get("categories", []),
                )

            logger.info(f"Crawl processing complete for audit {audit_id}")
        except Exception as e:
            logger.error(f"Failed to process crawl for audit {audit_id}: {e}")

    background_tasks.add_task(_process)
    return {"status": "processing", "audit_id": audit_id}


# --- Content Intelligence Endpoints (Sprint 4) ---

@app.get("/api/audit/wdf-idf/{audit_id}")
async def get_wdf_idf(audit_id: str, keyword: str | None = None):
    """Run or retrieve WDF*IDF gap analysis for an audit."""
    pages = await get_page_content_for_audit(audit_id)
    if not pages:
        raise HTTPException(status_code=404, detail="No page content found for this audit")

    # Use the first page with clean_text as the target
    target_page = next((p for p in pages if p.get("clean_text") and len((p.get("clean_text") or "").split()) > 20), None)
    if not target_page:
        raise HTTPException(status_code=400, detail="No page has enough extracted content for WDF*IDF analysis")

    result = await run_wdf_idf_analysis(
        target_url=target_page["url"],
        target_text=target_page["clean_text"],
        target_keyword=keyword,
    )
    return result.to_dict()


@app.get("/api/audit/interlinking/{audit_id}")
async def get_interlinking(audit_id: str):
    """Find interlinking opportunities for an audit's pages."""
    pages = await get_page_content_for_audit(audit_id)
    if not pages:
        raise HTTPException(status_code=404, detail="No page content found for this audit")

    pages_with_text = [
        {"url": p["url"], "clean_text": p.get("clean_text") or "", "title": p.get("title") or ""}
        for p in pages
    ]

    # Get existing links from link graph
    graph_data = await get_link_graph_data(audit_id)
    existing_links: set = set()
    if graph_data:
        for link in graph_data.get("links", []):
            existing_links.add((link["source"], link["target"]))

    result = find_interlinking_opportunities(pages_with_text, existing_links)
    return result.to_dict()


@app.get("/api/audit/content-profile/{audit_id}")
async def get_content_profile(audit_id: str):
    """Return content profile analysis for an audit's pages."""
    pages = await get_page_content_for_audit(audit_id)
    if not pages:
        raise HTTPException(status_code=404, detail="No page content found for this audit")

    profiles = []
    for page in pages[:50]:  # cap at 50 pages for response size
        clean_text = page.get("clean_text") or ""
        if len(clean_text.split()) < 10:
            continue
        profile = build_content_profile(
            page["url"], clean_text, page.get("h1_text"), page.get("title"),
        )
        # Enrich with existing NLP data if available
        if page.get("nlp_primary_entity"):
            profile.primary_entity = page["nlp_primary_entity"]
            profile.primary_entity_salience = page.get("nlp_primary_entity_salience")
            profile.entity_focus_aligned = page.get("nlp_entity_focus_aligned")
        if page.get("nlp_sentiment_score") is not None:
            profile.sentiment_score = page["nlp_sentiment_score"]
            profile.sentiment_magnitude = page.get("nlp_sentiment_magnitude")
        profiles.append(profile.to_dict())

    return {"audit_id": audit_id, "total_pages": len(profiles), "profiles": profiles}


@app.get("/api/audit/migration/{audit_id}")
async def get_audit_migration(audit_id: str):
    """Return CMS migration assessment for an audit."""
    assessment = await get_migration_assessment(audit_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="No migration assessment for this audit (may be a Webflow site)")
    return assessment


# --- Knowledge Base Export (Sprint 5A) ---

@app.post("/api/audit/knowledge-base/{audit_id}")
async def export_knowledge_base(audit_id: str):
    """Generate RAG-ready knowledge base from a premium audit.
    Returns a JSON Lines file for vector DB ingestion."""
    # Fetch the audit report from history
    from db_router import get_page_content_for_audit as get_pages
    pages = await get_pages(audit_id)

    # Get the report from the audits table
    migration = await get_migration_assessment(audit_id)

    # We need the full report — fetch from audit history
    import db_postgres as db_pg
    if os.environ.get("DATABASE_URL"):
        pool = await db_pg.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT url, report_json FROM audits WHERE id = $1",
                __import__("uuid").UUID(audit_id),
            )
        if not row:
            raise HTTPException(status_code=404, detail="Audit not found")
        report = json.loads(row["report_json"]) if isinstance(row["report_json"], str) else row["report_json"]
        site_url = row["url"]
    else:
        raise HTTPException(status_code=501, detail="Knowledge base export requires PostgreSQL")

    webflow_fixes = report.get("webflow_fixes")

    docs = generate_knowledge_base(
        audit_id=audit_id,
        site_url=site_url,
        report=report,
        pages=pages if pages else None,
        webflow_fixes=webflow_fixes,
        migration=migration,
    )

    jsonl_bytes = export_jsonl_bytes(docs)
    safe_url = site_url.replace("https://", "").replace("http://", "").replace("/", "_").strip("_")
    filename = f"WAIO_KB_{safe_url}_{audit_id[:8]}.jsonl"

    return Response(
        content=jsonl_bytes,
        media_type="application/jsonlines",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Cross-Audit Intelligence (Sprint 5B) ---

@app.get("/api/intelligence/summary")
async def get_intelligence_summary():
    """Comprehensive cross-audit intelligence summary."""
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=501, detail="Intelligence queries require PostgreSQL")
    return await cross_audit_queries.get_intelligence_summary()


@app.get("/api/intelligence/benchmarks/pillars")
async def get_pillar_benchmarks(tier: str | None = None):
    """Average scores by pillar across all audits."""
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=501, detail="Intelligence queries require PostgreSQL")
    return {"benchmarks": await cross_audit_queries.get_average_scores_by_pillar(tier)}


@app.get("/api/intelligence/benchmarks/cms")
async def get_cms_benchmarks():
    """Average scores grouped by detected CMS platform."""
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=501, detail="Intelligence queries require PostgreSQL")
    return {"benchmarks": await cross_audit_queries.get_scores_by_cms()}


@app.get("/api/intelligence/benchmarks/industry")
async def get_industry_benchmarks():
    """Average scores grouped by NLP-detected industry."""
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=501, detail="Intelligence queries require PostgreSQL")
    return {"benchmarks": await cross_audit_queries.get_scores_by_industry()}


@app.get("/api/intelligence/benchmarks/industry/{industry:path}")
async def get_industry_detail(industry: str):
    """Detailed pillar benchmarks for a specific industry."""
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=501, detail="Intelligence queries require PostgreSQL")
    return await cross_audit_queries.get_industry_pillar_benchmarks(industry)


@app.get("/api/intelligence/findings")
async def get_common_findings(cms: str | None = None, limit: int = 20):
    """Most common findings, optionally filtered by CMS."""
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=501, detail="Intelligence queries require PostgreSQL")
    return {"findings": await cross_audit_queries.get_common_findings(cms, min(limit, 100))}


@app.get("/api/intelligence/severity")
async def get_severity_by_cms():
    """Finding severity distribution grouped by CMS."""
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=501, detail="Intelligence queries require PostgreSQL")
    return {"distribution": await cross_audit_queries.get_severity_distribution_by_cms()}


@app.get("/api/intelligence/trend")
async def get_score_trend(url: str):
    """Score history for a URL across all audits."""
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=501, detail="Intelligence queries require PostgreSQL")
    return {"url": url, "trend": await cross_audit_queries.get_score_trend(url)}


# --- Export ---

@app.post("/api/export/pdf")
async def export_pdf(request: ExportRequest):
    """Generate and return a PDF of the audit report."""
    try:
        pdf_bytes = generate_pdf(request.report)
        url = request.report.get("url") or request.report.get("primary_url") or "report"
        safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_").strip("_")
        filename = f"WAIO_Audit_{safe_url}.pdf"
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"PDF export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@app.get("/api/audit/{audit_id}/export/pdf")
async def export_branded_pdf(audit_id: str):
    """Generate a branded premium 10-section PDF for an audit, fetched by ID.

    Goes through get_audit_report() so the lazy TIPR / cluster compute fires
    before rendering — guarantees the PDF and dashboard show the same data.
    """
    try:
        report = await get_audit_report(audit_id)
        if not report:
            raise HTTPException(status_code=404, detail="Audit not found")
        report["audit_id"] = str(audit_id)

        pdf_bytes = generate_branded_pdf(report)

        url = report.get("url") or "report"
        safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_").strip("_")
        filename = f"WAIO-Intelligence-Report-{safe_url}.pdf"
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Branded PDF export failed for {audit_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

@app.post("/api/export/md")
async def export_md(request: ExportRequest):
    """Generate and return a Markdown file of the audit report."""
    try:
        md_content = generate_markdown(request.report)
        url = request.report.get("url") or request.report.get("primary_url") or "report"
        safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_").strip("_")
        filename = f"WAIO_Audit_{safe_url}.md"
        return Response(
            content=md_content.encode("utf-8"),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"Markdown export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Markdown generation failed: {str(e)}")

@app.post("/api/send-report")
async def send_report(request: SendReportRequest):
    """Generate PDF and send it via email."""
    try:
        pdf_bytes = generate_pdf(request.report)
        result = send_report_email(request.email, request.report, pdf_bytes)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send report failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send report: {str(e)}")

@app.get("/api/export/link-data/{audit_id}")
async def export_link_data(audit_id: str, format: str = "xlsx"):
    """Export link intelligence data as Excel or CSV ZIP."""
    audit = await get_audit_by_id(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    report = audit.get("report_json") or {}
    if not report.get("link_analysis", {}).get("graph", {}).get("nodes"):
        raise HTTPException(status_code=404, detail="No link graph data available for this audit")

    url = report.get("url", "report")
    safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_").strip("_")

    if format == "csv":
        data = generate_link_data_csv_zip(report)
        return Response(
            content=data,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="WAIO-Link-Data-{safe_url}.zip"'},
        )
    else:
        data = generate_link_data_excel(report)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="WAIO-Link-Data-{safe_url}.xlsx"'},
        )


# --- AI Visibility Endpoints (Phase 1) ---

@app.get("/api/audit/{audit_id}/ai-visibility/brand-preview")
async def ai_visibility_brand_preview(audit_id: str):
    """Pre-flight for AI Visibility: returns auto-extracted brand, industry, competitors."""
    audit = await get_audit_by_id(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    report = audit.get("report_json") or {}
    nlp_data = report.get("nlp_analysis") or {}

    if not nlp_data:
        raise HTTPException(
            status_code=409,
            detail="NLP enrichment not yet complete — AI Visibility requires brand extraction",
        )

    entities = nlp_data.get("entities") or []

    # Try to auto-extract brand
    auto_extracted = None
    auto_salience = None
    try:
        brand_info = resolve_brand(brand_override=None, nlp_entities=entities)
        auto_extracted = brand_info.name
        auto_salience = brand_info.salience
    except BrandExtractionError:
        pass

    # Check for existing override
    existing_viz = report.get("ai_visibility") or {}
    override = existing_viz.get("brand_name") if existing_viz.get("brand_name_source") == "override" else None

    # Competitor preview
    competitor_urls = report.get("competitor_urls") or []
    competitive_data = report.get("competitive_data")
    user_provided = []
    auto_detected = []
    if competitor_urls:
        from ai_visibility.competitor_resolver import normalize_domain
        user_provided = [normalize_domain(u) for u in competitor_urls if normalize_domain(u)]
    elif competitive_data and competitive_data.get("rankings"):
        from ai_visibility.competitor_resolver import normalize_domain
        auto_detected = [
            normalize_domain(r.get("url", ""))
            for r in competitive_data["rankings"]
            if normalize_domain(r.get("url", ""))
        ]

    return {
        "auto_extracted": auto_extracted,
        "auto_extracted_salience": round(auto_salience, 4) if auto_salience else None,
        "override": override,
        "detected_industry": nlp_data.get("detected_industry"),
        "top_nlp_entity": nlp_data.get("primary_entity"),
        "competitors_preview": {
            "user_provided": user_provided,
            "auto_detected": auto_detected,
            "tier_3_fallback_available": True,
        },
        "cumulative_cost_usd": existing_viz.get("cumulative_cost_usd", 0),
        "run_count": existing_viz.get("run_count", 0),
    }


@app.post("/api/audit/{audit_id}/recompute-ai-visibility", status_code=202)
async def recompute_ai_visibility(audit_id: str, body: dict = Body(...)):
    """Kick off AI Visibility analysis as a background task."""
    audit = await get_audit_by_id(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    # Check DataForSEO credentials
    if not is_dataforseo_configured():
        raise HTTPException(
            status_code=503,
            detail="DataForSEO credentials not configured",
        )

    report = audit.get("report_json") or {}
    existing_viz = report.get("ai_visibility") or {}

    # Prevent concurrent runs
    if existing_viz.get("last_computed_status") == "running":
        raise HTTPException(
            status_code=409,
            detail="AI Visibility analysis is already running",
        )

    # Budget cap check
    monthly_cap = float(os.environ.get("AI_VISIBILITY_MONTHLY_CAP_USD", "100.0"))
    try:
        from db_postgres import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT COALESCE(SUM(ai_visibility_cumulative_cost_usd), 0) as total
                   FROM audits WHERE last_ai_visibility_run_at >= date_trunc('month', now())"""
            )
            month_spend = float(row["total"]) if row else 0.0
    except Exception:
        month_spend = 0.0

    estimated_cost = 2.00
    if month_spend + estimated_cost + 1.0 > monthly_cap:
        raise HTTPException(
            status_code=503,
            detail="AI Visibility monthly budget cap reached. Try again next month or contact admin.",
        )

    brand_name = body.get("brand_name", "").strip() if body.get("brand_name") else None

    # Write running state immediately so poller sees it
    from datetime import datetime as dt, timezone as tz
    started_at = dt.now(tz.utc).isoformat()
    await update_audit_report(audit_id, {
        "ai_visibility": {
            **existing_viz,
            "last_computed_status": "running",
            "started_at": started_at,
        }
    })

    # Save brand override if provided
    if brand_name:
        try:
            from db_postgres import get_pool
            pool = await get_pool()
            aid = uuid.UUID(str(audit_id)) if not isinstance(audit_id, uuid.UUID) else audit_id
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE audits SET brand_name_override = $1 WHERE id = $2",
                    brand_name, aid,
                )
        except Exception as e:
            logger.warning(f"Failed to save brand_name_override: {e}")

    # Fire background task
    asyncio.create_task(
        run_ai_visibility_analysis(audit_id, brand_override=brand_name)
    )

    return {
        "status": "running",
        "started_at": started_at,
        "estimated_duration_seconds": 150,
        "previous_cost_usd": existing_viz.get("cumulative_cost_usd", 0),
        "estimated_this_run_usd": estimated_cost,
    }


@app.get("/api/audit/{audit_id}/ai-visibility")
async def get_ai_visibility(audit_id: str):
    """Poll target for AI Visibility status/results."""
    audit = await get_audit_by_id(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    report = audit.get("report_json") or {}
    viz = report.get("ai_visibility")

    if not viz:
        return {"status": "not_computed"}

    status = viz.get("last_computed_status", "not_computed")
    if status == "running":
        return {
            "status": "running",
            "started_at": viz.get("started_at"),
        }

    # Complete (ok, partial, or failed)
    return {"status": status, **viz}


# --- Content Optimizer Endpoints ---

@app.post("/api/audit/{audit_id}/content-optimizer/run", status_code=202)
async def run_content_optimizer(audit_id: str, body: dict = Body(...)):
    """Kick off WDF*IDF content optimization as a background task.

    Body: {"url": "https://...", "keyword": "target keyword"}
    """
    audit = await get_audit_by_id(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    target_url = (body.get("url") or "").strip()
    keyword = (body.get("keyword") or "").strip()
    if not target_url or not keyword:
        raise HTTPException(status_code=400, detail="Both 'url' and 'keyword' are required")

    # Check SerpApi key
    if not os.environ.get("SERPAPI_KEY"):
        raise HTTPException(status_code=503, detail="SERPAPI_KEY not configured")

    # Try to get target text from existing crawl data
    report = audit.get("report_json") or {}
    target_text = ""

    # Check page_content DB
    pages = await get_page_content_for_audit(audit_id)
    for p in (pages or []):
        if p.get("url") == target_url and p.get("clean_text"):
            target_text = p["clean_text"]
            break

    # If not in DB, extract live via Trafilatura
    if not target_text:
        try:
            from content_optimizer.content_extractor import extract_content_from_urls
            extractions = await extract_content_from_urls([target_url], min_words=30)
            if extractions and extractions[0]["success"]:
                target_text = extractions[0]["text"]
        except Exception as e:
            logger.warning(f"Content optimizer: failed to extract target URL: {e}")

    if not target_text or len(target_text.split()) < 30:
        raise HTTPException(
            status_code=400,
            detail="Could not extract enough content from the target URL (minimum 30 words)",
        )

    # Get NLP entities for better term classification
    top_entities = None
    nlp_data = report.get("nlp_analysis") or {}
    entities = nlp_data.get("entities") or []
    if entities:
        top_entities = [e["name"] for e in entities[:20] if isinstance(e, dict) and e.get("name")]

    # Write running state
    from datetime import datetime, timezone
    from content_optimizer import analysis_key
    key = analysis_key(target_url, keyword)
    co = report.get("content_optimizer") or {}
    analyses = co.get("analyses") or {}

    # Prevent concurrent runs for same URL+keyword
    existing = analyses.get(key) or {}
    if existing.get("status") == "running":
        raise HTTPException(status_code=409, detail="Analysis already running for this URL+keyword")

    analyses[key] = {
        "url": target_url,
        "keyword": keyword,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
    }
    await update_audit_report(audit_id, {"content_optimizer": {"analyses": analyses}})

    # Fire background task
    from content_optimizer import run_content_optimization
    asyncio.create_task(
        run_content_optimization(
            audit_id=audit_id,
            target_url=target_url,
            target_text=target_text,
            keyword=keyword,
            top_entities=top_entities,
        )
    )

    return {"status": "running", "key": key}


@app.get("/api/audit/{audit_id}/content-optimizer")
async def get_content_optimizer_result(audit_id: str, url: str = "", keyword: str = ""):
    """Get content optimizer results for a specific URL+keyword, or a specific key."""
    audit = await get_audit_by_id(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    report = audit.get("report_json") or {}
    co = report.get("content_optimizer") or {}
    analyses = co.get("analyses") or {}

    if not analyses:
        return {"status": "not_computed"}

    # If url+keyword provided, find by key
    if url and keyword:
        from content_optimizer import analysis_key
        key = analysis_key(url.strip(), keyword.strip())
        entry = analyses.get(key)
        if not entry:
            return {"status": "not_computed"}
        return entry

    # If only url provided, return most recent analysis for that URL
    if url:
        url_analyses = [
            v for v in analyses.values()
            if isinstance(v, dict) and v.get("url") == url.strip()
        ]
        if not url_analyses:
            return {"status": "not_computed"}
        latest = max(url_analyses, key=lambda a: a.get("analyzed_at", ""))
        return latest

    # No filter — return most recent analysis
    all_entries = [v for v in analyses.values() if isinstance(v, dict)]
    if not all_entries:
        return {"status": "not_computed"}
    latest = max(all_entries, key=lambda a: a.get("analyzed_at", ""))
    return latest


@app.get("/api/audit/{audit_id}/content-optimizer/pages")
async def list_content_optimizer_pages(audit_id: str):
    """List all pages that have been analyzed with Content Optimizer."""
    audit = await get_audit_by_id(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    report = audit.get("report_json") or {}
    co = report.get("content_optimizer") or {}
    analyses = co.get("analyses") or {}

    pages = []
    for key, entry in analyses.items():
        if not isinstance(entry, dict):
            continue
        result = entry.get("result") or {}
        pages.append({
            "key": key,
            "url": entry.get("url", ""),
            "keyword": entry.get("keyword", ""),
            "status": entry.get("status", "unknown"),
            "analyzed_at": entry.get("analyzed_at"),
            "content_gap_score": result.get("summary", {}).get("content_gap_score"),
        })

    return {"pages": pages}


# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
    
    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                return f.read()
        return "Frontend build not found."
