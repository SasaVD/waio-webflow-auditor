# AI Visibility Feature — Design Spec

**Date:** 2026-04-15
**Status:** Approved, pre-implementation
**Scope:** One combined spec covering three implementation phases. Each phase ships via its own implementation plan.

## 1. Overview

Add an **AI Visibility** capability to the WAIO premium audit that gives clients a point-in-time snapshot of how their brand appears across AI engines (ChatGPT, Claude, Gemini, Perplexity, Google AI Overviews). The feature combines two distinct DataForSEO data sources and must keep them segregated for accurate interpretation:

- **LLM Mentions API** (pre-indexed database) — aggregated mention counts, AI search volume, impressions, and top cited pages across Google AI Overview and ChatGPT only. Derived from scanning thousands of pre-indexed AI responses.
- **LLM Responses API** (live queries) — sends 4 canonical prompts to each of 4 engines (ChatGPT, Claude, Gemini, Perplexity) and captures brand mention frequency. Sampled data, up to 120s per call.

Share of Voice is computed exclusively from the LLM Mentions `cross_aggregated` endpoint, because SOV from 4 live prompts would be statistically meaningless.

## 2. Non-goals / Out of scope

- Trend tracking across multiple snapshots (deferred to a future "AI Visibility Monitoring" upsell tier — requires scheduled audits, not one-off reports).
- Per-prompt / per-engine retry UI (Phase 2.5 enhancement — initial ship uses global recompute).
- Location-templated prompts (location is not reliably in the data model yet).
- Editable prompts from the dashboard (Phase 2/3 enhancement if template mismatches surface during live testing).
- Dedicated "INTELLIGENCE LAYERS" sidebar super-group refactor (cross-feature IA pass, out of scope for this spec).

## 3. Phased rollout

| Phase | Delivers | Trigger model |
|---|---|---|
| **Phase 1** | Probe script → backend pipeline → DB migration → two GET endpoints + one POST endpoint. No UI. Manual invocation only via curl/recompute endpoint. | Manual only |
| **Phase 2** | Dashboard page (6 sections), KPI card on overview, confirmation modal, Zustand polling slice, sidebar entry. Dashboard "Run AI Visibility Analysis" button fires recompute. | Manual via dashboard button |
| **Phase 3** | Premium audit form checkbox (defaults on) + optional brand name field. Auto-run as sibling task after enrichment. Executive summary integration across 4 read points. | Auto-run when opt-in flag set |

Each phase gets its own implementation plan via the `writing-plans` skill after this spec is approved.

## 4. Architecture

### 4.1 Module structure

New package `backend/ai_visibility/`:

```
backend/ai_visibility/
  __init__.py            # re-exports run_ai_visibility_analysis
  engine.py              # thin orchestrator (~120 lines)
  brand_resolver.py      # NLP extraction + override lookup (~80 lines)
  competitor_resolver.py # 3-tier fallback (~100 lines)
  prompts.py             # 4 canonical templates + builder (~60 lines)
  mentions_fetcher.py    # LLM Mentions API calls (~150 lines)
  responses_fetcher.py   # LLM Responses orchestration + per-engine isolation (~180 lines)
  sov_calculator.py      # Share of Voice math (~60 lines)
  schema.py              # @dataclass types (~100 lines)
  cost_tracker.py        # money_spent accumulator (~40 lines)
```

Rationale for pipeline-of-modules over monolithic:
- Each stage is independently unit-testable (especially SOV math, brand extraction, prompt templating).
- Phase 2/3's editable-prompts feature is a 20-line change to `prompts.py`, not a file-wide rewrite.
- Matches existing composite-feature conventions (`site_crawler` + `competitive_auditor` + `report_generator` pipeline).

### 4.2 Module responsibilities

