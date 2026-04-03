-- Sprint 3E/3F: CMS detection columns, NLP classification columns, industry detection

-- CMS detection on audits
ALTER TABLE audits ADD COLUMN IF NOT EXISTS detected_cms TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS cms_version TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS cms_confidence REAL;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS cms_detection_method TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS detected_technologies TEXT[];

-- Industry detection on audits (Sprint 3E)
ALTER TABLE audits ADD COLUMN IF NOT EXISTS detected_industry TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS detected_industry_confidence REAL;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS industry_categories JSONB;

CREATE INDEX IF NOT EXISTS idx_audits_cms ON audits(detected_cms);
CREATE INDEX IF NOT EXISTS idx_audits_industry ON audits(detected_industry);

-- NLP classification columns on page_content
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS clean_text TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS extraction_method TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS status_code INTEGER;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS click_depth INTEGER;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS is_orphan BOOLEAN;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_category TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_category_confidence REAL;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_categories JSONB;

CREATE INDEX IF NOT EXISTS idx_page_content_orphan ON page_content(is_orphan) WHERE is_orphan = TRUE;
CREATE INDEX IF NOT EXISTS idx_page_content_nlp_category ON page_content(nlp_category);

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
