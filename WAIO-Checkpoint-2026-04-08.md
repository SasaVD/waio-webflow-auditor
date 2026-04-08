# WAIO Webflow Auditor — Project Checkpoint
## Date: April 8, 2026

---

## Project Overview

**Product:** WAIO Audit Engine — website audit tool evolving into a SaaS platform
**Live URL:** https://waio.up.railway.app
**Repo:** github.com/SasaVD/waio-webflow-auditor
**Stack:** FastAPI (Python 3.10+) + React 19 + TypeScript + TailwindCSS 4 + Vite
**Deploy:** Docker multi-stage on Railway
**Database:** PostgreSQL on Railway

---

## CEO's 4-Phase Vision

- **Phase 1** (CURRENT): Framework → Audit Tool (free lead gen + $4,500 premium diagnostic)
- **Phase 2** (NEXT): AI Agent — conversational chatbot powered by RAG knowledge base (Firecrawl enters here)
- **Phase 3**: Platform — multi-tenant SaaS with login, client portals, cross-audit intelligence
- **Phase 4**: Ecosystem — external API access, integrations, marketplace

---

## What's Built (Complete)

### Backend — Sprints 1-5 (Phase 1 Feature Complete)
- **Sprint 1:** PostgreSQL migration, audit tier system (free/premium), normalized data storage
- **Sprint 2:** Executive summary generator, 54 Webflow fix instructions, competitor benchmarking
- **Sprint 3:** DataForSEO client, GSC/GA4 OAuth flow, link graph analysis, D3 visualization, topic clusters
- **Sprint 4:** WDF*IDF pipeline (SerpApi + Trafilatura), content profiling, CMS detection (29 platforms), migration intelligence
- **Sprint 5:** RAG-ready knowledge base generator, cross-audit intelligence queries

### Frontend — Sprint 6 (Complete)
- **6A:** TailwindCSS 4 dark-first theme with @theme directive (later switched to LIGHT theme)
- **6B:** React Router v7 with layout routes + Zustand store
- **6C:** Tabbed audit form (Quick Analysis / Comprehensive Audit Pro)
- **6D:** Sitebulb-style hint cards, severity filters, blurred premium previews
- **6E:** Premium dashboard with collapsible sidebar (256px/56px) + overview page + radar chart
- **6F:** Link graph page (react-force-graph-2d) — fully functional with optimizations
- **6G:** Export system (PDF, Excel, Markdown)
- **6H:** SSE-based audit streaming with progress indicators

### Post-Sprint Additions (Pre April 7)
- **Element pinpointing** in findings across all 9 HTML-facing auditors
- **Light theme** applied (switched from dark-first)
- **Outcome-focused copy** — all pillar names, headlines, CTAs, badge text updated
- **Authentication system** — email/password + Google OAuth, JWT httpOnly cookies, invite-only registration
- **Admin panel** at /admin — user management + audit history
- **Audit persistence** — all audits saved to PostgreSQL, retrievable via GET /api/audit/report/:id
- **Premium pipeline wired** — /api/audit/premium calls all premium modules
- **Dashboard sub-pages** — Summary, Fixes, Benchmark, Clusters, Export (5 pages + ErrorBoundary)
- **DataForSEO background poller** — polls for crawl results, builds link graph + topic clusters, updates saved report

### Sprint 7 — April 7-8, 2026 (Massive Feature Sprint)

#### 7A: Enrichment Progress Indicator
- **Backend:** Added `enrichment_status` and `enrichment_progress` fields to report JSON. Poller writes progress messages like "Crawling site... 200/359 pages discovered (poll 5/60)". Added `GET /api/audit/enrichment-status/{audit_id}` lightweight endpoint
- **Frontend:** Created `useEnrichmentPolling.ts` hook — polls every 10s, auto-refetches full report on completion, 25-minute timeout. Indigo progress banner in `DashboardLayout.tsx` above the outlet. Skeleton loading states on Link Graph and Topic Clusters pages
- **Progressive polling intervals:** Polls 1-10 at 15s, polls 11-30 at 20s, polls 31-60 at 30s (~25 min total)
- **Timeout handling:** "timed_out" status with soft message + manual "Refresh now" button + slow background polling at 60s intervals
- **Manual refresh endpoint:** `POST /api/audit/{audit_id}/refresh-enrichment`

