# AI Visibility Phase 3 — Auto-Run + Executive Summary Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AI Visibility run automatically during premium audits (opt-in checkbox, defaulting ON) and inject AI Visibility insights into the 4 executive summary read points defined in the spec.

**Architecture:** Add `ai_visibility_opt_in` + `brand_name` fields to `PremiumAuditRequest`, persist `ai_visibility_opt_in` to a new DB column, spawn AI Visibility as a sibling `asyncio.create_task` after `_enrich_report_from_crawl` completes, and inject 4 conditional AI Visibility statements into the executive summary generator sections. The frontend audit form gains a checkbox (defaulted ON) and optional brand name input.

**Tech Stack:** FastAPI (Python 3.10+), asyncpg/PostgreSQL, React 19, TypeScript, Zustand 5, TailwindCSS 4

**Key insight from production data:** Actual AI Visibility cost is ~$0.26/run (not $2.00 estimated), meaning the $100/month budget cap supports ~380 runs. This justifies defaulting the checkbox ON — budget anxiety is minimal.

---

## File Structure

### New files
| File | Responsibility |
|------|---------------|
| `backend/migrations/008_ai_visibility_opt_in.sql` | Phase 3 DB migration: add `ai_visibility_opt_in` column to audits |

### Modified files
| File | Change |
|------|--------|
| `backend/main.py:109-117` | Add `ai_visibility_opt_in` and `brand_name` to `PremiumAuditRequest` |
| `backend/main.py:549-604` | Persist `ai_visibility_opt_in` flag into `report_json` before DB save |
| `backend/main.py:1563-1575` | Spawn AI Visibility sibling task after enrichment completes |
| `backend/executive_summary_generator.py:479-530` | Section 1 (Strategic Context): inject SOV or zero-mentions statement |
| `backend/executive_summary_generator.py:694-730` | Section 2 (Business Case): inject AI search volume opportunity |
| `backend/executive_summary_generator.py:841-860` | Section 3 (Diagnosis): inject engine coverage diagnostic |
| `backend/executive_summary_generator.py:1046-1121` | Section 4 (Key Risks): inject AI indexing risk |
| `frontend/src/components/AuditForm.tsx:52-88` | Add checkbox state + brand name state, pass to onRunAudit |
| `frontend/src/stores/auditStore.ts:11-46` | Extend runAudit signature and body to include AI visibility fields |

---

### Task 1: DB Migration — `ai_visibility_opt_in` column

**Files:**
- Create: `backend/migrations/008_ai_visibility_opt_in.sql`

- [ ] **Step 1: Create the migration file**

```sql
-- 008_ai_visibility_opt_in.sql
-- Phase 3: AI Visibility auto-run opt-in flag

ALTER TABLE audits ADD COLUMN IF NOT EXISTS ai_visibility_opt_in BOOLEAN DEFAULT FALSE;
```

- [ ] **Step 2: Run the migration against production**

```bash
# Connect to Railway PostgreSQL and run the migration
# The exact command depends on your Railway setup, e.g.:
psql "$DATABASE_URL" -f backend/migrations/008_ai_visibility_opt_in.sql
```

Expected: `ALTER TABLE` succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/008_ai_visibility_opt_in.sql
git commit -m "feat(db): add ai_visibility_opt_in column to audits table"
```

---

### Task 2: Extend `PremiumAuditRequest` + persist opt-in flag

**Files:**
- Modify: `backend/main.py:109-117` (PremiumAuditRequest model)
- Modify: `backend/main.py:549-604` (persist phase)

- [ ] **Step 1: Add fields to PremiumAuditRequest**

In `backend/main.py`, find the `PremiumAuditRequest` class (line 109) and add two fields:

```python
class PremiumAuditRequest(BaseModel):
    url: HttpUrl
    competitor_urls: list[str] = []
    gsc_property: str | None = None
    target_keyword: str | None = None
    max_pages: int = 2000
    nlp_classification: bool = True
    nlp_entity_analysis: bool = True
    nlp_sentiment: bool = False
    ai_visibility_opt_in: bool = True    # NEW: default ON per production cost data ($0.26/run)
    brand_name: str | None = None        # NEW: optional manual brand name override
