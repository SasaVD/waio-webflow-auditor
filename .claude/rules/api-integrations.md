# External API Integration Rules

## Principle
External APIs are used ONLY in premium tier audits. Free tier audits must work with zero external API calls. API costs per premium audit should stay under $5.

## DataForSEO — On-Page API (Sprint 3)

### Purpose
Full website crawl with internal link extraction, orphan detection, and broken link analysis. Returns 120+ SEO metrics per page including click depth, orphan flags, and link graph data.

### Credentials
`DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` env vars. Basic auth over HTTPS.

### Workflow
1. POST task: `https://api.dataforseo.com/v3/on_page/task_post`
   - Set `max_crawl_pages`, `enable_javascript_rendering: true`
   - Optional: set `load_resources: true` for full resource analysis
2. Poll status: `https://api.dataforseo.com/v3/on_page/summary/{task_id}`
   - Or use pingback URL for async notification
3. Get pages: `https://api.dataforseo.com/v3/on_page/pages`
   - Returns `is_orphan_page` boolean, `click_depth`, `internal_links_count`
   - Also: title, description, status code, canonical, indexability
4. Get links: `https://api.dataforseo.com/v3/on_page/links`
   - Returns full link graph with source, target, anchor, dofollow status, link type

### Cost
- Basic crawl (60+ params): $0.000125/page → 500 pages = $0.06
- With JS rendering: $0.00125/page → 500 pages = $0.63
- Full browser (Core Web Vitals): $0.00425/page → 500 pages = $2.13
- All GET endpoints (pages, links, summary) are FREE after task completes
- Minimum deposit: $50 (never expires)

### Rate Limits
2,000 tasks per minute. Up to 30 simultaneous crawl tasks. No concern at our volume.

### Python SDK
`pip install dataforseo-client` — official typed Python client. Or use raw HTTP with Basic Auth.

## DataForSEO — SERP API (Sprint 4, alternative to SerpApi)

### Purpose
Get top-ranking URLs for WDF*IDF competitor corpus building. Alternative to SerpApi.

### Workflow
1. POST: `https://api.dataforseo.com/v3/serp/google/organic/live`
2. Results include: organic results with URL, title, snippet, position, SERP features

### Cost
- Standard queue (async, minutes): $0.0006/query → 100 queries = $0.06
- Live (real-time): $0.002/query → 100 queries = $0.20

### When to use instead of SerpApi
If you're already using DataForSEO for On-Page API, consolidating SERP queries here avoids a second vendor. Both are viable — DataForSEO is 40% cheaper, SerpApi has a free tier.

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
SerpApi returns SERP metadata only (URLs, titles, snippets). To get full page content for WDF*IDF, extract each competitor URL separately using Trafilatura (see below).

## Trafilatura — Content Extraction (Sprint 4)

### Purpose
Extract clean main content from web pages, stripping navigation, footers, ads, and boilerplate. Used for WDF*IDF competitor analysis, content profiling, and RAG knowledge base export. Replaces the need for custom boilerplate-removal code.

### Installation
`pip install trafilatura` — MIT license, ~15K GitHub stars, actively maintained.
No API key needed. No external service dependency. Runs entirely in-process.

### Usage Patterns

**Extract from pre-fetched HTML (for Webflow client pages already rendered by Playwright):**
```python
import trafilatura

# html_content already fetched by site_crawler.py via Playwright
result = trafilatura.extract(
    html_content,
    output_format="txt",       # or "xml" for structured output with headings
    include_links=True,        # preserve internal/external links
    include_tables=True,       # preserve table content
    favor_recall=True,         # prefer more content over precision
    url=page_url               # helps with relative link resolution
)
```

**Extract from URL (for competitor pages — Trafilatura handles fetching):**
```python
downloaded = trafilatura.fetch_url("https://competitor.com/page")
result = trafilatura.extract(downloaded, output_format="txt", include_links=True)
```

**Extract with metadata:**
```python
result = trafilatura.bare_extraction(
    html_content,
    url=page_url,
    with_metadata=True
)
# Returns dict with: text, title, author, date, description, sitename, language
```

### What Trafilatura handles
- Statistical main content detection (separates article body from chrome)
- Navigation, footer, sidebar, cookie banner removal
- Comment section removal
- Ad and widget removal
- Works on arbitrary websites (WordPress, Shopify, custom, etc.)
- Language detection
- Date extraction from article metadata

### Known limitations
- Does NOT render JavaScript. For JS-heavy competitor sites (React SPAs, Next.js), content may be incomplete.
  - Mitigation: For critical competitors, pipe Playwright-rendered HTML through Trafilatura instead of using `fetch_url()`.
  - Most marketing/content sites render server-side and work fine with direct fetch.
- Output is plain text, not markdown. Heading structure is partially preserved in XML output mode but less clean than Firecrawl's markdown.
- No structured entity extraction (no equivalent to Firecrawl's /extract endpoint).

### Fallback chain for content extraction
1. Try Trafilatura with `favor_recall=True`
2. If result is empty or < 50 words, try Trafilatura with `favor_precision=False`
3. If still empty, fall back to BeautifulSoup `get_text()` with manual `<nav>`, `<footer>`, `<header>`, `<aside>` stripping
4. Log extraction failures for review

### Performance
- Extraction speed: ~50-200ms per page (in-process, no network call for pre-fetched HTML)
- Memory: negligible
- No rate limits, no API costs, no vendor dependency

### Integration point
Create `backend/content_extractor.py` as a unified module:
```python
@dataclass
class CleanContent:
    clean_text: str
    title: str | None
    description: str | None
    word_count: int
    language: str | None
    extraction_method: str  # "trafilatura" | "beautifulsoup_fallback"
```

Store `clean_text` in `page_content.clean_text` column for WDF*IDF and RAG use.

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

## Phase 2 Upgrade: Firecrawl (WAIO Agent)

### When to add
When Phase 2 (embeddable AI chat agent) development begins. NOT needed for the $4,500 audit.

### Why upgrade from Trafilatura
- LLM-optimized markdown output (67% fewer tokens = cheaper embeddings + better retrieval)
- Heading structure preserved in markdown (enables intelligent semantic chunking)
- Native LangChain FireCrawlLoader and LlamaIndex FireCrawlWebReader integrations
- /extract endpoint for structured entity extraction → knowledge graphs
- /map endpoint for instant URL discovery (2-3 seconds, no crawling)
- Anti-bot bypass and rotating proxies for difficult sites
- Cleaner content = fewer RAG hallucinations = better agent responses

### Cost
Standard plan: $83/month for 100,000 credits (1 credit = 1 page).
Per 500-page crawl: ~$0.42. Trivial against agent recurring revenue.

### Integration
- `pip install firecrawl-py` (v4.21+, MIT license, full async support)
- `FIRECRAWL_API_KEY` env var
- Replace Trafilatura calls in `knowledge_base_generator.py` with Firecrawl /crawl
- Keep Trafilatura for Sprint 4 competitor extraction (audit tool)

## API Key Management
- All keys stored as env vars, NEVER in code
- Railway env vars for production
- `.env` file locally (gitignored)
- `backend/config.py` module to centralize key retrieval with fallback to None
- Premium features gracefully degrade if keys are missing (return "not configured" instead of crashing)

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
