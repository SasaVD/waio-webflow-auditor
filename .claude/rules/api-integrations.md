# External API Integration Rules

## Principle
External APIs are used ONLY in premium tier audits. Free tier audits must work with zero external API calls. API costs per premium audit should stay under $5.

## DataForSEO — On-Page API (Sprint 3)

### Purpose
Full website crawl with internal link extraction, orphan detection, and broken link analysis.

### Credentials
`DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` env vars. Basic auth over HTTPS.

### Workflow
1. POST task: `https://api.dataforseo.com/v3/on_page/task_post`
   - Set `max_crawl_pages`, `enable_javascript_rendering: true`
2. Poll status: `https://api.dataforseo.com/v3/on_page/summary/{task_id}`
3. Get pages: `https://api.dataforseo.com/v3/on_page/pages`
   - Returns `is_orphan_page` boolean, `click_depth`, `internal_links_count`
4. Get links: `https://api.dataforseo.com/v3/on_page/links`
   - Returns full link graph with source, target, anchor, dofollow status

### Cost
~$0.001625 per page (max feature set). 500-page site ≈ $0.81.

### Rate Limits
2,000 tasks per minute. No concern at our volume.

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
Per audit: ~15-20 searches = $0.00 on free tier, $0.38-$0.50 on Starter.

### Important
SerpApi returns SERP metadata only (URLs, titles, snippets). To get full page content for WDF*IDF, fetch each competitor URL separately using our existing crawler (Playwright/BeautifulSoup).

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
  - Returns sitemap metadata (not individual URLs — parse XML separately)
- URL Inspection: `POST /v1/urlInspection/index:inspect`
  - **2,000 queries/day per property** — batch intelligently for large sites
  - Returns: index status, last crawl, canonical, robots state

### Rate Limits
- Search Analytics: 1,200 queries/minute (generous)
- URL Inspection: 2,000/day/property (binding constraint for large sites)
- Overall: 50M tokens/day (not a concern)

## Google Analytics 4 Data API (Sprint 3)

### Purpose
Traffic data per URL to identify high-value orphan pages.

### OAuth Setup
Same OAuth flow as GSC. Additional scope: `https://www.googleapis.com/auth/analytics.readonly`

### Key Request
```json
{
  "dimensions": [{"name": "landingPage"}],
  "metrics": [{"name": "sessions"}, {"name": "activeUsers"}],
  "dateRanges": [{"startDate": "90daysAgo", "endDate": "today"}],
  "dimensionFilter": {
    "filter": {
      "fieldName": "sessionDefaultChannelGroup",
      "stringFilter": {"matchType": "EXACT", "value": "Organic Search"}
    }
  }
}
```

### Rate Limits
Token bucket: ~200,000 tokens/day for free GA4 properties. Not a concern at audit volume.

## API Key Management
- All keys stored as env vars, NEVER in code
- Railway env vars for production
- `.env` file locally (gitignored)
- `backend/config.py` module to centralize key retrieval with fallback to None
- Premium features gracefully degrade if keys are missing (return "not configured" instead of crashing)
