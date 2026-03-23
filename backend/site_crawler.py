import asyncio
import logging
from bs4 import BeautifulSoup
from typing import Set, List, Dict, Any
from urllib.parse import urlparse, urljoin

from crawler import fetch_page
from db import update_job_progress, save_page_audit

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

logger = logging.getLogger(__name__)

async def process_page_audit(url: str, html_content: str, soup: BeautifulSoup) -> dict:
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
    
    return {
        "url": url,
        "scores": scores,
        "html_res": html_res,
        "sd_res": sd_res,
        "css_js_res": css_js_res,
        "aeo_res": aeo_res,
        "rag_res": rag_res,
        "agent_res": agent_res,
        "data_res": data_res,
        "il_res": il_res,
        "a11y_res": a11y_res
    }

def get_internal_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    links = []
    base_parse = urlparse(base_url)
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
            continue
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        if parsed.netloc == base_parse.netloc:
            normalized = parsed._replace(fragment='').geturl()
            links.append(normalized)
    return list(set(links))

async def run_site_crawl(job_id: str, start_url: str, max_pages: int = 5):
    queue = asyncio.Queue()
    await queue.put(start_url)
    visited: Set[str] = set([start_url])
    completed_audits = []

    logger.info(f"Starting site crawl for {job_id} at {start_url} (max {max_pages})")
    
    while not queue.empty() and len(completed_audits) < max_pages:
        current_url = await queue.get()
        logger.info(f"Crawling {current_url} for job {job_id}")
        
        try:
            html_content, soup = await fetch_page(current_url)
            audit_res = await process_page_audit(current_url, html_content, soup)
            
            await save_page_audit(job_id, current_url, "completed", audit_res)
            completed_audits.append(audit_res)
            
            if len(completed_audits) < max_pages:
                links = get_internal_links(soup, start_url)
                for link in links:
                    if link not in visited and len(visited) < max_pages * 2:
                        visited.add(link)
                        await queue.put(link)
                        
        except Exception as e:
            logger.error(f"Failed crawling {current_url}: {e}")
            await save_page_audit(job_id, current_url, "failed", {"error": str(e)})
            
        await update_job_progress(job_id, total=min(len(visited), max_pages), completed=len(completed_audits))
        queue.task_done()
        
    logger.info(f"Site crawl {job_id} completed with {len(completed_audits)} pages.")
    
    from report_generator import generate_site_report
    final_report = generate_site_report(start_url, completed_audits, job_id)
    await update_job_progress(job_id, status="completed", total=len(completed_audits), completed=len(completed_audits), final_report=final_report)
