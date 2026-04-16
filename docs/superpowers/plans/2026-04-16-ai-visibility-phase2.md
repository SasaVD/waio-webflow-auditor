# AI Visibility Phase 2 — Dashboard UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the AI Visibility dashboard page, KPI card, confirmation modal, sidebar entry, and Zustand polling slice — plus fix the backend competitor_urls DB query gap discovered during Phase 1 production testing.

**Architecture:** A new lazy-loaded dashboard page (`DashboardAIVisibilityPage`) with 6 sections, a Zustand slice for polling, a confirmation modal triggered from both the overview KPI card and the page header, and sidebar entry placed after Content Intelligence. Backend fix adds `competitor_urls` column to the `get_audit_by_id` SELECT query.

**Tech Stack:** React 19, TypeScript strict, Zustand 5, Framer Motion 11 (import from `motion/react`), Recharts, Lucide icons, Radix UI primitives, TailwindCSS 4 with existing `@theme` tokens.

**Production data profiles driving design decisions:**
- Belt Creative: zero mentions, 4/4 engines ok, brand mentioned in 1/4 prompts (reputation only), no competitors, cost $0.26
- Veza Digital: zero mentions, 4/4 engines ok, brand mentioned in 1/4 prompts (reputation only), no competitors (DB gap), cost $0.25
- Zero-state is the common case for boutique agencies — dashboard must frame this as opportunity, not failure
- Perplexity consistently returns the richest responses with live citations

---

## File Structure

### New files
| File | Responsibility |
|------|---------------|
| `frontend/src/stores/aiVisibilityStore.ts` | Zustand store: fetch, poll, recompute actions for AI Visibility data |
| `frontend/src/pages/DashboardAIVisibilityPage.tsx` | Full page with 6 sections: header, SOV, platform breakdown, live engine tests, top pages, cost footer |
| `frontend/src/components/ai-visibility/AIVisibilityKpiCard.tsx` | Overview page card with 4 states (not_computed, running, zero-mentions, has-data) |
| `frontend/src/components/ai-visibility/AIVisibilityModal.tsx` | Confirmation modal: brand name input, industry display, cost warning, submit |
| `frontend/src/components/ai-visibility/EngineCard.tsx` | Single engine result card with status, brand mention count, expandable responses |
| `frontend/src/components/ai-visibility/ZeroMentionsCard.tsx` | Opportunity framing card for zero-mention brands |

### Modified files
| File | Change |
|------|--------|
| `frontend/src/router.tsx` | Add lazy import + route for `ai-visibility` |
| `frontend/src/layouts/DashboardLayout.tsx` | Add sidebar entry after Content Intelligence |
| `frontend/src/pages/DashboardOverviewPage.tsx` | Add AI Visibility KPI card in the intelligence cards section |
| `backend/db_postgres.py:275-300` | Add `competitor_urls` to SELECT in `get_audit_by_id` |
| `backend/db.py:172-190` | Add `competitor_urls` to SELECT in SQLite `get_audit_by_id` (if column exists) |

---

### Task 1: Fix `competitor_urls` not fetched from DB

**Files:**
- Modify: `backend/db_postgres.py:275-300`
- Test: `backend/tests/ai_visibility/test_engine_integration.py` (existing tests still pass)

- [ ] **Step 1: Add `competitor_urls` to the PostgreSQL SELECT query**

In `backend/db_postgres.py`, function `get_audit_by_id` (line ~275), update the SELECT to include `competitor_urls` and add it to the return dict:

```python
async def get_audit_by_id(audit_id) -> Optional[Dict[str, Any]]:
    """Retrieve a full audit (including report_json) by its UUID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, url, tier, audit_type, overall_score, overall_label,
                      report_json, created_at, detected_cms, competitor_urls
               FROM audits WHERE id = $1""",
            audit_id if isinstance(audit_id, uuid.UUID) else uuid.UUID(str(audit_id)),
        )
    if not row:
        return None
    report = row["report_json"]
    if isinstance(report, str):
        report = json.loads(report)
    return {
        "id": str(row["id"]),
        "url": row["url"],
        "tier": row["tier"],
        "audit_type": row["audit_type"],
        "overall_score": row["overall_score"],
        "overall_label": row["overall_label"],
        "report_json": report,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "detected_cms": row["detected_cms"],
        "competitor_urls": list(row["competitor_urls"]) if row["competitor_urls"] else [],
    }
```

- [ ] **Step 2: Update the engine orchestrator to read `competitor_urls` from the audit record**

In `backend/ai_visibility/engine.py`, find the line (around line 80-84):
```python
competitor_urls = report.get("competitor_urls") or []
```

Change it to also check the audit record's top-level field:
```python
competitor_urls = audit.get("competitor_urls") or report.get("competitor_urls") or []
```

This ensures competitor_urls are found whether stored in the audit column or inside report_json.

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `python3 -m pytest backend/tests/ai_visibility/ -v`
Expected: All 61 tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/db_postgres.py backend/ai_visibility/engine.py
git commit -m "fix(db): include competitor_urls in get_audit_by_id query"
```

---

### Task 2: Create the AI Visibility Zustand store

**Files:**
- Create: `frontend/src/stores/aiVisibilityStore.ts`

- [ ] **Step 1: Create the store file**

```typescript
import { create } from 'zustand';

const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

export interface BrandPreview {
  auto_extracted: string | null;
  auto_extracted_salience: number | null;
  override: string | null;
  detected_industry: string | null;
  top_nlp_entity: string | null;
  competitors_preview: {
    user_provided: string[];
    auto_detected: string[];
    tier_3_fallback_available: boolean;
  };
  cumulative_cost_usd: number;
  run_count: number;
}

export interface EngineResult {
  status: 'ok' | 'failed';
  cost_usd: number;
  brand_mentioned_in: number;
  error?: string;
  responses_by_prompt: Record<
    string,
    { text: string; mentioned: boolean }
  >;
}

