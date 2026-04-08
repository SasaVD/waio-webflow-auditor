import { useMemo } from 'react';
import { Link } from 'react-router';
import { motion } from 'framer-motion';
import {
  Activity,
  FileSearch,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Info,
  ExternalLink,
  Brain,
  ChevronRight,
  FileCode,
  FileJson,
  BookOpen,
  Paintbrush,
  Zap,
  Accessibility,
  Layers,
  Radio,
  ShieldCheck,
  Link2,
  ArrowRightLeft,
  Shield,
  Clock,
  Server,
} from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';
import { KpiCard } from '../components/dashboard/KpiCard';
import { PillarRadarChart } from '../components/dashboard/PillarRadarChart';
import { ExportButton } from '../components/export/ExportButton';
import { PILLAR_LABELS, PILLAR_SHORT_LABELS } from '../constants/pillarLabels';

/* ─── Helpers ─── */
const scoreColor = (score: number): string => {
  if (score >= 90) return '#22C55E';
  if (score >= 75) return '#84CC16';
  if (score >= 55) return '#EAB308';
  if (score >= 35) return '#F97316';
  return '#EF4444';
};

const scoreLabel = (score: number): string => {
  if (score >= 90) return 'Excellent';
  if (score >= 75) return 'Good';
  if (score >= 55) return 'Needs Work';
  if (score >= 35) return 'Poor';
  return 'Critical';
};

const pillarIcons: Record<string, React.ElementType> = {
  semantic_html: FileCode,
  structured_data: FileJson,
  aeo_content: BookOpen,
  css_quality: Paintbrush,
  js_bloat: Zap,
  accessibility: Accessibility,
  rag_readiness: Layers,
  agentic_protocols: Radio,
  data_integrity: ShieldCheck,
  internal_linking: Link2,
};

const pillarMeta: Record<string, { icon: React.ElementType; label: string; short: string }> = Object.fromEntries(
  Object.keys(PILLAR_LABELS).map((key) => [
    key,
    {
      icon: pillarIcons[key] ?? FileCode,
      label: PILLAR_LABELS[key],
      short: PILLAR_SHORT_LABELS[key] ?? key,
    },
  ])
);

const severityIcon: Record<string, React.ElementType> = {
  critical: XCircle,
  high: AlertCircle,
  medium: Info,
};

const severityColor: Record<string, string> = {
  critical: 'text-severity-critical',
  high: 'text-severity-high',
  medium: 'text-severity-medium',
};

const severityBg: Record<string, string> = {
  critical: 'bg-severity-critical',
  high: 'bg-severity-high',
  medium: 'bg-severity-medium',
};

interface Finding {
  severity: string;
  description: string;
  recommendation: string;
  pillar?: string;
}

