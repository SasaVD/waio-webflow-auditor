"""
PostgreSQL database layer for WAIO Audit Tool.
Mirrors the interface of db.py (SQLite) but uses asyncpg.
Also adds normalized storage for pillar scores and findings (Sprint 1C).
"""
import asyncpg
import json
import os
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        database_url = os.environ["DATABASE_URL"]
        _pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
    return _pool


async def init_db():
    """Run all migration SQL files in sorted order to create/update tables."""
    pool = await get_pool()
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    migration_files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))
    async with pool.acquire() as conn:
        for filename in migration_files:
            filepath = os.path.join(migrations_dir, filename)
            with open(filepath, "r") as f:
                sql = f.read()
            await conn.execute(sql)


async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# --- Jobs ---

async def create_job(job_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO jobs (job_id, status, total_urls, completed_urls) VALUES ($1, $2, $3, $4)",
            job_id, "running", 1, 0
        )


async def update_job_progress(
    job_id: str,
    status: Optional[str] = None,
    total: Optional[int] = None,
    completed: Optional[int] = None,
    final_report: Optional[dict] = None,
):
    pool = await get_pool()
    sets: List[str] = []
    vals: List[Any] = []
    idx = 1

    if status is not None:
        sets.append(f"status = ${idx}")
        vals.append(status)
        idx += 1
    if total is not None:
        sets.append(f"total_urls = ${idx}")
        vals.append(total)
        idx += 1
    if completed is not None:
        sets.append(f"completed_urls = ${idx}")
        vals.append(completed)
        idx += 1
    if final_report is not None:
        sets.append(f"final_report = ${idx}")
        vals.append(json.dumps(final_report))
        idx += 1

    if not sets:
        return

    sets.append(f"job_id = job_id")  # no-op to keep query valid
    query = f"UPDATE jobs SET {', '.join(sets)} WHERE job_id = ${idx}"
    vals.append(job_id)

    async with pool.acquire() as conn:
        await conn.execute(query, *vals)


async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status, total_urls, completed_urls, final_report FROM jobs WHERE job_id = $1",
            job_id,
        )
    if not row:
        return None
    fr = row["final_report"]
    return {
        "status": row["status"],
        "total_urls": row["total_urls"],
        "completed_urls": row["completed_urls"],
        "final_report": json.loads(fr) if isinstance(fr, str) else fr,
    }


# --- Page Audits ---

async def save_page_audit(job_id: str, url: str, status: str, results: dict):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO page_audits (job_id, url, status, results_json)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (job_id, url) DO UPDATE SET status = $3, results_json = $4""",
            job_id, url, status, json.dumps(results),
        )


async def get_page_audits(job_id: str) -> List[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT url, status, results_json FROM page_audits WHERE job_id = $1",
            job_id,
        )
    audits = []
    for row in rows:
        rj = row["results_json"]
        audits.append({
            "url": row["url"],
            "status": row["status"],
            "results": json.loads(rj) if isinstance(rj, str) else rj,
        })
    return audits


async def get_single_page_audit(job_id: str, url: str) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT results_json FROM page_audits WHERE job_id = $1 AND url = $2",
            job_id, url,
        )
    if row and row["results_json"]:
        rj = row["results_json"]
        return json.loads(rj) if isinstance(rj, str) else rj
    return None


# --- Audit History ---

async def save_audit_history(
    url: str,
    audit_type: str,
    overall_score: int,
    overall_label: str,
    report: dict,
    tier: str = "free",
    audit_id: Optional[uuid.UUID] = None,
):
    pool = await get_pool()
    if audit_id is None:
        audit_id = uuid.uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO audits (id, url, tier, audit_type, overall_score, overall_label, report_json, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            audit_id,
            url,
            tier,
            audit_type,
            overall_score,
            overall_label,
            json.dumps(report),
            datetime.now(timezone.utc),
        )
        # Sprint 1C: decompose into normalized tables
        await _save_normalized_data(conn, audit_id, report)
    return audit_id


async def _save_normalized_data(conn, audit_id: uuid.UUID, report: dict):
    """Decompose report JSON into pillar_scores and findings tables."""
    categories = report.get("categories", {})
    for pillar_key, pillar_data in categories.items():
        score = pillar_data.get("score", 0)
        label = pillar_data.get("label", "N/A")
        pillar_findings = pillar_data.get("findings", [])
        finding_count = len(pillar_findings)

        await conn.execute(
            """INSERT INTO pillar_scores (audit_id, pillar_key, score, label, finding_count)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (audit_id, pillar_key) DO UPDATE
               SET score = $3, label = $4, finding_count = $5""",
            audit_id, pillar_key, score, label, finding_count,
        )

        for finding in pillar_findings:
            await conn.execute(
                """INSERT INTO findings
                   (audit_id, pillar_key, check_name, severity, description, recommendation, reference, credibility_anchor)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                audit_id,
                pillar_key,
                finding.get("check", "unknown"),
                finding.get("severity", "medium"),
                finding.get("description", ""),
                finding.get("recommendation", ""),
                finding.get("reference", ""),
                finding.get("credibility_anchor", finding.get("why_it_matters", "")),
            )


