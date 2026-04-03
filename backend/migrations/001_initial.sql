-- WAIO Audit Tool — Initial PostgreSQL Schema
-- Sprint 1A: PostgreSQL Migration

-- Core audit record
CREATE TABLE IF NOT EXISTS audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    audit_type TEXT NOT NULL DEFAULT 'single',
    overall_score INTEGER,
    overall_label TEXT,
    report_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Premium tier fields (NULL for free audits)
    gsc_property_url TEXT,
    competitor_urls TEXT[],
    executive_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_audits_url ON audits(url);
CREATE INDEX IF NOT EXISTS idx_audits_created ON audits(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audits_tier ON audits(tier);

-- Individual pillar scores (queryable across audits)
CREATE TABLE IF NOT EXISTS pillar_scores (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    pillar_key TEXT NOT NULL,
    score INTEGER NOT NULL,
    label TEXT NOT NULL,
    finding_count INTEGER DEFAULT 0,
    UNIQUE(audit_id, pillar_key)
);

CREATE INDEX IF NOT EXISTS idx_pillar_scores_pillar ON pillar_scores(pillar_key);

-- Individual findings (queryable for frequency analysis + chatbot training)
CREATE TABLE IF NOT EXISTS findings (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    pillar_key TEXT NOT NULL,
    check_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT,
    reference TEXT,
    credibility_anchor TEXT,
    webflow_fix_key TEXT
);

CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_pillar ON findings(pillar_key);

-- Page content (for WDF*IDF, clustering, and RAG training)
CREATE TABLE IF NOT EXISTS page_content (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    h1_text TEXT,
    meta_description TEXT,
    visible_text TEXT,
    word_count INTEGER,
    heading_structure JSONB,
    internal_links JSONB,
    external_links JSONB,
    schema_types TEXT[],
    UNIQUE(audit_id, url)
);

CREATE INDEX IF NOT EXISTS idx_page_content_audit ON page_content(audit_id);

-- Link graph edges (for network visualization and cluster analysis)
CREATE TABLE IF NOT EXISTS link_graph (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    target_url TEXT NOT NULL,
    anchor_text TEXT,
    is_nofollow BOOLEAN DEFAULT FALSE,
    link_position TEXT
);

CREATE INDEX IF NOT EXISTS idx_link_graph_audit ON link_graph(audit_id);
CREATE INDEX IF NOT EXISTS idx_link_graph_source ON link_graph(source_url);
CREATE INDEX IF NOT EXISTS idx_link_graph_target ON link_graph(target_url);

-- Jobs (multi-page crawl tracking)
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    audit_id UUID REFERENCES audits(id),
    status TEXT,
    total_urls INTEGER,
    completed_urls INTEGER,
    final_report JSONB
);

-- Page audits (per-page results during crawl)
CREATE TABLE IF NOT EXISTS page_audits (
    job_id TEXT,
    url TEXT,
    status TEXT,
    results_json JSONB,
    UNIQUE(job_id, url)
);

-- Scheduled audits
CREATE TABLE IF NOT EXISTS scheduled_audits (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    email TEXT,
    frequency TEXT DEFAULT 'weekly',
    max_pages INTEGER DEFAULT 1,
    tier TEXT DEFAULT 'free',
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    enabled BOOLEAN DEFAULT TRUE
);

-- Webflow fix knowledge base (Sprint 2)
CREATE TABLE IF NOT EXISTS webflow_fixes (
    id SERIAL PRIMARY KEY,
    finding_pattern TEXT UNIQUE NOT NULL,
    pillar_key TEXT NOT NULL,
    title TEXT NOT NULL,
    steps_markdown TEXT NOT NULL,
    difficulty TEXT,
    estimated_time TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
