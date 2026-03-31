# Sprint Plan — WAIO Premium Audit Upgrade

## Context
Upgrading the free 10-pillar audit tool into a $4,500 premium diagnostic platform.
Total API cost per premium audit: ~$1-2 (DataForSEO + SerpApi). Revenue per audit: $4,500.

## Content Extraction Strategy
- **Phase 1 (Sprints 3-5):** Trafilatura (free, MIT-licensed Python library) + existing Playwright crawler
  - Webflow client sites: Playwright renders JS → Trafilatura extracts clean text from HTML
  - Competitor sites: Trafilatura fetches + extracts (handles arbitrary CMS/frameworks)
  - Sufficient for WDF*IDF, content profiling, interlinking analysis, and basic RAG export
- **Phase 2 (WAIO Agent):** Upgrade to Firecrawl ($83/mo) for production RAG pipeline
  - LLM-optimized markdown output (67% fewer tokens than HTML)
  - Native LangChain/LlamaIndex integrations
  - /extract endpoint for structured entity extraction and knowledge graphs
  - Quality gap vs. Trafilatura matters when RAG response accuracy = revenue

## Sprint 1: Database + Tier System (Foundation) ✅ COMPLETE

### 1A: PostgreSQL Migration ✅
- `backend/db_postgres.py` — async PostgreSQL module via asyncpg
- `backend/db_router.py` — auto-selects Postgres/SQLite based on DATABASE_URL
- `backend/migrations/001_initial.sql` — full normalized schema
- SQLite kept as local dev fallback

### 1B: Audit Tier System ✅
- `AuditRequest` model includes `tier: str = "free"`
- `PremiumAuditRequest` model with competitor_urls, gsc_property, target_keyword, max_pages
- POST `/api/audit/premium` endpoint with hooks for Sprint 2-4 modules

### 1C: Normalized Data Storage ✅
- Reports decomposed into `pillar_scores`, `findings`, `page_content` tables
- `report_json` JSONB column retained for backward compatibility

---

## Sprint 2: Premium Deliverables (Immediate $4,500 Value) ✅ COMPLETE

### 2A: Executive Summary Generator ✅
- `backend/executive_summary_generator.py` — template-based, no LLM dependency
- 6 sections: assessment, risks, strengths, ROI projection, action plan, competitor context
- `ExecutiveSummary.tsx` component for premium reports

### 2B: Webflow Fix Knowledge Base ✅
- `backend/webflow_fixes.py` — 54 curated fix entries across all 10 pillars
- GET `/api/fixes` and `/api/fixes/{pattern}` endpoints
- "How to Fix in Webflow" button with AnimatePresence expand/collapse

### 2C: Default Competitor Benchmarking ✅
- Premium endpoint runs `run_competitive_audit()` when competitor_urls provided
- `AuditForm.tsx` updated with premium tier toggle and competitor URL inputs
- `AuditReport.tsx` shows competitive ranking bar for premium reports

---

## Sprint 3: Link Intelligence (Architecture Analysis)

### 3A: DataForSEO On-Page API Integration
- Create `backend/dataforseo_client.py` — async client for On-Page API
- Workflow: POST task → poll status via pingback/webhook → GET results
- Extract: all internal links, orphan flags, click depth, broken links, 120+ SEO params
- Store raw DataForSEO page data for enriching other modules
- Cost: ~$0.63-$2.13 per 500-page site (depending on JS rendering + features)
- Requires `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` env vars

### 3B: GSC/GA4 OAuth Integration
- Create `backend/google_auth.py` — OAuth 2.0 flow for GSC + GA4
- Scopes: `webmasters.readonly`, `analytics.readonly`
- Store refresh tokens in database (encrypted)
- Pull: indexed URLs, search performance, sitemap URLs, traffic per page
- URL Inspection API: 2,000 queries/day limit — batch intelligently

### 3C: Site-Wide Link Graph Analysis
- Create `backend/link_graph_auditor.py`
- Input: crawl data (from DataForSEO) + GSC data + sitemap
- Compute: orphan pages, link depth (BFS from homepage), hub identification, link equity distribution
- Orphan detection formula: `(sitemap ∪ gsc_urls ∪ ga4_urls) − crawler_found_urls`
- Store edges in `link_graph` table
- Output: findings + graph data JSON for D3 visualization

### 3D: D3 Network Visualization (Obsidian-style)
- Create `frontend/src/components/LinkGraph.tsx`
- D3 force-directed graph with dark background (surface-dark)
- Nodes colored by topic cluster, sized by inbound links
- Orphan nodes visually distinct (red outline, floating at edges)
- Interactive: drag, zoom, hover tooltips, click-to-highlight connections
- Export as static SVG for PDF report
- Backend endpoint: GET `/api/audit/link-graph/{audit_id}`

