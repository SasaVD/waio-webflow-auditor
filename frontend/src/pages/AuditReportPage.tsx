import { useNavigate } from 'react-router';
import { useAuditStore } from '../stores/auditStore';
import { AuditReport } from '../components/AuditReport';
import { SiteAuditReport } from '../components/SiteAuditReport';
import { CompetitiveReport } from '../components/CompetitiveReport';
import { LoadingState } from '../components/LoadingState';

export function AuditReportPage() {
  const navigate = useNavigate();
  const { report, isLoading, auditedUrl } = useAuditStore();

  const handleNewAudit = () => {
    navigate('/');
  };

  if (isLoading) {
    return <LoadingState url={auditedUrl} />;
  }

  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
        <p className="text-lg font-semibold text-text mb-2">Report Not Available</p>
        <p className="text-text-secondary mb-6 text-sm">
          This audit report is no longer in memory. Run a new audit to generate fresh results.
        </p>
        <button
          onClick={handleNewAudit}
          className="bg-accent hover:bg-accent-hover text-white px-6 py-2.5 rounded-xl font-semibold transition-colors"
        >
          Run a New Audit
        </button>
      </div>
    );
  }

  if (report.is_site_audit) {
    return <SiteAuditReport report={report} onNewAudit={handleNewAudit} />;
  }
  if (report.is_competitive) {
    return <CompetitiveReport report={report} onNewAudit={handleNewAudit} />;
  }
  return (
    <AuditReport
      report={report}
      onNewAudit={handleNewAudit}
      onViewHistory={() =>
        navigate(`/history?url=${encodeURIComponent(report.url)}`)
      }
    />
  );
}
