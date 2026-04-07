import { useMemo } from 'react';
import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import { ArrowLeft, FileText, Info, ArrowRightLeft, Shield, CheckCircle2 } from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';

export default function DashboardSummaryPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);

  const summary: string | null = report?.executive_summary ?? null;

  const migration = useMemo(() => {
    if (!report?.migration_assessment) return null;
    return report.migration_assessment as Record<string, unknown>;
  }, [report]);

  const cmsName = useMemo(() => {
    const det = report?.cms_detection as Record<string, unknown> | null;
    const platform = det?.platform as string | undefined;
    if (!platform || platform === 'unknown' || platform === 'webflow') return null;
    return platform.charAt(0).toUpperCase() + platform.slice(1);
  }, [report]);

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <Link
          to={`/dashboard/${auditId}`}
          className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text transition-colors mb-4"
        >
          <ArrowLeft size={12} />
          Back to Overview
        </Link>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center">
            <FileText size={20} className="text-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text font-heading">
              Executive Summary
            </h1>
            <p className="text-sm text-text-secondary mt-0.5">
              Strategic assessment of your website's performance.
            </p>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        {summary ? (
          <div className="bg-surface-raised border border-border rounded-xl p-8">
            <div className="prose max-w-none text-text text-sm leading-relaxed whitespace-pre-wrap">
              {summary}
            </div>
          </div>
        ) : (
          <div className="bg-surface-raised border border-border rounded-xl p-8 text-center">
            <div className="w-12 h-12 mx-auto mb-4 bg-surface-overlay rounded-xl flex items-center justify-center">
              <Info size={20} className="text-text-muted" />
            </div>
            <p className="text-sm font-semibold text-text mb-1">
              Executive Summary Not Available
            </p>
            <p className="text-xs text-text-muted max-w-md mx-auto">
              Executive summary will be available after a full site crawl with
              DataForSEO. Run a Comprehensive Audit to generate this report.
            </p>
          </div>
        )}
      </motion.div>

      {/* Migration Assessment Section */}
      {migration && cmsName && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-4"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
              <ArrowRightLeft size={16} className="text-indigo-600" />
            </div>
            <h2 className="text-sm font-bold text-text uppercase tracking-widest">
              {cmsName} → Webflow Migration Path
            </h2>
          </div>

          <div className="bg-surface-raised border border-border rounded-xl p-6 space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-xs text-text-muted font-semibold uppercase">Current CMS</div>
                <div className="text-lg font-bold text-text font-heading mt-1 capitalize">
                  {(migration.source_cms as string) ?? cmsName}
                </div>
              </div>
              <div>
                <div className="text-xs text-text-muted font-semibold uppercase">Est. Timeline</div>
                <div className="text-lg font-bold text-text font-heading mt-1">
                  {(migration.migration_timeline as string) ?? 'TBD'}
                </div>
              </div>
              <div>
                <div className="text-xs text-text-muted font-semibold uppercase">Redirects Needed</div>
                <div className="text-lg font-bold text-text font-heading mt-1">
                  {(migration.redirect_count_estimate as number)?.toLocaleString() ?? '—'}
                </div>
              </div>
            </div>

            {Array.isArray(migration.platform_issues) && (migration.platform_issues as Array<Record<string, string>>).length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-2 flex items-center gap-1.5">
                  <Shield size={12} />
                  Key {cmsName} Risks
                </h3>
                <ul className="space-y-1.5">
                  {(migration.platform_issues as Array<Record<string, string>>).slice(0, 4).map((issue, i) => (
                    <li key={i} className="text-sm text-text-secondary flex items-start gap-2">
                      <span className="text-severity-high mt-1">•</span>
                      <span><strong className="text-text">{issue.title}</strong> — {issue.description}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {Array.isArray(migration.webflow_advantages) && (migration.webflow_advantages as Array<Record<string, string>>).length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-2 flex items-center gap-1.5">
                  <CheckCircle2 size={12} className="text-success" />
                  Webflow Advantages
                </h3>
                <ul className="space-y-1.5">
                  {(migration.webflow_advantages as Array<Record<string, string>>).slice(0, 4).map((adv, i) => (
                    <li key={i} className="text-sm text-text-secondary flex items-start gap-2">
                      <span className="text-success mt-1">•</span>
                      <span><strong className="text-text">{adv.title}</strong> — {adv.description}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}
