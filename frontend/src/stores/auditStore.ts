import { create } from 'zustand';

const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

interface AuditState {
  isLoading: boolean;
  report: Record<string, any> | null;
  error: string | null;
  auditedUrl: string;

  runAudit: (
    url: string,
    auditType: 'single' | 'site' | 'competitive',
    competitorUrls?: string[],
    tier?: 'free' | 'premium',
    aiVisibilityOptIn?: boolean,
    brandName?: string,
    /**
     * Workstream D3: user-declared industry override. When non-empty, flows
     * into `target_industry` on the audit request body and becomes the
     * user_declared layer of resolve_industry() on the backend.
     */
    targetIndustry?: string,
  ) => Promise<void>;
  loadReport: (jobId: string, pageUrl: string) => Promise<void>;
  fetchReport: (auditId: string) => Promise<void>;
  clearAudit: () => void;
}

export const useAuditStore = create<AuditState>((set) => ({
  isLoading: false,
  report: null,
  error: null,
  auditedUrl: '',

  runAudit: async (url, auditType, competitorUrls = [], tier = 'free', aiVisibilityOptIn, brandName, targetIndustry) => {
    set({ isLoading: true, error: null, report: null, auditedUrl: url });

    let apiUrl = `${apiBase}/api/audit`;
    if (tier === 'premium' && auditType === 'single') apiUrl += '/premium';
    else if (auditType === 'site') apiUrl += '/multi';
    else if (auditType === 'competitive') apiUrl += '/competitive';

    // Workstream D3: normalize targetIndustry — omit the field when the
    // user left it blank, so the backend resolver falls through to NLP
    // rather than treating "" as a user-declared empty string.
    const trimmedIndustry = targetIndustry?.trim();

    try {
      let body: Record<string, unknown>;
      if (tier === 'premium' && auditType === 'single') {
        body = {
          url,
          competitor_urls: competitorUrls,
          ai_visibility_opt_in: aiVisibilityOptIn ?? true,
          ...(brandName ? { brand_name: brandName } : {}),
          ...(trimmedIndustry ? { target_industry: trimmedIndustry } : {}),
        };
      } else if (auditType === 'site') {
        body = { url, max_pages: 50 };
      } else if (auditType === 'competitive') {
        body = { primary_url: url, competitor_urls: competitorUrls };
      } else {
        body = {
          url,
          ...(trimmedIndustry ? { target_industry: trimmedIndustry } : {}),
        };
      }

      const res = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to complete audit');
      }

      const data = await res.json();

      if (auditType === 'site') {
        const jobId = data.job_id as string;
        const statusUrl = `${apiBase}/api/audit/status/${jobId}`;

        const poll = async () => {
          try {
            const sRes = await fetch(statusUrl);
            const sData = await sRes.json();
            if (sData.status === 'completed') {
              set({ report: sData.final_report, isLoading: false });
            } else if (sData.status === 'failed') {
              set({ error: 'Site audit failed.', isLoading: false });
            } else {
              setTimeout(poll, 2500);
            }
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : 'Error polling audit status';
            set({ error: msg, isLoading: false });
          }
        };
        poll();
      } else {
        set({ report: data, isLoading: false });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'An unexpected error occurred.';
      set({ error: msg, isLoading: false });
    }
  },

  loadReport: async (jobId, pageUrl) => {
    set({ isLoading: true, error: null, auditedUrl: pageUrl });
    try {
      const res = await fetch(
        `${apiBase}/api/audit/page/${jobId}?url=${encodeURIComponent(pageUrl)}`
      );
      if (!res.ok) throw new Error('Report not found');
      const data = await res.json();
      set({ report: data, isLoading: false });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load report';
      set({ error: msg, isLoading: false });
    }
  },

  fetchReport: async (auditId: string) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`${apiBase}/api/audit/report/${auditId}`, {
        credentials: 'include',
      });
      if (!res.ok) {
        if (res.status === 404) throw new Error('Audit report not found');
        throw new Error('Failed to load audit report');
      }
      const data = await res.json();
      set({ report: data, isLoading: false, auditedUrl: data.url || '' });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load report';
      set({ error: msg, isLoading: false });
    }
  },

  clearAudit: () =>
    set({ isLoading: false, report: null, error: null, auditedUrl: '' }),
}));
