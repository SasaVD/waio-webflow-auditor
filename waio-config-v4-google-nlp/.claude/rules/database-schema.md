# Database Schema — PostgreSQL

## Current State
Sprint 1 implemented the PostgreSQL migration. Sprint 3A added DataForSEO task tracking.
`db_router.py` auto-selects Postgres (via `DATABASE_URL`) or SQLite fallback.

## Active Schema

```sql
-- Core audit record
CREATE TABLE audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    audit_type TEXT NOT NULL DEFAULT 'single',
    overall_score INTEGER,
    overall_label TEXT,
    report_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Premium tier fields
    gsc_property_url TEXT,
    competitor_urls TEXT[],
    executive_summary TEXT,
    max_pages_crawled INTEGER,
    
    -- CMS detection (Sprint 3F)
    detected_cms TEXT,
    cms_version TEXT,
    cms_confidence REAL,
    cms_detection_method TEXT,
    detected_technologies TEXT[],
    
    -- Google NLP industry detection (Sprint 3E)
    detected_industry TEXT,             -- top NLP classification across all pages
                                         -- e.g., "/Business & Industrial/Advertising & Marketing"
    detected_industry_confidence REAL,  -- aggregated confidence score
    industry_categories JSONB,          -- all detected categories with page counts
                                         -- [{"category": "/Finance/...", "page_count": 45, "avg_confidence": 0.82}]
    
    -- Migration assessment (Sprint 4E)
    migration_assessment JSONB,
    
    -- DataForSEO tracking (Sprint 3A)
    dataforseo_task_id TEXT
);

CREATE INDEX idx_audits_url ON audits(url);
CREATE INDEX idx_audits_created ON audits(created_at DESC);
CREATE INDEX idx_audits_tier ON audits(tier);
CREATE INDEX idx_audits_cms ON audits(detected_cms);
CREATE INDEX idx_audits_industry ON audits(detected_industry);

-- Individual pillar scores
CREATE TABLE pillar_scores (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    pillar_key TEXT NOT NULL,
    score INTEGER NOT NULL,
    label TEXT NOT NULL,
    finding_count INTEGER DEFAULT 0,
    UNIQUE(audit_id, pillar_key)
);

CREATE INDEX idx_pillar_scores_pillar ON pillar_scores(pillar_key);

-- Individual findings
CREATE TABLE findings (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    pillar_key TEXT NOT NULL,
    check_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT,
    reference TEXT,
    credibility_anchor TEXT,
    webflow_fix_key TEXT,
    cms_specific BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_pillar ON findings(pillar_key);

-- Page content with NLP analysis results
CREATE TABLE page_content (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    h1_text TEXT,
    meta_description TEXT,
    visible_text TEXT,
    clean_text TEXT,                     -- Trafilatura-extracted (Sprint 4A)
    word_count INTEGER,
    heading_structure JSONB,
    internal_links JSONB,
    external_links JSONB,
    schema_types TEXT[],
    language TEXT,
    extraction_method TEXT,
    status_code INTEGER,
    click_depth INTEGER,
    is_orphan BOOLEAN,
    
    -- Google NLP Classification (Sprint 3E, v2 API)
    nlp_category TEXT,                  -- primary classification
                                         -- e.g., "/Business & Industrial/Advertising & Marketing"
    nlp_category_confidence REAL,       -- 0.0-1.0
    nlp_categories JSONB,               -- all categories with confidence scores
                                         -- [{"category": "/...", "confidence": 0.85}, ...]
    
    -- Google NLP Entity Analysis (Sprint 4D, v1 API)
    nlp_entities JSONB,                 -- top entities with salience scores
                                         -- [{"name": "web design", "type": "OTHER",
                                         --   "salience": 0.73, "wikipedia_url": "...",
                                         --   "mentions_count": 12}, ...]
    nlp_primary_entity TEXT,            -- highest salience entity name
    nlp_primary_entity_salience REAL,   -- salience score of primary entity
    nlp_entity_focus_aligned BOOLEAN,   -- does primary entity match H1/title intent?
    
    -- Google NLP Sentiment (Sprint 4D, v1 API — selective, key pages only)
    nlp_sentiment_score REAL,           -- -1.0 to +1.0
    nlp_sentiment_magnitude REAL,       -- 0.0 to ∞
    nlp_entity_sentiments JSONB,        -- per-entity sentiment from analyzeEntitySentiment
                                         -- [{"entity": "HubSpot", "sentiment": 0.7,
                                         --   "mentions": 14, "type": "ORGANIZATION"}, ...]
    
    UNIQUE(audit_id, url)
);

CREATE INDEX idx_page_content_audit ON page_content(audit_id);
CREATE INDEX idx_page_content_orphan ON page_content(is_orphan) WHERE is_orphan = TRUE;
CREATE INDEX idx_page_content_nlp_category ON page_content(nlp_category);

-- Link graph edges
CREATE TABLE link_graph (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    target_url TEXT NOT NULL,
    anchor_text TEXT,
    is_nofollow BOOLEAN DEFAULT FALSE,
    link_position TEXT
);

CREATE INDEX idx_link_graph_audit ON link_graph(audit_id);
CREATE INDEX idx_link_graph_source ON link_graph(source_url);
CREATE INDEX idx_link_graph_target ON link_graph(target_url);

-- DataForSEO task tracking (Sprint 3A)
CREATE TABLE dataforseo_tasks (
    id SERIAL PRIMARY KEY,
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    pages_crawled INTEGER,
    pages_total INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Jobs, scheduled_audits, webflow_fixes, cms_known_issues
-- (unchanged from v3 — see previous schema)

CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    audit_id UUID REFERENCES audits(id),
    status TEXT,
    total_urls INTEGER,
    completed_urls INTEGER,
    final_report JSONB
);

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

CREATE TABLE webflow_fixes (
    id SERIAL PRIMARY KEY,
    finding_pattern TEXT UNIQUE NOT NULL,
    pillar_key TEXT NOT NULL,
    title TEXT NOT NULL,
    steps_markdown TEXT NOT NULL,
    difficulty TEXT,
    estimated_time TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE cms_known_issues (
    id SERIAL PRIMARY KEY,
    cms_platform TEXT NOT NULL,
    issue_category TEXT NOT NULL,
    issue_key TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,
    webflow_advantage TEXT,
    evidence TEXT,
    UNIQUE(cms_platform, issue_key)
);

CREATE INDEX idx_cms_issues_platform ON cms_known_issues(cms_platform);
```

