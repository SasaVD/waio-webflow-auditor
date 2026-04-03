# Sprint Plan — WAIO Premium Audit Upgrade

## Context
Upgrading the free 10-pillar audit tool into a $4,500 premium diagnostic platform.
The tool audits any CMS (WordPress, Shopify, Next.js, Framer, Wix, Squarespace, etc.) with Webflow as the recommended migration target.
Total API cost per premium audit: ~$3-20 depending on page count and NLP depth. Revenue per audit: $4,500.

## Page Scaling Strategy
- Free tier: up to 50 pages (existing site_crawler.py with Playwright)
- Premium tier default: up to 2,000 pages (via DataForSEO On-Page API)
- Premium tier max: up to 5,000 pages (configurable via `max_pages` parameter)
- DataForSEO cost at 2,000 pages with JS rendering: ~$2.50
- Google NLP cost at 2,000 pages: ~$0-10 (classification free, entity analysis ~$5)
- Full pipeline (crawl → extract → NLP → analyze → report): 30-90 minutes for 2,000 pages

## Content Extraction Strategy
- **Phase 1 (Sprints 3-5):** Trafilatura (free, MIT-licensed) + existing Playwright crawler
- **Phase 2 (WAIO Agent):** Upgrade to Firecrawl ($83/mo) for production RAG pipeline

