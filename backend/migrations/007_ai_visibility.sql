-- 007_ai_visibility.sql
-- Phase 1: AI Visibility columns on audits table

ALTER TABLE audits ADD COLUMN IF NOT EXISTS brand_name_override TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS ai_visibility_cumulative_cost_usd REAL DEFAULT 0;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS ai_visibility_run_count INTEGER DEFAULT 0;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS last_ai_visibility_run_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_audits_last_ai_viz_run ON audits(last_ai_visibility_run_at);
