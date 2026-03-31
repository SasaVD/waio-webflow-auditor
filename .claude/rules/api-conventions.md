# API Conventions — WAIO Audit Tool

## Endpoint Patterns

### Existing Endpoints (DO NOT BREAK)
```
GET  /api/health                    → {"status": "ok"}
POST /api/audit                     → single page audit
POST /api/audit/multi               → multi-page site crawl
POST /api/audit/competitive         → competitive benchmark
GET  /api/audit/status/{job_id}     → poll crawl progress
GET  /api/audit/page/{job_id}       → single page from crawl
GET  /api/history?url=              → audit history for URL
POST /api/schedules                 → create scheduled audit
GET  /api/schedules                 → list schedules
PUT  /api/schedules/{id}            → update schedule
DELETE /api/schedules/{id}          → delete schedule
POST /api/export/pdf                → generate PDF
POST /api/export/md                 → generate Markdown
POST /api/send-report               → email PDF report
```

### New Endpoints (added in Sprints 2-4)
```
# Tier system (modifies existing)
POST /api/audit                     → "tier" field in AuditRequest model

# Premium features (Sprint 2)
POST /api/audit/premium             → full premium audit with all integrations

# Webflow fix instructions (Sprint 2B)
GET  /api/fixes/{finding_pattern}   → curated Webflow fix for a finding type
GET  /api/fixes                     → list all available fix instructions

# Link intelligence (Sprint 3)
GET  /api/audit/link-graph/{id}     → link graph data for D3 visualization
GET  /api/audit/clusters/{id}       → topic cluster data

# CMS detection (Sprint 3F)
GET  /api/audit/cms/{id}            → CMS detection result for an audit

# GSC/GA4 OAuth (Sprint 3B)
GET  /api/auth/google               → initiate OAuth flow
GET  /api/auth/google/callback      → OAuth callback
GET  /api/auth/google/status        → check if tokens exist for a property

# Content intelligence (Sprint 4)
GET  /api/audit/wdf-idf/{id}        → WDF*IDF gap analysis results
GET  /api/audit/interlinking/{id}   → page-pair interlinking opportunities
GET  /api/audit/content-profile/{id} → content profile and persona

# Migration assessment (Sprint 4E)
GET  /api/audit/migration/{id}      → CMS migration assessment (NULL for Webflow sites)

# Executive summary (Sprint 2A)
GET  /api/audit/executive-summary/{id} → generated executive summary
```

## Request/Response Patterns

### Pydantic Models
```python
class AuditRequest(BaseModel):
    url: HttpUrl
    tier: str = "free"  # "free" or "premium"

class PremiumAuditRequest(BaseModel):
    url: HttpUrl
    competitor_urls: list[str] = []
    gsc_property: str | None = None
    target_keyword: str | None = None  # for WDF*IDF
    max_pages: int = 2000              # default 2,000 pages, max 5,000
    # CMS is auto-detected — no client input needed
```

### CMS Detection Response
```python
class CMSDetectionResult(BaseModel):
    platform: str          # "wordpress", "shopify", "webflow", "unknown"
    version: str | None
    confidence: float      # 0.0-1.0
    detection_method: str  # "regex", "wappalyzer", "dns", "combined"
    technologies: list[str]  # additional detected tech
```

### Migration Assessment Response (included in report JSON)
```python
class MigrationAssessment(BaseModel):
    source_cms: str                    # detected current CMS
    target_cms: str = "webflow"        # always Webflow
    platform_issues: list[dict]        # CMS-specific SEO problems found
    webflow_advantages: list[dict]     # how Webflow solves each issue
    redirect_count: int                # unique URLs needing 301 redirects
    migration_timeline: str            # "small: 2-4 weeks", etc.
    tco_comparison: dict | None        # total cost of ownership if estimable
```

### Error Handling Pattern
```python
@app.post("/api/audit")
async def perform_audit(request: AuditRequest):
    try:
        # ... audit logic
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Audit failed for {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")
```

### Frontend API Base
```typescript
const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';
```
All frontend API calls use this pattern.

## CORS
Currently allows all origins (`allow_origins=["*"]`). Keep this for now.

## Static File Serving
Backend serves frontend build from `backend/static/`. The catch-all route serves `index.html` for SPA routing. API routes are checked first (they start with `/api/`).