async def get_audit_history(url: str) -> List[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, url, audit_type, overall_score, overall_label, created_at
               FROM audits WHERE url = $1 ORDER BY created_at DESC""",
            url,
        )
    return [
        {
            "id": str(row["id"]),
            "url": row["url"],
            "audit_type": row["audit_type"],
            "overall_score": row["overall_score"],
            "overall_label": row["overall_label"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


async def get_latest_history_score(url: str) -> Optional[int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT overall_score FROM audits WHERE url = $1 ORDER BY created_at DESC LIMIT 1",
            url,
        )
    return row["overall_score"] if row else None


async def get_audit_by_id(audit_id) -> Optional[Dict[str, Any]]:
    """Retrieve a full audit (including report_json) by its UUID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, url, tier, audit_type, overall_score, overall_label,
                      report_json, created_at, detected_cms
               FROM audits WHERE id = $1""",
            audit_id if isinstance(audit_id, uuid.UUID) else uuid.UUID(str(audit_id)),
        )
    if not row:
        return None
    report = row["report_json"]
    if isinstance(report, str):
        report = json.loads(report)
    return {
        "id": str(row["id"]),
        "url": row["url"],
        "tier": row["tier"],
        "audit_type": row["audit_type"],
        "overall_score": row["overall_score"],
        "overall_label": row["overall_label"],
        "report_json": report,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "detected_cms": row["detected_cms"],
    }


async def list_all_audits(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """List all audits (admin view) ordered by most recent first."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, url, tier, audit_type, overall_score, overall_label,
                      created_at, detected_cms
               FROM audits ORDER BY created_at DESC LIMIT $1 OFFSET $2""",
            limit, offset,
        )
    return [
        {
            "id": str(row["id"]),
            "url": row["url"],
            "tier": row["tier"],
            "audit_type": row["audit_type"],
            "overall_score": row["overall_score"],
            "overall_label": row["overall_label"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "detected_cms": row["detected_cms"],
        }
        for row in rows
    ]


# --- Scheduled Audits ---

async def create_schedule(url: str, email: str, frequency: str, max_pages: int) -> int:
    pool = await get_pool()
    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO scheduled_audits (url, email, frequency, max_pages, next_run, enabled)
               VALUES ($1, $2, $3, $4, $5, TRUE) RETURNING id""",
            url, email, frequency, max_pages, now,
        )
    return row["id"]


async def get_schedules() -> List[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, url, email, frequency, max_pages, last_run, next_run, enabled FROM scheduled_audits ORDER BY id"
        )
    return [
        {
            "id": row["id"],
            "url": row["url"],
            "email": row["email"],
            "frequency": row["frequency"],
            "max_pages": row["max_pages"],
            "last_run": row["last_run"].isoformat() if row["last_run"] else None,
            "next_run": row["next_run"].isoformat() if row["next_run"] else None,
            "enabled": row["enabled"],
        }
        for row in rows
    ]


