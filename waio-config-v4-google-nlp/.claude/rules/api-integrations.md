# External API Integration Rules

## Principle
External APIs are used ONLY in premium tier audits. Free tier audits must work with zero external API calls. API costs per premium audit should stay under $20 (even for 5,000-page sites with full NLP analysis).

## DataForSEO — On-Page API (Sprint 3)

### Purpose
Full website crawl with internal link extraction, orphan detection, and broken link analysis. Returns 120+ SEO metrics per page.

### Credentials
`DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` env vars. Basic auth over HTTPS.

### Workflow
1. POST task with `max_crawl_pages` (default 2000), `enable_javascript_rendering: true`
2. Poll status or use pingback URL for async notification
3. GET pages (paginate at 1,000/request): orphan flags, click depth, internal links count
4. GET links: full link graph with source, target, anchor, dofollow status

### Cost by Site Size
| Pages | JS rendering | Full browser rendering |
|-------|-------------|----------------------|
| 500   | $0.63       | $2.13                |
| 1,000 | $1.25       | $4.25                |
| 2,000 | $2.50       | $8.50                |
| 5,000 | $6.25       | $21.25               |

All GET endpoints are FREE after task completes. Minimum deposit: $50 (never expires).

### Rate Limits
2,000 tasks/minute. Up to 30 simultaneous crawl tasks.

## Google Cloud Natural Language API (Sprints 3E + 4D)

### Purpose
Content intelligence layer powered by Google's own NLP models. Provides entity detection with salience scores (what Google thinks each page is about), content classification into 1,091 categories (industry/topic detection), and sentiment analysis (content tone profiling). The "Powered by Google's NLP API" positioning is a premium differentiator.

### Setup
Enable "Cloud Natural Language API" in the same Google Cloud project ("WAIO Audit Tool") that has GSC and GA4 APIs. Uses the same service account or OAuth credentials — no new keys needed.

Add `google-cloud-language` to `requirements.txt`.