| Module | Responsibility | Input | Output |
|---|---|---|---|
| `engine.py` | Orchestrator — calls stages in order, handles top-level try/except, writes to DB | `audit_id`, `brand_override?` | Writes `report["ai_visibility"]`, returns `None` |
| `brand_resolver.py` | Extract brand from NLP `ORGANIZATION` entities (salience > 0.3), with override precedence | `audit_id`, `brand_override?` | `BrandInfo(name, source, salience?)` |
| `competitor_resolver.py` | 3-tier fallback: `competitor_urls` → competitive_auditor → LLM Mentions co-mentions; dedupe to bare domains | `audit_id`, `brand_name` | `CompetitorSet(domains: list[str], source: str)` |
| `prompts.py` | Build 4 canonical prompts from `detected_industry` + top NLP entity + brand name | `industry`, `top_entity`, `brand_name` | `list[PromptTemplate]` |
| `mentions_fetcher.py` | LLM Mentions API — aggregated metrics, search, top pages, cross-aggregated | `brand_name`, `competitor_domains` | `MentionsResult(..., cost_usd)` |
| `responses_fetcher.py` | LLM Responses — 4 prompts × 4 engines with `Semaphore(4)` + per-engine isolation | `prompts`, `brand_name` | `ResponsesResult(engines, cost_usd)` |
| `sov_calculator.py` | Share of Voice math from `cross_aggregated_metrics` | `mentions` | `SOVResult(brand_sov, competitor_sov, total_mentions)` |
| `cost_tracker.py` | Accumulator for `money_spent` from every API call | — (mutable accumulator) | `float` |
| `schema.py` | Pure dataclasses — the typed intermediate types | — | (type definitions only) |

### 4.3 DataForSEO client extension

`backend/dataforseo_client.py` gains new methods under a **separate live-only base URL**. The existing `BASE_URL` remains sandbox-aware for On-Page API; AI Optimization ignores the sandbox flag:

```python
AI_OPT_BASE_URL = "https://api.dataforseo.com/v3/ai_optimization"  # always live

class DataForSEOClient:
    async def llm_mentions_aggregated(self, brand: str, engines: list[str]) -> dict: ...
    async def llm_mentions_search(self, brand: str, limit: int = 100) -> dict: ...
    async def llm_mentions_top_pages(self, brand: str, limit: int = 20) -> dict: ...
    async def llm_mentions_cross_aggregated(self, brands: list[str]) -> dict: ...
    async def llm_response(self, prompt: str, engine: str, timeout: float = 120.0) -> dict: ...
```

### 4.4 End-to-end lifecycle (manual trigger, Phases 1+2)

1. User opens premium dashboard, sees **"AI Visibility — Not yet computed"** KPI card on overview.
2. Clicks **"Run AI Visibility Analysis →"**.
3. Dashboard calls `GET /api/audit/{id}/ai-visibility/brand-preview` → returns auto-extracted brand + detected industry + competitor preview.
4. Modal opens with pre-filled brand name, editable.
5. On submit, dashboard calls `POST /api/audit/{id}/recompute-ai-visibility` with `{ brand_name }`.
6. Backend persists `audits.brand_name_override = "<confirmed_name>"`, checks monthly budget cap, returns `202 Accepted`.
7. `asyncio.create_task(run_ai_visibility_analysis(audit_id, ...))` fires.
8. Dashboard polls `GET /api/audit/{id}/ai-visibility` every 5s.
9. Engine writes result to `audits.report_json["ai_visibility"]` with `last_computed_at`, `last_computed_status`, per-engine statuses, total cost, and updated cumulative cost.

### 4.5 End-to-end lifecycle (auto-run, Phase 3)

Opt-in checkbox sets `audits.ai_visibility_opt_in = true`. The `_enrich_report_from_crawl` background task spawns a **sibling task** for AI Visibility after crawl enrichment finishes — not inside it. Enrichment's completion is reported to the user independently; AI Visibility status shows on its own card as "running" until done.

## 5. Data schema

### 5.1 Database migrations