async def update_schedule(
    schedule_id: int,
    enabled: Optional[bool] = None,
    frequency: Optional[str] = None,
    email: Optional[str] = None,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if enabled is not None:
            await conn.execute(
                "UPDATE scheduled_audits SET enabled = $1 WHERE id = $2", enabled, schedule_id
            )
        if frequency is not None:
            await conn.execute(
                "UPDATE scheduled_audits SET frequency = $1 WHERE id = $2", frequency, schedule_id
            )
        if email is not None:
            await conn.execute(
                "UPDATE scheduled_audits SET email = $1 WHERE id = $2", email, schedule_id
            )


async def delete_schedule(schedule_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM scheduled_audits WHERE id = $1", schedule_id)


async def get_due_schedules() -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, url, email, frequency, max_pages FROM scheduled_audits
               WHERE enabled = TRUE AND (next_run IS NULL OR next_run <= $1)""",
            now,
        )
    return [
        {"id": row["id"], "url": row["url"], "email": row["email"], "frequency": row["frequency"], "max_pages": row["max_pages"]}
        for row in rows
    ]


async def mark_schedule_run(schedule_id: int, frequency: str):
    now = datetime.now(timezone.utc)
    deltas = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1), "monthly": timedelta(days=30)}
    next_run = now + deltas.get(frequency, timedelta(weeks=1))
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE scheduled_audits SET last_run = $1, next_run = $2 WHERE id = $3",
            now, next_run, schedule_id,
        )


# --- DataForSEO Task Tracking (Sprint 3A) ---

async def save_dataforseo_task(
    task_id: str,
    audit_id: uuid.UUID,
    target_url: str,
    max_crawl_pages: int,
):
    """Record a submitted DataForSEO crawl task."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO dataforseo_tasks
               (task_id, audit_id, target_url, status, max_crawl_pages, created_at)
               VALUES ($1, $2, $3, 'crawling', $4, $5)
               ON CONFLICT (task_id) DO UPDATE
               SET audit_id = $2, status = 'crawling'""",
            task_id,
            audit_id,
            target_url,
            max_crawl_pages,
            datetime.now(timezone.utc),
        )
        # Also store task_id on the audit record
        await conn.execute(
            "UPDATE audits SET dataforseo_task_id = $1 WHERE id = $2",
            task_id,
            audit_id,
        )


async def update_dataforseo_task(
    task_id: str,
    status: str,
    summary: Optional[dict] = None,
):
    """Update a DataForSEO task after crawl completes or fails."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if summary:
            await conn.execute(
                """UPDATE dataforseo_tasks
                   SET status = $1,
                       pages_crawled = $2,
                       pages_count = $3,
                       internal_links_count = $4,
                       external_links_count = $5,
                       broken_links = $6,
                       summary_json = $7,
                       completed_at = $8
                   WHERE task_id = $9""",
                status,
                summary.get("pages_crawled", 0),
                summary.get("pages_count", 0),
                summary.get("internal_links_count", 0),
                summary.get("external_links_count", 0),
                summary.get("broken_links", 0),
                json.dumps(summary),
                datetime.now(timezone.utc),
                task_id,
            )
        else:
            await conn.execute(
                """UPDATE dataforseo_tasks SET status = $1, completed_at = $2
                   WHERE task_id = $3""",
                status,
                datetime.now(timezone.utc),
                task_id,
            )


async def get_dataforseo_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Look up a DataForSEO task by its task_id."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT task_id, audit_id, target_url, status, max_crawl_pages,
                      pages_crawled, pages_count, internal_links_count,
                      external_links_count, broken_links, summary_json,
                      created_at, completed_at
               FROM dataforseo_tasks WHERE task_id = $1""",
            task_id,
        )
    if not row:
        return None
    sj = row["summary_json"]
    return {
        "task_id": row["task_id"],
        "audit_id": str(row["audit_id"]),
        "target_url": row["target_url"],
        "status": row["status"],
        "max_crawl_pages": row["max_crawl_pages"],
        "pages_crawled": row["pages_crawled"],
        "pages_count": row["pages_count"],
        "internal_links_count": row["internal_links_count"],
        "external_links_count": row["external_links_count"],
        "broken_links": row["broken_links"],
        "summary": json.loads(sj) if isinstance(sj, str) else sj,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
    }


async def get_dataforseo_task_by_audit(audit_id_str: str) -> Optional[Dict[str, Any]]:
    """Look up a DataForSEO task by audit UUID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT task_id FROM dataforseo_tasks WHERE audit_id = $1",
            uuid.UUID(audit_id_str),
        )
    if not row:
        return None
    return await get_dataforseo_task(row["task_id"])


# --- Google OAuth Token Storage (Sprint 3B) ---

async def save_google_tokens(
    property_url: str,
    encrypted_tokens: str,
    email: str | None = None,
    ga4_property_id: str | None = None,
    scopes: str | None = None,
):
    """Store or update encrypted Google OAuth tokens for a GSC property."""
    pool = await get_pool()
    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO google_tokens
               (property_url, ga4_property_id, encrypted_tokens, email, scopes, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $6)
               ON CONFLICT (property_url) DO UPDATE
               SET encrypted_tokens = $3, ga4_property_id = $2, email = $4,
                   scopes = $5, updated_at = $6""",
            property_url,
            ga4_property_id,
            encrypted_tokens,
            email,
            scopes,
            now,
        )


async def get_google_tokens(property_url: str) -> Optional[Dict[str, Any]]:
    """Retrieve encrypted token record for a GSC property."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT property_url, ga4_property_id, encrypted_tokens, email, scopes,
                      created_at, updated_at
               FROM google_tokens WHERE property_url = $1""",
            property_url,
        )
    if not row:
        return None
    return {
        "property_url": row["property_url"],
        "ga4_property_id": row["ga4_property_id"],
        "encrypted_tokens": row["encrypted_tokens"],
        "email": row["email"],
        "scopes": row["scopes"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


async def list_google_tokens() -> List[Dict[str, Any]]:
    """List all connected Google properties (without decrypted tokens)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT property_url, ga4_property_id, email, scopes, updated_at
               FROM google_tokens ORDER BY updated_at DESC"""
        )
    return [
        {
            "property_url": row["property_url"],
            "ga4_property_id": row["ga4_property_id"],
            "email": row["email"],
            "scopes": row["scopes"],
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]


async def delete_google_tokens(property_url: str):
    """Remove stored tokens for a GSC property (disconnect)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM google_tokens WHERE property_url = $1",
            property_url,
        )