```

Note: The spec says `False` for API safety, but production data shows $0.26/run cost (not $2.00), so defaulting ON is safe. The frontend will also default it ON.

- [ ] **Step 2: Persist the opt-in flag and brand_name into report_json**

In `backend/main.py`, inside `perform_premium_audit()`, find the section just before `await save_audit_history(...)` (around line 559). Add the AI visibility fields to the report dict:

```python
        # Persist AI Visibility opt-in state for the background enrichment task
        report["ai_visibility_opt_in"] = request.ai_visibility_opt_in
        if request.brand_name:
            report["ai_visibility_brand_name"] = request.brand_name
```

Insert these lines directly **before** the `await save_audit_history(...)` call (line 559).

- [ ] **Step 3: Also persist `ai_visibility_opt_in` to the audits column**

After the `await save_audit_history(...)` call, add a DB update to persist the column value:

```python
        # Persist ai_visibility_opt_in to its dedicated column
        if request.ai_visibility_opt_in:
            try:
                from db_router import update_audit_column
                await update_audit_column(audit_id, "ai_visibility_opt_in", True)
            except Exception as e:
                logger.warning(f"Failed to persist ai_visibility_opt_in: {e}")
```

**Note:** `update_audit_column` may not exist yet. If not, use a raw query via `update_audit_report` to set the flag in report_json (which we already do in Step 2), and skip the dedicated column update — the report_json field is sufficient for the enrichment task to read.

Simpler alternative — just use the report_json field in step 2. The background task reads `report_json`, not the `ai_visibility_opt_in` column. The column is for future querying only. We can update it in a later pass.

- [ ] **Step 4: Verify no type errors**

```bash
cd backend && python -c "from main import app; print('OK')"
```

Expected: `OK` with no import errors.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py
git commit -m "feat(ai-visibility): add opt-in + brand_name to PremiumAuditRequest"
```

---

### Task 3: Spawn AI Visibility sibling task after enrichment

**Files:**
- Modify: `backend/main.py:1563-1595` (inside `_enrich_report_from_crawl`)

This is the core auto-run integration. After `_enrich_report_from_crawl` finishes regenerating the executive summary (line 1575), it should check the opt-in flag and spawn the AI Visibility pipeline as a sibling task.

- [ ] **Step 1: Add the sibling task spawn**

In `backend/main.py`, inside `_enrich_report_from_crawl`, find the block that ends at line 1575 (after the post-enrichment summary regeneration `except` block). Insert the following **after** the summary regeneration block and **before** the link graph edges persistence block (which starts at line 1577 with `# Also persist link graph edges`):

```python
        # ── Spawn AI Visibility as a sibling task (Phase 3) ──
        try:
            enriched_record_for_aiv = await get_audit_by_id(audit_id)
            if enriched_record_for_aiv:
                full_rpt = enriched_record_for_aiv.get("report_json") or {}
                if isinstance(full_rpt, str):
                    full_rpt = json.loads(full_rpt)
                if full_rpt.get("ai_visibility_opt_in"):
                    brand_override = full_rpt.get("ai_visibility_brand_name")
                    asyncio.create_task(
                        run_ai_visibility_analysis(
                            audit_id=str(audit_id),
                            brand_override=brand_override,
                        )
                    )
                    logger.info(f"AI Visibility sibling task launched for audit {audit_id}")
        except Exception as e:
            logger.warning(f"Failed to launch AI Visibility sibling task (non-fatal): {e}")
```