#### 7B: Topic Clusters Fix
- **Root cause:** Backend returned `prefix/coherence_score/dominant_category` but frontend expected `path/cohesion_score/nlp_category`
- **Fix:** Rewrote `DashboardClustersPage.tsx` to use correct field names. Added summary stats grid, proportional bars per cluster, and NLP category breakdown

#### 7C: Link Graph Optimization (react-force-graph-2d)
- **Performance:** `warmupTicks={100}`, `cooldownTicks={200}`, `d3AlphaDecay={0.05}`, `autoPauseRedraw={true}`
- **Level-of-detail rendering:** Dots at <0.5x zoom, colored circles at 0.5-1.5x, full labels at >1.5x
- **Dynamic node sizing:** Logarithmic scale based on computed inDegree — homepage=14, orphans=2.5, others scale by log2(inbound)
- **Cluster coloring:** Nodes colored by URL directory prefix cluster
- **Orphan highlighting:** Red/orange color for 0-inbound nodes
- **Directional arrows** on links showing flow direction
- **Force tuning:** Charge strength -120, link distance 30, link strength 0.7 for better spatial clustering
- **Hover highlights:** All connected edges and neighbor nodes highlight on hover
- **Stats bar:** 6 columns — Pages, Links, Avg Links/Page, Max Depth, Orphans (red), Hub Pages

#### 7D: Link Graph Edge Data Fix
- **Root cause:** `_normalize_url("/blog")` → `urlparse` produced `":///blog"` (empty scheme/netloc) for relative paths from DataForSEO. All 966 edges had broken source/target URLs that never matched node IDs
- **Fix:** `_normalize_url()` now accepts optional `base_url` parameter, resolves relative paths against homepage URL. Added link type filtering — only `anchor` and `link` types included as edges

#### 7E: SEO UX Layer for Link Graph
- **Search:** Type URL fragment to highlight matches, Enter to zoom to first match
- **Layout switcher:** Force-directed (default) vs Hierarchical tree (`dagMode="td"`)
- **Filter toggles:** All / Orphans only / Hubs only / Depth gradient coloring
- **Color-by dropdown:** Cluster / TIPR Quadrant / PageRank / Depth
- **Right-click context menu:** Open URL, Show inbound/outbound links, Focus here
- **Click-to-inspect:** Side panel with full URL, in/out link counts, depth, link lists
- **Export as PNG:** Downloads current canvas view

#### 7F: CMS-Aware Fix Guide
- **Created `generic_fixes.py`** — 20 platform-agnostic fix instructions covering all major pillars
- **CMS-based routing:** Webflow sites get Webflow-specific fixes, everything else gets generic fixes
- **Fix Guide header** shows detected CMS with confidence percentage
- **Info banner** for non-Webflow sites explaining generic instructions

#### 7G: Migration Intelligence
- **Dashboard Overview:** CMS badge with confidence %, migration section with timeline/redirects/platform risks/Webflow advantages (only shown for non-Webflow sites)
- **Executive Summary:** Migration assessment section with platform risks and Webflow advantages appended below summary

#### 7H: Pillar Sub-Pages
- **Created `DashboardPillarPage.tsx`** — generic pillar detail page at `/dashboard/:auditId/pillar/:slug`
- **Shows:** Score with circular gauge, pillar description, total/passed/failed checks, findings with severity cards, positive findings, inline fix suggestions
- **Sidebar links** updated to navigate to `/pillar/search-engine-clarity` etc.
- **10 pillar slugs** mapped to internal pillar keys (semantic_html, structured_data, aeo_content, etc.)

#### 7I: Crawled Pages Table
- **Created `DashboardPagesPage.tsx`** — sortable/searchable table of all crawled pages
- **Columns:** URL Path, Title, Depth, Inbound links, Outbound links, Status, Audit button
- **KPI cards:** Pages Found, Internal Links, Orphan Pages, Broken Links (computed from graph edges)
- **Filters:** Orphans Only toggle, search by URL
- **"Site Crawl" section** added to sidebar with "Crawled Pages" link