# --- Link Graph Storage (Sprint 3C) ---

async def save_link_graph_edges(
    audit_id: uuid.UUID,
    edges: List[Dict[str, Any]],
):
    """Bulk-insert link graph edges for an audit."""
    if not edges:
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO link_graph (audit_id, source_url, target_url, anchor_text, is_nofollow, link_position)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            [
                (
                    audit_id,
                    e.get("source", ""),
                    e.get("target", ""),
                    e.get("anchor", ""),
                    e.get("is_nofollow", False),
                    e.get("link_type", ""),
                )
                for e in edges
            ],
        )


async def get_link_graph_data(audit_id_str: str) -> Optional[Dict[str, Any]]:
    """Retrieve link graph nodes and edges for D3 visualization."""
    pool = await get_pool()
    aid = uuid.UUID(audit_id_str)
    async with pool.acquire() as conn:
        edges = await conn.fetch(
            """SELECT source_url, target_url, anchor_text, is_nofollow, link_position
               FROM link_graph WHERE audit_id = $1""",
            aid,
        )
        pages = await conn.fetch(
            """SELECT url, title, click_depth, is_orphan, nlp_category
               FROM page_content WHERE audit_id = $1""",
            aid,
        )
    if not edges and not pages:
        return None

    nodes = [
        {
            "id": row["url"],
            "label": row["title"] or row["url"].split("/")[-1] or "/",
            "depth": row["click_depth"],
            "is_orphan": row["is_orphan"] or False,
            "nlp_category": row["nlp_category"],
        }
        for row in pages
    ]
    links = [
        {
            "source": row["source_url"],
            "target": row["target_url"],
            "anchor": row["anchor_text"] or "",
            "is_nofollow": row["is_nofollow"] or False,
        }
        for row in edges
    ]
    return {"nodes": nodes, "links": links}


# --- Page Content with NLP (Sprint 3C/3E) ---

