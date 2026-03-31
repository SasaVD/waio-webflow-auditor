# Sprint Plan — WAIO Premium Audit Upgrade

## Context
Upgrading the free 10-pillar audit tool into a $4,500 premium diagnostic platform.
The tool audits any CMS (WordPress, Shopify, Next.js, Framer, Wix, Squarespace, etc.) with Webflow as the recommended migration target.
Total API cost per premium audit: ~$3-10 depending on page count. Revenue per audit: $4,500.

## Page Scaling Strategy
- Free tier: up to 50 pages (existing site_crawler.py with Playwright)
- Premium tier default: up to 2,000 pages (via DataForSEO On-Page API)
- Premium tier max: up to 5,000 pages (configurable via `max_pages` parameter)
- DataForSEO cost at 2,000 pages with JS rendering: ~$2.50
- DataForSEO cost at 5,000 pages with JS rendering: ~$6.25
- TF-IDF pairwise similarity at 2,000 pages: ~30 MB memory, sub-second computation
- Trafilatura extraction at 2,000 pages: ~4-8 minutes (parallelizable to 1-3 minutes)
- Full pipeline (crawl → extract → analyze → report): 30-90 minutes for 2,000 pages

## Content Extraction Strategy
- **Phase 1 (Sprints 3-5):** Trafilatura (free, MIT-licensed Python library) + existing Playwright crawler
  - Client sites (any CMS): DataForSEO crawls + Trafilatura extracts clean text
  - Competitor sites: Trafilatura fetches + extracts directly
- **Phase 2 (WAIO Agent):** Upgrade to Firecrawl ($83/mo) for production RAG pipeline

## CMS Support Strategy
- All 10 audit pillars are CMS-agnostic — they analyze rendered HTML/CSS/JS output
- CMS detection runs automatically on every premium audit (Sprint 3F)
- CMS-specific intelligence layer provides migration consulting value (Sprint 4E)
- Webflow fix instructions are always included; other CMS get "why migrate" recommendations
- When detected CMS is already Webflow, skip migration section, show Webflow-specific fixes

## Sprint 1: Database + Tier System (Foundation) ✅ COMPLETE

### 1A: PostgreSQL Migration ✅
### 1B: Audit Tier System ✅
### 1C: Normalized Data Storage ✅

---

## Sprint 2: Premium Deliverables (Immediate $4,500 Value) ✅ COMPLETE

### 2A: Executive Summary Generator ✅
### 2B: Webflow Fix Knowledge Base ✅
### 2C: Default Competitor Benchmarking ✅

---

## Sprint 3: Link Intelligence + CMS Detection

### 3A: DataForSEO On-Page API Integration
- Create `backend/dataforseo_client.py` — async client for On-Page API
- Workflow: POST task → poll status via pingback/webhook → GET results
- Set `max_crawl_pages` from PremiumAuditRequest.max_pages (default: 2000, max: 5000)
- Set `enable_javascript_rendering: true` for all premium audits
- Extract: all internal links, orphan flags, click depth, broken links, 120+ SEO params
- Store raw DataForSEO page data for enriching other modules
- Cost: ~$2.50 per 2,000-page site with JS rendering
- Requires `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` env vars

### 3B: GSC/GA4 OAuth Integration
- Create `backend/google_auth.py` — OAuth 2.0 flow for GSC + GA4
- Scopes: `webmasters.readonly`, `analytics.readonly`
- Store refresh tokens in database (encrypted)
- Pull: indexed URLs, search performance, sitemap URLs, traffic per page
- URL Inspection API: 2,000 queries/day limit — batch intelligently
- For sites > 2,000 pages, prioritize URL inspection by traffic (GA4) or impressions (GSC)

