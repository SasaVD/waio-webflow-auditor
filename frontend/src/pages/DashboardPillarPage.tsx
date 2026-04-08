import { useMemo } from 'react';
import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  XCircle,
  AlertCircle,
  Info,
  CheckCircle2,
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
  Wrench,
} from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';
import { PILLAR_LABELS } from '../constants/pillarLabels';

/* ─── Pillar slug → backend key mapping ─── */
const SLUG_TO_KEY: Record<string, string> = {
  'search-engine-clarity': 'semantic_html',
  'rich-search-presence': 'structured_data',
  'ai-answer-readiness': 'aeo_content',
  'visual-consistency': 'css_quality',
  'page-speed': 'js_bloat',
  'inclusive-reach': 'accessibility',
  'ai-retrieval-readiness': 'rag_readiness',
  'ai-agent-compatibility': 'agentic_protocols',
  'tracking-analytics': 'data_integrity',
  'content-architecture': 'internal_linking',
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

const PILLAR_DESCRIPTIONS: Record<string, string> = {
  semantic_html:
    'Evaluates how well your HTML communicates page structure to search engines — headings, landmarks, semantic elements, and meta tags.',
  structured_data:
    'Checks JSON-LD and structured data markup that enables rich search results like FAQ snippets, ratings, and breadcrumbs.',
  aeo_content:
    'Measures how effectively your content is formatted for AI engines to extract and cite — readability, Q&A patterns, and freshness signals.',
  css_quality:
    'Analyzes CSS naming consistency, framework adoption, inline styles, and render-blocking stylesheets.',
  js_bloat:
    'Identifies JavaScript performance issues — total script count, third-party bloat, and render-blocking resources.',
  accessibility:
    'Tests WCAG compliance including color contrast, keyboard navigation, ARIA labels, touch targets, and screen reader compatibility.',
  rag_readiness:
    'Assesses how easily AI retrieval systems can extract, chunk, and understand your content — noise ratio, heading pairing, and context independence.',
  agentic_protocols:
    'Checks support for AI agent interaction — llms.txt, robots.txt AI directives, sitemap quality, and API discoverability.',
  data_integrity:
    'Validates consistency of structured data across your site — prices, contact info, brand names, and schema entities.',
  internal_linking:
    'Evaluates your internal link architecture — link count, anchor text quality, self-references, and nofollow usage.',
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

const scoreColor = (score: number): string => {
  if (score >= 90) return '#22C55E';
  if (score >= 75) return '#84CC16';
  if (score >= 55) return '#EAB308';
  if (score >= 35) return '#F97316';
  return '#EF4444';
};

interface Finding {
  severity: string;
  description: string;
  recommendation: string;
  reference?: string;
  why_it_matters?: string;
  credibility_anchor?: string;
}

interface FixEntry {
  finding_pattern: string;
  pillar_key: string;
  title: string;
  steps_markdown: string;
  difficulty: string;
  estimated_time: string;
}

export default function DashboardPillarPage() {
  const { auditId, pillarSlug } = useParams();
  const report = useAuditStore((s) => s.report);

  // Resolve slug → pillar key: try the known mapping first, then fall back to
  // using the slug itself as a key (handles cases like /pillar/js_bloat).
  const pillarKey = pillarSlug
    ? SLUG_TO_KEY[pillarSlug] ??
      (PILLAR_LABELS[pillarSlug] ? pillarSlug : undefined)
    : undefined;
  const label = pillarKey ? PILLAR_LABELS[pillarKey] : pillarSlug;
  const description = pillarKey ? PILLAR_DESCRIPTIONS[pillarKey] : '';
  const PillarIcon = pillarKey ? (pillarIcons[pillarKey] ?? FileCode) : FileCode;

  // Get pillar data from report
  const pillarData = useMemo(() => {
    if (!report?.categories || !pillarKey) return null;
    return report.categories[pillarKey] as Record<string, unknown> | undefined;
  }, [report, pillarKey]);

  const score = (pillarData?.score as number) ?? 0;

  // Extract findings for this pillar
  const findings = useMemo(() => {
    if (!pillarData) return [];
    const checks = (pillarData.checks ?? {}) as Record<string, Record<string, unknown>>;
    const result: Finding[] = [];
    for (const check of Object.values(checks)) {
      if (Array.isArray(check.findings)) {
        for (const f of check.findings) {
          result.push(f as Finding);
        }
      }
    }
    return result.sort(
      (a, b) =>
        ({ critical: 0, high: 1, medium: 2 }[a.severity] ?? 3) -
        ({ critical: 0, high: 1, medium: 2 }[b.severity] ?? 3)
    );
  }, [pillarData]);

  // Extract positive findings for this pillar
  const positiveFindings = useMemo(() => {
    if (!pillarData) return [];
    const checks = (pillarData.checks ?? {}) as Record<string, Record<string, unknown>>;
    const result: string[] = [];
    for (const check of Object.values(checks)) {
      if (typeof check.positive_message === 'string') {
        result.push(check.positive_message);
      }
    }
    return result;
  }, [pillarData]);

  // Check stats
  const checkStats = useMemo(() => {
    if (!pillarData) return { total: 0, passed: 0, failed: 0 };
    const checks = (pillarData.checks ?? {}) as Record<string, Record<string, unknown>>;
    let total = 0, passed = 0, failed = 0;
    for (const check of Object.values(checks)) {
      total++;
      if (check.status === 'pass' || check.status === 'info') passed++;
      else failed++;
    }
    return { total, passed, failed };
  }, [pillarData]);

  // Fixes for this pillar
  const pillarFixes = useMemo(() => {
    if (!report?.webflow_fixes || !pillarKey) return [];
    const allFixes = report.webflow_fixes as Record<string, FixEntry>;
    return Object.values(allFixes).filter((f) => f.pillar_key === pillarKey);
  }, [report, pillarKey]);

  if (!pillarKey || !pillarData) {
    return (
      <div className="p-6 lg:p-8 max-w-4xl mx-auto">
        <Link
          to={`/dashboard/${auditId}`}
          className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text transition-colors mb-4"
        >
          <ArrowLeft size={12} />
          Back to Overview
        </Link>
        <div className="bg-surface-raised border border-border rounded-xl p-8 text-center">
          <Info size={20} className="text-text-muted mx-auto mb-3" />
          <p className="text-sm font-semibold text-text mb-1">Pillar Not Found</p>
          <p className="text-xs text-text-muted">
            No data found for this pillar. Run an audit to generate pillar results.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <Link
          to={`/dashboard/${auditId}`}
          className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text transition-colors mb-4"
        >
          <ArrowLeft size={12} />
          Back to Overview
        </Link>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center flex-shrink-0">
              <PillarIcon size={20} className="text-accent" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl font-bold text-text font-heading truncate">
                {label}
              </h1>
              <p className="text-sm text-text-secondary mt-0.5 line-clamp-2">
                {description}
              </p>
            </div>
          </div>
          <div
            className="w-16 h-16 rounded-xl flex items-center justify-center border-2 flex-shrink-0"
            style={{
              borderColor: scoreColor(score),
              backgroundColor: scoreColor(score) + '15',
            }}
          >
            <span
              className="text-2xl font-extrabold font-heading"
              style={{ color: scoreColor(score) }}
            >
              {score}
            </span>
          </div>
        </div>
      </motion.div>

      {/* Score breakdown */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="grid grid-cols-3 gap-3"
      >
        <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
          <div className="text-2xl font-bold text-text font-heading">{checkStats.total}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider mt-1">Total Checks</div>
        </div>
        <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
          <div className="text-2xl font-bold text-success font-heading">{checkStats.passed}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider mt-1">Passed</div>
        </div>
        <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
          <div className={`text-2xl font-bold font-heading ${checkStats.failed > 0 ? 'text-severity-high' : 'text-success'}`}>
            {checkStats.failed}
          </div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider mt-1">Failed</div>
        </div>
      </motion.div>

      {/* Findings */}
      {findings.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
            Issues Found ({findings.length})
          </h2>
          <div className="space-y-3">
            {findings.map((f, i) => {
              const SevIcon = severityIcon[f.severity] ?? Info;
              return (
                <div
                  key={i}
                  className={`bg-surface-raised border border-border border-l-4 ${severityBorder[f.severity] ?? 'border-l-text-muted'} rounded-xl p-4`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <SevIcon
                      size={14}
                      className={severityColor[f.severity] ?? 'text-text-muted'}
                    />
                    <span
                      className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded text-white ${severityBg[f.severity] ?? 'bg-text-muted'}`}
                    >
                      {f.severity}
                    </span>
                  </div>
                  <p className="text-sm text-text leading-relaxed">{f.description}</p>
                  {f.recommendation && (
                    <p className="text-xs text-text-secondary mt-2">
                      <strong className="text-text">Fix:</strong> {f.recommendation}
                    </p>
                  )}
                  {f.why_it_matters && (
                    <p className="text-xs text-text-muted mt-1.5 italic">{f.why_it_matters}</p>
                  )}
                  {f.reference && (
                    <a
                      href={f.reference}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-accent hover:text-accent-hover mt-1.5 inline-block"
                    >
                      Reference →
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Positive findings */}
      {positiveFindings.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
        >
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
            What's Done Right ({positiveFindings.length})
          </h2>
          <div className="space-y-2">
            {positiveFindings.map((msg, i) => (
              <div
                key={i}
                className="bg-surface-raised border border-border border-l-4 border-l-success rounded-xl p-4 flex items-start gap-3"
              >
                <CheckCircle2 size={14} className="text-success mt-0.5 flex-shrink-0" />
                <p className="text-sm text-text">{msg}</p>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Fix suggestions */}
      {pillarFixes.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
              Fix Suggestions ({pillarFixes.length})
            </h2>
            <Link
              to={`/dashboard/${auditId}/fixes`}
              className="text-xs text-accent hover:text-accent-hover font-semibold"
            >
              View All Fixes →
            </Link>
          </div>
          <div className="space-y-2">
            {pillarFixes.map((fix) => (
              <details
                key={fix.finding_pattern}
                className="group bg-surface-raised border border-border rounded-xl overflow-hidden"
              >
                <summary className="flex items-center justify-between gap-4 px-4 py-3 cursor-pointer select-none list-none hover:bg-surface-overlay/50 transition-colors">
                  <div className="flex items-center gap-2 min-w-0">
                    <Wrench size={13} className="text-accent flex-shrink-0" />
                    <span className="text-sm font-semibold text-text truncate">{fix.title}</span>
                  </div>
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    className="text-text-muted transition-transform group-open:rotate-180 flex-shrink-0"
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </summary>
                <div className="px-4 pb-4 pt-2 border-t border-border text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                  {fix.steps_markdown}
                </div>
              </details>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
