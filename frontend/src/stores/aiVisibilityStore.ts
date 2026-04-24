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

/**
 * Resolved-industry block carried on report.ai_visibility.industry
 * (Workstream D3, Contract 2). The frontend uses `source` to branch:
 * null → render "Needs attention"; "user_declared" / "nlp_detected" → normal tile.
 */
export interface AIVisibilityIndustry {
  value: string | null;
  source: 'user_declared' | 'nlp_detected' | null;
  user_provided: string | null;
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
  /**
   * Workstream D3 Contract 2: resolved industry. Use `industry.value` +
   * `industry.source` for all rendering decisions. The legacy flat
   * `detected_industry` field is still emitted by the backend for
   * backwards-compat but will be removed once all readers migrate.
   */
  industry?: AIVisibilityIndustry;
  /** @deprecated Use `industry.value`. Kept for backwards-compat with old payloads. */
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

type AIVisibilityStatus =
  | 'idle'
  | 'loading'
  | 'not_computed'
  | 'running'
  | 'ok'
  | 'partial'
  | 'failed'
  // Workstream D3: when resolve_industry() returns (None, None), the engine
  // emits this status and the dashboard renders a "Needs attention" card
  // prompting the user to declare an industry.
  | 'needs_industry_confirmation';

interface AIVisibilityState {
  data: AIVisibilityData | null;
  status: AIVisibilityStatus;
  brandPreview: BrandPreview | null;
  error: string | null;
  pollTimer: ReturnType<typeof setInterval> | null;

  fetchStatus: (auditId: string) => Promise<void>;
  fetchBrandPreview: (auditId: string) => Promise<void>;
  /**
   * Kick off an AI Visibility recompute. `targetIndustry` (Workstream D3)
   * is optional — when provided it becomes the user-declared override and
   * the backend writes `industry.source = "user_declared"`.
   */
  startRecompute: (
    auditId: string,
    brandName: string,
    targetIndustry?: string,
  ) => Promise<{ ok: boolean; error?: string }>;
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

  startRecompute: async (auditId: string, brandName: string, targetIndustry?: string) => {
    try {
      const body: Record<string, string> = { brand_name: brandName };
      // Workstream D3: only include target_industry when non-empty. An empty
      // string must NOT override any existing user_provided — the backend's
      // empty-string handling treats "" the same as null (falls through to
      // NLP), but being explicit here avoids accidental blanking on edits
      // where the user didn't change the industry.
      const trimmedIndustry = targetIndustry?.trim();
      if (trimmedIndustry) {
        body.target_industry = trimmedIndustry;
      }
      const res = await fetch(`${apiBase}/api/audit/${auditId}/recompute-ai-visibility`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
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