## Migrations

### Sprint 3 migration (002_cms_and_dataforseo.sql)
```sql
ALTER TABLE audits ADD COLUMN IF NOT EXISTS max_pages_crawled INTEGER;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS detected_cms TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS cms_version TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS cms_confidence REAL;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS cms_detection_method TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS detected_technologies TEXT[];
ALTER TABLE audits ADD COLUMN IF NOT EXISTS dataforseo_task_id TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS detected_industry TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS detected_industry_confidence REAL;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS industry_categories JSONB;

CREATE INDEX IF NOT EXISTS idx_audits_cms ON audits(detected_cms);
CREATE INDEX IF NOT EXISTS idx_audits_industry ON audits(detected_industry);

-- NLP classification columns on page_content
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_category TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_category_confidence REAL;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_categories JSONB;

CREATE INDEX IF NOT EXISTS idx_page_content_nlp_category ON page_content(nlp_category);
```

### Sprint 4 migration (003_content_and_nlp_entities.sql)
```sql
-- Content extraction columns
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS clean_text TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS extraction_method TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS status_code INTEGER;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS click_depth INTEGER;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS is_orphan BOOLEAN;
CREATE INDEX IF NOT EXISTS idx_page_content_orphan ON page_content(is_orphan) WHERE is_orphan = TRUE;

-- NLP entity analysis columns
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_entities JSONB;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_primary_entity TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_primary_entity_salience REAL;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_entity_focus_aligned BOOLEAN;

-- NLP sentiment columns
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_sentiment_score REAL;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_sentiment_magnitude REAL;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_entity_sentiments JSONB;

-- Migration assessment
ALTER TABLE audits ADD COLUMN IF NOT EXISTS migration_assessment JSONB;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS cms_specific BOOLEAN DEFAULT FALSE;

-- CMS known issues table
CREATE TABLE IF NOT EXISTS cms_known_issues (
    id SERIAL PRIMARY KEY,
    cms_platform TEXT NOT NULL,
    issue_category TEXT NOT NULL,
    issue_key TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,
    webflow_advantage TEXT,
    evidence TEXT,
    UNIQUE(cms_platform, issue_key)
);
CREATE INDEX IF NOT EXISTS idx_cms_issues_platform ON cms_known_issues(cms_platform);
```

## Environment Variables
```
DATABASE_URL=postgresql://...          (Railway auto-provides)
DATAFORSEO_LOGIN=...                   (Sprint 3A)
DATAFORSEO_PASSWORD=...                (Sprint 3A)
GOOGLE_CLIENT_ID=...                   (GSC/GA4 OAuth, Sprint 3B)
GOOGLE_CLIENT_SECRET=...               (GSC/GA4 OAuth, Sprint 3B)
GOOGLE_APPLICATION_CREDENTIALS=...     (NLP API service account, Sprint 3E — alternative to OAuth)
SERPAPI_KEY=...                        (Sprint 4)
```