### 3E: Topic Cluster Detection
- In `link_graph_auditor.py`, add cluster detection:
  - Group pages by URL path segments (e.g., /blog/*, /services/*)
  - Score clusters on: pillar identification, bidirectional linking, anchor relevance, cohesion
  - Flag: clusters without a clear pillar page, isolated clusters, cross-cluster link gaps
- Assign cluster IDs to nodes for D3 coloring

### Definition of Done
- Premium audit includes full link graph with orphan detection (crawl + GSC + sitemap)
- Interactive Obsidian-style graph renders in the report
- Topic clusters are detected and scored
- Per-audit DataForSEO cost < $2.50

---

## Sprint 4: Content Intelligence

### 4A: Content Extraction Layer (Trafilatura)
- Add `trafilatura` to `requirements.txt` (MIT license, ~15K stars, maintained)
- Create `backend/content_extractor.py` — unified content extraction module:
  - `extract_from_html(html: str, url: str) -> CleanContent` — for pages already fetched by Playwright
  - `extract_from_url(url: str) -> CleanContent` — for competitor pages (Trafilatura handles fetching)
  - `CleanContent` dataclass: clean_text, title, description, word_count, language, headings[]
- Trafilatura handles: boilerplate removal, nav/footer stripping, main content detection
- For Webflow client pages: feed Playwright-rendered HTML to Trafilatura (JS already executed)
- For competitor pages: Trafilatura fetches directly (handles most sites without JS rendering)
- Fallback: if Trafilatura extraction fails, fall back to BeautifulSoup `get_text()` with manual nav stripping
- Store extracted clean text in `page_content.clean_text` column

### 4B: WDF*IDF Pipeline
- Create `backend/wdf_idf_auditor.py`
- Step 1: Get competitor URLs from SerpApi SERP results (or from competitive audit)
- Step 2: Extract competitor content using `content_extractor.py` (Trafilatura)
- Step 3: Calculate TF-IDF vectors using scikit-learn's `TfidfVectorizer`
- Step 4: Compare audited page terms vs. competitor corpus
- Output: top 20 gap terms, over-optimized terms, coverage score
- Frontend: table showing term, your score, competitor average, gap direction

### 4C: Page-Pair Interlinking Opportunities
- Compute cosine similarity between all page-pair TF-IDF vectors (from clean_text)
- Cross-reference with `link_graph` table: find high-similarity pairs with no link
- Generate findings: "Page A and Page B share 73% semantic overlap but are not linked"
- Include recommended anchor text (most distinctive shared terms)

### 4D: Content Profile & Implicit Persona
- Create `backend/content_profile_auditor.py`
- Input: clean_text from Trafilatura extraction (not raw HTML)
- Infer from content: reading level (Flesch-Kincaid), vocabulary type (technical/consumer), funnel stage
- Present as: "Your content reads at Grade 11.2, uses enterprise terminology, addresses decision-stage queries"
- Flag funnel gaps: "No content addressing awareness-stage queries for your detected topics"
- Deterministic — no LLM needed. Based on readability scores, term frequency analysis, heading patterns

### Definition of Done
- Premium report includes WDF*IDF gap analysis table
- Interlinking opportunities with specific page pairs and suggested anchor text
- Content profile with implicit persona and funnel gap analysis
- Trafilatura extracts clean content from 90%+ of competitor sites without manual intervention

---

## Sprint 5: Knowledge Persistence (Bridge to WAIO Agent)

### 5A: Knowledge Base Generator
- Create `backend/knowledge_base_generator.py`
- Transform audit + crawl data into RAG-ready documents:
  - Each page → document with title, clean_text (from Trafilatura), topics, links, schema types
  - Each finding → document with problem, fix instruction, evidence
  - Each fix instruction → document with steps, difficulty, context
- Export format: JSON Lines (one document per line) for vector DB ingestion
- Store in `page_content` table with clean_text for future vector DB indexing
- NOTE: When upgrading to Phase 2, replace Trafilatura extraction with Firecrawl /crawl
  for LLM-optimized markdown (better chunking, 67% fewer tokens, source attribution metadata)

### 5B: Cross-Audit Intelligence Queries
- Build helper functions for querying across all audits:
  - Most common findings (by frequency across all audits)
  - Average scores by pillar (across all Webflow sites audited)
  - Industry benchmarks (group by detected site type)
- These feed the future chatbot's training data

### Definition of Done
- Every premium audit generates RAG-ready knowledge base export
- Cross-audit queries work for benchmarking and trend analysis
- Data format is ready for Phase 2 WAIO Agent ingestion
- Firecrawl upgrade path documented for Phase 2 transition

---

## Phase 2 Upgrade: Firecrawl (when WAIO Agent development begins)

When the embeddable AI chat agent moves into development:
1. Sign up for Firecrawl Standard plan ($83/mo, 100K credits)
2. Add `FIRECRAWL_API_KEY` to Railway env vars
3. Create `backend/firecrawl_client.py` (replaces Trafilatura in the RAG pipeline only)
4. Firecrawl /crawl → clean markdown → chunk by headings → embed → Pinecone/Qdrant
5. Firecrawl /extract → structured entities → knowledge graph (Neo4j or Postgres JSONB)
6. Keep Trafilatura as fallback for competitor extraction in the audit tool