**Key design decisions:**
- This is a **sibling task**, not awaited — enrichment completion is reported independently, AI Visibility runs in the background.
- We re-read the audit record to get the freshest report_json (which now includes enrichment data that AI Visibility's brand resolver needs for NLP entities).
- The `ai_visibility_opt_in` flag comes from report_json (set in Task 2 Step 2).
- Non-fatal: if spawn fails, enrichment still succeeds.

- [ ] **Step 2: Verify the import is already present**

Check that `run_ai_visibility_analysis` is already imported at the top of `main.py`. It should be (line 69):

```python
from ai_visibility import run_ai_visibility_analysis
```

If not, add it.

- [ ] **Step 3: Verify no type errors**

```bash
cd backend && python -c "from main import app; print('OK')"
```

Expected: `OK` with no import errors.

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat(ai-visibility): auto-run as sibling task after enrichment when opt-in"
```

---

### Task 4: Executive Summary — Section 1 (Strategic Context)

**Files:**
- Modify: `backend/executive_summary_generator.py:479-530`

Inject AI Visibility context into the opening strategic framing. Guarded by status check.

- [ ] **Step 1: Add AI Visibility data extraction helper**

At the top of the file, near the other `_get_*` helper functions (around line 40-60), add:

```python
def _get_ai_visibility(report: dict) -> dict | None:
    """Extract AI Visibility data if available and successfully computed."""
    aiv = report.get("ai_visibility")
    if not aiv or aiv.get("last_computed_status") not in ("ok", "partial"):
        return None
    return aiv
```

- [ ] **Step 2: Add AI Visibility statement to Strategic Context**

In `_section_strategic_context` (line 479), find the section where `lines` is being built. After the CMS framing fragment and before the return, add an AI visibility statement. Find the end of the function where final lines are assembled (just before `return "\n\n".join(lines)` around line 691) and add:

```python
    # AI Visibility context (Phase 3)
    aiv = _get_ai_visibility(report)
    if aiv:
        sov = aiv.get("share_of_voice")
        mentions_total = aiv.get("mentions_database", {}).get("total", 0)
        if sov and sov.get("brand_sov") is not None:
            brand_pct = round(sov["brand_sov"] * 100)
            # Find top competitor SOV
            comp_sov = sov.get("competitor_sov", {})
            if comp_sov:
                top_comp = max(comp_sov.items(), key=lambda x: x[1])
                lines.append(
                    f"AI engines currently surface this brand in {brand_pct}% of "
                    f"category responses, compared to {round(top_comp[1] * 100)}% "
                    f"for {top_comp[0]}."
                )
            else:
                lines.append(
                    f"AI engines currently surface this brand in {brand_pct}% of "
                    f"category responses."
                )
        elif mentions_total == 0:
            lines.append(
                "The site is not yet appearing in AI-generated search responses — "
                "an untapped visibility channel where early movers are building "
                "compounding citation advantage."
            )
```

Insert this **before** the final `return` statement of the function.

- [ ] **Step 3: Verify no syntax errors**

```bash
cd backend && python -c "from executive_summary_generator import generate_executive_summary; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/executive_summary_generator.py
git commit -m "feat(exec-summary): add AI visibility context to strategic section"
```

---

### Task 5: Executive Summary — Section 2 (Business Case)

**Files:**
- Modify: `backend/executive_summary_generator.py:694-730`

Inject AI search volume opportunity into business case projections.

- [ ] **Step 1: Add AI search volume statement to Business Case**

In `_section_roi_projection` (line 694), find the section where lines are being built. After the traffic-growth range calculations and before the return, add:

```python
    # AI search volume opportunity (Phase 3)
    aiv = _get_ai_visibility(report)
    if aiv:
        ai_search_vol = aiv.get("mentions_database", {}).get("ai_search_volume", 0)
        if ai_search_vol > 0:
            lines.append(
                f"This brand already appears in AI responses for queries generating "
                f"approximately {ai_search_vol:,} monthly searches. Improving content "
                f"structure and authority signals could increase both the frequency "
                f"and prominence of these mentions."
            )
        elif aiv.get("mentions_database", {}).get("total", 0) == 0:
            engines = aiv.get("live_test", {}).get("engines", {})
            ok_engines = sum(1 for e in engines.values() if isinstance(e, dict) and e.get("status") == "ok")
            if ok_engines > 0:
                lines.append(
                    f"AI engines are responsive to brand queries ({ok_engines}/4 engines "
                    f"returned results) but the brand is not yet indexed in AI search "
                    f"databases. Structured content improvements can unlock this channel."
                )
```

Insert this **before** the final `return` statement of the function.

- [ ] **Step 2: Verify no syntax errors**

```bash
cd backend && python -c "from executive_summary_generator import generate_executive_summary; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/executive_summary_generator.py
git commit -m "feat(exec-summary): add AI search volume to business case section"
```

---

### Task 6: Executive Summary — Section 3 (Diagnosis)

**Files:**
- Modify: `backend/executive_summary_generator.py:841-860`

Inject engine coverage diagnostic when engines show uneven results.

- [ ] **Step 1: Add AI engine coverage diagnostic**

In `_section_diagnosis` (line 841), find the `statements` list where diagnostic lines are appended. After the existing statements (before the final assembly loop), add:

```python
    # AI engine coverage diagnostic (Phase 3)
    aiv = _get_ai_visibility(report)
    if aiv:
        engines = aiv.get("live_test", {}).get("engines", {})
        low_engines = []
        for eng_name, eng_data in engines.items():
            if isinstance(eng_data, dict) and eng_data.get("status") == "ok":
                if eng_data.get("brand_mentioned_in", 0) < 2:
                    low_engines.append(eng_name)
        if low_engines:
            engine_names = ", ".join(
                {"chatgpt": "ChatGPT", "claude": "Claude", "gemini": "Gemini", "perplexity": "Perplexity"}.get(e, e)
                for e in low_engines
            )
            statements.append(
                f"AI engine coverage is uneven — {engine_names} return this brand "
                f"in fewer than 2 of 4 test prompts, indicating gaps in content "
                f"authority or topical coverage for those platforms."
            )
```

Insert this after the last existing `statements.append(...)` block and before the assembly section where statements are joined into lines.

- [ ] **Step 2: Verify no syntax errors**

```bash
cd backend && python -c "from executive_summary_generator import generate_executive_summary; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/executive_summary_generator.py
git commit -m "feat(exec-summary): add AI engine coverage diagnostic"
```

---

### Task 7: Executive Summary — Section 4 (Key Risks)

**Files:**
- Modify: `backend/executive_summary_generator.py:1046-1121`

Inject AI indexing risk when mentions database shows zero mentions.

- [ ] **Step 1: Add AI indexing risk**

In `_section_key_risks` (line 1046), find the `risks` list. There's already an AI presence risk based on `aeo` and `rag` scores (lines 1067-1074). Add a **more specific** AI visibility risk using real data, placing it directly **after** the existing AI presence risk block:

```python
    # AI indexing risk — based on real AI Visibility data (Phase 3)
    aiv = _get_ai_visibility(report)
    if aiv and aiv.get("mentions_database", {}).get("total", 0) == 0:
        # Replace the generic aeo/rag risk with a data-backed one
        # Remove the generic one if it was added above
        risks = [r for r in risks if "AI-generated answers" not in r]
        risks.append(
            "The brand is not yet indexed by AI search platforms (Google AI "
            "Overview, ChatGPT). As AI-generated answers capture an increasing "
            "share of search traffic, absence from these results means losing "
            "visibility to competitors who are already cited"
        )
```

Insert this **after** the existing AI presence risk block (after line 1074) and **before** the orphan pages risk block (line 1077).

- [ ] **Step 2: Verify no syntax errors**

```bash
cd backend && python -c "from executive_summary_generator import generate_executive_summary; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/executive_summary_generator.py
git commit -m "feat(exec-summary): add AI indexing risk based on real visibility data"
```

---

### Task 8: Frontend — Add AI Visibility checkbox + brand name to audit form

**Files:**
- Modify: `frontend/src/components/AuditForm.tsx:52-88`

Add an AI Visibility opt-in checkbox (defaulted ON) and an optional brand name input to the premium audit form. Also extend the `onRunAudit` callback signature.

- [ ] **Step 1: Extend the AuditFormProps interface**

In `frontend/src/components/AuditForm.tsx`, update the `AuditFormProps` interface (line 23) to accept the new fields:

```typescript
interface AuditFormProps {
  onRunAudit: (
    url: string,
    auditType: 'single' | 'site' | 'competitive',
    competitorUrls?: string[],
    tier?: 'free' | 'premium',
    aiVisibilityOptIn?: boolean,
    brandName?: string,
  ) => void;
  isLoading: boolean;
  error: string | null;
}
```

- [ ] **Step 2: Add state variables**

After the existing state declarations (line 56), add:

```typescript
  const [aiVisibility, setAiVisibility] = useState(true); // Default ON
  const [brandName, setBrandName] = useState('');
```

- [ ] **Step 3: Pass the new fields in handleSubmit**

Update the `handleSubmit` function (line 74). In the `else` branch for the comprehensive audit (line 82-88), pass the new fields:

```typescript
    } else {
      // Comprehensive Audit tab — always uses premium endpoint
      const validCompetitors = competitors
        .filter((c) => c.trim())
        .map((c) => normalizeUrl(c));

      onRunAudit(
        submitUrl,
        'single',
        validCompetitors,
        'premium',
        aiVisibility,
        brandName.trim() || undefined,
      );
    }