**Phase 1 migration:**
```sql
ALTER TABLE audits ADD COLUMN IF NOT EXISTS brand_name_override TEXT;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS ai_visibility_cumulative_cost_usd REAL DEFAULT 0;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS ai_visibility_run_count INTEGER DEFAULT 0;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS last_ai_visibility_run_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_audits_last_ai_viz_run ON audits(last_ai_visibility_run_at);
```
The index supports the monthly budget-cap aggregation query in §10.3.

**Phase 3 migration:**
```sql
ALTER TABLE audits ADD COLUMN IF NOT EXISTS ai_visibility_opt_in BOOLEAN DEFAULT FALSE;
```

### 5.2 `report["ai_visibility"]` blob

```json
{
  "last_computed_at": "2026-04-15T14:32:17Z",
  "last_computed_status": "ok",
  "run_count": 1,
  "brand_name": "Belt Creative",
  "brand_name_source": "override",
  "detected_industry": "/Business & Industrial/Advertising & Marketing",
  "competitors": {
    "domains": ["webflow.com", "wix.com", "squarespace.com"],
    "source": "user_provided"
  },

  "mentions_database": {
    "total": 103,
    "by_platform": { "google_ai_overview": 69, "chatgpt": 34 },
    "ai_search_volume": 156000,
    "impressions": 42300,
    "top_pages": [
      { "url": "https://beltcreative.com/...", "mention_count": 12 }
    ],
    "triggering_prompts": [
      { "prompt": "best advertising agencies 2026", "mention_count": 8, "platform": "chatgpt" }
    ]
  },

  "live_test": {
    "prompts_used": [
      { "id": 1, "category": "discovery", "text": "best advertising & marketing agencies" },
      { "id": 2, "category": "discovery", "text": "top advertising & marketing companies" },
      { "id": 3, "category": "discovery", "text": "advertising & marketing services for SaaS" },
      { "id": 4, "category": "reputation", "text": "Belt Creative reviews" }
    ],
    "engines": {
      "chatgpt":    { "status": "ok",     "responses_by_prompt": {}, "cost_usd": 0.42, "brand_mentioned_in": 2 },
      "claude":     { "status": "ok",     "responses_by_prompt": {}, "cost_usd": 0.38, "brand_mentioned_in": 1 },
      "gemini":     { "status": "ok",     "responses_by_prompt": {}, "cost_usd": 0.31, "brand_mentioned_in": 3 },
      "perplexity": { "status": "failed", "error": "timeout after 120s", "cost_usd": 0.00, "brand_mentioned_in": 0 }
    }
  },

  "share_of_voice": {
    "source": "mentions_database.cross_aggregated",
    "brand_sov": 0.12,
    "competitor_sov": { "webflow.com": 0.34, "wix.com": 0.28, "squarespace.com": 0.26 },
    "total_mentions_analyzed": 847
  },

  "cost_usd": 2.47,
  "cumulative_cost_usd": 4.94,
  "duration_seconds": 142
}
```

**Schema conventions:**
- `last_computed_status`: `"ok"` (4/4 engines), `"partial"` (1-3 succeeded), `"failed"` (0/4 or pre-engine failure).
- `brand_name_source`: `"override"` | `"nlp"` — drives UI *"Using manually set brand name"* indicator.
- `prompts_used.category`: `"discovery"` vs `"reputation"` — enables the dashboard to frame the two contexts separately.
- `brand_mentioned_in`: count of the 4 prompts where the brand appeared in that engine's response.
- `cost_usd`: cost of the most recent run only.
- `cumulative_cost_usd`: total spent across all runs for this audit_id — mirrors `audits.ai_visibility_cumulative_cost_usd`. Displayed in the UI so retries don't hide accumulated spend.
- `share_of_voice.source` is pinned to `mentions_database.cross_aggregated` — never computed from `live_test`.

### 5.3 Critical data segregation rule