## Content Intelligence Strategy (Google Cloud NLP API)
- **Entity Analysis (v1 API):** Detects entities with salience scores (0.0-1.0). Salience = how central an entity is to the page. This is what Google uses internally to understand page topics. Use for content profiling and focus alignment.
- **Content Classification (v2 API):** Classifies text into 1,091 hierarchical categories (e.g., /Finance/Personal Finance). Use for topic cluster validation and industry detection. FREE up to 30,000 units/month (~3 full audits at 2,000 pages).
- **Sentiment Analysis (v1 API):** Score (-1.0 to +1.0) and magnitude. Use for content tone analysis and competitor mention detection.
- **Entity Sentiment (v1 API):** Combined entity + sentiment in one call. Use for brand/competitor sentiment mapping.
- **CRITICAL: Use v1 for entity analysis (salience scores exist only in v1). Use v2 for classification (1,091 categories vs v1's 700+). Both versions can be used simultaneously.**

## CMS Support Strategy
- All 10 audit pillars are CMS-agnostic — they analyze rendered HTML/CSS/JS output
- CMS detection runs automatically on every premium audit (Sprint 3F)
- CMS-specific intelligence layer provides migration consulting value (Sprint 4E)
- Webflow fix instructions are always included; other CMS get "why migrate" recommendations

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

## Sprint 3: Link Intelligence + CMS Detection + NLP Foundation

### 3A: DataForSEO On-Page API Integration ✅ COMPLETE
- `backend/dataforseo_client.py` — async client with pingback support
- Default crawl limit: 2,000 pages, max 5,000
- Fire-and-forget architecture: 10-pillar audit returns immediately, crawl runs in background

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
- Compute: orphan pages, link depth, hub identification, link equity distribution
- Orphan detection formula: `(sitemap ∪ gsc_urls ∪ ga4_urls) − crawler_found_urls`
- Store edges in `link_graph` table
- At 2,000+ pages: use pagination when fetching DataForSEO links endpoint

### 3D: D3 Network Visualization (Obsidian-style)
- Create `frontend/src/components/LinkGraph.tsx`
- D3 force-directed graph with dark background (surface-dark)
- Nodes colored by topic cluster (from 3E), sized by inbound links
- Orphan nodes visually distinct (red outline, floating at edges)
- Interactive: drag, zoom, hover tooltips, click-to-highlight connections
- For large sites (1,000+ pages): level-of-detail rendering
- Export as static SVG for PDF report

### 3E: Topic Cluster Detection + Google NLP Classification
- In `link_graph_auditor.py`, add cluster detection:
  - Group pages by URL path segments (e.g., /blog/*, /services/*, /products/*)
  - Score clusters on: pillar identification, bidirectional linking, anchor relevance, cohesion
  - Flag: clusters without a clear pillar page, isolated clusters, cross-cluster link gaps
- **NEW: Google NLP Content Classification layer:**
  - Create `backend/google_nlp_client.py` — async client for Cloud Natural Language API
  - Run `classifyText` (v2 API) on clean_text from every crawled page
  - Returns hierarchical category (e.g., "/Business & Industrial/Advertising & Marketing") + confidence
  - Store classification in `page_content.nlp_category` and `page_content.nlp_category_confidence`
  - **Cluster Coherence Score:** For each URL-based cluster, calculate what % of pages share the same top-level NLP category. Score > 80% = coherent cluster. Score < 60% = finding: "Your /blog/ section contains pages classified across 4 different Google categories — this dilutes topical authority"
  - **Industry Detection:** Aggregate top classifications across all pages to auto-detect site industry/niche. Store in `audits.detected_industry`
  - Cost: $0 within free tier (30,000 units/month covers ~3 audits at 2,000 pages)
- Assign cluster IDs to nodes for D3 coloring (color by NLP category, not just URL pattern)

### 3F: CMS Detection Module
- Create `backend/cms_detector.py` — detect platform from HTML + HTTP headers
- Three-tier detection: custom regex → python-Wappalyzer → DNS CNAME
- Run on homepage HTML + headers — zero additional API cost
- Store `detected_cms` and `cms_version` in `audits` table

### Definition of Done
- Premium audit crawls up to 2,000 pages (configurable to 5,000)
- CMS is auto-detected and displayed in the report header
- Every page has a Google NLP category classification
- Topic clusters are validated against NLP classifications with coherence scores
- Site industry is auto-detected from aggregated NLP classifications
- Full link graph with orphan detection (crawl + GSC + sitemap)
- Interactive Obsidian-style graph renders with NLP-based cluster coloring
- Per-audit cost < $15 even at 5,000 pages

---

## Sprint 4: Content Intelligence + Migration Consulting

### 4A: Content Extraction Layer (Trafilatura)
- Add `trafilatura` to `requirements.txt`
- Create `backend/content_extractor.py` — unified content extraction module
- For sites > 1,000 pages: call `trafilatura.reset_caches()` every 500 pages
- Fallback chain: Trafilatura → BeautifulSoup → log failure
- Store extracted clean text in `page_content.clean_text`

### 4B: WDF*IDF Pipeline
- Create `backend/wdf_idf_auditor.py`
- Step 1: Get competitor URLs from SerpApi SERP results
- Step 2: Extract competitor content using Trafilatura
- Step 3: Calculate TF-IDF vectors using scikit-learn's `TfidfVectorizer`
- Step 4: Compare audited page terms vs. competitor corpus
- Output: top 20 gap terms, over-optimized terms, coverage score per page

### 4C: Page-Pair Interlinking Opportunities
- Compute cosine similarity between all page-pair TF-IDF vectors
- For 2,000 pages: ~2M pairs, ~30 MB matrix, sub-second computation
- For 5,000+ pages: use `sparse_dot_topn` for top-K pairs only
- Cross-reference with `link_graph` table: find high-similarity pairs with no link
- Limit output to top 50 interlinking opportunities

### 4D: Content Profile + Google NLP Entity Intelligence
- Create `backend/content_profile_auditor.py`
- **Deterministic layer (no API):**
  - Reading level (Flesch-Kincaid), vocabulary type, funnel stage detection
  - Based on readability scores, term frequency analysis, heading patterns
- **Google NLP Entity Analysis layer (v1 API for salience scores):**
  - Run `analyzeEntities` on top pages (homepage, key service/product pages, top traffic pages)
  - For each page: extract top 10 entities with salience scores, types, Wikipedia URLs
  - **Entity Focus Alignment:** Compare page's intended topic (from H1/title) against highest-salience entity. Mismatch = finding: "Google sees your homepage as being about 'software development' (salience 0.82) when your H1 says 'Marketing Agency'"
  - **Site Entity Map:** Aggregate all entities across the site, ranked by frequency × salience. This is what Google understands your site to be about — present as a visual entity cloud or ranked table
  - Store top entities per page in `page_content.nlp_entities` JSONB column
- **Google NLP Sentiment layer (selective, premium pages only):**
  - Run `analyzeEntitySentiment` (v1 API, combines entities + sentiment in one call) on 100-200 key pages
  - **Brand Sentiment:** Detect mentions of client's brand and competitor brands, score sentiment for each
  - Finding example: "Your competitor 'HubSpot' is mentioned 47 times across your blog with average sentiment +0.7 — you may be inadvertently promoting them"
  - **Content Tone Profile:** Aggregate sentiment across page types. "Your service pages average +0.3 (professional), your blog averages +0.6 (enthusiastic)" — compare against Surfer SEO benchmark (87.7% of top-10 pages have positive sentiment)
- **Two-layer intelligence (TF-IDF + NLP combined):**
  - TF-IDF reveals vocabulary gaps (which terms competitors use that you don't)
  - Entity analysis reveals semantic gaps (which concepts Google associates with topic that your pages lack)
  - Cross-reference: terms in TF-IDF gaps that are also Google NLP entities = highest priority content recommendations

### 4E: CMS-Specific Migration Intelligence
- Create `backend/cms_migration_auditor.py`
- Only runs when detected CMS ≠ Webflow
- Platform-specific analysis: WordPress security/plugins, Shopify URL duplication, Wix performance, etc.
- **NEW: NLP-powered migration content mapping:**
  - Compare NLP classifications between current site sections and ideal Webflow structure
  - Quantify content gaps by category count and confidence
  - Example: "Your site has 120 pages classified as /Finance/Insurance but only 3 pages with entity salience > 0.5 for 'insurance' — most pages mention it tangentially"
- Redirect mapping estimate, migration timeline, TCO comparison

### Definition of Done
- Premium report includes WDF*IDF gap analysis table
- Interlinking opportunities with specific page pairs and suggested anchor text
- Content profile shows Google NLP entity analysis with salience scores
- Entity focus alignment findings flag pages where Google's understanding ≠ intended topic
- Brand/competitor sentiment mapping for key pages
- Two-layer content intelligence (TF-IDF + NLP entities) produces unified recommendations
- Non-Webflow sites get CMS-specific migration assessment with NLP content mapping
- "Powered by Google's Natural Language API" badge on premium reports

---

## Sprint 5: Knowledge Persistence (Bridge to WAIO Agent)

### 5A: Knowledge Base Generator
- Create `backend/knowledge_base_generator.py`
- Transform audit + crawl + NLP data into RAG-ready documents:
  - Each page → document with title, clean_text, NLP entities, NLP category, topics, links
  - Each finding → document with problem, fix instruction, evidence
  - Each fix instruction → document with steps, difficulty, context
  - CMS migration assessment → document with platform comparison + NLP content mapping
- Export format: JSON Lines for vector DB ingestion

### 5B: Cross-Audit Intelligence Queries
- Build helper functions for querying across all audits:
  - Most common findings by CMS type
  - Average scores by pillar across all sites audited
  - CMS-specific benchmarks (group by detected_cms)
  - **NEW: Industry benchmarks by NLP category** (group by detected_industry)
  - "The average Technology/Software site scores 72 on Structured Data vs 58 for Finance/Banking"
- These feed the future chatbot's training data

### Definition of Done
- Every premium audit generates RAG-ready knowledge base export (including NLP data)
- Cross-audit queries work by CMS type AND industry (via NLP classification)
- Data format is ready for Phase 2 WAIO Agent ingestion

---

6. Sprint 6: Frontend UI/UX Redesign (see .claude/rules/frontend-redesign.md)
   - 6A: TailwindCSS 4 Theme + Design System
   - 6B: React Router Restructure
   - 6C: Audit Form Redesign (Tab Selector)
   - 6D: Free Report Redesign (Hint Cards + Blurred Premium)
   - 6E: Premium Dashboard (Sidebar + Overview)
   - 6F: Link Graph Visualization
   - 6G: Export System (PDF/Excel/MD)
   - 6H: Audit Streaming UX

## Phase 2 Upgrade: Firecrawl (when WAIO Agent development begins)

When the embeddable AI chat agent moves into development:
1. Sign up for Firecrawl Standard plan ($83/mo, 100K credits)
2. Replace Trafilatura in RAG pipeline only
3. Keep Trafilatura for competitor extraction in audit tool
4. Google NLP data carries forward into agent knowledge base

