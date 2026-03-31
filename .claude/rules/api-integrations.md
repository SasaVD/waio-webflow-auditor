# External API Integration Rules

## Principle
External APIs are used ONLY in premium tier audits. Free tier audits must work with zero external API calls. API costs per premium audit should stay under $15 (even for 5,000-page sites).

## DataForSEO — On-Page API (Sprint 3)

### Purpose
Full website crawl with internal link extraction, orphan detection, and broken link analysis. Returns 120+ SEO metrics per page including click depth, orphan flags, and link graph data. Handles sites from 10 to 5,000 pages.

### Credentials
`DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` env vars. Basic auth over HTTPS.

### Workflow
1. POST task: `https://api.dataforseo.com/v3/on_page/task_post`
   - Set `max_crawl_pages` from PremiumAuditRequest.max_pages (default: 2000, max: 5000)
   - Set `enable_javascript_rendering: true` for all premium audits
   - Optional: set `load_resources: true` for full resource analysis
   - Optional: set `enable_browser_rendering: true` for Core Web Vitals ($0.00425/page)
2. Poll status: `https://api.dataforseo.com/v3/on_page/summary/{task_id}`
   - Or use pingback URL for async notification (preferred for 2,000+ page crawls)
   - Crawl time estimates: 1,000 pages ~1h, 2,000 pages ~2-4h, 5,000 pages ~4-8h with JS rendering
3. Get pages: `https://api.dataforseo.com/v3/on_page/pages`
   - Returns `is_orphan_page` boolean, `click_depth`, `internal_links_count`
   - Paginate: max 1,000 results per request, use `offset` for larger sites
4. Get links: `https://api.dataforseo.com/v3/on_page/links`
   - Returns full link graph with source, target, anchor, dofollow status, link type
   - Paginate: same 1,000 per page limit

### Cost by Site Size
| Pages | JS rendering | Full browser rendering |
|-------|-------------|----------------------|
| 500   | $0.63       | $2.13                |
| 1,000 | $1.25       | $4.25                |
| 2,000 | $2.50       | $8.50                |
| 5,000 | $6.25       | $21.25               |

All GET endpoints (pages, links, summary, resources, duplicate content) are FREE after task completes.
Minimum deposit: $50 (never expires). Results persist for 30 days.

### Rate Limits
2,000 tasks per minute. Up to 30 simultaneous crawl tasks. No `max_crawl_pages` hard ceiling documented.

### Python SDK
`pip install dataforseo-client` — official typed Python client. Or use raw HTTP with Basic Auth.

## DataForSEO — SERP API (Sprint 4, alternative to SerpApi)

### Purpose
Get top-ranking competitor URLs for WDF*IDF competitor corpus building. Alternative to SerpApi.

### Cost
- Standard queue (async, minutes): $0.0006/query → 100 queries = $0.06
- Live (real-time): $0.002/query → 100 queries = $0.20

## SerpApi — SERP Data (Sprint 4)

### Purpose
Get top-ranking URLs for WDF*IDF competitor corpus building.

### Credentials
`SERPAPI_KEY` env var. API key in query parameter.

### Workflow
1. GET `https://serpapi.com/search?engine=google&q={query}&api_key={key}&num=20`
2. Parse `organic_results[].link` for competitor URLs
3. Also extract: `related_questions` (People Also Ask) for content gap analysis

### Cost
Free tier: 250 searches/month ($0/search). Starter: $25/month for 1,000 searches.
Per audit: ~15-20 searches = $0.00 on free tier.

## Trafilatura — Content Extraction (Sprint 4)

### Purpose
Extract clean main content from web pages (any CMS), stripping navigation, footers, ads, and boilerplate. Used for WDF*IDF, content profiling, interlinking, and RAG export.

### Installation
`pip install trafilatura` — MIT license, ~15K GitHub stars, actively maintained.
No API key needed. Runs entirely in-process.

### Usage Patterns

**From pre-fetched HTML (for client pages rendered by DataForSEO or Playwright):**
```python
import trafilatura
result = trafilatura.extract(
    html_content,
    output_format="txt",
    include_links=True,
    include_tables=True,
    favor_recall=True,
    url=page_url
)
```

**From URL (for competitor pages):**
```python
downloaded = trafilatura.fetch_url("https://competitor.com/page")
result = trafilatura.extract(downloaded, output_format="txt", include_links=True)
```

### Scaling (2,000+ pages)
- Extraction speed: 50-300ms per page (single-threaded), 20-50ms in fast mode
- 2,000 pages single-threaded: 4-8 minutes; with 4-core parallelism: 1-3 minutes
- **CRITICAL: call `trafilatura.reset_caches()` every 500 pages** to prevent memory growth
- Resident memory stays under 1 GB for 5,000 pages with cache resets

### Fallback chain
1. Trafilatura with `favor_recall=True`
2. If empty or < 50 words: Trafilatura with `favor_precision=False`
3. If still empty: BeautifulSoup `get_text()` with manual nav stripping
4. Log extraction failures for review

## CMS Detection — Custom Patterns + Wappalyzer (Sprint 3)

### Purpose
Auto-detect the CMS/framework powering the client's website. Enables CMS-specific migration intelligence and reporting. Zero additional API cost.

### Implementation: `backend/cms_detector.py`