**Never conflate `mentions_database` with `live_test` counts.** These are fundamentally different data sources: database counts are derived from scanning thousands of pre-indexed AI responses (covers Google AI Overview + ChatGPT only); live_test counts come from 4 sampled prompts per engine (covers all 4 engines). Presenting them under a unified `by_engine` shape would mislead the client about sample sizes and methodology.

## 6. API endpoints

All three are under `/api/audit/{audit_id}/`:

### 6.1 `GET /ai-visibility/brand-preview`

Lightweight pre-flight for the confirmation modal. No DataForSEO calls.

```python
# Response 200
{
  "auto_extracted": "Belt Creative",
  "auto_extracted_salience": 0.71,
  "override": null,
  "detected_industry": "/Business & Industrial/Advertising & Marketing",
  "top_nlp_entity": "web design",
  "competitors_preview": {
    "user_provided": ["webflow.com", "wix.com"],
    "auto_detected": [],
    "tier_3_fallback_available": true
  },
  "cumulative_cost_usd": 4.94,
  "run_count": 2
}

# Response 404 if audit_id not found
# Response 409 if nlp_analysis missing:
#   { "detail": "NLP enrichment not yet complete — AI Visibility requires brand extraction" }
```

### 6.2 `POST /ai-visibility/recompute`

Kicks off the background run.

```python
# Request
{
  "brand_name": "Belt Creative",
  "competitor_domains_override": null   # optional, Phase 2/3 future use
}

# Response 202 Accepted
{
  "status": "running",
  "started_at": "2026-04-15T14:32:17Z",
  "estimated_duration_seconds": 150,
  "previous_cost_usd": 4.94,
  "estimated_this_run_usd": 2.00
}

# Response 409 if a run is already in-flight
# Response 503 if DataForSEO credentials missing or AI Optimization subscription inactive
# Response 503 if month-to-date spend + $3 budget > AI_VISIBILITY_MONTHLY_CAP_USD
```

Side effects:
- Writes `audits.brand_name_override`.
- Sets `report_json["ai_visibility"] = { status: "running", started_at: ... }` so the poller sees immediate state change.
- Spawns `asyncio.create_task(run_ai_visibility_analysis(...))`.

### 6.3 `GET /ai-visibility`

Dashboard poll target.

```python
# Never-run state
{ "status": "not_computed" }

# Running state
{ "status": "running", "started_at": "..." }

# Complete
{ "status": "ok" | "partial" | "failed", ... full blob from §5.2 ... }
```

## 7. Frontend architecture (Phase 2)

### 7.1 New page: `DashboardAIVisibilityPage.tsx`

Modeled on `DashboardLinkIntelligencePage.tsx`. Six sections, top to bottom:

1. **Header + metadata strip** — brand name (with *"manually set"* badge if override), last computed timestamp, overall status pill, total cost, duration, cumulative cost + run count. *"Recompute"* button opens the modal.
2. **Share of Voice** — horizontal Recharts bar chart. Brand row in accent color, competitors neutral. Explainer: *"Measured across {total_mentions_analyzed} AI responses from Google AI Overview + ChatGPT."*
3. **Platform Breakdown (Database)** — two cards for Google AI Overview and ChatGPT with mention count, AI search volume, impressions. Top triggering prompts listed below.
4. **Live Engine Tests** — 2×2 grid of cards (ChatGPT, Claude, Gemini, Perplexity). Each shows status pill, `brand_mentioned_in X/4 prompts`, expandable responses-by-prompt accordion, per-engine cost. Discovery vs reputation prompt labeling. Failed engines show error state (global retry in Phase 2; per-engine retry in Phase 2.5).
5. **Top Cited Pages** — table from `mentions_database.top_pages`: URL, mention count, clickable link.
6. **Cost & Methodology footer** — `cost_usd`, `cumulative_cost_usd`, prompts used (with discovery/reputation labels), data-source disclaimers explaining database vs live_test methodology.