async def save_page_content_batch(
    audit_id: uuid.UUID,
    pages: List[Dict[str, Any]],
):
    """Bulk-insert page content records for an audit."""
    if not pages:
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO page_content
               (audit_id, url, title, h1_text, meta_description, status_code,
                click_depth, is_orphan, nlp_category, nlp_category_confidence, nlp_categories)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
               ON CONFLICT (audit_id, url) DO UPDATE
               SET title = $3, status_code = $6, click_depth = $7, is_orphan = $8,
                   nlp_category = $9, nlp_category_confidence = $10, nlp_categories = $11""",
            [
                (
                    audit_id,
                    p.get("url", ""),
                    p.get("title"),
                    p.get("h1_text"),
                    p.get("meta_description"),
                    p.get("status_code"),
                    p.get("click_depth"),
                    p.get("is_orphan", False),
                    p.get("nlp_category"),
                    p.get("nlp_category_confidence"),
                    json.dumps(p.get("nlp_categories")) if p.get("nlp_categories") else None,
                )
                for p in pages
            ],
        )


# --- CMS Detection Storage (Sprint 3F) ---

async def save_cms_detection(
    audit_id: uuid.UUID,
    platform: str,
    version: str | None,
    confidence: float,
    detection_method: str,
    technologies: List[str],
):
    """Store CMS detection result on the audit record."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE audits
               SET detected_cms = $1, cms_version = $2, cms_confidence = $3,
                   cms_detection_method = $4, detected_technologies = $5
               WHERE id = $6""",
            platform,
            version,
            confidence,
            detection_method,
            technologies,
            audit_id,
        )


async def save_industry_detection(
    audit_id: uuid.UUID,
    industry: str | None,
    confidence: float,
    categories: List[Dict[str, Any]],
):
    """Store NLP industry detection result on the audit record."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE audits
               SET detected_industry = $1, detected_industry_confidence = $2,
                   industry_categories = $3
               WHERE id = $4""",
            industry,
            confidence,
            json.dumps(categories),
            audit_id,
        )


# --- Sprint 4: Content extraction, NLP entities, migration ---


async def update_page_content_text(
    audit_id: uuid.UUID,
    url: str,
    clean_text: str | None,
    word_count: int | None = None,
    language: str | None = None,
    extraction_method: str | None = None,
):
    """Update page content with extracted clean text (Sprint 4A)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE page_content
               SET clean_text = $1, word_count = $2, language = $3, extraction_method = $4
               WHERE audit_id = $5 AND url = $6""",
            clean_text, word_count, language, extraction_method, audit_id, url,
        )


async def update_page_nlp_entities(
    audit_id: uuid.UUID,
    url: str,
    entities_json: str | None,
    primary_entity: str | None,
    primary_entity_salience: float | None,
    entity_focus_aligned: bool | None,
):
    """Store NLP entity analysis results for a page (Sprint 4D)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE page_content
               SET nlp_entities = $1, nlp_primary_entity = $2,
                   nlp_primary_entity_salience = $3, nlp_entity_focus_aligned = $4
               WHERE audit_id = $5 AND url = $6""",
            entities_json, primary_entity, primary_entity_salience,
            entity_focus_aligned, audit_id, url,
        )


async def update_page_nlp_sentiment(
    audit_id: uuid.UUID,
    url: str,
    sentiment_score: float | None,
    sentiment_magnitude: float | None,
    entity_sentiments_json: str | None,
):
    """Store NLP sentiment results for a page (Sprint 4D)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE page_content
               SET nlp_sentiment_score = $1, nlp_sentiment_magnitude = $2,
                   nlp_entity_sentiments = $3
               WHERE audit_id = $4 AND url = $5""",
            sentiment_score, sentiment_magnitude, entity_sentiments_json,
            audit_id, url,
        )


async def get_page_content_for_audit(
    audit_id_str: str,
) -> List[Dict[str, Any]]:
    """Retrieve all page content records for an audit (for NLP/content analysis)."""
    pool = await get_pool()
    aid = uuid.UUID(audit_id_str)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT url, title, h1_text, meta_description, clean_text, word_count,
                      language, extraction_method, status_code, click_depth, is_orphan,
                      nlp_category, nlp_category_confidence,
                      nlp_primary_entity, nlp_primary_entity_salience, nlp_entity_focus_aligned,
                      nlp_sentiment_score, nlp_sentiment_magnitude
               FROM page_content WHERE audit_id = $1
               ORDER BY click_depth ASC NULLS LAST""",
            aid,
        )
    return [
        {
            "url": row["url"],
            "title": row["title"],
            "h1_text": row["h1_text"],
            "meta_description": row["meta_description"],
            "clean_text": row["clean_text"],
            "word_count": row["word_count"],
            "language": row["language"],
            "extraction_method": row["extraction_method"],
            "status_code": row["status_code"],
            "click_depth": row["click_depth"],
            "is_orphan": row["is_orphan"],
            "nlp_category": row["nlp_category"],
            "nlp_category_confidence": row["nlp_category_confidence"],
            "nlp_primary_entity": row["nlp_primary_entity"],
            "nlp_primary_entity_salience": row["nlp_primary_entity_salience"],
            "nlp_entity_focus_aligned": row["nlp_entity_focus_aligned"],
            "nlp_sentiment_score": row["nlp_sentiment_score"],
            "nlp_sentiment_magnitude": row["nlp_sentiment_magnitude"],
        }
        for row in rows
    ]