#### 7J: Per-Page Audit System
- **Backend:** `POST /api/audit/page` endpoint — runs same 10-pillar analysis on any individual URL
- **Saves results** linked to parent audit via `parent_audit_id` field
- **Frontend:** `PageAuditView.tsx` at `/dashboard/:auditId/page-audit?url=encoded_url`
- **Crawled Pages table:** "Audit" button per page, score badge (colored 0-100) for audited pages
- **Rate limited:** Max 5 concurrent page audits per parent audit

#### 7K: Content Intelligence (Google NLP)
- **Backend enhanced:** Premium audit now calls all three Google NLP methods:
  - `classifyText` (existing) — industry classification
  - `analyzeEntities` (new) — extracts entities with salience scores, types, Wikipedia links
  - `analyzeSentiment` (new) — content tone/score/magnitude
  - Derives insights: SEO alignment, entity diversity, focus alignment, keyword entities
  - All stored under `report["nlp_analysis"]` with full structure
- **Dedicated page:** `DashboardContentIntelligencePage.tsx` at `/dashboard/:auditId/content-intelligence`
  - Section A: Industry classification with breadcrumb taxonomy and confidence gauge
  - Section B: Entity analysis — top 10 cards grid, salience bar chart (Recharts), entity type pie chart, full sortable table for 10+ entities
  - Section C: Sentiment gauge with visual indicator, tone interpretation, magnitude context
  - Section D: SEO Intelligence panel — "What Google Sees" summary, contextual recommendations (positive/warning/info)
  - Graceful empty states when NLP data is missing
- **Sidebar:** "Content Intelligence" (Brain icon) under Content & SEO group
- **Integration:** Overview page NLP summary card, Executive Summary brief section, Markdown/Excel export with full entity table and sentiment data

#### 7L: TIPR Link Intelligence Engine
- **Created `tipr_engine.py`** — pure Python TIPR scoring engine:
  - `compute_pagerank()` — Power-iteration PageRank via scipy sparse matrices (30-60 iterations, <1s for 2000 pages)
  - `compute_cheirank()` — CheiRank (PageRank on reversed graph)
  - `compute_tipr_scores()` — Rank-averaged composite (2-signal mode, 3-signal ready for future backlink integration)
  - `classify_pages()` — Percentile rank-based quadrant classification: Star/Hoarder/Waster/Dead Weight (~25% each)
  - `generate_link_recommendations()` — 3 strategies: hoarder redistribution, orphan boosting, waster pruning. Scored by PR contribution × target deficit × content relevance × diminishing returns
  - `run_tipr_analysis()` — Main entry point, integrated into DataForSEO enrichment pipeline with lazy computation fallback
- **Created `link_data_export.py`** — Screaming Frog-style exports:
  - 6-sheet Excel workbook (Pages, Links, TIPR, Recommendations, Orphans, Summary)
  - CSV ZIP archive with matching files
  - `GET /api/export/link-data/{audit_id}?format=xlsx|csv`
- **Dedicated page:** `DashboardLinkIntelligencePage.tsx` at `/dashboard/:auditId/link-intelligence` — 8 sections:
  1. Quadrant KPI cards (Stars/Hoarders/Wasters/Dead Weight counts)
  2. Recharts ScatterChart — PageRank vs CheiRank with quadrant lines and color coding
  3. Top Hoarders table with sortable columns (URL, Out Links, In Links, PR Score, CR Score, Type)
  4. Top Wasters table
  5. Orphan Pages analysis with suggested source pages for each orphan
  6. Link Depth distribution chart (flagging depth 4+)
  7. Hub Pages table with classification badges
  8. Grouped recommendations (Quick Win/Strategic/Maintenance) with Export CSV button
- **Sidebar:** "Link Intelligence" with Sparkles icon under Links & Architecture
- **Graph integration:** "Color by" dropdown with TIPR Quadrant / PageRank / Depth options, TIPR-based node sizing
- **Pages table integration:** PR Score, TIPR Rank, Classification columns with sorting
- **Executive Summary:** Link Intelligence brief with health percentage and top recommendation
- **Overview:** TIPR summary card with recommendations count, stars, and orphan count
- **Exports:** Markdown gets full TIPR section with hoarders, wasters, top 10 recommendations. Excel gets 3 new sheets (TIPR Summary, TIPR Scores, Link Recommendations)
- **Admin endpoint:** `POST /api/audit/{audit_id}/recompute-tipr` to clear cached TIPR data and force recomputation

