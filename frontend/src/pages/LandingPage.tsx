import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { AuditForm } from '../components/AuditForm';
import { AuditProgress } from '../components/audit/AuditProgress';
import { useAuditStore } from '../stores/auditStore';

export function LandingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isLoading, auditedUrl, error, runAudit, loadReport, clearAudit } =
    useAuditStore();

  // On mount: handle legacy ?job_id=&page_url= params, or clear stale data
  useEffect(() => {
    const jobId = searchParams.get('job_id');
    const pageUrl = searchParams.get('page_url');
    if (jobId && pageUrl) {
      loadReport(jobId, pageUrl);
    } else {
      clearAudit();
    }
  }, [searchParams, loadReport, clearAudit]);

  // Navigate to report page when audit completes
  useEffect(() => {
    const unsub = useAuditStore.subscribe((state, prev) => {
      if (state.report && !state.isLoading && (!prev.report || prev.isLoading)) {
        const id = state.report.audit_id || state.report.job_id || 'latest';
        navigate(`/audit/${id}`);
      }
    });
    return unsub;
  }, [navigate]);

  if (isLoading) {
    return <AuditProgress isLoading={isLoading} />;
  }

  return <AuditForm onRunAudit={runAudit} isLoading={isLoading} error={error} />;
}