async def save_migration_assessment(
    audit_id: uuid.UUID,
    assessment_json: str,
):
    """Store CMS migration assessment on the audit record (Sprint 4E)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE audits SET migration_assessment = $1 WHERE id = $2",
            assessment_json, audit_id,
        )


async def get_migration_assessment(
    audit_id_str: str,
) -> Optional[Dict[str, Any]]:
    """Retrieve migration assessment for an audit."""
    pool = await get_pool()
    aid = uuid.UUID(audit_id_str)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT migration_assessment FROM audits WHERE id = $1", aid,
        )
    if not row or not row["migration_assessment"]:
        return None
    ma = row["migration_assessment"]
    return json.loads(ma) if isinstance(ma, str) else ma


# --- User Authentication (Sprint Auth) ---


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, name, role, auth_provider, google_id, avatar_url, is_active, created_at, last_login FROM users WHERE email = $1",
            email,
        )
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "password_hash": row["password_hash"],
        "name": row["name"],
        "role": row["role"],
        "auth_provider": row["auth_provider"],
        "google_id": row["google_id"],
        "avatar_url": row["avatar_url"],
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "last_login": row["last_login"].isoformat() if row["last_login"] else None,
    }


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, name, role, auth_provider, google_id, avatar_url, is_active, created_at, last_login FROM users WHERE id = $1",
            uuid.UUID(user_id),
        )
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "password_hash": row["password_hash"],
        "name": row["name"],
        "role": row["role"],
        "auth_provider": row["auth_provider"],
        "google_id": row["google_id"],
        "avatar_url": row["avatar_url"],
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "last_login": row["last_login"].isoformat() if row["last_login"] else None,
    }


async def get_user_by_google_id(google_id: str) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, name, role, auth_provider, google_id, avatar_url, is_active, created_at, last_login FROM users WHERE google_id = $1",
            google_id,
        )
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "password_hash": row["password_hash"],
        "name": row["name"],
        "role": row["role"],
        "auth_provider": row["auth_provider"],
        "google_id": row["google_id"],
        "avatar_url": row["avatar_url"],
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "last_login": row["last_login"].isoformat() if row["last_login"] else None,
    }


async def create_user(
    email: str,
    password_hash: str | None = None,
    name: str | None = None,
    role: str = "user",
    auth_provider: str = "email",
    google_id: str | None = None,
    avatar_url: str | None = None,
) -> str:
    pool = await get_pool()
    uid = uuid.uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO users (id, email, password_hash, name, role, auth_provider, google_id, avatar_url)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            uid, email, password_hash, name, role, auth_provider, google_id, avatar_url,
        )
    return str(uid)


async def update_user_last_login(user_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET last_login = $1 WHERE id = $2",
            datetime.now(timezone.utc), uuid.UUID(user_id),
        )


async def update_user_password(user_id: str, password_hash: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET password_hash = $1 WHERE id = $2",
            password_hash, uuid.UUID(user_id),
        )


async def update_user_google_info(
    user_id: str,
    google_id: str,
    avatar_url: str | None = None,
    name: str | None = None,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE users SET google_id = $1, avatar_url = COALESCE($2, avatar_url),
               name = COALESCE($3, name), auth_provider = 'google'
               WHERE id = $4""",
            google_id, avatar_url, name, uuid.UUID(user_id),
        )


async def update_user_active(user_id: str, is_active: bool):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_active = $1 WHERE id = $2",
            is_active, uuid.UUID(user_id),
        )


async def list_users() -> List[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, email, name, role, auth_provider, avatar_url, is_active, created_at, last_login FROM users ORDER BY created_at"
        )
    return [
        {
            "id": str(row["id"]),
            "email": row["email"],
            "name": row["name"],
            "role": row["role"],
            "auth_provider": row["auth_provider"],
            "avatar_url": row["avatar_url"],
            "is_active": row["is_active"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "last_login": row["last_login"].isoformat() if row["last_login"] else None,
        }
        for row in rows
    ]


async def has_any_admin() -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1")
    return row is not None