export interface AIVisibilityData {
  status: string;
  last_computed_at: string;
  last_computed_status: string;
  run_count: number;
  brand_name: string;
  brand_name_source: string;
  detected_industry: string | null;
  competitors: { domains: string[]; source: string };
  mentions_database: {
    total: number;
    by_platform: Record<string, number>;
    ai_search_volume: number;
    impressions: number;
    top_pages: Array<{ url: string; mention_count: number }>;
    triggering_prompts: Array<{
      prompt: string;
      platform: string;
      model_name: string;
      ai_search_volume: number;
    }>;
  };
  live_test: {
    prompts_used: Array<{ id: number; text: string; category: string }>;
    engines: Record<string, EngineResult>;
  };
  share_of_voice?: {
    source: string;
    brand_sov: number;
    competitor_sov: Record<string, number>;
    total_mentions_analyzed: number;
  };
  cost_usd: number;
  cumulative_cost_usd: number;
  duration_seconds: number;
}

type AIVisibilityStatus = 'idle' | 'loading' | 'not_computed' | 'running' | 'ok' | 'partial' | 'failed';

interface AIVisibilityState {
  data: AIVisibilityData | null;
  status: AIVisibilityStatus;
  brandPreview: BrandPreview | null;
  error: string | null;
  pollTimer: ReturnType<typeof setInterval> | null;

  fetchStatus: (auditId: string) => Promise<void>;
  fetchBrandPreview: (auditId: string) => Promise<void>;
  startRecompute: (auditId: string, brandName: string) => Promise<{ ok: boolean; error?: string }>;
  startPolling: (auditId: string) => void;
  stopPolling: () => void;
  reset: () => void;
}

export const useAIVisibilityStore = create<AIVisibilityState>((set, get) => ({
  data: null,
  status: 'idle',
  brandPreview: null,
  error: null,
  pollTimer: null,

  fetchStatus: async (auditId: string) => {
    set({ status: 'loading', error: null });
    try {
      const res = await fetch(`${apiBase}/api/audit/${auditId}/ai-visibility`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to fetch AI Visibility status');
      const json = await res.json();

      if (json.status === 'not_computed') {
        set({ status: 'not_computed', data: null });
      } else if (json.status === 'running') {
        set({ status: 'running', data: null });
        get().startPolling(auditId);
      } else {
        set({
          status: json.last_computed_status as AIVisibilityStatus,
          data: json as AIVisibilityData,
        });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      set({ status: 'failed', error: msg });
    }
  },

  fetchBrandPreview: async (auditId: string) => {
    try {
      const res = await fetch(`${apiBase}/api/audit/${auditId}/ai-visibility/brand-preview`, {
        credentials: 'include',
      });
      if (!res.ok) {
        if (res.status === 409) {
          set({ error: 'NLP enrichment not yet complete — run a premium audit first.' });
          return;
        }
        throw new Error('Failed to fetch brand preview');
      }
      const json = await res.json();
      set({ brandPreview: json as BrandPreview });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      set({ error: msg });
    }
  },

  startRecompute: async (auditId: string, brandName: string) => {
    try {
      const res = await fetch(`${apiBase}/api/audit/${auditId}/recompute-ai-visibility`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ brand_name: brandName }),
      });
      if (!res.ok) {
        const errData = await res.json();
        const detail = errData.detail || 'Failed to start analysis';
        set({ error: typeof detail === 'string' ? detail : JSON.stringify(detail) });
        return { ok: false, error: typeof detail === 'string' ? detail : 'Request failed' };
      }
      set({ status: 'running', error: null });
      get().startPolling(auditId);
      return { ok: true };
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      set({ error: msg });
      return { ok: false, error: msg };
    }
  },

  startPolling: (auditId: string) => {
    const existing = get().pollTimer;
    if (existing) clearInterval(existing);

    const timer = setInterval(async () => {
      try {
        const res = await fetch(`${apiBase}/api/audit/${auditId}/ai-visibility`, {
          credentials: 'include',
        });
        if (!res.ok) return;
        const json = await res.json();

        if (json.status === 'running') return; // keep polling

        // Complete — stop polling and update state
        get().stopPolling();
        if (json.status === 'not_computed') {
          set({ status: 'not_computed', data: null });
        } else {
          set({
            status: json.last_computed_status as AIVisibilityStatus,
            data: json as AIVisibilityData,
          });
        }
      } catch {
        // Silently retry on network error
      }
    }, 5000);

    set({ pollTimer: timer });
  },

  stopPolling: () => {
    const timer = get().pollTimer;
    if (timer) clearInterval(timer);
    set({ pollTimer: null });
  },

  reset: () => {
    get().stopPolling();
    set({ data: null, status: 'idle', brandPreview: null, error: null });
  },
}));
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors related to `aiVisibilityStore.ts`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/aiVisibilityStore.ts
git commit -m "feat(ai-visibility): add Zustand store with polling"
```

---

### Task 3: Create the confirmation modal

**Files:**
- Create: `frontend/src/components/ai-visibility/AIVisibilityModal.tsx`

- [ ] **Step 1: Create the modal component**

```tsx
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Eye, AlertTriangle, DollarSign } from 'lucide-react';
import { useAIVisibilityStore } from '../../stores/aiVisibilityStore';

interface AIVisibilityModalProps {
  auditId: string;
  open: boolean;
  onClose: () => void;
}