Route addition in `frontend/src/router.tsx`:
```tsx
{ path: 'ai-visibility', lazy: () => import('./pages/DashboardAIVisibilityPage') }
```

### 7.2 KPI card: `AIVisibilityKpiCard.tsx`

Shown on `DashboardOverviewPage.tsx`. Four states:

- **Not computed:** *"AI Visibility — Not yet computed. [Run Analysis →]"* button opens modal directly.
- **Running:** *"AI Visibility — Running... ETA 2m 30s"* with spinner.
- **Computed (with competitors):** SOV percentage as hero number, *"X / 4 engines returned data"* subtext, *"View details →"* link. Age display uses `last_computed_at` ("Computed 3 days ago").
- **Computed (no competitors):** `mentions_database.total` as hero number (e.g. *"103 total mentions"*), subtext *"No competitors detected for SOV comparison"*, *"View details →"* link. Triggered when `competitors.domains.length === 0` OR `share_of_voice.competitor_sov` is empty.

### 7.3 Confirmation modal: `AIVisibilityModal.tsx`

Triggered from the KPI card or page. Shows:
- Auto-extracted brand name (editable text field, pre-filled from preview endpoint)
- Detected industry (read-only display)
- Competitor list (read-only in Phase 2, editable in Phase 3)
- Cost disclaimer: *"Previous runs total: ${cumulative_cost_usd}. This run will add ~$2.00."*
- *"Run Analysis"* confirm button

### 7.4 Sidebar placement

In `frontend/src/layouts/DashboardLayout.tsx`, add **AI Visibility** as a standalone entry **directly after Content Intelligence**. Not nested inside the CONTENT & SEO pillar group — AI Visibility is an intelligence layer (cross-cutting analysis), not a pillar page (deterministic scoring). Grouping it with pillar pages would blur the distinction.

A future "INTELLIGENCE LAYERS" super-group refactor (bundling Link Intelligence + Content Intelligence + AI Visibility) is tracked as an IA cleanup outside this spec's scope.

### 7.5 State management (Zustand)

Addition to `frontend/src/stores/auditStore.ts`:

```ts
aiVisibility: {
  data: AIVisibilitySnapshot | null,
  status: 'not_computed' | 'running' | 'ok' | 'partial' | 'failed',
  pollInterval: number | null,
  actions: {
    fetchStatus: (auditId: string) => Promise<void>,
    startRecompute: (auditId: string, brandName: string) => Promise<void>,
    startPolling: (auditId: string) => void,
    stopPolling: () => void,
  }
}
```

Polling: 5s interval while `status === 'running'`, stopped on completion or component unmount.

## 8. Phase 3 integration

### 8.1 Premium audit form changes

In `frontend/src/components/AuditForm.tsx` (FullSiteForm tab), add two optional fields below existing competitor URL inputs:

```tsx
<label>
  <input type="checkbox" name="ai_visibility_opt_in" defaultChecked={true} />
  Include AI Visibility analysis (adds ~$2.00 per audit, adds 2-3min to completion)
</label>

<input
  name="brand_name"
  placeholder="Brand name (optional — auto-detected if blank)"
  type="text"
/>
```

### 8.2 Backend request model extension

`PremiumAuditRequest` in `backend/main.py` — no new competitor field (reuses existing `competitor_urls`):

```python
class PremiumAuditRequest(BaseModel):
    # ... existing fields ...
    ai_visibility_opt_in: bool = False    # default True via frontend, False via API for safety
    brand_name: str | None = None          # auto-detect if None
```

### 8.3 Auto-run sibling task

After `_enrich_report_from_crawl` completes, check `audits.ai_visibility_opt_in`. If true:

```python
asyncio.create_task(
    run_ai_visibility_analysis(
        audit_id=audit_id,
        brand_override=audit_record.brand_name_override,
    )
)
```

Sibling — not awaited inside enrichment. Enrichment completion is reported to the user independently; AI Visibility status renders on its own card as "running" until done.

