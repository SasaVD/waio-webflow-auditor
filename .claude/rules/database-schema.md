# Database Schema — PostgreSQL

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
    executive_summary TEXT,
    max_pages_crawled INTEGER,             -- actual pages crawled (may differ from requested)
    
    -- CMS detection (Sprint 3F)
    detected_cms TEXT,                     -- 'wordpress', 'shopify', 'webflow', 'nextjs', etc.
    cms_version TEXT,                      -- e.g., '6.4.3' for WordPress (if detectable)
    cms_confidence REAL,                   -- 0.0-1.0 detection confidence
    cms_detection_method TEXT,             -- 'regex', 'wappalyzer', 'dns', 'combined'
    detected_technologies TEXT[],          -- ['React', 'Cloudflare', 'Google Analytics', ...]
    
    -- Migration assessment (Sprint 4E, NULL for Webflow sites)
    migration_assessment JSONB             -- full migration report data
                                           -- includes: platform_issues[], webflow_advantages[],
                                           -- redirect_count, migration_timeline, tco_comparison
);

CREATE INDEX idx_audits_url ON audits(url);
CREATE INDEX idx_audits_created ON audits(created_at DESC);
CREATE INDEX idx_audits_tier ON audits(tier);
CREATE INDEX idx_audits_cms ON audits(detected_cms);

-- Individual pillar scores (queryable across audits)
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
    webflow_fix_key TEXT,               -- maps to fix knowledge base (for Webflow sites)
    cms_specific BOOLEAN DEFAULT FALSE  -- true if finding is CMS-specific (e.g., Shopify URL duplication)
);

CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_pillar ON findings(pillar_key);

-- Page content (for WDF*IDF, clustering, and RAG training)
-- Designed to handle 2,000-5,000 pages per audit
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
                                -- Phase 2 upgrade: replace with Firecrawl markdown
    word_count INTEGER,
    heading_structure JSONB,   -- [{level, text}]
    internal_links JSONB,      -- [{href, anchor_text}]
    external_links JSONB,
    schema_types TEXT[],       -- ['Organization', 'WebSite', ...]
    language TEXT,             -- detected language (from Trafilatura metadata)
    extraction_method TEXT,    -- 'trafilatura' | 'beautifulsoup_fallback' | 'firecrawl' (future)
    status_code INTEGER,       -- HTTP status code from DataForSEO
    click_depth INTEGER,       -- clicks from homepage (from DataForSEO)
    is_orphan BOOLEAN,         -- orphan page flag (from DataForSEO + GSC cross-reference)
    UNIQUE(audit_id, url)
);

CREATE INDEX idx_page_content_audit ON page_content(audit_id);
CREATE INDEX idx_page_content_orphan ON page_content(is_orphan) WHERE is_orphan = TRUE;

-- Link graph edges (for network visualization and cluster analysis)
-- At 2,000 pages with ~10 links per page: ~20,000 rows per audit
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
    finding_pattern TEXT UNIQUE NOT NULL,
    pillar_key TEXT NOT NULL,
    title TEXT NOT NULL,
    steps_markdown TEXT NOT NULL,
    difficulty TEXT,
    estimated_time TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- CMS-specific known issues (curated knowledge base for migration intelligence)
-- Maps CMS platforms to common SEO problems and Webflow advantages
CREATE TABLE cms_known_issues (
    id SERIAL PRIMARY KEY,
    cms_platform TEXT NOT NULL,       -- 'wordpress', 'shopify', 'wix', 'squarespace', 'nextjs'
    issue_category TEXT NOT NULL,     -- 'security', 'performance', 'url_structure', 'seo_limitation'
    issue_key TEXT NOT NULL,          -- 'wp_plugin_vulnerabilities', 'shopify_duplicate_urls'
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,           -- 'critical', 'high', 'medium'
    webflow_advantage TEXT,           -- how Webflow solves this issue
    evidence TEXT,                    -- credibility anchor (study, statistic, source)
    UNIQUE(cms_platform, issue_key)
);

CREATE INDEX idx_cms_issues_platform ON cms_known_issues(cms_platform);
```

## Migrations

### Sprint 3 migration (002_cms_detection.sql)
```sql
ALTER TABLE audits ADD COLUMN IF NOT EXISTS max_pages_crawled INTEGER;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS detected_cms TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS cms_version TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS cms_confidence REAL;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS cms_detection_method TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS detected_technologies TEXT[];
CREATE INDEX IF NOT EXISTS idx_audits_cms ON audits(detected_cms);
```

### Sprint 4 migration (003_content_and_migration.sql)
```sql
-- Content extraction columns
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS clean_text TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS extraction_method TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS status_code INTEGER;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS click_depth INTEGER;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS is_orphan BOOLEAN;
CREATE INDEX IF NOT EXISTS idx_page_content_orphan ON page_content(is_orphan) WHERE is_orphan = TRUE;

-- Migration assessment
ALTER TABLE audits ADD COLUMN IF NOT EXISTS migration_assessment JSONB;

-- CMS-specific findings flag
ALTER TABLE findings ADD COLUMN IF NOT EXISTS cms_specific BOOLEAN DEFAULT FALSE;

-- CMS known issues knowledge base
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
DATABASE_URL=postgresql://...      (Railway auto-provides this)
DATAFORSEO_LOGIN=...               (for On-Page API, Sprint 3)
DATAFORSEO_PASSWORD=...            (for On-Page API, Sprint 3)
GOOGLE_CLIENT_ID=...               (for GSC/GA4 OAuth, Sprint 3)
GOOGLE_CLIENT_SECRET=...           (for GSC/GA4 OAuth, Sprint 3)
SERPAPI_KEY=...                    (for WDF*IDF SERP data, Sprint 4)
```