### 3C: Site-Wide Link Graph Analysis
- Create `backend/link_graph_auditor.py`
- Input: crawl data (from DataForSEO) + GSC data + sitemap
- Compute: orphan pages, link depth (BFS from homepage), hub identification, link equity distribution
- Orphan detection formula: `(sitemap ∪ gsc_urls ∪ ga4_urls) − crawler_found_urls`
- Store edges in `link_graph` table
- Output: findings + graph data JSON for D3 visualization
- At 2,000+ pages: use pagination when fetching DataForSEO links endpoint (1,000 results per call)

### 3D: D3 Network Visualization (Obsidian-style)
- Create `frontend/src/components/LinkGraph.tsx`
- D3 force-directed graph with dark background (surface-dark)
- Nodes colored by topic cluster, sized by inbound links
- Orphan nodes visually distinct (red outline, floating at edges)
- Interactive: drag, zoom, hover tooltips, click-to-highlight connections
- For large sites (1,000+ pages): implement level-of-detail rendering
  - Default view: show top 200 pages by inbound links + all orphan pages
  - Cluster view: show cluster centroids, expand on click
  - Full view: toggle to render all nodes (warn user about performance)
- Export as static SVG for PDF report
- Backend endpoint: GET `/api/audit/link-graph/{audit_id}`

