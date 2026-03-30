# Auditor Interface Contract

## Every Auditor Must Follow This Contract

### Input
Auditors receive parsed page data. The standard signature is:
```python
def run_[name]_audit(soup: BeautifulSoup, html_content: str, url: str = None, **kwargs) -> Dict[str, Any]
```

Some auditors receive additional data:
- `structured_data_auditor`: receives `(html_content, url)` — uses extruct internally
- `accessibility_auditor`: receives `(url)` — runs async with Playwright
- `internal_linking_auditor`: receives `(soup, html_content, url, site_data)` — site_data is for cross-page analysis

### Output
Every auditor returns:
```python
{
    "checks": {
        "check_name": {
            "status": "pass" | "fail" | "info",
            "details": { ... },  # check-specific data
            "findings": [ ... ],  # list of finding dicts (if status is "fail")
            "positive_message": "...",  # string (if status is "pass")
        }
    },
    "positive_findings": [ ... ],  # aggregated from all checks
    "findings": [ ... ]  # aggregated from all checks
}
```

### Finding Object
```python
{
    "severity": "critical" | "high" | "medium",
    "description": "Human-readable description of the issue.",
    "recommendation": "Specific action to fix this issue.",
    "reference": "URL to the relevant standard or documentation.",
    "credibility_anchor": "Data point from a verified study. (Source, Year).",
    "why_it_matters": "Optional extended explanation."
}
```

### Integration Checklist (when adding a new auditor)
1. Create `backend/[name]_auditor.py` following the pattern above
2. Import and call it in `backend/main.py` inside `perform_audit()`
3. Add to `backend/scoring.py`:
   - Add score calculation in `compile_scores()`
   - Add weight to the overall score formula
   - Add to both `scores` and `labels` dicts
4. Add to `backend/report_generator.py`:
   - Add to `all_findings` aggregation
   - Add to `all_positive` aggregation
   - Add to `categories` dict
5. Update `frontend/src/components/AuditReport.tsx`:
   - Add entry to `pillarMeta` object
   - Import the appropriate Lucide icon
6. Update `frontend/src/components/LoadingState.tsx`:
   - Add a loading step message
7. Update `backend/pdf_generator.py` and `backend/md_generator.py`:
   - Add to `PILLAR_META` dict
8. If multi-page: update `backend/site_crawler.py` `process_page_audit()`
9. If competitive: update `backend/competitive_auditor.py` `PILLAR_KEYS` and `PILLAR_LABELS`

### Scoring Registration
In `scoring.py`, the overall score formula:
```python
overall = (html * 0.12) + (sd * 0.12) + (aeo * 0.10) + (css * 0.05) + (js * 0.05) + (a11y * 0.18) + (rag * 0.10) + (agent * 0.08) + (data * 0.08) + (il * 0.12)
```
Weights MUST sum to 1.0. When adding new pillars for premium tier, either:
- Add them as sub-scores within existing pillars, OR
- Create a separate premium scoring function that doesn't affect the free tier score
