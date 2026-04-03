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
# Premium audit (Sprint 2)
POST /api/audit/premium             → full premium audit with all integrations

# Webflow fix instructions (Sprint 2B)
GET  /api/fixes/{finding_pattern}   → curated Webflow fix
GET  /api/fixes                     → list all fix instructions

# DataForSEO (Sprint 3A)
GET  /api/dataforseo/pingback       → webhook DataForSEO calls when crawl finishes
GET  /api/audit/crawl-status/{task_id} → poll crawl progress

# Link intelligence (Sprint 3C-3E)
GET  /api/audit/link-graph/{id}     → link graph data for D3 visualization
GET  /api/audit/clusters/{id}       → topic cluster data with NLP classifications

# CMS detection (Sprint 3F)
GET  /api/audit/cms/{id}            → CMS detection result

# GSC/GA4 OAuth (Sprint 3B)
GET  /api/auth/google               → initiate OAuth flow
GET  /api/auth/google/callback      → OAuth callback
GET  /api/auth/google/status        → check token status

# Content intelligence (Sprint 4)
GET  /api/audit/wdf-idf/{id}        → WDF*IDF gap analysis results
GET  /api/audit/interlinking/{id}   → page-pair interlinking opportunities
GET  /api/audit/content-profile/{id} → content profile with NLP entity analysis
GET  /api/audit/nlp-analysis/{id}   → full NLP results (entities, classification, sentiment)

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
    tier: str = "free"

class PremiumAuditRequest(BaseModel):
    url: HttpUrl
    competitor_urls: list[str] = []
    gsc_property: str | None = None
    target_keyword: str | None = None
    max_pages: int = 2000
    # NLP analysis depth (controls cost)
    nlp_classification: bool = True       # classify all pages (free tier)
    nlp_entity_analysis: bool = True      # entity analysis on top pages
    nlp_sentiment: bool = False           # entity sentiment on key pages (opt-in)
```

### CMS Detection Response
```python
class CMSDetectionResult(BaseModel):
    platform: str
    version: str | None
    confidence: float
    detection_method: str
    technologies: list[str]
```

### NLP Analysis Response
```python
class NLPPageAnalysis(BaseModel):
    url: str
    # Classification (v2 API)
    category: str | None               # "/Business & Industrial/..."
    category_confidence: float | None
    all_categories: list[dict] | None   # [{"category": "...", "confidence": 0.85}]
    # Entity Analysis (v1 API)
    primary_entity: str | None          # highest salience entity
    primary_entity_salience: float | None
    entity_focus_aligned: bool | None   # matches H1/title?
    top_entities: list[dict] | None     # [{"name": "...", "type": "...", "salience": 0.73}]
    # Sentiment (v1 API, selective)
    sentiment_score: float | None       # -1.0 to +1.0
    sentiment_magnitude: float | None

class SiteNLPSummary(BaseModel):
    detected_industry: str              # top classification across all pages
    industry_confidence: float
    industry_breakdown: list[dict]      # [{"category": "...", "page_count": 45}]
    top_entities_site_wide: list[dict]  # aggregated entities across all pages
    cluster_coherence_scores: dict      # {"/blog/": 0.85, "/services/": 0.92}
    brand_sentiment: dict | None        # {"brand": "+0.4", "competitor_x": "+0.7"}
```

### Migration Assessment Response
```python
class MigrationAssessment(BaseModel):
    source_cms: str
    target_cms: str = "webflow"
    platform_issues: list[dict]
    webflow_advantages: list[dict]
    redirect_count: int
    migration_timeline: str
    tco_comparison: dict | None
    nlp_content_mapping: dict | None    # NLP category gaps between platforms
```

### Error Handling Pattern
```python
@app.post("/api/audit")
async def perform_audit(request: AuditRequest):
    try:
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

## CORS
Currently allows all origins (`allow_origins=["*"]`).

## Static File Serving
Backend serves frontend build from `backend/static/`. API routes checked first (`/api/`).
