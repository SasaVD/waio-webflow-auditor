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

### New Endpoints (to add)
```
# Tier system (modify existing)
POST /api/audit                     → add "tier" field to AuditRequest model

# Premium features
POST /api/audit/premium             → full premium audit with GSC/GA4/DataForSEO
GET  /api/audit/link-graph/{id}     → link graph data for D3 visualization
GET  /api/audit/wdf-idf/{id}        → WDF*IDF gap analysis results
GET  /api/audit/executive-summary/{id} → generated executive summary

# Webflow fix instructions
GET  /api/fixes/{finding_pattern}   → curated Webflow fix for a finding type
GET  /api/fixes                     → list all available fix instructions

# GSC/GA4 OAuth
GET  /api/auth/google               → initiate OAuth flow
GET  /api/auth/google/callback      → OAuth callback
GET  /api/auth/google/status        → check if tokens exist for a property
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
    max_pages: int = 50
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
All frontend API calls use this pattern. In production, requests go to same origin.
In development, they go to localhost:8000.

## CORS
Currently allows all origins (`allow_origins=["*"]`). Keep this for now.
In production SaaS phase, restrict to known domains.

## Static File Serving
Backend serves frontend build from `backend/static/`. The catch-all route serves `index.html` for SPA routing.
API routes are checked first (they start with `/api/`).
