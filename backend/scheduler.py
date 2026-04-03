import asyncio
import logging
from db_router import get_due_schedules, mark_schedule_run, save_audit_history, get_latest_history_score
from email_sender import send_regression_alert

logger = logging.getLogger(__name__)

REGRESSION_THRESHOLD = 5  # Score drop threshold to trigger alert

async def run_scheduled_audit(schedule: dict):
    """Execute a single scheduled audit (single or multi-page)."""
    url = schedule["url"]
    email = schedule["email"]
    max_pages = schedule.get("max_pages", 1)
    schedule_id = schedule["id"]
    frequency = schedule["frequency"]

    logger.info(f"Running scheduled audit for {url} (max_pages={max_pages})")

    try:
        old_score = await get_latest_history_score(url)

        if max_pages > 1:
            # Multi-page audit
            from site_crawler import run_site_crawl
            import uuid
            from db_router import create_job, get_job_status
            job_id = str(uuid.uuid4())
            await create_job(job_id)
            await run_site_crawl(job_id, url, max_pages)
            job_data = await get_job_status(job_id)
            if job_data and job_data.get("final_report"):
                report = job_data["final_report"]
                new_score = report.get("overall_score", 0)
                new_label = report.get("overall_label", "N/A")
                await save_audit_history(url, "site", new_score, new_label, report)
            else:
                logger.error(f"Scheduled site audit for {url} produced no report")
                return
        else:
            # Single-page audit
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

            scores = compile_scores(html_res, sd_res, aeo_res, css_js_res, a11y_res, rag_res, agent_res, data_res, il_res)
            report = generate_report(url, html_res, sd_res, aeo_res, css_js_res, a11y_res, rag_res, agent_res, data_res, scores, il_res)

            new_score = report.get("overall_score", 0)
            new_label = report.get("overall_label", "N/A")
            await save_audit_history(url, "single", new_score, new_label, report)

        # Check for regression
        if old_score is not None and new_score < old_score - REGRESSION_THRESHOLD:
            diff = old_score - new_score
            logger.warning(f"Regression detected for {url}: {old_score} -> {new_score} (diff={diff})")
            if email:
                send_regression_alert(email, url, old_score, new_score, diff)

        await mark_schedule_run(schedule_id, frequency)
        logger.info(f"Scheduled audit complete for {url}: score={new_score}")

    except Exception as e:
        logger.error(f"Scheduled audit failed for {url}: {e}")


async def scheduler_loop():
    """Background loop that checks for and runs due scheduled audits every 60 seconds."""
    logger.info("Scheduler loop started")
    while True:
        try:
            due = await get_due_schedules()
            if due:
                logger.info(f"Found {len(due)} due scheduled audit(s)")
            for schedule in due:
                await run_scheduled_audit(schedule)
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        await asyncio.sleep(60)
