import { useMemo, useState, useEffect, useCallback } from 'react';
import { useParams, useSearchParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Activity,
  FileSearch,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Info,
  ExternalLink,
  Loader2,
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
  Play,
} from 'lucide-react';
import { KpiCard } from '../components/dashboard/KpiCard';
import { PILLAR_LABELS } from '../constants/pillarLabels';

const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

const scoreColor = (score: number): string => {
  if (score >= 90) return '#22C55E';
  if (score >= 75) return '#84CC16';
  if (score >= 55) return '#EAB308';
  if (score >= 35) return '#F97316';
  return '#EF4444';
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

const severityBorder: Record<string, string> = {
  critical: 'border-l-severity-critical',
  high: 'border-l-severity-high',
  medium: 'border-l-severity-medium',
};

interface Finding {
  severity: string;
  description: string;
  recommendation: string;
  pillar?: string;
}

type AuditStatus = 'idle' | 'loading' | 'running' | 'done' | 'error';

export default function DashboardPageAuditPage() {
  const { auditId } = useParams();
  const [searchParams] = useSearchParams();
  const pageUrl = searchParams.get('url') ?? '';

  const [status, setStatus] = useState<AuditStatus>('idle');
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');

  // Check if page audit already exists
  const checkExisting = useCallback(async () => {
    if (!auditId || !pageUrl) return;
    setStatus('loading');
    try {
      const res = await fetch(
        `${apiBase}/api/audit/${auditId}/page-audit?url=${encodeURIComponent(pageUrl)}`,
        { credentials: 'include' },
      );
      if (res.ok) {
        const data = await res.json();
        setReport(data);
        setStatus('done');
      } else {
        setStatus('idle');
      }
    } catch {
      setStatus('idle');
    }
  }, [auditId, pageUrl]);

  useEffect(() => {
    checkExisting();
  }, [checkExisting]);

  // Auto-run if the URL param `autorun=1` is set
  const autorun = searchParams.get('autorun') === '1';
  const [didAutorun, setDidAutorun] = useState(false);

  const runAudit = useCallback(async () => {
    if (!pageUrl) return;
    setStatus('running');
    setError('');
    try {
      const res = await fetch(`${apiBase}/api/audit/page`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ url: pageUrl, parent_audit_id: auditId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Audit failed' }));
        throw new Error(err.detail || 'Audit failed');
      }
      const data = await res.json();
      setReport(data);
      setStatus('done');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Audit failed');
      setStatus('error');
    }
  }, [pageUrl, auditId]);

  useEffect(() => {
    if (autorun && !didAutorun && status === 'idle') {
      setDidAutorun(true);
      runAudit();
    }
  }, [autorun, didAutorun, status, runAudit]);

  // Parse report data
  const overallScore = (report?.overall_score as number) ?? 0;
  const categories = (report?.categories ?? {}) as Record<string, Record<string, unknown>>;

  const pillarScores = useMemo(() => {
    return Object.entries(PILLAR_LABELS)
      .filter(([key]) => categories[key])
      .map(([key, label]) => ({
        key,
        label,
        icon: pillarIcons[key] ?? FileCode,
        score: (categories[key].score as number) ?? 0,
      }));
  }, [categories]);

  const allFindings = useMemo(() => {
    const findings: Finding[] = [];
    for (const [pillarKey, cat] of Object.entries(categories)) {
      const checks = (cat.checks ?? {}) as Record<string, Record<string, unknown>>;
      for (const check of Object.values(checks)) {
        if (Array.isArray(check.findings)) {
          for (const f of check.findings) {
            findings.push({ ...(f as Finding), pillar: pillarKey });
          }
        }
      }
    }
    return findings.sort(
      (a, b) =>
        ({ critical: 0, high: 1, medium: 2 }[a.severity] ?? 3) -
        ({ critical: 0, high: 1, medium: 2 }[b.severity] ?? 3),
    );
  }, [categories]);

  const positiveCount = useMemo(() => {
    let count = 0;
    for (const cat of Object.values(categories)) {
      const checks = (cat.checks ?? {}) as Record<string, Record<string, unknown>>;
      for (const check of Object.values(checks)) {
        if (typeof check.positive_message === 'string') count++;
      }
    }
    return count;
  }, [categories]);

  const criticalCount = allFindings.filter((f) => f.severity === 'critical').length;

  // Extract path from URL for display
  const displayPath = (() => {
    try {
      const u = new URL(pageUrl);
      return u.pathname || '/';
    } catch {
      return pageUrl;
    }
  })();

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <Link
          to={`/dashboard/${auditId}/pages`}
          className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text transition-colors mb-4"
        >
          <ArrowLeft size={12} />
          Back to Crawled Pages
        </Link>
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-text font-heading truncate">
              Page Audit: {displayPath}
            </h1>
            <a
              href={pageUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-accent hover:text-accent-hover inline-flex items-center gap-1 mt-1"
            >
              {pageUrl}
              <ExternalLink size={12} />
            </a>
          </div>
          {status === 'done' && (
            <div
              className="w-16 h-16 rounded-xl flex items-center justify-center border-2 flex-shrink-0"
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
          )}
        </div>
      </motion.div>

      {/* Idle state — show "Run Audit" button */}
      {status === 'idle' && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-raised border border-border rounded-xl p-10 text-center"
        >
          <FileSearch size={32} className="text-accent mx-auto mb-4" />
          <p className="text-sm font-semibold text-text mb-1">
            No audit results for this page yet
          </p>
          <p className="text-xs text-text-muted max-w-md mx-auto mb-5">
            Run a 10-pillar analysis on this page. This takes about 30 seconds.
          </p>
          <button
            onClick={runAudit}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent-hover text-white text-sm font-semibold rounded-xl transition-colors shadow-glow-accent"
          >
            <Play size={14} />
            Run Audit
          </button>
        </motion.div>
      )}

      {/* Loading / checking state */}
      {status === 'loading' && (
        <div className="bg-surface-raised border border-border rounded-xl p-10 text-center">
          <Loader2 size={24} className="text-accent animate-spin mx-auto mb-3" />
          <p className="text-sm text-text-muted">Checking for existing results...</p>
        </div>
      )}

      {/* Running state */}
      {status === 'running' && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-raised border border-border rounded-xl p-10 text-center"
        >
          <Loader2 size={32} className="text-accent animate-spin mx-auto mb-4" />
          <p className="text-sm font-semibold text-text mb-1">
            Analyzing {displayPath}...
          </p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Running all 10 audit pillars. This takes about 30 seconds.
          </p>
          <div className="mt-4 h-1.5 max-w-xs mx-auto bg-surface-overlay rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full"
              style={{ animation: 'shimmer 1.5s ease-in-out infinite', width: '33%' }}
            />
          </div>
        </motion.div>
      )}

      {/* Error state */}
      {status === 'error' && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-raised border border-border rounded-xl p-10 text-center"
        >
          <AlertTriangle size={32} className="text-amber-500 mx-auto mb-4" />
          <p className="text-sm font-semibold text-text mb-1">Audit failed</p>
          <p className="text-xs text-text-muted max-w-md mx-auto mb-4">{error}</p>
          <button
            onClick={runAudit}
            className="inline-flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white text-sm font-semibold rounded-xl transition-colors"
          >
            Try Again
          </button>
        </motion.div>
      )}

      {/* Results */}
      {status === 'done' && report && (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard
              label="Health Score"
              value={overallScore}
              icon={Activity}
              color={`text-[${scoreColor(overallScore)}]`}
            />
            <KpiCard
              label="Pillars Analyzed"
              value={pillarScores.length}
              icon={FileSearch}
            />
            <KpiCard
              label="Issues Found"
              value={allFindings.length}
              subtitle={criticalCount > 0 ? `${criticalCount} critical` : undefined}
              icon={AlertTriangle}
              color={criticalCount > 0 ? 'text-severity-critical' : 'text-text-muted'}
            />
            <KpiCard
              label="Passed Checks"
              value={positiveCount}
              icon={CheckCircle2}
              color="text-success"
            />
          </div>

          {/* Pillar score grid */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
              Pillar Scores
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5">
              {pillarScores.map((p) => {
                const PIcon = p.icon;
                return (
                  <div
                    key={p.key}
                    className="bg-surface-raised border border-border rounded-xl p-3.5 flex items-center gap-3"
                  >
                    <div
                      className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: scoreColor(p.score) + '18' }}
                    >
                      <PIcon size={16} style={{ color: scoreColor(p.score) }} />
                    </div>
                    <div className="min-w-0">
                      <div
                        className="text-xl font-extrabold font-heading"
                        style={{ color: scoreColor(p.score) }}
                      >
                        {p.score}
                      </div>
                      <div className="text-[10px] text-text-muted font-semibold leading-tight truncate">
                        {p.label}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>

          {/* Top findings */}
          {allFindings.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
            >
              <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
                Issues Found ({allFindings.length})
              </h2>
              <div className="space-y-2.5">
                {allFindings.map((f, i) => {
                  const SevIcon = severityIcon[f.severity] ?? Info;
                  return (
                    <div
                      key={i}
                      className={`bg-surface-raised border border-border border-l-4 ${severityBorder[f.severity] ?? 'border-l-text-muted'} rounded-xl p-4`}
                    >
                      <div className="flex items-center gap-2 mb-1.5">
                        <SevIcon
                          size={14}
                          className={severityColor[f.severity] ?? 'text-text-muted'}
                        />
                        <span
                          className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded text-white ${severityBg[f.severity] ?? 'bg-text-muted'}`}
                        >
                          {f.severity}
                        </span>
                        {f.pillar && (
                          <span className="text-[10px] text-text-muted font-medium">
                            {PILLAR_LABELS[f.pillar] ?? f.pillar}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-text leading-relaxed">{f.description}</p>
                      {f.recommendation && (
                        <p className="text-xs text-text-secondary mt-1.5">
                          <strong className="text-text">Fix:</strong> {f.recommendation}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </>
      )}
    </div>
  );
}