## 9. Executive summary integration

Four read points in `backend/executive_summary_generator.py`, all guarded by:
```python
if report.get("ai_visibility", {}).get("last_computed_status") == "ok":
```

### 9.1 Strategic Context section

If SOV data exists:
> *"AI engines surface your brand in {brand_sov*100:.0f}% of category responses, compared to {top_competitor_sov*100:.0f}% for {top_competitor}."*

### 9.2 Business Case section

If `mentions_database.ai_search_volume > 0`:
> *"Your brand appears in AI responses for queries generating approximately {ai_search_volume:,} monthly searches. Improving content structure and authority signals could increase both the frequency and prominence of these mentions."*

This is the strongest business-value statement in the dataset — a concrete traffic number tied directly to optimization opportunity.

### 9.3 Audit Diagnosis section

If any engine has `brand_mentioned_in < 2` (out of 4 prompts):
> *"AI engine coverage is uneven — {engines_with_low_mentions} return your brand in fewer than 2 of 4 test prompts."*

### 9.4 Key Risks section

If `mentions_database.total == 0`:
> *"Your brand is not yet indexed by AI search platforms (Google AI Overview, ChatGPT). This may indicate insufficient authority signals or recent brand establishment."*

## 10. Error handling & budget control

### 10.1 Per-engine isolation

`responses_fetcher.py` uses `asyncio.gather(*engine_tasks, return_exceptions=True)` with per-engine try/except wrapping:

```python
async def fetch_engine(engine: str) -> EngineResult:
    async with sem:  # global Semaphore(4) across all live calls
        try:
            responses = []
            for prompt in prompts:
                result = await client.llm_response(prompt.text, engine, timeout=120.0)
                cost_tracker.add(result.get("money_spent", 0))
                responses.append(result)
            return EngineResult(status="ok", responses=responses, ...)
        except httpx.TimeoutException:
            return EngineResult(status="failed", error=f"timeout after 120s", ...)
        except DataForSEOError as e:
            return EngineResult(status="failed", error=f"{e.status_code}: {e.message}", ...)
        except Exception as e:
            logger.exception(f"Unhandled error in {engine}")
            return EngineResult(status="failed", error=f"unexpected: {type(e).__name__}", ...)
```

### 10.2 Top-level status resolution

```python
def resolve_status(engine_results) -> str:
    oks = sum(1 for r in engine_results.values() if r.status == "ok")
    if oks == 4:   return "ok"
    if oks >= 1:   return "partial"
    return "failed"
```

### 10.3 Budget cap

**Soft-cap** before spawning a run:
```sql
SELECT SUM(ai_visibility_cumulative_cost_usd) FROM audits
  WHERE last_ai_visibility_run_at >= date_trunc('month', now());
```

If `month_to_date_spend + $3 > AI_VISIBILITY_MONTHLY_CAP_USD` (env var, default `100.0`):
→ respond `503 { detail: "AI Visibility monthly budget cap reached. Try again next month or contact admin." }`.

**Hard-cap:** none — once a run starts, it completes. Avoids mid-run abortion leaving partial charges.

### 10.4 Failure mode matrix

| Failure | Storage | UI behavior |
|---|---|---|
| Brand extraction fails (no salient ORGANIZATION) | `status: "failed"`, pre-engine | Modal error before recompute: *"No brand name could be auto-detected. Please enter manually."* |
| All 4 engines fail | `status: "failed"`, per-engine errors stored | Dashboard shows all-failed state + *"Retry"*. Costs logged even on failure (DataForSEO may charge for failed responses). |
| 1-3 engines fail | `status: "partial"`, successful engines populated | Failed engines show error cards. Global *"Retry"* recomputes everything (see §10.5 on cost-on-retry). |
| LLM Mentions returns empty | `mentions_database.total: 0`, blob still `ok` | Dashboard shows *"Your brand is not yet indexed. See Key Risks."* Live test still renders. |
| DataForSEO subscription inactive | Recompute `503` before any spend | Modal: *"AI Optimization subscription required. Contact admin."* |
| Monthly budget cap reached | Recompute `503` | Modal: *"Monthly budget cap reached."* |