### 3E: Topic Cluster Detection
- In `link_graph_auditor.py`, add cluster detection:
  - Group pages by URL path segments (e.g., /blog/*, /services/*, /products/*)
  - Score clusters on: pillar identification, bidirectional linking, anchor relevance, cohesion
  - Flag: clusters without a clear pillar page, isolated clusters, cross-cluster link gaps
- Assign cluster IDs to nodes for D3 coloring
- For Shopify sites: detect /collections/*/products/* duplicate URL patterns and flag in findings

### 3F: CMS Detection Module
- Create `backend/cms_detector.py` — detect platform from HTML + HTTP headers
- Three-tier detection with fallback chain:
  1. **Custom regex patterns** (primary — fast, free, handles 90%+ of sites):
     - WordPress: `/wp-content/`, `/wp-includes/`, `<meta name="generator" content="WordPress">`
     - Shopify: `cdn.shopify.com`, `Shopify.theme`, `X-Shopify-Stage` header
     - Webflow: `data-wf-page`, `data-wf-site`, `<meta name="generator" content="Webflow">`
     - Framer: `framer-body` class, `data-framer-hydrate-v2`, `framerusercontent.com`
     - Wix: `static.parastorage.com`, `X-Wix-Request-Id` header
     - Squarespace: `static.squarespace.com`, `sqsp-` classes, `<meta name="generator" content="Squarespace">`
     - Next.js: `__NEXT_DATA__` script tag, `/_next/static/`, `X-Powered-By: Next.js` header
     - Gatsby: `<div id="___gatsby">`, `<meta name="generator" content="Gatsby">`
     - Nuxt: `__NUXT__` script tag, `/_nuxt/` paths
  2. **python-Wappalyzer** (fallback for unrecognized sites): 3,000+ tech fingerprints
  3. **DNS CNAME check** (supplemental): `*.shopify.com`, `*.webflow.io`, `*.squarespace.com` CNAME patterns
- Run on the first page fetched (homepage HTML + headers) — zero additional API cost
- Output: `CMSDetectionResult` dataclass with `platform`, `version`, `confidence`, `detection_method`
- Store in `audits` table: `detected_cms` and `cms_version` columns
- Include CMS detection result in report JSON and executive summary

### Definition of Done
- Premium audit crawls up to 2,000 pages by default (configurable to 5,000)
- CMS is auto-detected and displayed in the report header
- Full link graph with orphan detection (crawl + GSC + sitemap)
- Interactive Obsidian-style graph renders in the report (with LOD for large sites)
- Topic clusters are detected and scored
- Per-audit DataForSEO cost < $10 even at 5,000 pages

---

## Sprint 4: Content Intelligence + Migration Consulting

### 4A: Content Extraction Layer (Trafilatura)
- Add `trafilatura` to `requirements.txt` (MIT license, ~15K stars, maintained)
- Create `backend/content_extractor.py` — unified content extraction module:
  - `extract_from_html(html: str, url: str) -> CleanContent` — for pages already fetched
  - `extract_from_url(url: str) -> CleanContent` — for competitor pages
  - `CleanContent` dataclass: clean_text, title, description, word_count, language, headings[]
- For sites > 1,000 pages: call `trafilatura.reset_caches()` every 500 pages to prevent memory growth
- Fallback: if Trafilatura extraction fails, fall back to BeautifulSoup `get_text()` with manual nav stripping
- Store extracted clean text in `page_content.clean_text` column

### 4B: WDF*IDF Pipeline
- Create `backend/wdf_idf_auditor.py`
- Step 1: Get competitor URLs from SerpApi SERP results (or from competitive audit)
- Step 2: Extract competitor content using `content_extractor.py` (Trafilatura)
- Step 3: Calculate TF-IDF vectors using scikit-learn's `TfidfVectorizer`
  - For 2,000-page corpora: sparse matrix ~7 MB, fit_transform < 10 seconds
  - Use `max_features=30000` and `min_df=2` to keep vocabulary manageable
- Step 4: Compare audited page terms vs. competitor corpus
- Output: top 20 gap terms, over-optimized terms, coverage score per page
- Frontend: table showing term, your score, competitor average, gap direction

### 4C: Page-Pair Interlinking Opportunities
- Compute cosine similarity between all page-pair TF-IDF vectors (from clean_text)
- For 2,000 pages: ~2M pairs, ~30 MB matrix, sub-second computation via sparse dot product
- For 5,000+ pages: use `sparse_dot_topn` for top-K pairs only (avoids full N×N matrix)
- Cross-reference with `link_graph` table: find high-similarity pairs with no link
- Generate findings: "Page A and Page B share 73% semantic overlap but are not linked"
- Include recommended anchor text (most distinctive shared terms)
- Limit output to top 50 interlinking opportunities (sorted by similarity × pagerank product)

### 4D: Content Profile & Implicit Persona
- Create `backend/content_profile_auditor.py`
- Input: clean_text from Trafilatura extraction (not raw HTML)
- Infer from content: reading level (Flesch-Kincaid), vocabulary type (technical/consumer), funnel stage
- Present as: "Your content reads at Grade 11.2, uses enterprise terminology, addresses decision-stage queries"
- Flag funnel gaps: "No content addressing awareness-stage queries for your detected topics"
- Deterministic — no LLM needed. Based on readability scores, term frequency analysis, heading patterns

### 4E: CMS-Specific Migration Intelligence
- Create `backend/cms_migration_auditor.py`
- Input: `detected_cms` from Sprint 3F + all audit findings + link graph data
- Only runs when detected CMS is NOT Webflow (skip for Webflow sites — show fixes instead)
- Produces a "Migration Assessment" report section with:

  **For WordPress sites:**
  - Security exposure score (detect vulnerable plugin patterns, outdated PHP hints)
  - Plugin bloat analysis (count external plugin JS/CSS, estimate removal savings)
  - Theme complexity assessment (page builder detection: Elementor, Divi, WPBakery)
  - Maintenance burden summary (hosting, caching, security, updates)
  - Webflow advantage: managed hosting, zero plugins, automatic SSL, no PHP

  **For Shopify sites:**
  - Duplicate URL pattern detection (`/collections/X/products/Y` vs `/products/Y`)
  - URL structure rigidity analysis (mandatory `/products/`, `/collections/` prefixes)
  - App bloat detection (third-party Shopify app JS injection count)
  - Redirect limit awareness (100,000 limit — flag if site approaches this)
  - Webflow advantage: clean custom URLs, full URL control, no forced prefixes

  **For Wix sites:**
  - Performance benchmark vs. Google thresholds (LCP, CLS, FID/INP)
  - JavaScript rendering overhead measurement
  - Content export limitation warning
  - Webflow advantage: clean HTML output, CDN-optimized, better Core Web Vitals

  **For Squarespace sites:**
  - Heading hierarchy analysis (H1-H4 only limitation)
  - Structured data limitations (template-driven schema)
  - Performance gap quantification
  - Webflow advantage: full heading control, custom schema, faster rendering

  **For Next.js / Gatsby / Nuxt sites:**
  - SSR vs SSG vs CSR detection (check for `__NEXT_DATA__`, pre-rendered content)
  - Hydration issue detection (empty body on initial HTML fetch)
  - Canonical tag presence check (50% of Next.js sites lack them per SALT.agency study)
  - 404 handling check (82% return 200 for non-existent URLs)
  - Webflow advantage: server-rendered HTML, proper status codes, built-in SEO controls

  **For all non-Webflow CMS:**
  - Total cost of ownership comparison (current platform costs vs. Webflow subscription)
  - Redirect mapping requirements estimate (count unique URLs needing 301 redirects)
  - Content migration scope (page count, media assets, CMS collection items)
  - Timeline estimate based on site complexity (small: 2-4 weeks, medium: 4-8 weeks, large: 8-16 weeks)

- Store migration assessment in `migration_assessment` JSONB column on `audits` table
- Frontend: new `MigrationAssessment.tsx` component (only renders when CMS ≠ Webflow)
- Include migration summary in executive summary generator context

### Definition of Done
- Premium report includes WDF*IDF gap analysis table
- Interlinking opportunities with specific page pairs and suggested anchor text
- Content profile with implicit persona and funnel gap analysis
- Non-Webflow sites get a CMS-specific migration assessment with quantified gaps
- Migration assessment integrates into the executive summary narrative
- Trafilatura handles 2,000+ pages with cache resets, no memory issues

---

## Sprint 5: Knowledge Persistence (Bridge to WAIO Agent)

### 5A: Knowledge Base Generator
- Create `backend/knowledge_base_generator.py`
- Transform audit + crawl data into RAG-ready documents:
  - Each page → document with title, clean_text (from Trafilatura), topics, links, schema types
  - Each finding → document with problem, fix instruction, evidence, CMS context
  - Each fix instruction → document with steps, difficulty, context
  - CMS migration assessment → document with platform comparison data
- Export format: JSON Lines (one document per line) for vector DB ingestion
- Store in `page_content` table with clean_text for future vector DB indexing
- NOTE: When upgrading to Phase 2, replace Trafilatura extraction with Firecrawl /crawl

### 5B: Cross-Audit Intelligence Queries
- Build helper functions for querying across all audits:
  - Most common findings by CMS type (e.g., "WordPress sites average 42 on JS Bloat")
  - Average scores by pillar across all Webflow sites audited
  - CMS-specific benchmarks (group by detected_cms)
  - Migration success metrics (if post-migration re-audit data exists)
- These feed the future chatbot's training data

### Definition of Done
- Every premium audit generates RAG-ready knowledge base export
- Cross-audit queries work for benchmarking and trend analysis (including by CMS)
- Data format is ready for Phase 2 WAIO Agent ingestion
- Firecrawl upgrade path documented for Phase 2 transition

---

## Phase 2 Upgrade: Firecrawl (when WAIO Agent development begins)

When the embeddable AI chat agent moves into development:
1. Sign up for Firecrawl Standard plan ($83/mo, 100K credits)
2. Add `FIRECRAWL_API_KEY` to Railway env vars
3. Create `backend/firecrawl_client.py` (replaces Trafilatura in the RAG pipeline only)
4. Firecrawl /crawl → clean markdown → chunk by headings → embed → Pinecone/Qdrant
5. Firecrawl /extract → structured entities → knowledge graph
6. Keep Trafilatura as fallback for competitor extraction in the audit tool
