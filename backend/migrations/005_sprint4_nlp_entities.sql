-- Sprint 4: NLP entity analysis, sentiment, content extraction, migration assessment

-- NLP entity analysis columns on page_content (Sprint 4D, v1 API)
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_entities JSONB;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_primary_entity TEXT;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_primary_entity_salience REAL;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_entity_focus_aligned BOOLEAN;

-- NLP sentiment columns on page_content (Sprint 4D, v1 API — selective)
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_sentiment_score REAL;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_sentiment_magnitude REAL;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS nlp_entity_sentiments JSONB;

-- Content extraction metadata on page_content (Sprint 4A)
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS word_count INTEGER;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS heading_structure JSONB;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS internal_links JSONB;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS external_links JSONB;
ALTER TABLE page_content ADD COLUMN IF NOT EXISTS schema_types TEXT[];

-- Migration assessment on audits (Sprint 4E)
ALTER TABLE audits ADD COLUMN IF NOT EXISTS migration_assessment JSONB;