### CRITICAL: v1 vs v2 API Versioning
- **Use v1 (`language_v1`) for Entity Analysis** — only v1 returns salience scores (0.0-1.0), Wikipedia URLs, and Knowledge Graph MIDs. v2 removed salience entirely.
- **Use v2 (`language_v2`) for Content Classification** — v2 has 1,091 categories (vs v1's ~700). Returns multiple categories with confidence scores.
- Both versions can be imported and used simultaneously in the same module.

```python
from google.cloud import language_v1   # Entity analysis (salience scores)
from google.cloud import language_v2   # Content classification (1,091 categories)
```

### Endpoints and SEO Value

**Entity Analysis (`analyzeEntities`, v1)** — HIGH VALUE for Sprint 4D
- Detects 12+ entity types: PERSON, LOCATION, ORGANIZATION, EVENT, CONSUMER_GOOD, WORK_OF_ART, etc.
- Each entity returns: name, type, salience score (0.0-1.0), Wikipedia URL, Knowledge Graph MID, mentions with positions
- Salience = how central the entity is to the document. Highest salience entity = what Google considers the page to be "about"
- SEO application: Compare intended topic vs. highest-salience entity → detect focus misalignment

**Content Classification (`classifyText`, v2)** — HIGH VALUE for Sprint 3E
- Classifies text into hierarchical taxonomy: 1,091 categories, up to 4 levels deep
- Example: "/Business & Industrial/Advertising & Marketing" with confidence 0.85
- Returns multiple categories with confidence scores
- Minimum 20 tokens required for classification
- SEO application: Validate topic clusters by checking classification consistency across pages

**Sentiment Analysis (`analyzeSentiment`, v1)** — MEDIUM VALUE for Sprint 4D
- Returns score (-1.0 to +1.0) and magnitude (0.0 to ∞)
- Document-level and sentence-level breakdown
- SEO application: Content tone profiling, detecting overly sales-y content

**Entity Sentiment (`analyzeEntitySentiment`, v1)** — HIGH VALUE for Sprint 4D
- Combines entity analysis + sentiment in ONE call
- Returns everything from entity analysis PLUS per-entity and per-mention sentiment
- SEO application: Brand/competitor sentiment mapping across all pages
- Priced at combined rate but saves a separate API call

**`annotateText` method** — runs multiple analyses in one call (bills as sum of features)

### Pricing

A "unit" = 1,000 Unicode characters (including whitespace). A 5,000-character page = 5 units.

| Feature | Per 1,000 units (5K-1M) | Free tier/month |
|---------|--------------------------|-----------------|
| Entity Analysis | $1.00 | 5,000 units |
| Sentiment Analysis | $1.00 | 5,000 units |
| Entity Sentiment | $2.00 | 5,000 units |
| Content Classification | $2.00 | **30,000 units** |
| Syntax Analysis | $0.50 | 5,000 units |

### Cost per Audit (2,000 pages, ~5,000 chars each = 10,000 units per feature)

**Selective strategy (recommended):**
| Analysis | Pages analyzed | Cost |
|----------|---------------|------|
| Classification (all pages) | 2,000 | $0 (within 30K free tier) |
| Entity Analysis (top 500 pages) | 500 | ~$2.50 |
| Entity Sentiment (key 200 pages) | 200 | ~$2.00 |
| **Total per audit** | | **~$4.50** |

**Full analysis (every feature on every page):**
| Analysis | Units | Cost |
|----------|-------|------|
| Classification | 10,000 | $0-$16 |
| Entity Analysis | 10,000 | $5-$10 |
| Sentiment | 10,000 | $5-$10 |
| **Total per audit** | | **~$10-36** |

### Implementation: `backend/google_nlp_client.py`

```python
from google.cloud import language_v1
from google.cloud import language_v2
from dataclasses import dataclass

@dataclass
class NLPEntityResult:
    name: str
    entity_type: str       # PERSON, ORGANIZATION, CONSUMER_GOOD, etc.
    salience: float        # 0.0-1.0 (v1 only)
    wikipedia_url: str | None
    mentions_count: int

@dataclass
class NLPClassificationResult:
    category: str          # e.g., "/Business & Industrial/Advertising & Marketing"
    confidence: float      # 0.0-1.0

@dataclass
class NLPSentimentResult:
    score: float           # -1.0 to +1.0
    magnitude: float       # 0.0 to ∞

@dataclass
class PageNLPAnalysis:
    url: str
    classifications: list[NLPClassificationResult]
    entities: list[NLPEntityResult]
    sentiment: NLPSentimentResult | None
    primary_entity: str | None       # highest salience entity name
    primary_entity_salience: float | None
    entity_focus_aligned: bool | None  # does primary entity match H1/title intent?
```

### Input Requirements
- Submit as `PLAIN_TEXT` (not HTML) — feed Trafilatura clean_text output
- Max document size: 1 MB per request
- One document per API call (no native batching — use asyncio.gather for parallelism)
- For long pages: chunk into 500-800 word segments for more accurate classification
- Classification requires minimum 20 tokens

### Rate Limits
- 600 requests per minute (default quota)
- 800,000 requests per day
- More than sufficient for 2,000-page audits
- Use asyncio.Semaphore(50) to control concurrency and avoid hitting per-minute limits

### Selective Analysis Strategy (for cost optimization)
- **All pages:** Content classification (free tier covers it)
- **Top 500 pages** (by traffic or inbound links): Full entity analysis with salience
- **Top 200 pages** (homepage, service pages, key blog posts): Entity sentiment analysis
- **Competitor pages** (from WDF*IDF corpus): Entity analysis only (compare entity coverage)
- Page selection criteria: sort by `click_depth ASC, internal_links_count DESC` from DataForSEO data

## SerpApi — SERP Data (Sprint 4)

### Purpose
Get top-ranking URLs for WDF*IDF competitor corpus building.

### Credentials
`SERPAPI_KEY` env var.

### Cost
Free tier: 250 searches/month. Per audit: ~15-20 searches = $0.00 on free tier.

## Trafilatura — Content Extraction (Sprint 4)

### Purpose
Extract clean main content from web pages (any CMS). Feeds both WDF*IDF analysis and Google NLP API (NLP needs clean text, not raw HTML with nav/footer noise).

### Installation
`pip install trafilatura` — MIT license, no API key needed.

### Scaling
- 50-300ms per page extraction, parallelizable
- Call `trafilatura.reset_caches()` every 500 pages for 2,000+ page sites
- Fallback: BeautifulSoup `get_text()` with manual nav stripping

### Integration with Google NLP
Trafilatura clean_text → Google NLP API. The extraction step is critical because:
- NLP classification accuracy improves significantly on clean text vs. HTML with nav/footer
- Character count (billing units) drops ~60% when boilerplate is removed
- Entity salience scores are more accurate when navigation text doesn't dilute the signal

## Google Search Console API (Sprint 3)

### Purpose
Indexed URLs, search performance, sitemap data. Critical for orphan page detection.

### OAuth Setup
Same Google Cloud project as NLP API. Scope: `webmasters.readonly`.

### Rate Limits
- Search Analytics: 1,200 queries/minute
- URL Inspection: 2,000/day/property

## Google Analytics 4 Data API (Sprint 3)

### Purpose
Traffic data per URL. Additional scope: `analytics.readonly`.

## CMS Detection — Custom Patterns + Wappalyzer (Sprint 3)

### Purpose
Auto-detect CMS/framework. Zero API cost. See v3 api-integrations.md for full signature patterns.

## Phase 2 Upgrade: Firecrawl (WAIO Agent)

When Phase 2 begins: $83/month for 100,000 credits. Replace Trafilatura in RAG pipeline only.

## API Key Management
- All keys stored as env vars, NEVER in code
- Railway env vars for production, `.env` file locally (gitignored)
- `backend/config.py` module for centralized key retrieval with graceful degradation
- Google NLP uses same project credentials as GSC/GA4 — no additional key needed

### Environment Variables (add to Railway)
```
DATABASE_URL=postgresql://...      (Railway auto-provides this)
DATAFORSEO_LOGIN=...               (for On-Page API, Sprint 3)
DATAFORSEO_PASSWORD=...            (for On-Page API, Sprint 3)
GOOGLE_CLIENT_ID=...               (for GSC/GA4 OAuth + NLP, Sprint 3)
GOOGLE_CLIENT_SECRET=...           (for GSC/GA4 OAuth + NLP, Sprint 3)
GOOGLE_APPLICATION_CREDENTIALS=... (service account JSON path, for NLP API — alternative to OAuth)
SERPAPI_KEY=...                    (for WDF*IDF SERP data, Sprint 4)
```

**Note on NLP authentication:** Google NLP API can authenticate via either:
1. Service account (recommended for server-side): set `GOOGLE_APPLICATION_CREDENTIALS` to JSON key file path
2. OAuth user credentials: reuse the same OAuth flow as GSC/GA4
Option 1 is simpler for NLP since it doesn't require user consent — NLP analyzes your own extracted text, not the user's Google account data.