---

## Current State (April 8, 2026)

### What's Working
- Free Quick Analysis: fully functional, no auth required, saves to DB
- Auth system: email/password login, Google OAuth, admin panel, invite-only
- Premium audit: requires auth, runs full pipeline including DataForSEO crawl + NLP
- 10-pillar analysis: all pillars run correctly with element pinpointing
- CMS detection: identifies Webflow (and 28 other platforms), CMS-aware fix guide
- Migration intelligence: generates and displays migration assessment for non-Webflow sites
- Content Intelligence: Google NLP classifyText + analyzeEntities + analyzeSentiment with full dashboard
- TIPR Link Intelligence: PageRank + CheiRank + quadrant classification + link recommendations
- Link Graph: react-force-graph-2d with dynamic node sizing, cluster coloring, TIPR quadrant coloring, depth coloring, search, layout switcher, filters, export PNG
- Pillar sub-pages: each pillar has its own detail page with findings, score, and fixes
- Per-page auditing: on-demand 10-pillar analysis for individual crawled pages
- Crawled Pages table: sortable, searchable, with audit scores
- Topic Clusters: renders with correct data from DataForSEO
- Enrichment progress: real-time progress banner, skeleton loading states, timeout handling with manual refresh
- Exports: PDF, Excel, Markdown (all include premium data), Link Intelligence Excel/CSV export (6 sheets, Gephi-compatible)
- DataForSEO background poller: progressive intervals, 60-poll limit (~25 min), link graph + topic clusters + TIPR computation

### Known Issues / TODO
- **Link Intelligence polish:** Scatter plot could use better axis labels and tooltips. Recommendation text is somewhat repetitive ("This page is a strong equity distributor..."). Needs more varied, specific recommendation language
- **Graph visual quality:** Nodes still cluster tightly in the center — needs more force repulsion or initial positioning spread. Labels overlap at medium zoom
- **Orphan count discrepancy:** Crawled Pages KPI shows 0 orphans while Link Graph shows 103. The KPI card computes from graph edges but may have a different threshold or data source
- **Executive Summary renders raw markdown:** The `##` headings and `**bold**` markers show as plaintext instead of rendered HTML on the summary page
- **DataForSEO crawl timeout for some sites:** upstreamworks.com (WordPress) timed out at 30/30 polls with 0/0 pages. May be blocked by WAF/Cloudflare. Need better error detection for "crawler blocked" vs "still crawling"
- **DATAFORSEO_USE_SANDBOX:** Must be set to "false" for live crawls. Verify this is correct in Railway
- **Railway credits:** ~$3.14 remaining (~14 days). MUST upgrade to Hobby plan ($5/month) ASAP
- **Pillar "web-perf" slug mismatch:** One pillar sub-page showed "Pillar Not Found" for the `web-perf` slug — may need to check the slug-to-key mapping for all 10 pillars

---

## Architecture

### 10 Audit Pillars (CMS-Agnostic, Zero AI Dependency)
1. Search Engine Clarity (semantic_html) — 12%
2. Rich Search Presence (structured_data) — 12%
3. AI Answer Readiness (aeo_content) — 10%
4. Visual Consistency (css_quality) — 5%
5. Page Speed & Load Time (js_performance) — 5%
6. Inclusive Reach (accessibility) — 18%
7. AI Retrieval Readiness (rag_readiness) — 10%
8. AI Agent Compatibility (agentic_protocols) — 8%
9. Tracking & Analytics Accuracy (data_integrity) — 8%
10. Content Architecture (internal_linking) — 12%

### Two-Tier System
- **Free tier:** 10-pillar analysis, single page, no auth required, lead gen tool
- **Premium tier ($4,500):** Everything in free + full-site crawl (2,000 pages), CMS detection, DataForSEO crawl, link graph, topic clusters, executive summary, CMS-aware fixes, WDF*IDF, Google NLP (classify + entities + sentiment), competitor benchmarks, migration intelligence, TIPR link intelligence, per-page auditing, Content Intelligence dashboard, Link Intelligence dashboard