export function AIVisibilityModal({ auditId, open, onClose }: AIVisibilityModalProps) {
  const { brandPreview, fetchBrandPreview, startRecompute, error } = useAIVisibilityStore();
  const [brandName, setBrandName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      fetchBrandPreview(auditId);
    }
  }, [open, auditId, fetchBrandPreview]);

  useEffect(() => {
    if (brandPreview) {
      setBrandName(
        brandPreview.override || brandPreview.auto_extracted || ''
      );
    }
  }, [brandPreview]);

  const handleSubmit = async () => {
    if (!brandName.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    const result = await startRecompute(auditId, brandName.trim());
    setSubmitting(false);
    if (result.ok) {
      onClose();
    } else {
      setSubmitError(result.error || 'Failed to start analysis');
    }
  };

  const industryLeaf = brandPreview?.detected_industry
    ?.split('/')
    .filter(Boolean)
    .pop();

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={onClose}
          />
          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              className="bg-surface-raised border border-border rounded-2xl shadow-2xl w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-5 border-b border-border">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-accent/10 flex items-center justify-center">
                    <Eye size={18} className="text-accent" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-text font-heading">
                      AI Visibility Analysis
                    </h2>
                    <p className="text-xs text-text-muted">
                      Test your brand across 4 AI engines
                    </p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="w-8 h-8 rounded-lg hover:bg-surface-overlay flex items-center justify-center transition-colors"
                >
                  <X size={16} className="text-text-muted" />
                </button>
              </div>

              {/* Body */}
              <div className="p-5 space-y-4">
                {/* Brand name input */}
                <div>
                  <label className="text-xs font-semibold text-text-muted uppercase tracking-widest block mb-1.5">
                    Brand Name
                  </label>
                  <input
                    type="text"
                    value={brandName}
                    onChange={(e) => setBrandName(e.target.value)}
                    placeholder="Enter your brand name"
                    className="w-full px-3 py-2.5 bg-surface-overlay border border-border rounded-xl text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-all"
                  />
                  {brandPreview?.override && (
                    <p className="text-[10px] text-text-muted mt-1">
                      Using manually set brand name from previous run
                    </p>
                  )}
                  {!brandPreview?.override && brandPreview?.auto_extracted && (
                    <p className="text-[10px] text-text-muted mt-1">
                      Auto-detected from NLP analysis (salience{' '}
                      {brandPreview.auto_extracted_salience
                        ? `${Math.round(brandPreview.auto_extracted_salience * 100)}%`
                        : 'n/a'}
                      )
                    </p>
                  )}
                </div>

                {/* Industry (read-only) */}
                {industryLeaf && (
                  <div>
                    <label className="text-xs font-semibold text-text-muted uppercase tracking-widest block mb-1.5">
                      Detected Industry
                    </label>
                    <div className="px-3 py-2.5 bg-surface-overlay border border-border rounded-xl text-sm text-text-secondary">
                      {industryLeaf}
                    </div>
                  </div>
                )}

                {/* Cost disclaimer */}
                <div className="flex items-start gap-3 p-3 bg-amber-500/5 border border-amber-500/20 rounded-xl">
                  <DollarSign size={16} className="text-amber-400 mt-0.5 flex-shrink-0" />
                  <div className="text-xs text-text-secondary">
                    {brandPreview && brandPreview.run_count > 0 ? (
                      <>
                        Previous runs total:{' '}
                        <strong className="text-text">
                          ${brandPreview.cumulative_cost_usd.toFixed(2)}
                        </strong>
                        . This run will add ~$0.25.
                      </>
                    ) : (
                      <>Estimated cost: ~$0.25 per analysis run.</>
                    )}
                  </div>
                </div>

                {/* Error display */}
                {(submitError || error) && (
                  <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
                    <AlertTriangle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-red-300">{submitError || error}</p>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="p-5 border-t border-border flex justify-end gap-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-semibold text-text-secondary hover:text-text rounded-xl hover:bg-surface-overlay transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={submitting || !brandName.trim()}
                  className="px-5 py-2 text-sm font-bold text-white bg-accent hover:bg-accent-hover rounded-xl shadow-glow-accent/20 hover:shadow-glow-accent transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? 'Starting...' : 'Run Analysis'}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors related to `AIVisibilityModal.tsx`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ai-visibility/AIVisibilityModal.tsx
git commit -m "feat(ai-visibility): add confirmation modal with brand name input"
```

---

### Task 4: Create the zero-mentions opportunity card

**Files:**
- Create: `frontend/src/components/ai-visibility/ZeroMentionsCard.tsx`

- [ ] **Step 1: Create the component**

This card appears when `mentions_database.total === 0`. It frames the zero-state as an opportunity, not an error.

```tsx
import { TrendingUp, Target } from 'lucide-react';
import { motion } from 'framer-motion';

interface ZeroMentionsCardProps {
  brandName: string;
  industryLeaf?: string;
}

export function ZeroMentionsCard({ brandName, industryLeaf }: ZeroMentionsCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface-raised border border-border rounded-xl p-6"
    >
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
          <Target size={20} className="text-amber-400" />
        </div>
        <div className="space-y-3">
          <div>
            <h3 className="text-sm font-bold text-text font-heading">
              AI Visibility Opportunity
            </h3>
            <p className="text-sm text-text-secondary mt-1 leading-relaxed">
              <strong className="text-text">{brandName}</strong> is not yet appearing in
              AI-generated responses for{' '}
              {industryLeaf ? (
                <>{industryLeaf.toLowerCase()} category searches</>
              ) : (
                <>category searches</>
              )}
              . This represents an untapped channel — competitors who establish AI
              visibility now build compounding advantage.
            </p>
          </div>
          <div className="flex items-start gap-3 p-3 bg-accent/5 border border-accent/10 rounded-lg">
            <TrendingUp size={14} className="text-accent mt-0.5 flex-shrink-0" />
            <p className="text-xs text-text-muted leading-relaxed">
              The pre-indexed AI mention database (Google AI Overview + ChatGPT)
              currently shows zero mentions for your brand. This means no AI search
              queries are returning your content in their responses. Improving content
              structure, authority signals, and topical coverage can change this.
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ai-visibility/ZeroMentionsCard.tsx
git commit -m "feat(ai-visibility): add zero-mentions opportunity card"
```

---

### Task 5: Create the engine result card

**Files:**
- Create: `frontend/src/components/ai-visibility/EngineCard.tsx`

- [ ] **Step 1: Create the component**

Each engine card shows status, brand mention count, and an expandable accordion of prompt responses. Discovery vs reputation prompts are labeled differently.

```tsx
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, XCircle, ChevronDown, Sparkles, Search, MessageSquare } from 'lucide-react';
import type { EngineResult } from '../../stores/aiVisibilityStore';

const ENGINE_LABELS: Record<string, string> = {
  chatgpt: 'ChatGPT',
  claude: 'Claude',
  gemini: 'Gemini',
  perplexity: 'Perplexity',
};

const ENGINE_COLORS: Record<string, string> = {
  chatgpt: 'bg-green-500/10 text-green-400',
  claude: 'bg-orange-500/10 text-orange-400',
  gemini: 'bg-blue-500/10 text-blue-400',
  perplexity: 'bg-purple-500/10 text-purple-400',
};

interface EngineCardProps {
  engineKey: string;
  engine: EngineResult;
  prompts: Array<{ id: number; text: string; category: string }>;
  totalPrompts: number;
}

export function EngineCard({ engineKey, engine, prompts, totalPrompts }: EngineCardProps) {
  const [expanded, setExpanded] = useState(false);

  const label = ENGINE_LABELS[engineKey] || engineKey;
  const colorClass = ENGINE_COLORS[engineKey] || 'bg-accent/10 text-accent';
  const isOk = engine.status === 'ok';

  // Build prompt lookup for category labels
  const promptMap = Object.fromEntries(prompts.map((p) => [String(p.id), p]));

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface-raised border border-border rounded-xl overflow-hidden"
    >
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-surface-overlay/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${colorClass}`}>
            <MessageSquare size={16} />
          </div>
          <div className="text-left">
            <div className="text-sm font-bold text-text">{label}</div>
            <div className="text-xs text-text-muted mt-0.5">
              {isOk ? (
                <>
                  Mentioned in{' '}
                  <strong className={engine.brand_mentioned_in > 0 ? 'text-success' : 'text-text-secondary'}>
                    {engine.brand_mentioned_in}/{totalPrompts}
                  </strong>{' '}
                  prompts
                </>
              ) : (
                <span className="text-red-400">{engine.error || 'Failed'}</span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Status pill */}
          {isOk ? (
            <span className="flex items-center gap-1 text-[10px] font-bold text-success bg-success/10 px-2 py-1 rounded-full">
              <CheckCircle2 size={10} />
              OK
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] font-bold text-red-400 bg-red-500/10 px-2 py-1 rounded-full">
              <XCircle size={10} />
              FAILED
            </span>
          )}
          {/* Cost */}
          <span className="text-[10px] text-text-muted font-mono">
            ${engine.cost_usd.toFixed(3)}
          </span>
          <ChevronDown
            size={14}
            className={`text-text-muted transition-transform ${expanded ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      {/* Expanded responses */}
      <AnimatePresence>
        {expanded && isOk && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border p-4 space-y-3">
              {Object.entries(engine.responses_by_prompt).map(([promptId, response]) => {
                const prompt = promptMap[promptId];
                const isReputation = prompt?.category === 'reputation';
                return (
                  <div key={promptId} className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      {isReputation ? (
                        <Sparkles size={12} className="text-accent" />
                      ) : (
                        <Search size={12} className="text-text-muted" />
                      )}
                      <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                        {isReputation ? 'Reputation' : 'Discovery'}
                      </span>
                      <span className="text-xs text-text-secondary truncate">
                        "{prompt?.text || `Prompt ${promptId}`}"
                      </span>
                      {response.mentioned && (
                        <span className="ml-auto text-[10px] font-bold text-success bg-success/10 px-1.5 py-0.5 rounded">
                          MENTIONED
                        </span>
                      )}
                    </div>
                    <div className="pl-5 text-xs text-text-secondary leading-relaxed max-h-32 overflow-y-auto bg-surface-overlay rounded-lg p-3">
                      {response.text.length > 600
                        ? response.text.slice(0, 600) + '…'
                        : response.text}
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ai-visibility/EngineCard.tsx
git commit -m "feat(ai-visibility): add engine result card with expandable responses"
```

---

### Task 6: Create the AI Visibility KPI card for the overview page

**Files:**
- Create: `frontend/src/components/ai-visibility/AIVisibilityKpiCard.tsx`

- [ ] **Step 1: Create the KPI card component**

This card appears on the DashboardOverviewPage alongside other intelligence layer cards. Four states: not_computed, running, zero-mentions, has-data.

```tsx
import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { motion } from 'framer-motion';
import { Eye, ChevronRight, Loader2, Target } from 'lucide-react';
import { useAIVisibilityStore } from '../../stores/aiVisibilityStore';
import { AIVisibilityModal } from './AIVisibilityModal';

interface AIVisibilityKpiCardProps {
  auditId: string;
}

export function AIVisibilityKpiCard({ auditId }: AIVisibilityKpiCardProps) {
  const { data, status, fetchStatus } = useAIVisibilityStore();
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    fetchStatus(auditId);
    return () => {
      useAIVisibilityStore.getState().stopPolling();
    };
  }, [auditId, fetchStatus]);

  // Not computed — show CTA
  if (status === 'not_computed' || status === 'idle') {
    return (
      <>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.26 }}
        >
          <button
            onClick={() => setModalOpen(true)}
            className="w-full text-left bg-surface-raised border border-border border-dashed rounded-xl p-5 hover:border-accent/30 transition-all group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center group-hover:bg-accent/20 transition-all">
                  <Eye size={18} className="text-accent" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-text">AI Visibility</h2>
                  <p className="text-xs text-text-muted mt-0.5">
                    Not yet computed.{' '}
                    <span className="text-accent font-semibold">
                      Run Analysis →
                    </span>
                  </p>
                </div>
              </div>
            </div>
          </button>
        </motion.div>
        <AIVisibilityModal
          auditId={auditId}
          open={modalOpen}
          onClose={() => setModalOpen(false)}
        />
      </>
    );
  }

  // Running — show spinner
  if (status === 'running' || status === 'loading') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.26 }}
        className="bg-surface-raised border border-border rounded-xl p-5"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center">
            <Loader2 size={18} className="text-accent animate-spin" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-text">AI Visibility</h2>
            <p className="text-xs text-text-muted mt-0.5">
              Running analysis across 4 AI engines... ~45s
            </p>
          </div>
        </div>
      </motion.div>
    );
  }

  // Has data — determine which variant to show
  const hasMentions = data && data.mentions_database.total > 0;
  const engineCount = data ? Object.keys(data.live_test.engines).length : 0;
  const okEngines = data
    ? Object.values(data.live_test.engines).filter((e) => e.status === 'ok').length
    : 0;

  // Computed with data
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.26 }}
    >
      <Link
        to={`/dashboard/${auditId}/ai-visibility`}
        className="block bg-surface-raised border border-border rounded-xl p-5 hover:border-accent/30 transition-all group"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center group-hover:bg-accent/20 transition-all">
              {hasMentions ? (
                <Eye size={18} className="text-accent" />
              ) : (
                <Target size={18} className="text-amber-400" />
              )}
            </div>
            <div>
              <h2 className="text-sm font-bold text-text">AI Visibility</h2>
              <p className="text-xs text-text-muted mt-0.5">
                {hasMentions ? (
                  <>
                    {data!.mentions_database.total} mentions across AI platforms
                  </>
                ) : (
                  <>
                    Not yet indexed — untapped opportunity
                  </>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <div className="text-lg font-bold text-text font-heading">
                {okEngines}/{engineCount}
              </div>
              <div className="text-[10px] text-text-muted">Engines</div>
            </div>
            {data?.last_computed_at && (
              <div className="text-right hidden md:block">
                <div className="text-xs font-semibold text-text-secondary">
                  {formatTimeAgo(data.last_computed_at)}
                </div>
                <div className="text-[10px] text-text-muted">Last run</div>
              </div>
            )}
            <ChevronRight
              size={16}
              className="text-text-muted group-hover:text-accent transition-colors"
            />
          </div>
        </div>
      </Link>
    </motion.div>
  );
}

function formatTimeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ai-visibility/AIVisibilityKpiCard.tsx
git commit -m "feat(ai-visibility): add KPI card with 4 states for overview page"
```

---

### Task 7: Create the full AI Visibility dashboard page

**Files:**
- Create: `frontend/src/pages/DashboardAIVisibilityPage.tsx`

- [ ] **Step 1: Create the page component**

This is the main page with 6 sections. It reads data from the `aiVisibilityStore`, handles running/error states, and renders the full analysis results.

```tsx
import { useEffect, useState } from 'react';
import { useParams } from 'react-router';
import { motion } from 'framer-motion';
import {
  Eye,
  RefreshCw,
  Clock,
  DollarSign,
  Globe,
  ChevronRight,
  ExternalLink,
  BarChart3,
  Database,
  Loader2,
} from 'lucide-react';
import { useAIVisibilityStore } from '../stores/aiVisibilityStore';
import { EngineCard } from '../components/ai-visibility/EngineCard';
import { ZeroMentionsCard } from '../components/ai-visibility/ZeroMentionsCard';
import { AIVisibilityModal } from '../components/ai-visibility/AIVisibilityModal';

export default function DashboardAIVisibilityPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { data, status, fetchStatus } = useAIVisibilityStore();
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    if (auditId) fetchStatus(auditId);
    return () => {
      useAIVisibilityStore.getState().stopPolling();
    };
  }, [auditId, fetchStatus]);

  // Loading state
  if (status === 'loading' || status === 'idle') {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <Loader2 size={24} className="text-accent animate-spin" />
      </div>
    );
  }

  // Not computed state
  if (status === 'not_computed') {
    return (
      <div className="p-6 lg:p-8 max-w-4xl mx-auto">
        <div className="text-center py-16">
          <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Eye size={24} className="text-accent" />
          </div>
          <h1 className="text-xl font-bold text-text font-heading mb-2">
            AI Visibility Analysis
          </h1>
          <p className="text-sm text-text-muted max-w-md mx-auto mb-6">
            Test how your brand appears across ChatGPT, Claude, Gemini, and Perplexity.
            Discover if AI engines mention you in category searches and reputation queries.
          </p>
          <button
            onClick={() => setModalOpen(true)}
            className="px-6 py-2.5 text-sm font-bold text-white bg-accent hover:bg-accent-hover rounded-xl shadow-glow-accent/20 hover:shadow-glow-accent transition-all"
          >
            Run Analysis
          </button>
        </div>
        {auditId && (
          <AIVisibilityModal
            auditId={auditId}
            open={modalOpen}
            onClose={() => setModalOpen(false)}
          />
        )}
      </div>
    );
  }

  // Running state
  if (status === 'running') {
    return (
      <div className="p-6 lg:p-8 max-w-4xl mx-auto">
        <div className="text-center py-16">
          <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Loader2 size={24} className="text-accent animate-spin" />
          </div>
          <h1 className="text-xl font-bold text-text font-heading mb-2">
            Analysis Running
          </h1>
          <p className="text-sm text-text-muted max-w-md mx-auto">
            Querying 4 AI engines with 4 prompts each. This typically takes 30–60 seconds.
          </p>
        </div>
      </div>
    );
  }

  // Failed without data
  if (!data) {
    return (
      <div className="p-6 lg:p-8 max-w-4xl mx-auto">
        <div className="text-center py-16">
          <h1 className="text-xl font-bold text-text font-heading mb-2">
            Analysis Failed
          </h1>
          <p className="text-sm text-text-muted mb-4">
            Something went wrong. Try running the analysis again.
          </p>
          <button
            onClick={() => setModalOpen(true)}
            className="px-6 py-2.5 text-sm font-bold text-white bg-accent hover:bg-accent-hover rounded-xl transition-all"
          >
            Retry
          </button>
          {auditId && (
            <AIVisibilityModal
              auditId={auditId}
              open={modalOpen}
              onClose={() => setModalOpen(false)}
            />
          )}
        </div>
      </div>
    );
  }

  // ───── Has data ─────
  const { mentions_database: mentions, live_test: liveTest } = data;
  const hasMentions = mentions.total > 0;
  const hasSov = !!data.share_of_voice;
  const industryLeaf = data.detected_industry?.split('/').filter(Boolean).pop();
  const engines = liveTest.engines;
  const prompts = liveTest.prompts_used;
  const totalPrompts = prompts.length;

  // Compute competitive intelligence from discovery responses
  // Which brands ARE mentioned across all engines even when the audited brand isn't?
  const competitorMentions = extractCompetitorMentions(engines, prompts, data.brand_name);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* ── Section 1: Header + metadata ── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-start justify-between gap-4"
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-text-muted uppercase tracking-widest">
              AI Visibility
            </span>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                data.last_computed_status === 'ok'
                  ? 'text-success bg-success/10'
                  : data.last_computed_status === 'partial'
                    ? 'text-amber-400 bg-amber-500/10'
                    : 'text-red-400 bg-red-500/10'
              }`}
            >
              {data.last_computed_status}
            </span>
          </div>
          <h1 className="text-xl font-bold text-text font-heading">
            {data.brand_name}
          </h1>
          <div className="flex items-center gap-3 mt-1 text-xs text-text-muted">
            {data.brand_name_source === 'override' && (
              <span className="bg-accent/10 text-accent px-1.5 py-0.5 rounded text-[10px] font-semibold">
                Manually set
              </span>
            )}
            {industryLeaf && (
              <span>{industryLeaf}</span>
            )}
            <span className="flex items-center gap-1">
              <Clock size={10} />
              {new Date(data.last_computed_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
            <span>{data.duration_seconds}s</span>
            <span>Run #{data.run_count}</span>
          </div>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-accent bg-accent/10 hover:bg-accent/20 rounded-xl transition-all"
        >
          <RefreshCw size={14} />
          Recompute
        </button>
      </motion.div>

      {/* ── Section 2: Share of Voice (if competitors available) ── */}
      {hasSov && data.share_of_voice && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="bg-surface-raised border border-border rounded-xl p-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 size={16} className="text-accent" />
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
              Share of Voice
            </h2>
          </div>
          <p className="text-xs text-text-muted mb-4">
            Measured across {data.share_of_voice.total_mentions_analyzed.toLocaleString()} AI
            responses from Google AI Overview + ChatGPT.
          </p>
          <div className="space-y-3">
            {/* Brand row */}
            <SovBar
              label={data.brand_name}
              value={data.share_of_voice.brand_sov}
              isAccent
            />
            {/* Competitor rows */}
            {Object.entries(data.share_of_voice.competitor_sov)
              .sort(([, a], [, b]) => b - a)
              .map(([domain, sov]) => (
                <SovBar key={domain} label={domain} value={sov} />
              ))}
          </div>
        </motion.div>
      )}

      {/* ── Section 3: Platform Breakdown (Database) ── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Database size={16} className="text-text-muted" />
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
            Pre-Indexed Mentions
          </h2>
        </div>

        {hasMentions ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {Object.entries(mentions.by_platform).map(([platform, count]) => (
              <div
                key={platform}
                className="bg-surface-raised border border-border rounded-xl p-5"
              >
                <div className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                  {platform.replace(/_/g, ' ')}
                </div>
                <div className="text-2xl font-extrabold text-text font-heading">
                  {count}
                </div>
                <div className="text-xs text-text-muted mt-1">mentions</div>
              </div>
            ))}
            {mentions.ai_search_volume > 0 && (
              <div className="bg-surface-raised border border-border rounded-xl p-5">
                <div className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                  AI Search Volume
                </div>
                <div className="text-2xl font-extrabold text-text font-heading">
                  {mentions.ai_search_volume.toLocaleString()}
                </div>
                <div className="text-xs text-text-muted mt-1">monthly queries</div>
              </div>
            )}
          </div>
        ) : (
          <ZeroMentionsCard
            brandName={data.brand_name}
            industryLeaf={industryLeaf}
          />
        )}

        {/* Triggering prompts */}
        {mentions.triggering_prompts.length > 0 && (
          <div className="mt-4 bg-surface-raised border border-border rounded-xl p-5">
            <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-3">
              Triggering Prompts
            </h3>
            <div className="space-y-2">
              {mentions.triggering_prompts.map((tp, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-2 border-b border-border last:border-0"
                >
                  <span className="text-sm text-text">{tp.prompt}</span>
                  <div className="flex items-center gap-3 text-xs text-text-muted">
                    <span>{tp.platform.replace(/_/g, ' ')}</span>
                    {tp.ai_search_volume > 0 && (
                      <span>{tp.ai_search_volume.toLocaleString()} vol</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.div>

      {/* ── Section 4: Live Engine Tests ── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
      >
        <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
          Live Engine Tests
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(engines).map(([engineKey, engine]) => (
            <EngineCard
              key={engineKey}
              engineKey={engineKey}
              engine={engine}
              prompts={prompts}
              totalPrompts={totalPrompts}
            />
          ))}
        </div>
      </motion.div>

      {/* ── Section 4.5: Competitive Intelligence (brands mentioned in discovery) ── */}
      {competitorMentions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.18 }}
          className="bg-surface-raised border border-border rounded-xl p-5"
        >
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
            Brands Mentioned in Discovery Prompts
          </h2>
          <p className="text-xs text-text-muted mb-4">
            These brands appeared in AI responses to your industry's discovery prompts — even though{' '}
            <strong className="text-text">{data.brand_name}</strong> was not mentioned.
            These are your AI visibility competitors.
          </p>
          <div className="flex flex-wrap gap-2">
            {competitorMentions.slice(0, 20).map((brand) => (
              <span
                key={brand.name}
                className="text-xs font-semibold text-text-secondary bg-surface-overlay px-2.5 py-1 rounded-lg"
              >
                {brand.name}
                <span className="text-text-muted ml-1">×{brand.count}</span>
              </span>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Section 5: Top Cited Pages ── */}
      {mentions.top_pages.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-surface-raised border border-border rounded-xl p-5"
        >
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
            Top Cited Pages
          </h2>
          <div className="space-y-2">
            {mentions.top_pages.map((page, i) => (
              <div
                key={i}
                className="flex items-center justify-between py-2 border-b border-border last:border-0"
              >
                <a
                  href={page.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-accent hover:text-accent-hover transition-colors inline-flex items-center gap-1 truncate max-w-[80%]"
                >
                  {page.url.replace(/^https?:\/\//, '')}
                  <ExternalLink size={10} />
                </a>
                <span className="text-sm font-bold text-text">{page.mention_count}</span>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Section 6: Cost & Methodology Footer ── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="bg-surface-raised border border-border rounded-xl p-5"
      >
        <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
          Cost & Methodology
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          <div>
            <div className="text-xs text-text-muted">This Run</div>
            <div className="text-sm font-bold text-text">${data.cost_usd.toFixed(4)}</div>
          </div>
          <div>
            <div className="text-xs text-text-muted">Cumulative</div>
            <div className="text-sm font-bold text-text">${data.cumulative_cost_usd.toFixed(4)}</div>
          </div>
          <div>
            <div className="text-xs text-text-muted">Duration</div>
            <div className="text-sm font-bold text-text">{data.duration_seconds}s</div>
          </div>
          <div>
            <div className="text-xs text-text-muted">Total Runs</div>
            <div className="text-sm font-bold text-text">{data.run_count}</div>
          </div>
        </div>

        <div className="space-y-2 text-xs text-text-muted">
          <p>
            <strong className="text-text-secondary">Pre-Indexed Mentions</strong> — aggregated
            from DataForSEO's database of pre-scanned AI responses. Covers Google AI Overview
            and ChatGPT only. Updated periodically by DataForSEO.
          </p>
          <p>
            <strong className="text-text-secondary">Live Engine Tests</strong> — fresh queries
            sent to each AI engine at the time of analysis. Results are sampled from 4 canonical
            prompts (3 discovery + 1 reputation). Different engines may produce different results
            on repeat queries.
          </p>
          {hasSov && (
            <p>
              <strong className="text-text-secondary">Share of Voice</strong> — computed from
              cross-aggregated mention counts across the pre-indexed database. Not derived from
              live test responses.
            </p>
          )}
        </div>

        {/* Prompts used */}
        <div className="mt-4 pt-4 border-t border-border">
          <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-2">
            Prompts Used
          </h3>
          <div className="space-y-1">
            {prompts.map((p) => (
              <div key={p.id} className="flex items-center gap-2 text-xs">
                <span
                  className={`font-bold uppercase tracking-wider ${
                    p.category === 'reputation' ? 'text-accent' : 'text-text-muted'
                  }`}
                >
                  {p.category}
                </span>
                <span className="text-text-secondary">"{p.text}"</span>
              </div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Modal */}
      {auditId && (
        <AIVisibilityModal
          auditId={auditId}
          open={modalOpen}
          onClose={() => setModalOpen(false)}
        />
      )}
    </div>
  );
}

/* ── SOV Bar helper ── */
function SovBar({ label, value, isAccent }: { label: string; value: number; isAccent?: boolean }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-text-secondary w-36 truncate font-semibold">{label}</span>
      <div className="flex-1 h-6 bg-surface-overlay rounded-lg overflow-hidden">
        <div
          className={`h-full rounded-lg transition-all duration-500 ${
            isAccent ? 'bg-accent' : 'bg-text-muted/30'
          }`}
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
      <span className={`text-sm font-bold w-12 text-right ${isAccent ? 'text-accent' : 'text-text-secondary'}`}>
        {pct}%
      </span>
    </div>
  );
}

/* ── Competitive intelligence extraction ── */
interface BrandMention {
  name: string;
  count: number;
}

function extractCompetitorMentions(
  engines: Record<string, { status: string; responses_by_prompt: Record<string, { text: string; mentioned: boolean }> }>,
  prompts: Array<{ id: number; text: string; category: string }>,
  brandName: string,
): BrandMention[] {
  // Only analyze discovery prompts (not reputation)
  const discoveryIds = new Set(
    prompts.filter((p) => p.category === 'discovery').map((p) => String(p.id))
  );

  // Common agency/company name patterns — extract bold names from markdown responses
  const brandCounts: Record<string, number> = {};
  const brandNameLower = brandName.toLowerCase();

  for (const engine of Object.values(engines)) {
    if (engine.status !== 'ok') continue;
    for (const [promptId, response] of Object.entries(engine.responses_by_prompt)) {
      if (!discoveryIds.has(promptId)) continue;

      // Extract bold text patterns like **Name** or **1. Name**
      const boldMatches = response.text.matchAll(/\*\*(?:\d+\.\s*)?([A-Z][A-Za-z\s&.'-]+?)(?:\s*[-—:]|\*\*)/g);
      for (const match of boldMatches) {
        const name = match[1].trim();
        // Skip the audited brand itself, single words, and generic terms
        if (
          name.toLowerCase() === brandNameLower ||
          name.length < 3 ||
          name.split(' ').length > 4 ||
          /^(here|the|key|top|core|what|how|why|additional|notable|other|factors)/i.test(name)
        ) continue;
        brandCounts[name] = (brandCounts[name] || 0) + 1;
      }
    }
  }

  return Object.entries(brandCounts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/DashboardAIVisibilityPage.tsx
git commit -m "feat(ai-visibility): add full dashboard page with 6 sections"
```

