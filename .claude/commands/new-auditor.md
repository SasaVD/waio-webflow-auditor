# /project:new-auditor

Create a new audit pillar module. Follow the full integration checklist.

**Arguments:** pillar_name (snake_case), pillar_label (human readable), weight (decimal, e.g. 0.08)

**Steps:**

1. Read `.claude/rules/auditor-interface.md` for the contract
2. Create `backend/{pillar_name}_auditor.py` following the standard pattern
3. Add the `run_{pillar_name}_audit()` function with proper signature
4. Include the `create_finding()` helper
5. Import and call in `backend/main.py` → `perform_audit()`
6. Register in `backend/scoring.py`:
   - Add score calculation
   - Adjust weights (must sum to 1.0)
   - Add to `scores` and `labels` dicts
7. Add to `backend/report_generator.py` → `categories` dict
8. Add to `frontend/src/components/AuditReport.tsx` → `pillarMeta`
9. Add loading step in `frontend/src/components/LoadingState.tsx`
10. Add to `backend/pdf_generator.py` → `PILLAR_META`
11. Add to `backend/md_generator.py` → `PILLAR_META`
12. Add to `backend/site_crawler.py` → `process_page_audit()`
13. Add to `backend/competitive_auditor.py` → `PILLAR_KEYS` and `PILLAR_LABELS`
14. Test by running a local audit against https://example.com
