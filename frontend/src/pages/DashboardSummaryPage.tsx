import { useMemo } from 'react';
import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import { ArrowLeft, FileText, Info, ArrowRightLeft, Shield, CheckCircle2, Brain, Zap } from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';

export default function DashboardSummaryPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);

  const summary: string | null = report?.executive_summary ?? null;

  const migration = useMemo(() => {
    if (!report?.migration_assessment) return null;
    return report.migration_assessment as Record<string, unknown>;
  }, [report]);

  const nlp = useMemo(() => {
    const data = report?.nlp_analysis as Record<string, any> | null;
    if (!data) return null;
    const industry = data.detected_industry as string | undefined;
    const primaryTopic = data.insights?.primary_topic as string | undefined;
    const entities = data.entities as Array<Record<string, any>> | undefined;
    const topEntities = entities?.slice(0, 3).map((e) => e.name as string) ?? [];
    const tone = (data.sentiment as Record<string, any>)?.tone as string | undefined;
    return {
      topic: primaryTopic ?? (industry ? industry.split('/').filter(Boolean).pop() : null),
      confidence: (data.industry_confidence as number) ?? 0,
      topEntities,
      tone: tone ?? null,
    };
  }, [report]);

  const tipr = useMemo(() => {
    const data = report?.tipr_analysis as Record<string, any> | null;
    if (!data?.summary) return null;
    const s = data.summary;
    const recs = (data.recommendations as any[]) || [];
    const topRec = recs.find((r: any) => r.priority === 'high' && r.type === 'add_link');
    return {
      total: s.total_pages as number,
      stars: s.stars as number,
      hoarders: s.hoarders as number,
      orphans: s.orphan_count as number,
      healthPct: s.total_pages > 0 ? Math.round((s.stars / s.total_pages) * 100) : 0,
      topRecSource: topRec?.source_url as string | undefined,
      topRecTarget: topRec?.target_url as string | undefined,
    };
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

      {/* Content Intelligence Brief */}
      {nlp && nlp.topic && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-surface-raised border border-border rounded-xl p-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <Brain size={16} className="text-accent" />
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
              Content Intelligence
            </h2>
          </div>
          <div className="space-y-2 text-sm text-text-secondary leading-relaxed">
            <p>
              Google classifies your content as{' '}
              <strong className="text-text">{nlp.topic}</strong> with{' '}
              <strong className="text-text">{Math.round(nlp.confidence * 100)}%</strong> confidence.
            </p>
            {nlp.topEntities.length > 0 && (
              <p>
                Top content entities:{' '}
                {nlp.topEntities.map((e, i) => (
                  <span key={i}>
                    <strong className="text-text">{e}</strong>
                    {i < nlp.topEntities.length - 1 ? ', ' : ''}
                  </span>
                ))}
              </p>
            )}
            {nlp.tone && (
              <p>
                Content tone: <strong className="text-text">{nlp.tone}</strong>
              </p>
            )}
          </div>
          <Link
            to={`/dashboard/${auditId}/content-intelligence`}
            className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-accent hover:text-accent-hover transition-colors"
          >
            View full analysis →
          </Link>
        </motion.div>
      )}

      {/* Link Intelligence Brief */}
      {tipr && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.18 }}
          className="bg-surface-raised border border-border rounded-xl p-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <Zap size={16} className="text-amber-400" />
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
              Link Intelligence
            </h2>
          </div>
          <div className="space-y-2 text-sm text-text-secondary leading-relaxed">
            <p>
              Internal Link Health: <strong className="text-text">{tipr.healthPct}%</strong> of
              pages are healthy hubs (Stars). <strong className="text-text">{tipr.hoarders}</strong> pages
              are hoarding equity and <strong className="text-text">{tipr.orphans}</strong> pages are orphaned.
            </p>
            {tipr.topRecSource && tipr.topRecTarget && (
              <p>
                Top recommendation: Add links from{' '}
                <strong className="text-text font-mono text-xs">{new URL(tipr.topRecSource.startsWith('http') ? tipr.topRecSource : `https://example.com${tipr.topRecSource}`).pathname}</strong>
                {' '}to{' '}
                <strong className="text-text font-mono text-xs">{new URL(tipr.topRecTarget.startsWith('http') ? tipr.topRecTarget : `https://example.com${tipr.topRecTarget}`).pathname}</strong>
                {' '}to redistribute equity.
              </p>
            )}
          </div>
          <Link
            to={`/dashboard/${auditId}/link-intelligence`}
            className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-accent hover:text-accent-hover transition-colors"
          >
            View full analysis →
          </Link>
        </motion.div>
      )}

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