export default function DashboardOverviewPage() {
  const report = useAuditStore((s) => s.report);

  // Flatten all findings with pillar key
  const allFindings = useMemo(() => {
    if (!report?.categories) return [];
    const findings: Finding[] = [];
    for (const [pillarKey, cat] of Object.entries(report.categories)) {
      const catObj = cat as Record<string, any>;
      const checks = catObj.checks || {};
      for (const check of Object.values(checks)) {
        const checkObj = check as Record<string, any>;
        if (checkObj.findings) {
          for (const f of checkObj.findings) {
            findings.push({ ...f, pillar: pillarKey });
          }
        }
      }
    }
    return findings.sort(
      (a, b) =>
        ({ critical: 0, high: 1, medium: 2 }[a.severity] ?? 3) -
        ({ critical: 0, high: 1, medium: 2 }[b.severity] ?? 3)
    );
  }, [report]);

  const topFindings = allFindings.slice(0, 5);

  // Build radar chart data
  const radarData = useMemo(() => {
    if (!report?.categories) return [];
    return Object.entries(pillarMeta)
      .filter(([key]) => report.categories[key])
      .map(([key, meta]) => ({
        pillar: meta.short,
        score: report.categories[key].score ?? 0,
        fullMark: 100,
      }));
  }, [report]);

  // Pillar scores for the grid
  const pillarScores = useMemo(() => {
    if (!report?.categories) return [];
    return Object.entries(pillarMeta)
      .filter(([key]) => report.categories[key])
      .map(([key, meta]) => ({
        key,
        ...meta,
        score: report.categories[key].score ?? 0,
        label: report.categories[key].label ?? '',
      }));
  }, [report]);

  // CMS detection info
  const cmsInfo = useMemo(() => {
    const det = report?.cms_detection as Record<string, unknown> | null;
    return {
      platform: (det?.platform as string) ?? 'unknown',
      confidence: (det?.confidence as number) ?? 0,
    };
  }, [report]);

  // NLP content intelligence
  const nlpInfo = useMemo(() => {
    const nlp = report?.nlp_analysis as Record<string, any> | null;
    if (!nlp) return null;
    const industry = nlp.detected_industry as string | undefined;
    const entities = nlp.entities as Array<Record<string, any>> | undefined;
    const primaryTopic = nlp.insights?.primary_topic as string | undefined;
    return {
      industry: primaryTopic ?? (industry ? industry.split('/').filter(Boolean).pop() : null),
      confidence: (nlp.industry_confidence as number) ?? 0,
      entityCount: entities?.length ?? 0,
      primaryEntity: (nlp.primary_entity as string) ?? null,
      tone: (nlp.sentiment as Record<string, any>)?.tone as string | undefined,
    };
  }, [report]);

  // Migration assessment (only for non-Webflow sites)
  const migration = useMemo(() => {
    if (!report?.migration_assessment) return null;
    return report.migration_assessment as Record<string, unknown>;
  }, [report]);

  // TIPR link intelligence summary
  const tiprInfo = useMemo(() => {
    const tipr = report?.tipr_analysis as Record<string, any> | null;
    if (!tipr?.summary) return null;
    const s = tipr.summary;
    return {
      total: s.total_pages as number,
      stars: s.stars as number,
      hoarders: s.hoarders as number,
      wasters: s.wasters as number,
      orphans: s.orphan_count as number,
      recCount: (tipr.recommendations as any[])?.length ?? 0,
      healthPct: s.total_pages > 0 ? Math.round((s.stars / s.total_pages) * 100) : 0,
    };
  }, [report]);

  if (!report) {
    return (
      <div className="p-8 text-center">
        <p className="text-text-muted mb-4">
          No audit data loaded. Run an audit first.
        </p>
        <Link
          to="/"
          className="text-sm text-accent hover:text-accent-hover font-semibold transition-colors"
        >
          Go to Auditor
        </Link>
      </div>
    );
  }

  const overallScore = report.overall_score ?? 0;
  const crit = report.summary?.critical ?? 0;
  const high = report.summary?.high ?? 0;
  const med = report.summary?.medium ?? 0;
  const totalFindings = report.summary?.total_findings ?? allFindings.length;
  const positiveCount = report.positive_findings?.length ?? 0;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Top Bar */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-text-muted uppercase tracking-widest">
              Dashboard
            </span>
            {cmsInfo.platform && cmsInfo.platform !== 'unknown' && (
              <span className="text-[10px] font-bold text-accent bg-accent-muted px-2 py-0.5 rounded-full uppercase">
                {cmsInfo.platform}
                {cmsInfo.confidence > 0 && ` ${Math.round(cmsInfo.confidence * 100)}%`}
              </span>
            )}
          </div>
          <a
            href={report.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xl font-bold text-text hover:text-accent transition-colors inline-flex items-center gap-2 font-heading"
          >
            {report.url}
            <ExternalLink size={14} className="text-text-muted" />
          </a>
          <div className="text-xs text-text-muted mt-1">
            {new Date(report.audit_timestamp).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        </div>

        {/* Health Score Badge + Export */}
        <div className="flex items-center gap-4">
          <ExportButton report={report} />
          <div
            className="w-16 h-16 rounded-xl flex items-center justify-center border-2"
            style={{
              borderColor: scoreColor(overallScore),
              backgroundColor: scoreColor(overallScore) + '15',
            }}
          >
            <span
              className="text-2xl font-extrabold font-heading"
              style={{ color: scoreColor(overallScore) }}
            >
              {overallScore}
            </span>
          </div>
          <div>
            <div
              className="text-sm font-bold"
              style={{ color: scoreColor(overallScore) }}
            >
              {scoreLabel(overallScore)}
            </div>
            <div className="text-xs text-text-muted">Health Score</div>
          </div>
        </div>
      </motion.div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Health Score"
          value={overallScore}
          subtitle={scoreLabel(overallScore)}
          icon={Activity}
          color="text-score-excellent"
        />
        <KpiCard
          label="Total Findings"
          value={totalFindings}
          subtitle={`${crit} critical, ${high} high, ${med} medium`}
          icon={FileSearch}
          color="text-severity-high"
        />
        <KpiCard
          label="Critical Issues"
          value={crit}
          subtitle={crit > 0 ? 'Requires immediate attention' : 'No critical issues'}
          icon={AlertTriangle}
          color={crit > 0 ? 'text-severity-critical' : 'text-success'}
        />
        <KpiCard
          label="Positive Findings"
          value={positiveCount}
          subtitle="Things done right"
          icon={CheckCircle2}
          color="text-success"
        />
      </div>

      {/* Radar Chart + Top Issues */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-surface-raised border border-border rounded-xl p-6"
        >
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-4">
            Pillar Scores
          </h2>
          {radarData.length > 0 ? (
            <PillarRadarChart data={radarData} />
          ) : (
            <div className="h-[320px] flex items-center justify-center text-text-muted text-sm">
              No pillar data available
            </div>
          )}
        </motion.div>

        {/* Top 5 Critical Issues */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-surface-raised border border-border rounded-xl p-6"
        >
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-4">
            Top Issues
          </h2>
          {topFindings.length > 0 ? (
            <div className="space-y-3">
              {topFindings.map((f, i) => {
                const SevIcon = severityIcon[f.severity] ?? Info;
                return (
                  <div
                    key={i}
                    className="flex items-start gap-3 p-3 bg-surface-overlay rounded-lg"
                  >
                    <SevIcon
                      size={16}
                      className={`mt-0.5 flex-shrink-0 ${severityColor[f.severity] ?? 'text-text-muted'}`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded text-white ${severityBg[f.severity] ?? 'bg-text-muted'}`}
                        >
                          {f.severity}
                        </span>
                        {f.pillar && pillarMeta[f.pillar] && (
                          <span className="text-[10px] text-text-muted font-semibold">
                            {pillarMeta[f.pillar].label}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-text leading-snug line-clamp-2">
                        {f.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="h-[320px] flex items-center justify-center text-text-muted text-sm">
              No issues found
            </div>
          )}
        </motion.div>
      </div>

      {/* Pillar Score Grid */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-4">
          Pillar Breakdown
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {pillarScores.map((p) => {
            const PIcon = p.icon;
            return (
              <div
                key={p.key}
                className="bg-surface-raised border border-border rounded-xl p-4 hover:border-accent/20 transition-all group"
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-surface-overlay group-hover:bg-accent/10 flex items-center justify-center transition-all">
                    <PIcon
                      size={15}
                      className="text-text-muted group-hover:text-accent transition-colors"
                    />
                  </div>
                  <span className="text-xs font-semibold text-text-secondary truncate">
                    {p.short}
                  </span>
                </div>
                <div
                  className="text-2xl font-extrabold font-heading mb-1"
                  style={{ color: scoreColor(p.score) }}
                >
                  {p.score}
                </div>
                {/* Progress bar */}
                <div className="h-1.5 bg-surface-overlay rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${p.score}%`,
                      backgroundColor: scoreColor(p.score),
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* Content Intelligence Card */}
      {nlpInfo && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.22 }}
        >
          <Link
            to={`/dashboard/${report.audit_id}/content-intelligence`}
            className="block bg-surface-raised border border-border rounded-xl p-5 hover:border-accent/30 transition-all group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center group-hover:bg-accent/20 transition-all">
                  <Brain size={18} className="text-accent" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-text">Content Intelligence</h2>
                  <p className="text-xs text-text-muted mt-0.5">
                    Google classifies your content as{' '}
                    <strong className="text-text-secondary">{nlpInfo.industry}</strong>
                    {nlpInfo.confidence > 0 && (
                      <> ({Math.round(nlpInfo.confidence * 100)}% confidence)</>
                    )}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {nlpInfo.entityCount > 0 && (
                  <div className="text-right hidden sm:block">
                    <div className="text-lg font-bold text-text font-heading">{nlpInfo.entityCount}</div>
                    <div className="text-[10px] text-text-muted">Entities</div>
                  </div>
                )}
                {nlpInfo.tone && (
                  <div className="text-right hidden md:block">
                    <div className="text-xs font-semibold text-text-secondary">{nlpInfo.tone}</div>
                    <div className="text-[10px] text-text-muted">Tone</div>
                  </div>
                )}
                <ChevronRight size={16} className="text-text-muted group-hover:text-accent transition-colors" />
              </div>
            </div>
          </Link>
        </motion.div>
      )}

      {/* Link Intelligence (TIPR) Card */}
      {tiprInfo && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.23 }}
        >
          <Link
            to={`/dashboard/${report.audit_id}/link-intelligence`}
            className="block bg-surface-raised border border-border rounded-xl p-5 hover:border-accent/30 transition-all group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-amber-500/10 rounded-xl flex items-center justify-center group-hover:bg-amber-500/20 transition-all">
                  <Zap size={18} className="text-amber-400" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-text">Link Intelligence</h2>
                  <p className="text-xs text-text-muted mt-0.5">
                    {tiprInfo.healthPct}% healthy hubs &middot; {tiprInfo.hoarders} hoarders &middot; {tiprInfo.orphans} orphans
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right hidden sm:block">
                  <div className="text-lg font-bold text-text font-heading">{tiprInfo.recCount}</div>
                  <div className="text-[10px] text-text-muted">Recommendations</div>
                </div>
                <div className="text-right hidden md:block">
                  <div className="text-lg font-bold text-green-400 font-heading">{tiprInfo.stars}</div>
                  <div className="text-[10px] text-text-muted">Stars</div>
                </div>
                <ChevronRight size={16} className="text-text-muted group-hover:text-accent transition-colors" />
              </div>
            </div>
          </Link>
        </motion.div>
      )}

      {/* Migration Intelligence — only for non-Webflow sites */}
      {migration && cmsInfo.platform !== 'webflow' && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="space-y-4"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
              <ArrowRightLeft size={16} className="text-indigo-600" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-text uppercase tracking-widest">
                Migration Intelligence
              </h2>
              <p className="text-xs text-text-muted">
                {cmsInfo.platform.charAt(0).toUpperCase() + cmsInfo.platform.slice(1)} → Webflow migration assessment
              </p>
            </div>
          </div>

          {/* Migration summary cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-surface-raised border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Server size={14} className="text-text-muted" />
                <span className="text-xs font-semibold text-text-muted">Current Platform</span>
              </div>
              <div className="text-lg font-bold text-text font-heading capitalize">
                {(migration.source_cms as string) ?? cmsInfo.platform}
              </div>
              <div className="text-xs text-text-muted mt-0.5">
                {cmsInfo.confidence > 0 && `${Math.round(cmsInfo.confidence * 100)}% confidence`}
              </div>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Clock size={14} className="text-text-muted" />
                <span className="text-xs font-semibold text-text-muted">Est. Timeline</span>
              </div>
              <div className="text-lg font-bold text-text font-heading">
                {(migration.migration_timeline as string) ?? 'TBD'}
              </div>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <ArrowRightLeft size={14} className="text-text-muted" />
                <span className="text-xs font-semibold text-text-muted">Est. Redirects</span>
              </div>
              <div className="text-lg font-bold text-text font-heading">
                {(migration.redirect_count_estimate as number)?.toLocaleString() ?? '—'}
              </div>
            </div>
          </div>

          {/* Platform issues */}
          {Array.isArray(migration.platform_issues) && (migration.platform_issues as Array<Record<string, string>>).length > 0 && (
            <div className="bg-surface-raised border border-border rounded-xl p-5">
              <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-3 flex items-center gap-2">
                <Shield size={13} />
                Platform-Specific Risks
              </h3>
              <div className="space-y-2.5">
                {(migration.platform_issues as Array<Record<string, string>>).slice(0, 5).map((issue, i) => {
                  const sevColor: Record<string, string> = {
                    critical: 'bg-severity-critical',
                    high: 'bg-severity-high',
                    medium: 'bg-severity-medium',
                  };
                  return (
                    <div key={i} className="flex items-start gap-3 p-3 bg-surface-overlay rounded-lg">
                      <span className={`text-[10px] font-bold uppercase text-white px-1.5 py-0.5 rounded mt-0.5 flex-shrink-0 ${sevColor[issue.severity] ?? 'bg-text-muted'}`}>
                        {issue.severity}
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-text">{issue.title}</p>
                        <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">{issue.description}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Webflow advantages */}
          {Array.isArray(migration.webflow_advantages) && (migration.webflow_advantages as Array<Record<string, string>>).length > 0 && (
            <div className="bg-surface-raised border border-border rounded-xl p-5">
              <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-3 flex items-center gap-2">
                <CheckCircle2 size={13} className="text-success" />
                Webflow Migration Benefits
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {(migration.webflow_advantages as Array<Record<string, string>>).slice(0, 6).map((adv, i) => (
                  <div key={i} className="flex items-start gap-2.5 p-3 bg-success/5 border border-success/10 rounded-lg">
                    <CheckCircle2 size={14} className="text-success mt-0.5 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-text">{adv.title}</p>
                      <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">{adv.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