### 10.5 Cost-on-retry semantics

Phase 2's initial ship uses **global recompute**, which re-pays for engines that already succeeded. Per-engine retry is deferred to Phase 2.5.

To avoid the retry-spend trap, three mitigations:
1. Recompute endpoint response includes `previous_cost_usd` (cumulative across all runs for this audit).
2. Modal displays: *"Previous runs total: ${cumulative_cost_usd}. This run will add ~$2.00."* — user sees total exposure before confirming.
3. `audits.ai_visibility_cumulative_cost_usd` is additive, mirrored into `report["ai_visibility"]["cumulative_cost_usd"]`. Dashboard always shows cumulative, never just latest.

## 11. Cost tracking

Every DataForSEO response includes a `money_spent` field. The `cost_tracker.py` accumulator pulls this into a single float per run.

On run completion:
```python
UPDATE audits SET
  ai_visibility_cumulative_cost_usd = ai_visibility_cumulative_cost_usd + :this_run_cost,
  ai_visibility_run_count = ai_visibility_run_count + 1,
  last_ai_visibility_run_at = NOW()
WHERE id = :audit_id;
```

Report blob writes both:
- `cost_usd`: this run only
- `cumulative_cost_usd`: total across all runs

## 12. Testing strategy

### 12.1 Stage 1 — Probe script (ships first)

`backend/scripts/probe_ai_visibility.py`:
- Makes ONE call to `llm_mentions_aggregated` for brand `"webflow"`.
- Makes ONE call to `llm_response` via the smallest engine (`gemini`).
- Prints: subscription status, sample response, reported `money_spent`, total cost.
- Run: `python -m backend.scripts.probe_ai_visibility`
- Cost: ~$0.10.

This is the **first thing merged**. Runs against live credentials. If it fails, we stop before writing 800 lines of engine code.

### 12.2 Stage 2 — Unit tests

Location: `backend/tests/ai_visibility/`. All fixture-driven, no network.

| Test file | Coverage |
|---|---|
| `test_prompts.py` | 4 templates render with `detected_industry`, `top_entity`, `brand_name` inputs. Discovery vs reputation tagging correct. |
| `test_brand_resolver.py` | Override always wins. NLP extraction picks highest salience ORGANIZATION. No ORGANIZATION entities → raises `BrandExtractionError`. |
| `test_competitor_resolver.py` | 3-tier fallback ordering. Domain normalization (`https://www.webflow.com/about` → `webflow.com`). |
| `test_sov_calculator.py` | SOV math with known inputs. Brand SOV capped at 1.0. Empty competitor set returns `{}` (feeds no-competitors KPI fallback). |
| `test_cost_tracker.py` | Accumulator handles None, missing keys, malformed floats. |
| `test_schema.py` | Dataclass round-trip to dict matches `report["ai_visibility"]` shape. |

Target: ~90% line coverage on pure-logic modules.

### 12.3 Stage 3 — Integration tests

`backend/tests/ai_visibility/test_engine_integration.py` — mocks `DataForSEOClient`. Verifies:
- Happy path: 4 engines succeed, status `"ok"`.
- Partial failure: 2 engines succeed + 2 timeout, status `"partial"`.
- Brand override path: `brand_name_override` in DB beats NLP extraction.
- No-competitors path: empty competitor set produces empty `competitor_sov`, status still `"ok"`.
- Cost tracking: mocked `money_spent` values summed correctly into `cost_usd`; `cumulative_cost_usd` increments correctly across multiple runs.

### 12.4 Stage 4 — Live manual tests

Executed from local dev against live DataForSEO:

1. **Belt Creative audit** (`4ef284bb-9c43-4150-a82d-25a92886d9ed`):
   - Dashboard → "Run AI Visibility Analysis".
   - Verify modal pre-fills "Belt Creative" as brand.
   - Submit, watch polling.
   - On complete: verify all 6 dashboard sections render, `cost_usd` logged, at least 3/4 engines succeeded.
   - Verify `audits.brand_name_override = 'Belt Creative'` in DB.
2. **Veza Digital audit** (`b5afb24f-89ba-4643-92cf-9a5dfff5e8fa`):
   - Same flow, verify different brand auto-extracts.
   - Deliberately edit brand in modal to test override persists.
3. **Recompute test** on Belt Creative:
   - Click Recompute — verify modal uses saved override, not re-detected NLP value.
   - Verify `cumulative_cost_usd` updates correctly.
4. **Budget cap test:**
   - Temporarily set `AI_VISIBILITY_MONTHLY_CAP_USD=0.01`.
   - Verify 503 response from recompute endpoint.

Total manual test suite cost: ~$6-8.

## 13. Rollout checklist

### Phase 1 (backend foundation)
- [ ] Probe script merged and run successfully
- [ ] DB migration applied (both dev and production)
- [ ] `backend/ai_visibility/` package created per §4.1
- [ ] `DataForSEOClient` extended with 5 new methods
- [ ] Three API endpoints live
- [ ] Unit + integration tests pass
- [ ] Manual test against Belt Creative via curl succeeds

### Phase 2 (dashboard UI)
- [ ] `DashboardAIVisibilityPage.tsx` renders all 6 sections against Belt Creative data
- [ ] `AIVisibilityKpiCard.tsx` renders all 4 states
- [ ] `AIVisibilityModal.tsx` pre-fills + submits correctly
- [ ] Sidebar entry placed as standalone item after Content Intelligence
- [ ] Zustand polling slice stops polling on completion/unmount
- [ ] Manual test: run + recompute flow on Belt Creative + Veza Digital

### Phase 3 (integration polish)
- [ ] Premium audit form has opt-in checkbox + optional brand field
- [ ] `ai_visibility_opt_in` persisted to audits table
- [ ] Auto-run sibling task spawns correctly after enrichment
- [ ] Four executive summary read points render with real data
- [ ] Regression: premium audits without opt-in don't trigger AI Visibility

### Cross-phase operational
- [ ] `AI_VISIBILITY_MONTHLY_CAP_USD` env var set on Railway (default 100)
- [ ] DataForSEO AI Optimization subscription verified active
- [ ] Cost tracking verified: $2.00 ± $0.60 per run across 5 runs
- [ ] Error log monitoring set up for engine failures

## 14. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Enrichment pipeline blocks waiting for 16 live LLM calls | AI Visibility runs as separate `asyncio.create_task`, never inside enrichment |
| Sandbox mode breaks AI Optimization calls | Hardcoded live `AI_OPT_BASE_URL`, ignores `DATAFORSEO_USE_SANDBOX` flag |
| `competitor_urls` field collision with existing competitive_auditor/WDF*IDF usage | Reused, not replaced — competitor_resolver extracts bare domains from URLs without mutating field semantics |
| Unverified DataForSEO subscription burns budget on false assumptions | Probe script ships first; engine work is blocked until probe succeeds |
| NLP brand extraction fails for single-founder / personal brands | `brand_name_override` column + modal confirmation flow |
| Runaway costs from retries or buggy loops | Monthly soft-cap enforced at recompute endpoint; `cumulative_cost_usd` surfaced in UI so users see total spend |
| Client misreads database mentions vs live_test counts as equivalent | Schema splits sources into `mentions_database` and `live_test`; dashboard sections + methodology footer explain the difference |
| AI Visibility sidebar entry gets grouped with pillar pages | Placed as standalone intelligence-layer entry after Content Intelligence, explicitly not inside CONTENT & SEO pillar group |