---

### Task 8: Wire up routing, sidebar, and overview card

**Files:**
- Modify: `frontend/src/router.tsx`
- Modify: `frontend/src/layouts/DashboardLayout.tsx`
- Modify: `frontend/src/pages/DashboardOverviewPage.tsx`

- [ ] **Step 1: Add lazy import and route in `router.tsx`**

After the existing `DashboardLinkIntelligencePage` lazy import (around line 44-46), add:

```typescript
const DashboardAIVisibilityPage = lazy(
  () => import('./pages/DashboardAIVisibilityPage')
);
```

In the dashboard children array, after the `link-intelligence` route block (around line 184-187), add:

```typescript
      {
        path: 'ai-visibility',
        element: (
          <Suspense fallback={dashboardFallback}>
            <DashboardAIVisibilityPage />
          </Suspense>
        ),
      },
```

- [ ] **Step 2: Add sidebar entry in `DashboardLayout.tsx`**

At the top of the file, add `Eye` to the lucide-react import:

```typescript
import {
  // ... existing imports ...
  Eye,
} from 'lucide-react';
```

In the `navGroups` array, after the `'Content & SEO'` group (around line 62-69), add a new standalone entry. The spec says AI Visibility should be placed as a standalone entry after Content Intelligence. The cleanest approach is to add it as the last item in the `'Content & SEO'` group, after `Content Intelligence`:

