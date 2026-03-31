# Database Schema — PostgreSQL Migration Plan

## Current State
Sprint 1 implemented the PostgreSQL migration. `db_router.py` auto-selects Postgres (via `DATABASE_URL`) or SQLite fallback.

## Active Schema

```sql
-- Core audit record
CREATE TABLE audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',  -- 'free' or 'premium'
    audit_type TEXT NOT NULL DEFAULT 'single',  -- 'single', 'site', 'competitive'
    overall_score INTEGER,
    overall_label TEXT,
    report_json JSONB,  -- full report for backward compatibility
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Premium tier fields (NULL for free audits)
    gsc_property_url TEXT,
    competitor_urls TEXT[],
    executive_summary TEXT
);

CREATE INDEX idx_audits_url ON audits(url);
CREATE INDEX idx_audits_created ON audits(created_at DESC);
CREATE INDEX idx_audits_tier ON audits(tier);

-- Individual pillar scores (queryable across audits)
CREATE TABLE pillar_scores (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    pillar_key TEXT NOT NULL,  -- 'semantic_html', 'structured_data', etc.
    score INTEGER NOT NULL,
    label TEXT NOT NULL,
    finding_count INTEGER DEFAULT 0,
    UNIQUE(audit_id, pillar_key)
);

CREATE INDEX idx_pillar_scores_pillar ON pillar_scores(pillar_key);

-- Individual findings (queryable for frequency analysis + chatbot training)
CREATE TABLE findings (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    pillar_key TEXT NOT NULL,
    check_name TEXT NOT NULL,
    severity TEXT NOT NULL,  -- 'critical', 'high', 'medium'
    description TEXT NOT NULL,
    recommendation TEXT,
    reference TEXT,
    credibility_anchor TEXT,
    webflow_fix_key TEXT  -- maps to fix knowledge base
);

CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_pillar ON findings(pillar_key);

-- Page content (for WDF*IDF, clustering, and RAG training)
CREATE TABLE page_content (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    h1_text TEXT,
    meta_description TEXT,
    visible_text TEXT,          -- raw extracted body text (from BeautifulSoup get_text)
    clean_text TEXT,            -- Trafilatura-extracted main content (Sprint 4)
                                -- boilerplate-free, nav/footer stripped
                                -- used for WDF*IDF, content profiling, interlinking, RAG export
                                -- Phase 2 upgrade: replace with Firecrawl markdown for better RAG quality
    word_count INTEGER,
    heading_structure JSONB,   -- [{level, text}]
    internal_links JSONB,      -- [{href, anchor_text}]
    external_links JSONB,
    schema_types TEXT[],       -- ['Organization', 'WebSite', ...]
    language TEXT,             -- detected language (from Trafilatura metadata)
    extraction_method TEXT,    -- 'trafilatura' | 'beautifulsoup_fallback' | 'firecrawl' (future)
    UNIQUE(audit_id, url)
);

CREATE INDEX idx_page_content_audit ON page_content(audit_id);

-- Link graph edges (for network visualization and cluster analysis)
CREATE TABLE link_graph (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    target_url TEXT NOT NULL,
    anchor_text TEXT,
    is_nofollow BOOLEAN DEFAULT FALSE,
    link_position TEXT  -- 'nav', 'content', 'footer', 'sidebar'
);

CREATE INDEX idx_link_graph_audit ON link_graph(audit_id);
CREATE INDEX idx_link_graph_source ON link_graph(source_url);
CREATE INDEX idx_link_graph_target ON link_graph(target_url);

-- Jobs (for multi-page crawl tracking)
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    audit_id UUID REFERENCES audits(id),
    status TEXT,
    total_urls INTEGER,
    completed_urls INTEGER,
    final_report JSONB
);

-- Scheduled audits
CREATE TABLE scheduled_audits (
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

-- Webflow fix knowledge base (curated, static)
CREATE TABLE webflow_fixes (
    id SERIAL PRIMARY KEY,
    finding_pattern TEXT UNIQUE NOT NULL,  -- e.g., 'missing_h1', 'no_json_ld'
    pillar_key TEXT NOT NULL,
    title TEXT NOT NULL,
    steps_markdown TEXT NOT NULL,  -- full fix instruction in Markdown
    difficulty TEXT,  -- 'easy', 'medium', 'advanced'
    estimated_time TEXT,  -- '2 minutes', '15 minutes'
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Migration for Sprint 4 (add clean_text columns)

```sql
-- migrations/002_content_extraction.sql
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS clean_text TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS extraction_method TEXT;
```

## Environment Variables (add to Railway)
```
DATABASE_URL=postgresql://...      (Railway auto-provides this)
DATAFORSEO_LOGIN=...               (for On-Page API, Sprint 3)
DATAFORSEO_PASSWORD=...            (for On-Page API, Sprint 3)
GOOGLE_CLIENT_ID=...               (for GSC/GA4 OAuth, Sprint 3)
GOOGLE_CLIENT_SECRET=...           (for GSC/GA4 OAuth, Sprint 3)
SERPAPI_KEY=...                    (for WDF*IDF SERP data, Sprint 4)
```
