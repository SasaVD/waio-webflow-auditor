import logging
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import os
import asyncio
import base64

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
from pdf_generator import generate_pdf
from md_generator import generate_markdown
from email_sender import send_report_email
from db import (init_db, create_job, get_job_status, get_single_page_audit,
                save_audit_history, get_audit_history,
                create_schedule, get_schedules, update_schedule, delete_schedule)
from site_crawler import run_site_crawl
from scheduler import scheduler_loop
from competitive_auditor import run_competitive_audit
import uuid

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

class AuditRequest(BaseModel):
    url: HttpUrl

class MultiAuditRequest(BaseModel):
    url: HttpUrl
    max_pages: int = 5

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

@app.on_event("startup")
async def startup_event():
    await init_db()
    asyncio.create_task(scheduler_loop())

@app.on_event("shutdown")
async def shutdown_event():
    await close_browser()

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/audit")
async def perform_audit(request: AuditRequest):
    url = str(request.url)
    logger.info(f"Starting audit for {url}")
    try:
        html_content, soup = await fetch_page(url)
        
        # Run audits in parallel where possible
        # crawler.fetch_page guarantees we have html_content
        # Accessibility is async via playwright
        
        # CPU-bound synchronous audits via to_thread or just run directly
        # It's fast enough to run sequentially for now.
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
        report = generate_report(url, html_res, sd_res, aeo_res, css_js_res, a11y_res, rag_res, agent_res, data_res, scores, il_res)
        
        # Auto-save to audit history
        await save_audit_history(url, "single", report.get("overall_score", 0), report.get("overall_label", "N/A"), report)
        
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
        await save_audit_history(primary, "competitive", p.get("overall_score", 0), p.get("overall_label", "N/A"), result)
        
        return result
    except Exception as e:
        logger.error(f"Competitive audit failed: {e}")
        raise HTTPException(status_code=500, detail=f"Competitive audit failed: {str(e)}")

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
