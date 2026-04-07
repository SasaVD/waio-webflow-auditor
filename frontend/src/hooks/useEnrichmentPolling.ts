import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuditStore } from '../stores/auditStore';

const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

interface EnrichmentStatus {
  enrichment_status: 'polling' | 'complete' | 'failed';
  enrichment_progress: string;
  has_link_graph: boolean;
  has_topic_clusters: boolean;
}

interface UseEnrichmentPollingResult {
  status: 'polling' | 'complete' | 'failed' | 'idle';
  progress: string;
  hasLinkGraph: boolean;
  hasTopicClusters: boolean;
}

const POLL_INTERVAL = 10_000; // 10 seconds
const MAX_POLL_DURATION = 10 * 60 * 1000; // 10 minutes

export function useEnrichmentPolling(auditId: string | undefined): UseEnrichmentPollingResult {
  const report = useAuditStore((s) => s.report);
  const fetchReport = useAuditStore((s) => s.fetchReport);

  const initialStatus = report?.enrichment_status ?? 'idle';
  const [status, setStatus] = useState<'polling' | 'complete' | 'failed' | 'idle'>(
    initialStatus === 'polling' ? 'polling' : initialStatus === 'failed' ? 'failed' : initialStatus === 'complete' ? 'complete' : 'idle'
  );
  const [progress, setProgress] = useState(report?.enrichment_progress ?? '');
  const [hasLinkGraph, setHasLinkGraph] = useState(false);
  const [hasTopicClusters, setHasTopicClusters] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
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
      }
    } catch {
      // Silently ignore network errors — will retry next interval
    }
  }, [auditId, fetchReport]);

  useEffect(() => {
    if (status !== 'polling' || !auditId) return;

    startTimeRef.current = Date.now();

    // Poll immediately on start
    poll();

    timerRef.current = setInterval(() => {
      if (Date.now() - startTimeRef.current > MAX_POLL_DURATION) {
        setStatus('failed');
        setProgress('Enrichment polling timed out.');
        if (timerRef.current) clearInterval(timerRef.current);
        return;
      }
      poll();
    }, POLL_INTERVAL);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [status, auditId, poll]);

  // Stop polling when status changes away from "polling"
  useEffect(() => {
    if (status !== 'polling' && timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, [status]);

  return { status, progress, hasLinkGraph, hasTopicClusters };
}