In the `'Content & SEO'` group, add as the last item:
```typescript
      { icon: Eye, label: 'AI Visibility', href: 'ai-visibility' },
```

So the full `Content & SEO` group becomes:
```typescript
  {
    label: 'Content & SEO',
    items: [
      { icon: BookOpen, label: PILLAR_LABELS.aeo_content, href: 'pillar/ai-answer-readiness' },
      { icon: FileJson, label: PILLAR_LABELS.structured_data, href: 'pillar/rich-search-presence' },
      { icon: Layers, label: PILLAR_LABELS.rag_readiness, href: 'pillar/ai-retrieval-readiness' },
      { icon: Brain, label: 'Content Intelligence', href: 'content-intelligence' },
      { icon: Eye, label: 'AI Visibility', href: 'ai-visibility' },
    ],
  },
```

- [ ] **Step 3: Add AI Visibility KPI card to the overview page**

In `frontend/src/pages/DashboardOverviewPage.tsx`, add the import at the top (after existing imports):

```typescript
import { AIVisibilityKpiCard } from '../components/ai-visibility/AIVisibilityKpiCard';
```

Then find the Content Intelligence card section (around line 471, the `{nlpInfo && (` block). **Before** it, add:

```tsx
      {/* AI Visibility Card */}
      {report?.audit_id && (
        <AIVisibilityKpiCard auditId={report.audit_id} />
      )}
```

