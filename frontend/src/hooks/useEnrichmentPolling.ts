import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuditStore } from '../stores/auditStore';

const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

interface EnrichmentStatus {
  enrichment_status: 'polling' | 'complete' | 'failed' | 'timed_out';
  enrichment_progress: string;
  has_link_graph: boolean;
  has_topic_clusters: boolean;
}

export type EnrichmentState = 'polling' | 'complete' | 'failed' | 'timed_out' | 'idle';

interface UseEnrichmentPollingResult {
  status: EnrichmentState;
  progress: string;
  hasLinkGraph: boolean;
  hasTopicClusters: boolean;
  /** Manually trigger a refresh check (calls POST refresh-enrichment) */
  refreshNow: () => Promise<void>;
  isRefreshing: boolean;
}

const POLL_INTERVAL = 10_000; // 10 seconds for active polling
const MAX_POLL_DURATION = 25 * 60 * 1000; // 25 minutes (matches backend progressive polling)
const SLOW_POLL_INTERVAL = 60_000; // 60 seconds for post-timeout auto-retry

export function useEnrichmentPolling(auditId: string | undefined): UseEnrichmentPollingResult {
  const report = useAuditStore((s) => s.report);
  const fetchReport = useAuditStore((s) => s.fetchReport);

  const initialStatus = report?.enrichment_status ?? 'idle';
  const [status, setStatus] = useState<EnrichmentState>(
    initialStatus === 'polling' ? 'polling'
      : initialStatus === 'failed' ? 'failed'
      : initialStatus === 'timed_out' ? 'timed_out'
      : initialStatus === 'complete' ? 'complete'
      : 'idle'
  );
  const [progress, setProgress] = useState(report?.enrichment_progress ?? '');
  const [hasLinkGraph, setHasLinkGraph] = useState(false);
  const [hasTopicClusters, setHasTopicClusters] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const slowTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(Date.now());

  // Sync from report when it changes (e.g. initial load)
  useEffect(() => {
    const rs = report?.enrichment_status;
    if (rs === 'polling') {
      setStatus('polling');
      setProgress(report?.enrichment_progress ?? '');
    } else if (rs === 'complete') {
      setStatus('complete');
      setProgress('');
      setHasLinkGraph(!!report?.link_analysis?.graph?.nodes?.length);
      setHasTopicClusters(!!report?.link_analysis?.clusters?.length);
    } else if (rs === 'timed_out') {
      setStatus('timed_out');
      setProgress(report?.enrichment_progress ?? '');
    } else if (rs === 'failed') {
      setStatus('failed');
      setProgress(report?.enrichment_progress ?? '');
    }
  }, [report?.enrichment_status, report?.enrichment_progress, report?.link_analysis]);

  const poll = useCallback(async () => {
    if (!auditId) return;
    try {
      const res = await fetch(`${apiBase}/api/audit/enrichment-status/${auditId}`, {
        credentials: 'include',
      });
      if (!res.ok) return;
      const data: EnrichmentStatus = await res.json();

      setProgress(data.enrichment_progress);
      setHasLinkGraph(data.has_link_graph);
      setHasTopicClusters(data.has_topic_clusters);

      if (data.enrichment_status === 'complete') {
        setStatus('complete');
        // Refetch full report to get the enriched data
        fetchReport(auditId);
      } else if (data.enrichment_status === 'failed') {
        setStatus('failed');
      } else if (data.enrichment_status === 'timed_out') {
        setStatus('timed_out');
      }
    } catch {
      // Silently ignore network errors — will retry next interval
    }
  }, [auditId, fetchReport]);

  // Active polling while status is 'polling'
  useEffect(() => {
    if (status !== 'polling' || !auditId) return;

    startTimeRef.current = Date.now();

    // Poll immediately on start
    poll();

    timerRef.current = setInterval(() => {
      if (Date.now() - startTimeRef.current > MAX_POLL_DURATION) {
        setStatus('timed_out');
        setProgress('Crawl is still processing. Try refreshing in a few minutes.');
        if (timerRef.current) clearInterval(timerRef.current);
        return;
      }
      poll();
    }, POLL_INTERVAL);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [status, auditId, poll]);

  // Stop active polling when status changes away from "polling"
  useEffect(() => {
    if (status !== 'polling' && timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, [status]);

  // Slow auto-retry when timed_out — poll every 60s to catch late completions
  useEffect(() => {
    if (status !== 'timed_out' || !auditId) {
      if (slowTimerRef.current) {
        clearInterval(slowTimerRef.current);
        slowTimerRef.current = null;
      }
      return;
    }

    slowTimerRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${apiBase}/api/audit/enrichment-status/${auditId}`, {
          credentials: 'include',
        });
        if (!res.ok) return;
        const data: EnrichmentStatus = await res.json();

        if (data.enrichment_status === 'complete') {
          setStatus('complete');
          setProgress('');
          fetchReport(auditId);
        } else if (data.enrichment_status === 'polling') {
          // Backend poller or pingback kicked in — switch back to active polling
          setStatus('polling');
          setProgress(data.enrichment_progress);
        }
      } catch {
        // Ignore
      }
    }, SLOW_POLL_INTERVAL);

    return () => {
      if (slowTimerRef.current) clearInterval(slowTimerRef.current);
    };
  }, [status, auditId, fetchReport]);

  // Manual refresh
  const refreshNow = useCallback(async () => {
    if (!auditId) return;
    setIsRefreshing(true);
    try {
      const res = await fetch(`${apiBase}/api/audit/${auditId}/refresh-enrichment`, {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) return;
      const data = await res.json();

      if (data.enrichment_status === 'complete' || data.enrichment_status === 'polling') {
        // Data is ready or being processed — switch to polling to pick it up
        setStatus('polling');
        setProgress(data.message || '');
        fetchReport(auditId);
      } else {
        setProgress(data.message || 'Still processing...');
      }
    } catch {
      // Ignore
    } finally {
      setIsRefreshing(false);
    }
  }, [auditId, fetchReport]);

  return { status, progress, hasLinkGraph, hasTopicClusters, refreshNow, isRefreshing };
}
