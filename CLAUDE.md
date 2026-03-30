# WAIO Webflow Audit Tool — Claude Code Instructions

## Project Overview

WAIO (Website AI Optimization) Audit Tool by Veza Digital. A 10-pillar deterministic website audit engine for Webflow sites, evolving into a premium $4,500 diagnostic platform with AI-powered enhancements.

**Live app:** https://waio.up.railway.app/
**Repo:** github.com/SasaVD/waio-webflow-auditor
**Stack:** FastAPI (Python 3.10+) + React 19 + Vite + TypeScript + TailwindCSS 4
**Deploy:** Docker multi-stage on Railway

## Architecture Rules

- **Keep the existing codebase.** Do NOT rewrite or create a new project. All upgrades build on existing modules.
- **Auditor interface contract:** Every auditor takes `(soup, html_content, url)` or similar, returns `{"checks": {}, "positive_findings": [], "findings": []}`.
- **Zero AI dependency for core audit pillars.** The 10 deterministic pillars must never call an LLM API. AI features (fix generator, personas) are separate premium layers.
- **Findings must include:** severity, description, recommendation, reference, credibility_anchor (evidence-based data point from a verified study).
- **Positive findings matter.** When something is correct, acknowledge it with a credibility anchor.

## Current 10 Pillars

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
- **Premium tier** (`tier: "premium"`): Everything in free + GSC/GA4 integration, DataForSEO crawl, competitor WDF*IDF, link graph visualization, executive summary, Webflow fix instructions.

## Sprint Plan (see .claude/rules/ for details)

1. **Sprint 1:** PostgreSQL migration + normalized schema + audit tier system
2. **Sprint 2:** Executive summary generator + Webflow fix knowledge base + competitor benchmarking default
3. **Sprint 3:** DataForSEO On-Page API + site-wide link graph + D3 network visualization + GSC/GA4 OAuth
4. **Sprint 4:** WDF*IDF pipeline (SerpApi + content extraction) + page-pair interlinking + content profile
5. **Sprint 5:** Knowledge base generator for RAG (bridge to Phase 2 WAIO Agent)

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
- `backend/db.py` — Database layer (currently aiosqlite, migrating to PostgreSQL)
- `backend/site_crawler.py` — Multi-page crawl engine, up to 50 pages
- `backend/competitive_auditor.py` — Concurrent audit of primary + up to 4 competitors
- `frontend/src/components/AuditReport.tsx` — Main report UI, pillarMeta registry
- `frontend/src/index.css` — Design tokens (@theme block with CSS variables)

## Code Style

See `.claude/rules/code-style.md` for full details. Key points:
- Python: async/await, type hints, Pydantic models for API
- TypeScript: strict mode, functional components, no `any` without justification
- CSS: Tailwind utility classes, design tokens from `index.css` @theme block
- Never add `data-ai-*` attributes — these are excluded from this tool's scope
