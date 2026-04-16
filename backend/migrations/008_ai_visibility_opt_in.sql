-- 008_ai_visibility_opt_in.sql
-- Phase 3: AI Visibility auto-run opt-in flag

ALTER TABLE audits ADD COLUMN IF NOT EXISTS ai_visibility_opt_in BOOLEAN DEFAULT FALSE;