- [ ] **Step 4: Verify TypeScript compiles and the dev server starts**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -30`
Expected: No errors

Run: `cd frontend && npm run dev` (verify the app starts without errors in the terminal)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/router.tsx frontend/src/layouts/DashboardLayout.tsx frontend/src/pages/DashboardOverviewPage.tsx
git commit -m "feat(ai-visibility): wire up route, sidebar entry, and overview KPI card"
```

---

### Task 9: End-to-end test on production

- [ ] **Step 1: Push to origin**

```bash
git push origin main
```

- [ ] **Step 2: Wait for Railway deploy (~3 minutes) and verify health**

```bash
sleep 200 && curl -s https://waio.up.railway.app/api/health
```
Expected: `{"status": "ok"}`

- [ ] **Step 3: Open the Belt Creative dashboard in a browser**

Navigate to: `https://waio.up.railway.app/dashboard/4ef284bb-9c43-4150-a82d-25a92886d9ed`

Verify:
1. AI Visibility appears in the sidebar under Content & SEO
2. Overview page shows the AI Visibility KPI card with previous run data (4/4 engines, "Not yet indexed" message)
3. Clicking the KPI card navigates to the AI Visibility page
4. AI Visibility page renders all 6 sections with Belt Creative's data
5. Zero-mentions opportunity card appears in the Pre-Indexed Mentions section
6. All 4 engine cards render with expandable responses
7. Discovery vs reputation labels show correctly
8. Competitive intelligence section shows brands mentioned in discovery prompts
9. Cost & Methodology footer renders correctly
10. Recompute button opens the modal with pre-filled brand name

