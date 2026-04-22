-- 009_coverage_and_scan_status.sql
-- BUG-1 fix: pillar-level scan status tracking + coverage-weighted overall score.
--
-- Previously, a pillar scan that crashed (e.g. Playwright timeout on the
-- accessibility pillar) synthesized a "high" severity finding that deducted
-- ~10 points from the pillar, producing a fabricated 90/100 that made the
-- site look fine when the scan never actually ran.
--
-- New model:
--   * Each pillar reports scan_status = 'ok' | 'failed' | 'incomplete'.
--   * Infrastructure failures set scan_status='failed' and produce NO findings.
--   * compile_scores drops failed pillars' weights from the weighted average
--     (Option A: renormalize over covered weight). If covered_weight < 0.70,
--     the overall score is suppressed entirely (stored as NULL).
--   * coverage_weight (0.0–1.0) is persisted on the audit record so the UI
--     can render a disclosure chip ("82% coverage — accessibility failed").

ALTER TABLE audits ADD COLUMN IF NOT EXISTS coverage_weight REAL DEFAULT 1.0;
ALTER TABLE pillar_scores ADD COLUMN IF NOT EXISTS scan_status TEXT DEFAULT 'ok';

-- Indexable so we can surface "sites with partial coverage" in admin views
-- without scanning every audit.
CREATE INDEX IF NOT EXISTS idx_audits_coverage ON audits(coverage_weight)
    WHERE coverage_weight < 1.0;
CREATE INDEX IF NOT EXISTS idx_pillar_scores_failed ON pillar_scores(audit_id, pillar_key)
    WHERE scan_status <> 'ok';