### API Stack (Premium Only)
- DataForSEO On-Page API — site crawling, link graph (~$0.50-2.50/audit)
- DataForSEO SERP API or SerpApi — competitor URLs for WDF*IDF
- Google Cloud Natural Language API — classifyText + analyzeEntities + analyzeSentiment (5,000 free units/month, ~3 units per audit)
- Google Search Console API — indexed URLs, search performance (free, OAuth)
- Google GA4 Data API — traffic per URL (free, OAuth)
- Trafilatura — content extraction (free, in-process)

### Route Structure
```
/                                          → Landing page with audit form
/audit/:auditId                            → Free report (public, shareable)
/dashboard/:auditId                        → Premium dashboard overview
/dashboard/:auditId/pillar/:slug           → Pillar detail page (10 pillars)
/dashboard/:auditId/content-intelligence   → Content Intelligence (NLP)
/dashboard/:auditId/link-intelligence      → Link Intelligence (TIPR)
/dashboard/:auditId/graph                  → Link graph visualization
/dashboard/:auditId/clusters               → Topic clusters
/dashboard/:auditId/pages                  → Crawled pages table
/dashboard/:auditId/page-audit?url=...     → Per-page audit results
/dashboard/:auditId/summary                → Executive summary
/dashboard/:auditId/fixes                  → CMS-aware fix guide
/dashboard/:auditId/benchmark              → Competitor benchmarks
/dashboard/:auditId/export                 → Export page (PDF, Excel, MD, Link Data)
/admin                                     → Admin panel (auth required, admin role)
```

### Key Backend Files
- main.py — FastAPI app, all endpoints, premium audit logic, DataForSEO background poller, lazy TIPR trigger
- tipr_engine.py — TIPR scoring engine (PageRank, CheiRank, classification, recommendations)
- link_data_export.py — Screaming Frog-style Excel/CSV export
- link_graph_auditor.py — builds link graph from DataForSEO data with URL normalization
- google_nlp_client.py — Google NLP entity analysis + classification + sentiment
- generic_fixes.py — 20 platform-agnostic fix instructions
- webflow_fixes.py — 54 curated Webflow-specific fix instructions
- auth.py — bcrypt password hashing, JWT tokens
- auth_routes.py — login, logout, admin user management endpoints
- dataforseo_client.py — DataForSEO API client with sandbox/live toggle
- executive_summary_generator.py — template-based executive summary
- competitive_auditor.py — competitor benchmarking
- scoring.py — pillar weights and scoring calculations
- db_postgres.py — PostgreSQL operations including update_audit_report()

### Key Frontend Files
- router.tsx — route definitions with lazy loading (15+ routes)
- stores/authStore.ts — Zustand auth state
- stores/auditStore.ts — Zustand audit data state
- hooks/useEnrichmentPolling.ts — enrichment progress polling hook
- components/LinkGraph.tsx — react-force-graph-2d with TIPR coloring, dynamic sizing, search, filters
- components/dashboard/DashboardLayout.tsx — sidebar + outlet + enrichment banner
- components/dashboard/DashboardOverviewPage.tsx — main dashboard with TIPR + NLP summary cards
- components/dashboard/DashboardPillarPage.tsx — generic pillar detail page
- pages/DashboardLinkIntelligencePage.tsx — TIPR analysis (8 sections)
- pages/DashboardContentIntelligencePage.tsx — NLP analysis (4 sections)
- components/dashboard/DashboardPagesPage.tsx — crawled pages table
- components/dashboard/DashboardPageAuditPage.tsx — per-page audit results
- components/dashboard/DashboardFixesPage.tsx — CMS-aware fix guide
- components/dashboard/DashboardClustersPage.tsx — topic clusters
- components/dashboard/DashboardGraphPage.tsx — link graph page
- components/dashboard/DashboardSummaryPage.tsx — executive summary
- components/dashboard/DashboardExportPage.tsx — all exports including link data

---

## Environment Variables (Railway)

