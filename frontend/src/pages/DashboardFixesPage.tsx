import { useMemo } from 'react';
import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import { ArrowLeft, Wrench, Info, Clock, Gauge } from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';
import { PILLAR_LABELS } from '../constants/pillarLabels';

interface Fix {
  finding_pattern: string;
  pillar_key: string;
  title: string;
  steps_markdown: string;
  difficulty: string;
  estimated_time: string;
}

const difficultyColor: Record<string, string> = {
  easy: 'text-success bg-success/10',
  medium: 'text-warning bg-warning/10',
  advanced: 'text-severity-high bg-severity-high/10',
};

export default function DashboardFixesPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);

  const detectedCms = (report?.cms_detection as Record<string, unknown> | null)?.platform as string | undefined;
  const cmsConfidence = (report?.cms_detection as Record<string, unknown> | null)?.confidence as number | undefined;
  const isWebflow = detectedCms === 'webflow';

  const fixesByPillar = useMemo(() => {
    const raw: Record<string, Fix> = report?.webflow_fixes ?? {};
    const fixes = Object.values(raw);
    if (fixes.length === 0) return null;

    const grouped: Record<string, Fix[]> = {};
    for (const fix of fixes) {
      const key = fix.pillar_key || 'other';
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(fix);
    }
    return grouped;
  }, [report]);

  // Build header text based on detected CMS
  const headerTitle = isWebflow
    ? 'Webflow Fix Guide'
    : 'Fix Guide';

  const headerSubtitle = isWebflow
    ? 'Step-by-step instructions to fix each issue in Webflow.'
    : detectedCms && detectedCms !== 'unknown'
      ? `Step-by-step instructions to fix each issue. Your site was detected as ${detectedCms.charAt(0).toUpperCase() + detectedCms.slice(1)}${cmsConfidence ? ` (${Math.round(cmsConfidence * 100)}% confidence)` : ''}.`
      : 'Step-by-step instructions to fix each issue.';

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
            <Wrench size={20} className="text-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text font-heading">
              {headerTitle}
            </h1>
            <p className="text-sm text-text-secondary mt-0.5">
              {headerSubtitle}
            </p>
          </div>
        </div>
      </motion.div>

      {/* CMS badge */}
      {detectedCms && detectedCms !== 'unknown' && !isWebflow && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-center gap-3"
        >
          <Info size={16} className="text-amber-600 flex-shrink-0" />
          <p className="text-xs text-amber-800">
            These are platform-agnostic fix instructions. For CMS-specific guidance,
            consider migrating to Webflow where Veza Digital provides tailored implementation support.
          </p>
        </motion.div>
      )}

      {fixesByPillar ? (
        <div className="space-y-8">
          {Object.entries(fixesByPillar).map(([pillarKey, fixes], gi) => (
            <motion.div
              key={pillarKey}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * gi }}
            >
              <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
                {PILLAR_LABELS[pillarKey as keyof typeof PILLAR_LABELS] ?? pillarKey}
              </h2>
              <div className="space-y-3">
                {fixes.map((fix) => (
                  <details
                    key={fix.finding_pattern}
                    className="group bg-surface-raised border border-border rounded-xl overflow-hidden"
                  >
                    <summary className="flex items-center justify-between gap-4 px-5 py-4 cursor-pointer select-none list-none hover:bg-surface-overlay/50 transition-colors">
                      <div className="flex items-center gap-3 min-w-0">
                        <Wrench size={14} className="text-accent flex-shrink-0" />
                        <span className="text-sm font-semibold text-text truncate">
                          {fix.title}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span
                          className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${difficultyColor[fix.difficulty] ?? 'text-text-muted bg-surface-overlay'}`}
                        >
                          {fix.difficulty}
                        </span>
                        <span className="text-[10px] text-text-muted flex items-center gap-1">
                          <Clock size={10} />
                          {fix.estimated_time}
                        </span>
                        <svg
                          width="12"
                          height="12"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          className="text-text-muted transition-transform group-open:rotate-180"
                        >
                          <polyline points="6 9 12 15 18 9" />
                        </svg>
                      </div>
                    </summary>
                    <div className="px-5 pb-5 pt-2 border-t border-border">
                      <div className="flex items-center gap-3 mb-3">
                        <span className="flex items-center gap-1 text-[10px] text-text-muted">
                          <Gauge size={10} />
                          Difficulty: {fix.difficulty}
                        </span>
                        <span className="flex items-center gap-1 text-[10px] text-text-muted">
                          <Clock size={10} />
                          {fix.estimated_time}
                        </span>
                      </div>
                      <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                        {fix.steps_markdown}
                      </div>
                    </div>
                  </details>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-surface-raised border border-border rounded-xl p-8 text-center"
        >
          <div className="w-12 h-12 mx-auto mb-4 bg-surface-overlay rounded-xl flex items-center justify-center">
            <Info size={20} className="text-text-muted" />
          </div>
          <p className="text-sm font-semibold text-text mb-1">
            Fix Instructions Not Available
          </p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Fix instructions will appear after premium analysis. Run a
            Comprehensive Audit to generate fix guides for your site.
          </p>
        </motion.div>
      )}
    </div>
  );
}
