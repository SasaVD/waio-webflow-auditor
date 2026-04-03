"""
Database router — selects PostgreSQL (asyncpg) or SQLite (aiosqlite)
based on whether DATABASE_URL is set in the environment.
"""
import os

if os.environ.get("DATABASE_URL"):
    from db_postgres import (  # noqa: F401
        init_db,
        close_db,
        create_job,
        update_job_progress,
        get_job_status,
        save_page_audit,
        get_page_audits,
        get_single_page_audit,
        save_audit_history,
        get_audit_history,
        get_latest_history_score,
        create_schedule,
        get_schedules,
        update_schedule,
        delete_schedule,
        get_due_schedules,
        mark_schedule_run,
        save_dataforseo_task,
        update_dataforseo_task,
        get_dataforseo_task,
        get_dataforseo_task_by_audit,
        save_google_tokens,
        get_google_tokens,
        list_google_tokens,
        delete_google_tokens,
        save_link_graph_edges,
        get_link_graph_data,
        save_page_content_batch,
        save_cms_detection,
        save_industry_detection,
        # Sprint 4
        update_page_content_text,
        update_page_nlp_entities,
        update_page_nlp_sentiment,
        get_page_content_for_audit,
        save_migration_assessment,
        get_migration_assessment,
    )
else:
    from db import (  # noqa: F401 type: ignore[assignment]
        init_db,
        create_job,
        update_job_progress,
        get_job_status,
        save_page_audit,
        get_page_audits,
        get_single_page_audit,
        save_audit_history,
        get_audit_history,
        get_latest_history_score,
        create_schedule,
        get_schedules,
        update_schedule,
        delete_schedule,
        get_due_schedules,
        mark_schedule_run,
        save_dataforseo_task,
        update_dataforseo_task,
        get_dataforseo_task,
        get_dataforseo_task_by_audit,
        save_google_tokens,
        get_google_tokens,
        list_google_tokens,
        delete_google_tokens,
        save_link_graph_edges,
        get_link_graph_data,
        save_page_content_batch,
        save_cms_detection,
        save_industry_detection,
        # Sprint 4
        update_page_content_text,
        update_page_nlp_entities,
        update_page_nlp_sentiment,
        get_page_content_for_audit,
        save_migration_assessment,
        get_migration_assessment,
    )

    async def close_db():  # noqa: F811
        pass  # SQLite has no connection pool to close
