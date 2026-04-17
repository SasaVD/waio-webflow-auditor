import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { AuditForm } from '../components/AuditForm';
import { AuditProgress } from '../components/audit/AuditProgress';
import { useAuditStore } from '../stores/auditStore';
import { ThreeAudiencesSection } from '../components/landing/ThreeAudiencesSection';
import { PillarsByWeightSection } from '../components/landing/PillarsByWeightSection';
import { FreeVsPremiumSection } from '../components/landing/FreeVsPremiumSection';
import { DifferentiatorsSection } from '../components/landing/DifferentiatorsSection';
import { FinalCTASection } from '../components/landing/FinalCTASection';

export function LandingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isLoading, error, runAudit, loadReport, clearAudit } =
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
        const isPremium = state.report.tier === 'premium' || state.report.executive_summary;
        if (isPremium) {
          navigate(`/dashboard/${id}`);
        } else {
          navigate(`/audit/${id}`);
        }
      }
    });
    return unsub;
  }, [navigate]);

  if (isLoading) {
    return <AuditProgress isLoading={isLoading} />;
  }

  return (
    <>
      <section id="audit-form" className="scroll-mt-20">
        <AuditForm onRunAudit={runAudit} isLoading={isLoading} error={error} />
      </section>
      <ThreeAudiencesSection />
      <PillarsByWeightSection />
      <FreeVsPremiumSection />
      <DifferentiatorsSection />
      <FinalCTASection />
    </>
  );
}