### Set and Working
- DATABASE_URL — PostgreSQL connection
- ADMIN_EMAIL / ADMIN_PASSWORD — admin account
- JWT_SECRET — 64-char string for JWT signing
- VITE_GOOGLE_CLIENT_ID — Google OAuth client ID (frontend)
- GOOGLE_CLIENT_SECRET — Google OAuth client secret
- GOOGLE_API_KEY — Google Cloud NLP API key (classifyText + analyzeEntities + analyzeSentiment)
- DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD — DataForSEO credentials
- DATAFORSEO_USE_SANDBOX — MUST be "false" for live crawls
- SERPAPI_KEY — SerpApi key for WDF*IDF
- APP_BASE_URL — https://waio.up.railway.app
- FROM_EMAIL / RESEND_API_KEY — email delivery
- PLAYWRIGHT_BROWSERS_PATH — Chromium path

---

## DataForSEO Balance
- Started: $50.00
- Current: ~$44 (estimate — several test audits run)
- Cost per audit: ~$0.50-2.50 depending on site size

## Railway Status
- Plan: Free tier
- Credit remaining: ~$3.14 (14 days)
- ⚠️ CRITICAL: MUST UPGRADE TO HOBBY PLAN ($5/month) IMMEDIATELY
- PostgreSQL addon active

---

## Test Audits Run
- vezadigital.com (Webflow) — audit ID: dddc4ce0-a118-4bcf-8230-0c757e2ec66f — 359 pages, 966 links
- beltcreative.com (Webflow) — audit ID: 4ef284bb-9c43-4150-a82d-25a92886d9ed — 171 pages, 969 links, TIPR computed
- upstreamworks.com (WordPress) — audit ID: c33dcd1e-ba69-457f-a7d2-3daa778d8f12 — DataForSEO crawl timed out (0/0 pages)
- hedrick.io — free audit test

---

## Conversation History Links
- Main strategy conversation: https://claude.ai/chat/f7be604a-bf9a-41c5-96b6-49a61e1fd9a0
- Sprint 7 implementation (April 7-8): (this conversation)

---

## Immediate Next Steps (In Order)

1. **UPGRADE RAILWAY PLAN** — $3.14 left, app will go offline without upgrade
2. **Polish Link Intelligence recommendations** — recommendation text is repetitive, needs more varied and specific language per recommendation type
3. **Fix Executive Summary rendering** — raw markdown showing instead of rendered HTML
4. **Fix pillar slug mismatch** — "web-perf" slug returns "Pillar Not Found", verify all 10 slug-to-key mappings
5. **Test a fresh audit end-to-end** — run premium audit on a new site and verify TIPR computes during enrichment (not just lazy)
6. **Test WordPress audit** — verify CMS-aware generic fixes, migration intelligence, and DataForSEO crawl completion for non-Webflow sites
7. **Graph visual polish** — nodes cluster too tightly in center, labels overlap at medium zoom

## Medium-Term Priorities
- GSC/GA4 OAuth integration (connect client's Google accounts for orphan page detection + traffic data + crawl frequency proxy for TIPR signal 4)
- Premium export polish (branded PDF with cover page, charts rendered as images)
- Landing page refinement (visual design improvement)
- 3-signal TIPR (add backlink data from DataForSEO Backlinks API as third signal)
- Automated link suggestion anchor text (use NLP entities for semantic matching)
- DataForSEO sandbox toggle for development/staging environments

## Phase 2 Preparation
- Sprint 5's knowledge base generator already exports RAG-ready JSON Lines
- Firecrawl ($83/month) replaces Trafilatura in the RAG pipeline only
- Every audit feeds the future chatbot's training data
- Database schema supports cross-audit intelligence queries
- TIPR engine + Content Intelligence provide rich structured data for RAG context

---

## How to Resume This Conversation

Start a new chat with:

> I'm continuing work on the WAIO Webflow Auditor app. I'll upload the checkpoint document that captures the full project state. Please read it and we'll continue from where we left off.

Then upload this checkpoint file.

## How to Resume Claude Code Sessions

For any Claude Code work:

> Read CLAUDE.md and all .claude/rules/ files. Refer to the checkpoint document for current project state. [Then describe the specific task]