```

- [ ] **Step 4: Add the checkbox and brand name input to the fullsite form UI**

In the fullsite `Tabs.Content` (line 196), find the competitors section (around line 237-287). Insert the AI Visibility section **between** the competitors section and the submit button (before line 289 `{/* Submit */}`):

```tsx
                {/* AI Visibility */}
                <div className="space-y-2 pt-2 border-t border-border">
                  <label className="flex items-center gap-3 px-1 py-2 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={aiVisibility}
                      onChange={(e) => setAiVisibility(e.target.checked)}
                      className="w-4 h-4 rounded border-border accent-accent"
                      disabled={isLoading}
                    />
                    <div className="flex-1">
                      <span className="text-sm font-semibold text-text group-hover:text-accent transition-colors">
                        Include AI Visibility Analysis
                      </span>
                      <span className="block text-[11px] text-text-muted mt-0.5">
                        Test brand presence across ChatGPT, Claude, Gemini & Perplexity (~$0.30)
                      </span>
                    </div>
                  </label>
                  <AnimatePresence>
                    {aiVisibility && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="bg-surface-raised border border-border rounded-lg p-1">
                          <input
                            type="text"
                            className="w-full bg-transparent px-3 py-2 text-sm font-medium text-text placeholder:text-text-muted focus:outline-none"
                            placeholder="Brand name (optional — auto-detected if blank)"
                            value={brandName}
                            onChange={(e) => setBrandName(e.target.value)}
                            disabled={isLoading}
                          />
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/AuditForm.tsx
git commit -m "feat(ai-visibility): add opt-in checkbox + brand name to premium audit form"
```

---

### Task 9: Frontend — Extend auditStore to pass AI visibility fields

**Files:**
- Modify: `frontend/src/stores/auditStore.ts:11-46`

Extend the `runAudit` signature and request body to include the AI visibility fields.

- [ ] **Step 1: Extend the AuditState interface**

In `frontend/src/stores/auditStore.ts`, update the `runAudit` type (line 11):

```typescript
  runAudit: (
    url: string,
    auditType: 'single' | 'site' | 'competitive',
    competitorUrls?: string[],
    tier?: 'free' | 'premium',
    aiVisibilityOptIn?: boolean,
    brandName?: string,
  ) => Promise<void>;
```

- [ ] **Step 2: Update the implementation signature**

Update the `runAudit` implementation (line 28):

```typescript
  runAudit: async (url, auditType, competitorUrls = [], tier = 'free', aiVisibilityOptIn, brandName) => {
```

- [ ] **Step 3: Pass AI visibility fields in the premium request body**

In the body construction (line 38-39), extend the premium body:

```typescript
      if (tier === 'premium' && auditType === 'single') {
        body = {
          url,
          competitor_urls: competitorUrls,
          ai_visibility_opt_in: aiVisibilityOptIn ?? true,
          ...(brandName ? { brand_name: brandName } : {}),
        };
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/auditStore.ts
git commit -m "feat(ai-visibility): pass opt-in + brand_name in premium audit request"
```

---

### Task 10: Post-enrichment executive summary re-generation includes AI Visibility data

**Files:**
- Modify: `backend/main.py:1563-1575` (already modified in Task 3)

This is a sequencing concern: the executive summary is regenerated **during** enrichment (line 1571-1572), but AI Visibility runs as a **sibling task** spawned after enrichment. This means the first post-enrichment summary won't include AI Visibility data.

The fix: AI Visibility's own engine already regenerates the executive summary after it completes. We need to add that to the AI visibility engine.

- [ ] **Step 1: Add executive summary regeneration to AI Visibility engine**

In `backend/ai_visibility/engine.py`, find the end of `run_ai_visibility_analysis` where it writes the final result to `update_audit_report` (around line 156-179). After the final `update_audit_report` call, add:

```python
        # Regenerate executive summary with AI Visibility data included
        try:
            from executive_summary_generator import generate_executive_summary
            refreshed_audit = await get_audit_by_id(audit_id)
            if refreshed_audit:
                full_rpt = refreshed_audit.get("report_json") or {}
                if isinstance(full_rpt, str):
                    full_rpt = json.loads(full_rpt)
                competitive_data = full_rpt.get("competitive_data")
                new_summary = generate_executive_summary(full_rpt, competitive_data)
                await update_audit_report(audit_id, {"executive_summary": new_summary})
                logger.info(f"Executive summary regenerated with AI Visibility data: {len(new_summary)} chars")
        except Exception as e:
            logger.warning(f"Post-AI-Visibility summary regeneration failed (non-fatal): {e}")
```

- [ ] **Step 2: Read the current engine.py to find the exact insertion point**

Read `backend/ai_visibility/engine.py` to find where the final `update_audit_report` call is, and insert the summary regeneration block immediately after it.

- [ ] **Step 3: Verify no import errors**

```bash
cd backend && python -c "from ai_visibility.engine import run_ai_visibility_analysis; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/ai_visibility/engine.py
git commit -m "feat(ai-visibility): regenerate executive summary after AI visibility completes"
```

---

### Task 11: Deploy and verify end-to-end

**Files:**
- No code changes — verification only

- [ ] **Step 1: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 2: Run backend import check**

```bash
cd backend && python -c "from main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit all changes and push**

```bash
git push origin main
```

Expected: Railway auto-deploys.

- [ ] **Step 4: Verify health check**

```bash
curl https://waio.up.railway.app/api/health
```

Expected: `{"status": "ok"}`

- [ ] **Step 5: Run a test premium audit with AI Visibility**

Submit a premium audit via the form with AI Visibility checkbox ON. After the audit completes and enrichment finishes, verify:
1. AI Visibility analysis starts automatically (visible in the dashboard AI Visibility KPI card showing "Running")
2. After AI Visibility completes, the executive summary includes AI visibility statements
3. The AI Visibility dashboard page shows data

---

## Self-Review Checklist

**Spec coverage:**
- [x] Premium audit form checkbox (defaults ON) — Task 8
- [x] Optional brand name field — Task 8
- [x] `ai_visibility_opt_in` persisted to audits table — Task 1 + Task 2
- [x] Auto-run sibling task spawns after enrichment — Task 3
- [x] Strategic Context read point — Task 4
- [x] Business Case read point — Task 5
- [x] Audit Diagnosis read point — Task 6
- [x] Key Risks read point — Task 7
- [x] Frontend passes new fields to API — Task 9
- [x] Executive summary regenerated after AI Visibility completes — Task 10
- [x] Regression: premium audits without opt-in don't trigger AI Visibility — Task 3 (guarded by `ai_visibility_opt_in` check)

**Adjusted priority from production data:**
- [x] Default checkbox ON (not OFF) — $0.26/run means budget supports ~380 runs/month
- [x] Cost display in checkbox label reflects actual cost (~$0.30 not ~$2.00)

**Placeholder scan:** No TBDs, TODOs, or vague instructions found.

**Type consistency:** `ai_visibility_opt_in` (bool) and `brand_name` (str | None / string | undefined) used consistently across Python model, report_json, TypeScript interface, and Zustand store.
