-- Sprint 3A: DataForSEO On-Page API task tracking

-- New columns on audits for crawl metadata
ALTER TABLE audits ADD COLUMN IF NOT EXISTS max_pages_crawled INTEGER;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS dataforseo_task_id TEXT;

-- DataForSEO crawl task tracking table
CREATE TABLE IF NOT EXISTS dataforseo_tasks (
    id SERIAL PRIMARY KEY,
    task_id TEXT UNIQUE NOT NULL,           -- DataForSEO task ID
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    target_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | crawling | completed | failed
    max_crawl_pages INTEGER,
    pages_crawled INTEGER,
    pages_count INTEGER,
    internal_links_count INTEGER,
    external_links_count INTEGER,
    broken_links INTEGER,
    summary_json JSONB,                     -- full summary response for reference
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_dfs_tasks_task_id ON dataforseo_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_dfs_tasks_audit_id ON dataforseo_tasks(audit_id);
CREATE INDEX IF NOT EXISTS idx_dfs_tasks_status ON dataforseo_tasks(status);
