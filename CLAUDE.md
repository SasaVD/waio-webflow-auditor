# WAIO Webflow Audit Tool — Claude Code Instructions

## Project Overview

WAIO (Website AI Optimization) Audit Tool by Veza Digital. A 10-pillar deterministic website audit engine that works on any CMS (Webflow, WordPress, Shopify, Next.js, Framer, Wix, Squarespace, and more), with Webflow-specific fix instructions and migration consulting intelligence. Evolving into a premium $4,500 diagnostic platform with AI-powered enhancements.

**Live app:** https://waio.up.railway.app/
**Repo:** github.com/SasaVD/waio-webflow-auditor
**Stack:** FastAPI (Python 3.10+) + React 19 + Vite + TypeScript + TailwindCSS 4
**Deploy:** Docker multi-stage on Railway

## Architecture Rules

- **Keep the existing codebase.** Do NOT rewrite or create a new project. All upgrades build on existing modules.
- **CMS-agnostic core.** All 10 audit pillars analyze rendered HTML/CSS/JS output, not CMS source code. They work identically on any platform. CMS-specific intelligence is a separate layer on top.
- **Auditor interface contract:** Every auditor takes `(soup, html_content, url)` or similar, returns `{"checks": {}, "positive_findings": [], "findings": []}`.
- **Zero AI dependency for core audit pillars.** The 10 deterministic pillars must never call an LLM API. AI features (fix generator, personas) are separate premium layers. Google NLP API is a premium-only intelligence layer — not a core pillar dependency.
- **Findings must include:** severity, description, recommendation, reference, credibility_anchor (evidence-based data point from a verified study).
- **Positive findings matter.** When something is correct, acknowledge it with a credibility anchor.

## Current 10 Pillars (CMS-Agnostic)

1. Semantic HTML (`html_auditor.py`) — 12% weight
2. Structured Data (`structured_data_auditor.py`) — 12% weight
3. AEO Content (`aeo_content_auditor.py`) — 10% weight
4. CSS Quality (`css_js_auditor.py` css_keys) — 5% weight
5. JS Bloat (`css_js_auditor.py` js_keys) — 5% weight
6. Accessibility (`accessibility_auditor.py`) — 18% weight
7. RAG Readiness (`rag_readiness_auditor.py`) — 10% weight
8. Agentic Protocols (`agentic_protocol_auditor.py`) — 8% weight
9. Data Integrity (`data_integrity_auditor.py`) — 8% weight
10. Internal Linking (`internal_linking_auditor.py`) — 12% weight

## Two-Tier System

- **Free tier** (`tier: "free"`): Existing 10-pillar analysis, up to 50 pages, PDF/MD export. Lead gen tool.
- **Premium tier** (`tier: "premium"`): Everything in free + full-site crawl (up to 2,000 pages default, 5,000 max), CMS detection, GSC/GA4 integration, DataForSEO crawl, competitor WDF*IDF, link graph visualization, executive summary, Webflow fix instructions, CMS-specific migration intelligence, Google NLP content intelligence.

## API Stack (Premium Tier Only)

- **DataForSEO On-Page API** — site crawling, link graph, orphan detection, 120+ SEO metrics (~$2.50/2,000 pages with JS rendering)
- **DataForSEO SERP API or SerpApi** — competitor URLs for WDF*IDF (~$0.06/audit)
- **Google Cloud Natural Language API** — entity analysis with salience scores, content classification (1,091 categories), sentiment analysis. Powered by Google's own NLP models (~$0-10/audit using free tier strategically)
- **Trafilatura** — clean content extraction from any CMS (free, in-process, no API key)
- **Google Search Console API** — indexed URLs, search performance (free, OAuth required)
- **Google GA4 Data API** — traffic per URL for orphan prioritization (free, OAuth required)
- Total API cost per premium audit: ~$3-20 (scales with page count and NLP depth)

## Sprint Plan (see .claude/rules/sprint-plan.md for details)

1. **Sprint 1:** PostgreSQL migration + normalized schema + audit tier system ✅
2. **Sprint 2:** Executive summary generator + Webflow fix knowledge base + competitor benchmarking ✅
3. **Sprint 3:** DataForSEO On-Page API + CMS detection + site-wide link graph + D3 network visualization + GSC/GA4 OAuth + Google NLP topic cluster validation
4. **Sprint 4:** Trafilatura content extraction + WDF*IDF pipeline + page-pair interlinking + Google NLP content profile + CMS migration intelligence
5. **Sprint 5:** Knowledge base generator for RAG (bridge to Phase 2 WAIO Agent)

## Page Limits

- **Free tier:** up to 50 pages (existing `site_crawler.py`)
- **Premium tier default:** up to 2,000 pages (via DataForSEO)
- **Premium tier max:** up to 5,000 pages (configurable per audit, higher cost)

## Supported CMS Platforms

WAIO detects and provides platform-specific intelligence for:
- **Webflow** — full fix instructions (54 curated entries), migration target platform
- **WordPress** — security vulnerability analysis, plugin bloat detection, migration recommendations
- **Shopify** — URL structure limitations, duplicate content patterns, redirect constraints
- **Next.js** — SSR/SSG detection, hydration issues, routing analysis
- **Framer** — performance benchmarking, export limitations
- **Wix** — performance issues, export limitations, SEO constraints
- **Squarespace** — heading hierarchy limitations, performance gaps, structured data constraints
- **Other/Custom** — generic audit (all 10 pillars work on any HTML output)

## Build & Run Commands

```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python -m uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Docker build
docker build -t waio-audit .
docker run -p 8000:8000 waio-audit

# Deploy (Railway)
git push origin main  # Railway auto-deploys from main branch
```

## Key Files to Know

- `backend/main.py` — FastAPI app, all API endpoints, orchestrates auditors
- `backend/scoring.py` — Weighted scoring model, `compile_scores()` and `calculate_score()`
- `backend/report_generator.py` — Compiles all auditor results into final JSON report
- `backend/db_router.py` — Auto-selects PostgreSQL or SQLite based on DATABASE_URL
- `backend/db_postgres.py` — Async PostgreSQL module (production)
- `backend/db.py` — SQLite module (local dev fallback)
- `backend/dataforseo_client.py` — Async DataForSEO On-Page API client (Sprint 3A)
- `backend/site_crawler.py` — Multi-page crawl engine, up to 50 pages (free tier)
- `backend/competitive_auditor.py` — Concurrent audit of primary + up to 4 competitors
- `backend/executive_summary_generator.py` — Template-based executive summary (Sprint 2A)
- `backend/webflow_fixes.py` — 54 curated Webflow fix instructions (Sprint 2B)
- `frontend/src/components/AuditReport.tsx` — Main report UI, pillarMeta registry
- `frontend/src/components/AuditForm.tsx` — Audit form with premium tier toggle
- `frontend/src/components/ExecutiveSummary.tsx` — Premium executive summary display
- `frontend/src/index.css` — Design tokens (@theme block with CSS variables)

## Code Style

See `.claude/rules/code-style.md` for full details. Key points:
- Python: async/await, type hints, Pydantic models for API
- TypeScript: strict mode, functional components, no `any` without justification
- CSS: Tailwind utility classes, design tokens from `index.css` @theme block
- Never add `data-ai-*` attributes — these are excluded from this tool's scope
