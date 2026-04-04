import aiosqlite
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

DB_PATH = "audits.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT,
                total_urls INTEGER,
                completed_urls INTEGER,
                final_report TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS page_audits (
                job_id TEXT,
                url TEXT,
                status TEXT,
                results_json TEXT,
                UNIQUE(job_id, url)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS audit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                audit_type TEXT DEFAULT 'single',
                overall_score INTEGER,
                overall_label TEXT,
                report_json TEXT,
                created_at TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                email TEXT,
                frequency TEXT DEFAULT 'weekly',
                max_pages INTEGER DEFAULT 1,
                last_run TEXT,
                next_run TEXT,
                enabled INTEGER DEFAULT 1
            )
        ''')
        await db.commit()

async def create_job(job_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO jobs (job_id, status, total_urls, completed_urls) VALUES (?, ?, ?, ?)",
            (job_id, "running", 1, 0)
        )
        await db.commit()

async def update_job_progress(job_id: str, status: Optional[str] = None, total: Optional[int] = None, completed: Optional[int] = None, final_report: Optional[dict] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        updates: List[str] = []
        params: List[Any] = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if total is not None:
            updates.append("total_urls = ?")
            params.append(total)
        if completed is not None:
            updates.append("completed_urls = ?")
            params.append(completed)
        if final_report is not None:
            updates.append("final_report = ?")
            params.append(json.dumps(final_report))
            
        if not updates:
            return
            
        query = "UPDATE jobs SET " + ", ".join(updates) + " WHERE job_id = ?"
        params.append(job_id)
        
        await db.execute(query, params)
        await db.commit()

async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT status, total_urls, completed_urls, final_report FROM jobs WHERE job_id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "status": row[0],
                "total_urls": row[1],
                "completed_urls": row[2],
                "final_report": json.loads(row[3]) if row[3] else None
            }

async def save_page_audit(job_id: str, url: str, status: str, results: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        results_str = json.dumps(results)
        await db.execute(
            "INSERT OR REPLACE INTO page_audits (job_id, url, status, results_json) VALUES (?, ?, ?, ?)",
            (job_id, url, status, results_str)
        )
        await db.commit()

async def get_page_audits(job_id: str) -> List[Dict[str, Any]]:
    audits = []
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT url, status, results_json FROM page_audits WHERE job_id = ?", (job_id,)) as cursor:
            async for row in cursor:
                audits.append({
                    "url": row[0],
                    "status": row[1],
                    "results": json.loads(row[2]) if row[2] else None
                })
    return audits

async def get_single_page_audit(job_id: str, url: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT results_json FROM page_audits WHERE job_id = ? AND url = ?", (job_id, url)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return json.loads(row[0])
            return None

# --- Audit History ---

async def save_audit_history(url: str, audit_type: str, overall_score: int, overall_label: str, report: dict, tier: str = "free", audit_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO audit_history (url, audit_type, overall_score, overall_label, report_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (url, audit_type, overall_score, overall_label, json.dumps(report), datetime.now(timezone.utc).isoformat())
        )
        await db.commit()

async def get_audit_history(url: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, url, audit_type, overall_score, overall_label, created_at FROM audit_history WHERE url = ? ORDER BY created_at DESC", (url,)) as cursor:
            async for row in cursor:
                results.append({"id": row[0], "url": row[1], "audit_type": row[2], "overall_score": row[3], "overall_label": row[4], "created_at": row[5]})
    return results

async def get_latest_history_score(url: str) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT overall_score FROM audit_history WHERE url = ? ORDER BY created_at DESC LIMIT 1", (url,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_audit_by_id(audit_id) -> Optional[Dict[str, Any]]:
    """Retrieve a full audit by its ID (SQLite fallback)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, url, audit_type, overall_score, overall_label, report_json, created_at FROM audit_history WHERE id = ?",
            (str(audit_id),)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            report = row[5]
            if isinstance(report, str):
                report = json.loads(report)
            return {
                "id": str(row[0]),
                "url": row[1],
                "tier": "free",
                "audit_type": row[2],
                "overall_score": row[3],
                "overall_label": row[4],
                "report_json": report,
                "created_at": row[6],
                "detected_cms": None,
            }


async def list_all_audits(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """List all audits (SQLite fallback)."""
    results: List[Dict[str, Any]] = []
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, url, audit_type, overall_score, overall_label, created_at FROM audit_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ) as cursor:
            async for row in cursor:
                results.append({
                    "id": str(row[0]),
                    "url": row[1],
                    "tier": "free",
                    "audit_type": row[2],
                    "overall_score": row[3],
                    "overall_label": row[4],
                    "created_at": row[5],
                    "detected_cms": None,
                })
    return results


# --- Scheduled Audits ---

async def create_schedule(url: str, email: str, frequency: str, max_pages: int) -> int:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO scheduled_audits (url, email, frequency, max_pages, next_run, enabled) VALUES (?, ?, ?, ?, ?, 1)",
            (url, email, frequency, max_pages, now)
        )
        await db.commit()
        last_row_id = cursor.lastrowid or 0
    return last_row_id

async def get_schedules() -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, url, email, frequency, max_pages, last_run, next_run, enabled FROM scheduled_audits ORDER BY id") as cursor:
            async for row in cursor:
                results.append({"id": row[0], "url": row[1], "email": row[2], "frequency": row[3], "max_pages": row[4], "last_run": row[5], "next_run": row[6], "enabled": bool(row[7])})
    return results

async def update_schedule(schedule_id: int, enabled: Optional[bool] = None, frequency: Optional[str] = None, email: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if enabled is not None:
            await db.execute("UPDATE scheduled_audits SET enabled = ? WHERE id = ?", (1 if enabled else 0, schedule_id))
        if frequency is not None:
            await db.execute("UPDATE scheduled_audits SET frequency = ? WHERE id = ?", (frequency, schedule_id))
        if email is not None:
            await db.execute("UPDATE scheduled_audits SET email = ? WHERE id = ?", (email, schedule_id))
        await db.commit()

async def delete_schedule(schedule_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM scheduled_audits WHERE id = ?", (schedule_id,))
        await db.commit()

async def get_due_schedules() -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    results: List[Dict[str, Any]] = []
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, url, email, frequency, max_pages FROM scheduled_audits WHERE enabled = 1 AND (next_run IS NULL OR next_run <= ?)", (now,)) as cursor:
            async for row in cursor:
                results.append({"id": row[0], "url": row[1], "email": row[2], "frequency": row[3], "max_pages": row[4]})
    return results

async def mark_schedule_run(schedule_id: int, frequency: str):
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    deltas = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1), "monthly": timedelta(days=30)}
    next_run = now + deltas.get(frequency, timedelta(weeks=1))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE scheduled_audits SET last_run = ?, next_run = ? WHERE id = ?", (now.isoformat(), next_run.isoformat(), schedule_id))
        await db.commit()


# --- DataForSEO stubs (premium-only, requires PostgreSQL) ---

async def save_dataforseo_task(task_id, audit_id, target_url, max_crawl_pages):
    pass

async def update_dataforseo_task(task_id, status, summary=None):
    pass

async def get_dataforseo_task(task_id):
    return None

async def get_dataforseo_task_by_audit(audit_id_str):
    return None


# --- Google OAuth stubs (premium-only, requires PostgreSQL) ---

async def save_google_tokens(property_url, encrypted_tokens, email=None, ga4_property_id=None, scopes=None):
    pass

async def get_google_tokens(property_url):
    return None

async def list_google_tokens():
    return []

async def delete_google_tokens(property_url):
    pass


# --- Link graph / page content / CMS stubs (premium, requires PostgreSQL) ---

async def save_link_graph_edges(audit_id, edges):
    pass

async def get_link_graph_data(audit_id_str):
    return None

async def save_page_content_batch(audit_id, pages):
    pass

async def save_cms_detection(audit_id, platform, version, confidence, detection_method, technologies):
    pass

async def save_industry_detection(audit_id, industry, confidence, categories):
    pass


# --- Sprint 4 stubs (premium-only, requires PostgreSQL) ---

async def update_page_content_text(audit_id, url, clean_text, word_count=None, language=None, extraction_method=None):
    pass

async def update_page_nlp_entities(audit_id, url, entities_json, primary_entity, primary_entity_salience, entity_focus_aligned):
    pass

async def update_page_nlp_sentiment(audit_id, url, sentiment_score, sentiment_magnitude, entity_sentiments_json):
    pass

async def get_page_content_for_audit(audit_id_str):
    return []

async def save_migration_assessment(audit_id, assessment_json):
    pass

async def get_migration_assessment(audit_id_str):
    return None


# --- User Authentication stubs (requires PostgreSQL for production) ---

async def get_user_by_email(email):
    return None

async def get_user_by_id(user_id):
    return None

async def get_user_by_google_id(google_id):
    return None

async def create_user(email, password_hash=None, name=None, role="user", auth_provider="email", google_id=None, avatar_url=None):
    return "stub-user-id"

async def update_user_last_login(user_id):
    pass

async def update_user_password(user_id, password_hash):
    pass

async def update_user_google_info(user_id, google_id, avatar_url=None, name=None):
    pass

async def update_user_active(user_id, is_active):
    pass

async def list_users():
    return []

async def has_any_admin():
    return False
