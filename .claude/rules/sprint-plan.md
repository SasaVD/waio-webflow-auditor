# Sprint Plan — WAIO Premium Audit Upgrade

## Context
Upgrading the free 10-pillar audit tool into a $4,500 premium diagnostic platform.
Total API cost per premium audit: ~$3-5. Revenue per audit: $4,500.

## Sprint 1: Database + Tier System (Foundation)

### 1A: PostgreSQL Migration
- Add `asyncpg` and `python-dotenv` to `requirements.txt`
- Create `backend/db_postgres.py` implementing same interface as `db.py`
- Create `backend/migrations/001_initial.sql` with full schema (see database-schema.md)
- Update `backend/main.py` startup to initialize Postgres
- Add Railway Postgres addon and set `DATABASE_URL` env var
- Keep SQLite as fallback for local dev: check for `DATABASE_URL`, fall back to SQLite if absent

### 1B: Audit Tier System
- Modify `AuditRequest` model to include `tier: str = "free"`
- In `perform_audit()`, check tier and conditionally run premium modules
- Store tier in `audits` table
- Frontend: no changes needed yet (premium UI comes in Sprint 2)

### 1C: Normalized Data Storage
- After each audit, decompose the report JSON into normalized tables:
  - `pillar_scores` — one row per pillar per audit
  - `findings` — one row per finding
  - `page_content` — extracted text, headings, links per page (for multi-page audits)
- Keep `report_json` JSONB column for backward-compatible full report retrieval

### Definition of Done
- Free audit works exactly as before (no regressions)
- Audit results stored in both JSON and normalized form
- Can query: "Show average semantic_html score across all audits" via SQL

---

## Sprint 2: Premium Deliverables (Immediate $4,500 Value)

### 2A: Executive Summary Generator
- Create `backend/executive_summary_generator.py`
- Template-based prose with dynamic data insertion (NOT LLM-generated for MVP)
- Template sections:
  1. Overall assessment (score, label, one-sentence verdict)
  2. Top 3 strategic risks (from highest-severity findings)
  3. Top 3 strengths (from positive findings with credibility anchors)
  4. ROI projection ("Fixing the top 3 issues could improve AI citation likelihood by X% based on [study]")
  5. Prioritized action plan (ordered by impact × effort)
  6. Competitor context (if competitive audit: rank + gap summary)
- Output: Markdown string included in report JSON as `executive_summary` field
- Frontend: new `ExecutiveSummary` component at the top of premium reports

### 2B: Webflow Fix Knowledge Base
- Create `backend/webflow_fixes.py` with a FIXES dict mapping finding patterns to instructions
- Each fix entry:
  ```python
  {
      "finding_pattern": "missing_h1",
      "pillar": "semantic_html",
      "title": "Add an H1 Heading in Webflow",
      "steps_markdown": "1. Open your page...",
      "difficulty": "easy",
      "estimated_time": "2 minutes"
  }
  ```
- Create GET `/api/fixes/{pattern}` endpoint
- Target: ~60-80 fix entries covering all common findings across 10 pillars
- Frontend: "How to Fix in Webflow" button on each finding card, opens expandable section
- Populate `webflow_fixes` table for persistent storage + future CMS management

### 2C: Default Competitor Benchmarking
- Modify the premium audit flow to ALWAYS include 2-3 competitor audits
- Auto-detect competitors OR require client to provide URLs
- Add competitor scores to executive summary context
- Reuse existing `competitive_auditor.py` infrastructure

### Definition of Done
- Premium report includes executive summary with ROI strategy
- Every finding has a "Fix in Webflow" button with verified instructions
- Premium reports include competitor benchmark context

---

## Sprint 3: Link Intelligence (Architecture Analysis)

### 3A: DataForSEO On-Page API Integration
- Create `backend/dataforseo_client.py` — async client for On-Page API
- Endpoint: POST task → poll status → GET results
- Extract: all internal links, orphan flags, click depth, broken links
- Cost: ~$0.81 per 500-page site
- Requires `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` env vars

### 3B: GSC/GA4 OAuth Integration
- Create `backend/google_auth.py` — OAuth 2.0 flow for GSC + GA4
- Scopes: `webmasters.readonly`, `analytics.readonly`
- Store tokens in database (encrypted)
- Pull: indexed URLs, search performance, sitemap URLs, traffic per page
- URL Inspection API: 2,000 queries/day limit — batch intelligently

### 3C: Site-Wide Link Graph Analysis
- Create `backend/link_graph_auditor.py`
- Input: crawl data (from DataForSEO or own crawler) + GSC data + sitemap
- Compute: orphan pages, link depth (BFS from homepage), hub identification, link equity distribution
- Orphan detection formula: `(sitemap ∪ gsc_urls ∪ ga4_urls) − crawler_found_urls`
- Store edges in `link_graph` table
- Output: findings + graph data JSON for D3 visualization

### 3D: D3 Network Visualization (Obsidian-style)
- Create `frontend/src/components/LinkGraph.tsx`
- D3 force-directed graph with dark background
- Nodes colored by topic cluster, sized by inbound links
- Orphan nodes visually distinct (red outline, floating at edges)
- Interactive: drag, zoom, hover tooltips, click-to-highlight
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
- Per-audit API cost < $2

---

## Sprint 4: Content Intelligence

### 4A: WDF*IDF Pipeline
- Create `backend/wdf_idf_auditor.py`
- Step 1: Get competitor URLs (from competitive audit or SerpApi SERP results)
- Step 2: Fetch competitor page content (reuse Playwright/BeautifulSoup from crawler.py)
- Step 3: Calculate TF-IDF vectors using scikit-learn's TfidfVectorizer
- Step 4: Compare audited page terms vs. competitor corpus
- Output: top 20 gap terms, over-optimized terms, coverage score
- Frontend: table showing term, your score, competitor average, gap

### 4B: Page-Pair Interlinking Opportunities
- In the multi-page crawl, compute cosine similarity between all page-pair TF-IDF vectors
- Cross-reference with link_graph table: find high-similarity pairs with no link
- Generate findings: "Page A and Page B share 73% semantic overlap but are not linked"
- Include recommended anchor text (most distinctive shared terms)

### 4C: Content Profile & Implicit Persona
- Create `backend/content_profile_auditor.py`
- Infer from page content: reading level, vocabulary type (technical/consumer), funnel stage
- Present as: "Your content reads at Grade 11.2, uses enterprise terminology, addresses decision-stage queries"
- Flag funnel gaps: "No content addressing awareness-stage queries for your detected topics"
- This is deterministic (no LLM needed) — based on readability scores, term analysis, heading patterns

### Definition of Done
- Premium report includes WDF*IDF gap analysis table
- Interlinking opportunities with specific page pairs and suggested anchor text
- Content profile with implicit persona and funnel gap analysis

---

## Sprint 5: Knowledge Persistence (Bridge to WAIO Agent)

### 5A: Knowledge Base Generator
- Create `backend/knowledge_base_generator.py`
- Transform audit + crawl data into RAG-ready documents:
  - Each page → document with title, content, topics, links, schema types
  - Each finding → document with problem, fix, evidence
  - Each fix instruction → document with steps, difficulty, context
- Export format: JSON Lines (one document per line) for vector DB ingestion
- Store in `page_content` table with full text for future Pinecone/Qdrant indexing

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