**Tier 1: Custom regex patterns (primary, free, instant)**
Check HTML content + HTTP response headers + cookies:
```python
CMS_SIGNATURES = {
    "wordpress": {
        "html": [r'/wp-content/', r'/wp-includes/', r'<meta name="generator" content="WordPress'],
        "headers": [r'X-Powered-By: PHP', r'Link:.*wp-json'],
    },
    "shopify": {
        "html": [r'cdn\.shopify\.com', r'Shopify\.theme'],
        "headers": [r'X-Shopify-Stage', r'X-ShopId'],
    },
    "webflow": {
        "html": [r'data-wf-page', r'data-wf-site', r'<meta name="generator" content="Webflow"'],
    },
    "framer": {
        "html": [r'framer-body', r'data-framer-hydrate-v2', r'framerusercontent\.com'],
    },
    "wix": {
        "html": [r'static\.parastorage\.com', r'wixstatic\.com'],
        "headers": [r'X-Wix-Request-Id'],
    },
    "squarespace": {
        "html": [r'static\.squarespace\.com', r'sqsp-', r'<meta name="generator" content="Squarespace"'],
    },
    "nextjs": {
        "html": [r'__NEXT_DATA__', r'/_next/static/'],
        "headers": [r'X-Powered-By: Next\.js'],
    },
    "gatsby": {
        "html": [r'<div id="___gatsby">', r'<meta name="generator" content="Gatsby"'],
    },
    "nuxt": {
        "html": [r'__NUXT__', r'/_nuxt/'],
    },
}
```

**Tier 2: python-Wappalyzer (fallback for unrecognized sites)**
`pip install python-Wappalyzer` — 3,000+ technology fingerprints with version detection.
Only invoked when Tier 1 returns no match. Returns CMS, JS frameworks, analytics tools, CDN info.
Note: Original Wappalyzer archived in 2023; use community fork `dochne/wappalyzer` or `wap` library.

**Tier 3: DNS CNAME check (supplemental signal)**
```python
import dns.resolver
# Check CNAME for known platform patterns
cname = dns.resolver.resolve(domain, 'CNAME')
# *.shopify.com, *.webflow.io, *.squarespace.com, *.framer.app
```
Add `dnspython` to requirements.txt.

### Output
```python
@dataclass
class CMSDetectionResult:
    platform: str          # "wordpress", "shopify", "webflow", "unknown", etc.
    version: str | None    # e.g., "6.4.3" for WordPress (if detectable)
    confidence: float      # 0.0-1.0
    detection_method: str  # "regex", "wappalyzer", "dns", "combined"
    technologies: list[str]  # additional detected tech: ["React", "Cloudflare", "Google Analytics"]
```

### Integration
- Run on homepage HTML + headers (available from first DataForSEO page result or initial fetch)
- Store `detected_cms` and `cms_version` in `audits` table
- Pass `CMSDetectionResult` to executive summary generator for CMS-aware narrative
- Pass to `cms_migration_auditor.py` (Sprint 4E) for migration intelligence

## Google Search Console API (Sprint 3)

### Purpose
Indexed URLs, search performance, sitemap data. Critical for orphan page detection.

### OAuth Setup
1. Create OAuth 2.0 credentials in Google Cloud Console
2. Scopes: `https://www.googleapis.com/auth/webmasters.readonly`
3. Redirect URI: `{app_url}/api/auth/google/callback`
4. Store refresh tokens in database (encrypted)

### Key Endpoints
- Search Analytics: `POST /webmasters/v3/sites/{site}/searchAnalytics/query`
  - Request `page` dimension to get all URLs with impressions
  - Max 25,000 rows per request, paginate with `startRow`
  - 16 months historical data
- Sitemaps: `GET /webmasters/v3/sites/{site}/sitemaps`
- URL Inspection: `POST /v1/urlInspection/index:inspect`
  - **2,000 queries/day per property** — for sites > 2,000 pages, prioritize by GA4 traffic

### Rate Limits
- Search Analytics: 1,200 queries/minute
- URL Inspection: 2,000/day/property (binding constraint for large sites)

## Google Analytics 4 Data API (Sprint 3)

### Purpose
Traffic data per URL to identify high-value orphan pages and prioritize URL inspection.

### OAuth Setup
Same OAuth flow as GSC. Additional scope: `https://www.googleapis.com/auth/analytics.readonly`

### Rate Limits
Token bucket: ~200,000 tokens/day for free GA4 properties.

## Phase 2 Upgrade: Firecrawl (WAIO Agent)

### When to add
When Phase 2 (embeddable AI chat agent) development begins. NOT needed for the $4,500 audit.

### Cost
Standard plan: $83/month for 100,000 credits. Per 2,000-page crawl: ~$1.68.

### Integration
- `pip install firecrawl-py` (v4.21+, MIT license, full async support)
- Replace Trafilatura calls in `knowledge_base_generator.py` with Firecrawl /crawl
- Keep Trafilatura for Sprint 4 competitor extraction

## API Key Management
- All keys stored as env vars, NEVER in code
- Railway env vars for production, `.env` file locally (gitignored)
- `backend/config.py` module to centralize key retrieval with fallback to None
- Premium features gracefully degrade if keys are missing

### Environment Variables (add to Railway)
```
DATABASE_URL=postgresql://...      (Railway auto-provides this)
DATAFORSEO_LOGIN=...               (for On-Page API, Sprint 3)
DATAFORSEO_PASSWORD=...            (for On-Page API, Sprint 3)
GOOGLE_CLIENT_ID=...               (for GSC/GA4 OAuth, Sprint 3)
GOOGLE_CLIENT_SECRET=...           (for GSC/GA4 OAuth, Sprint 3)
SERPAPI_KEY=...                    (for WDF*IDF SERP data, Sprint 4)
# Future Phase 2:
# FIRECRAWL_API_KEY=...            (for WAIO Agent RAG pipeline)
```