- [ ] **Step 4: Test the Veza Digital dashboard**

Navigate to: `https://waio.up.railway.app/dashboard/b5afb24f-89ba-4643-92cf-9a5dfff5e8fa`

Verify the same checklist as above. Additionally verify:
1. Perplexity's rich reputation response (Clutch 4.9/5, clients listed) renders correctly
2. The brand name shows "Veza Digital" with "Manually set" badge

- [ ] **Step 5: Test the recompute flow**

From the Veza Digital AI Visibility page:
1. Click "Recompute"
2. Verify modal opens with "Veza Digital" pre-filled
3. Click "Run Analysis"
4. Verify page shows "Running" state with spinner
5. Wait ~45s — verify page auto-updates to show new results
6. Verify cumulative cost increased

- [ ] **Step 6: Commit verification notes**

No code changes needed. Mark the task as complete.

---

## Self-Review Checklist

**1. Spec coverage:**
- ✅ §7.1 DashboardAIVisibilityPage with 6 sections → Task 7
- ✅ §7.2 AIVisibilityKpiCard with 4 states → Task 6
- ✅ §7.3 AIVisibilityModal → Task 3
- ✅ §7.4 Sidebar placement after Content Intelligence → Task 8
- ✅ §7.5 Zustand store with polling → Task 2
- ✅ §5.3 Data segregation (mentions_database vs live_test) → Task 7 renders them in separate sections with methodology disclaimer
- ✅ §10.4 Failure mode matrix → Task 7 handles not_computed, running, failed, partial, ok states
- ✅ §10.5 Cost-on-retry semantics → Task 3 modal shows cumulative cost before confirming
- ✅ Zero-state UX → Task 4 (ZeroMentionsCard with opportunity framing)
- ✅ Competitor_urls DB fix → Task 1
- ✅ Competitive intelligence from discovery responses → Task 7 (extractCompetitorMentions)

**2. Placeholder scan:** No TBD, TODO, or "implement later" found.

**3. Type consistency:** `AIVisibilityData`, `EngineResult`, `BrandPreview` types defined in Task 2 store and used consistently in Tasks 3-7. `formatTimeAgo` helper defined in Task 6 where it's used. `extractCompetitorMentions` defined in Task 7 where it's used.
