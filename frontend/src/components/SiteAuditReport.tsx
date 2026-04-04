import { ArrowLeft, ExternalLink, Globe } from 'lucide-react';

interface SiteReportProps {
  report: any;
  onNewAudit: () => void;
}

const scoreColorClass = (label: string): string => {
  const l = label?.toLowerCase() || '';
  if (l === 'excellent') return 'text-score-excellent';
  if (l === 'good') return 'text-score-good';
  if (l === 'needs improvement') return 'text-score-needs';
  if (l === 'poor') return 'text-score-poor';
  return 'text-score-critical';
};

export const SiteAuditReport: React.FC<SiteReportProps> = ({ report, onNewAudit }) => {
  if (!report) return null;

  return (
    <div className="bg-surface-secondary min-h-screen pb-12">
      <div className="bg-white border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <span className="text-xs font-semibold text-text-muted uppercase tracking-widest">Site Crawler Report</span>
                <span className="text-xs text-text-muted">
                  {new Date(report.audit_timestamp).toLocaleDateString()}
                </span>
              </div>
              <h2 className="text-xl md:text-2xl font-bold text-text-primary inline-flex items-center gap-2">
                <Globe size={20} className="text-primary" />
                {report.url}
              </h2>
            </div>
            <button
              onClick={onNewAudit}
              className="flex items-center gap-2 bg-white hover:bg-surface-secondary border border-border text-text-primary font-semibold px-4 py-2.5 rounded-xl transition-all text-sm"
            >
              <ArrowLeft size={16} />
              New Audit
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="bg-surface-raised border border-border rounded-2xl p-8 flex flex-col items-center justify-center text-center mb-8">
          <h3 className="text-sm font-bold uppercase tracking-widest text-text-muted mb-2">Aggregate Site Score</h3>
          <div className={`text-[6rem] font-extrabold leading-none ${scoreColorClass(report.overall_label)}`}>
            {report.overall_score}
          </div>
          <div className={`text-sm font-bold uppercase tracking-widest mt-2 ${scoreColorClass(report.overall_label)}`}>
            {report.overall_label}
          </div>
          <div className="text-sm font-medium text-text-muted mt-4 pt-4 border-t border-border">
            Across {report.pages_crawled} compiled pages
          </div>
        </div>

        <h3 className="text-lg font-bold text-text-primary mb-4">Crawled Pages Snapshot</h3>
        <div className="space-y-3">
          {report.pages?.map((p: any, i: number) => (
            <div key={i} className="bg-white border border-border-light rounded-xl p-4 flex items-center justify-between transition-shadow hover:shadow-sm">
              <a href={`/?job_id=${report.job_id}&page_url=${encodeURIComponent(p.url)}`} target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-text-primary hover:text-primary transition-colors flex items-center gap-2 truncate max-w-[60%]">
                <span className="truncate">{p.url}</span>
                <ExternalLink size={14} className="text-text-muted flex-shrink-0" />
              </a>
              <div className="flex items-center gap-4">
                <span className={`hidden sm:inline-block text-[10px] font-bold uppercase tracking-wider bg-surface-secondary px-2 py-1 rounded ${scoreColorClass(p.overall_label)}`}>
                  {p.overall_label}
                </span>
                <span className={`text-2xl font-extrabold ${scoreColorClass(p.overall_label)} w-12 text-right`}>
                  {p.overall_score}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
