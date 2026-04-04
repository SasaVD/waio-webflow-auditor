import { useState, useEffect, useRef, useCallback } from 'react';

interface AuditStreamState {
  progress: number;
  currentStage: string;
  stageIndex: number;
  findings: number;
  isComplete: boolean;
  error: string | null;
}

const STAGES = [
  { key: 'fetch', label: 'Fetching page content' },
  { key: 'html', label: 'Checking search engine clarity' },
  { key: 'structured_data', label: 'Evaluating rich search presence' },
  { key: 'aeo', label: 'Testing AI answer readiness' },
  { key: 'css_js', label: 'Reviewing visual consistency & speed' },
  { key: 'accessibility', label: 'Running inclusive reach checks' },
  { key: 'rag', label: 'Assessing AI retrieval readiness' },
  { key: 'agentic', label: 'Checking AI agent compatibility' },
  { key: 'data_integrity', label: 'Validating tracking accuracy' },
  { key: 'internal_links', label: 'Analyzing content architecture' },
  { key: 'report', label: 'Compiling your intelligence report' },
];

/**
 * Hook for audit progress tracking.
 * Currently uses simulated progress based on elapsed time.
 * When backend SSE is available, pass an `auditId` to connect to the stream.
 */
export function useAuditStream(isLoading: boolean, auditId?: string): AuditStreamState {
  const [state, setState] = useState<AuditStreamState>({
    progress: 0,
    currentStage: STAGES[0].label,
    stageIndex: 0,
    findings: 0,
    isComplete: false,
    error: null,
  });

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

  // SSE connection (when backend supports it)
  useEffect(() => {
    if (!auditId || !isLoading) return;

    const url = `${apiBase}/api/audit/stream/${auditId}`;
    let es: EventSource | null = null;

    try {
      es = new EventSource(url);

      es.addEventListener('progress', (e) => {
        const data = JSON.parse(e.data);
        setState((prev) => ({ ...prev, progress: data.progress ?? prev.progress }));
      });

      es.addEventListener('stage', (e) => {
        const data = JSON.parse(e.data);
        const idx = STAGES.findIndex((s) => s.key === data.stage);
        setState((prev) => ({
          ...prev,
          currentStage: data.label || STAGES[idx]?.label || prev.currentStage,
          stageIndex: idx >= 0 ? idx : prev.stageIndex,
        }));
      });

      es.addEventListener('finding', (e) => {
        const data = JSON.parse(e.data);
        setState((prev) => ({
          ...prev,
          findings: data.count ?? prev.findings + 1,
        }));
      });

      es.addEventListener('complete', () => {
        setState((prev) => ({ ...prev, isComplete: true, progress: 100 }));
        es?.close();
      });

      es.addEventListener('error', () => {
        // SSE not available — fall through to simulated progress
        es?.close();
      });
    } catch {
      // SSE not supported — simulated progress will handle it
    }

    return () => {
      es?.close();
    };
  }, [auditId, isLoading, apiBase]);

  // Simulated progress fallback
  const startSimulation = useCallback(() => {
    let elapsed = 0;
    const totalDuration = 25000; // 25s estimated for single page audit

    intervalRef.current = setInterval(() => {
      elapsed += 400;
      const rawProgress = Math.min((elapsed / totalDuration) * 100, 95);
      const stageIdx = Math.min(
        Math.floor((rawProgress / 100) * STAGES.length),
        STAGES.length - 1
      );

      setState((prev) => ({
        ...prev,
        progress: Math.round(rawProgress),
        currentStage: STAGES[stageIdx].label,
        stageIndex: stageIdx,
        findings: Math.floor(rawProgress / 12), // simulated count
      }));
    }, 400);
  }, []);

  useEffect(() => {
    if (isLoading && !auditId) {
      // No SSE — use simulated progress
      setState({
        progress: 0,
        currentStage: STAGES[0].label,
        stageIndex: 0,
        findings: 0,
        isComplete: false,
        error: null,
      });
      startSimulation();
    }

    if (!isLoading) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setState((prev) =>
        prev.progress > 0
          ? { ...prev, progress: 100, isComplete: true }
          : prev
      );
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isLoading, auditId, startSimulation]);

  return state;
}

export { STAGES };
