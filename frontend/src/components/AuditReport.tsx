import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, ExternalLink, FileCode, FileJson, Paintbrush, Zap, Accessibility,
  AlertTriangle, AlertCircle, XCircle, Info, CheckCircle2, ChevronDown, ChevronUp,
  BookOpen, Layers, Radio, ShieldCheck, Download, Mail, FileText, Loader2, X,
  Link2, Wrench, Code2, Crown, Lock,
} from 'lucide-react';
import { ExecutiveSummary } from './ExecutiveSummary';
import { LinkGraph } from './LinkGraph';

interface ReportProps {
  report: any;
  onNewAudit: () => void;
  onViewHistory?: () => void;
}

/* ─── Color Helpers ─── */
const scoreColor = (label: string): string => {
  const l = label.toLowerCase();
  if (l === 'excellent') return '#22C55E';
  if (l === 'good') return '#84CC16';
  if (l === 'needs improvement') return '#EAB308';
  if (l === 'poor') return '#F97316';
  return '#EF4444';
};

const scoreColorClass = (label: string): string => {
  const l = label.toLowerCase();
  if (l === 'excellent') return 'text-score-excellent';
  if (l === 'good') return 'text-score-good';
  if (l === 'needs improvement') return 'text-score-needs';
  if (l === 'poor') return 'text-score-poor';
  return 'text-score-critical';
};

const severityStyles: Record<string, { bg: string; border: string; text: string; badge: string; icon: any }> = {
  critical: { bg: 'bg-severity-critical-bg', border: 'border-l-severity-critical', text: 'text-red-300', badge: 'bg-severity-critical', icon: XCircle },
  high:     { bg: 'bg-severity-high-bg', border: 'border-l-severity-high', text: 'text-red-300', badge: 'bg-severity-high', icon: AlertCircle },
  medium:   { bg: 'bg-severity-medium-bg', border: 'border-l-severity-medium', text: 'text-yellow-200', badge: 'bg-severity-medium', icon: Info },
};

const pillarMeta: Record<string, { icon: any; label: string }> = {
  semantic_html: { icon: FileCode, label: 'Semantic HTML' },
  structured_data: { icon: FileJson, label: 'Structured Data' },
  aeo_content: { icon: BookOpen, label: 'AEO Content' },
  css_quality: { icon: Paintbrush, label: 'CSS Quality' },
  js_bloat: { icon: Zap, label: 'JS Performance' },
  accessibility: { icon: Accessibility, label: 'Accessibility' },
  rag_readiness: { icon: Layers, label: 'RAG Readiness' },
  agentic_protocols: { icon: Radio, label: 'Agentic Protocols' },
  data_integrity: { icon: ShieldCheck, label: 'Data Integrity' },
  internal_linking: { icon: Link2, label: 'Internal Linking' },
};

/* ─── Main Report Component ─── */
export const AuditReport: React.FC<ReportProps> = ({ report, onNewAudit, onViewHistory }) => {
  const [pdfLoading, setPdfLoading] = useState(false);
  const [mdLoading, setMdLoading] = useState(false);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [email, setEmail] = useState('');
  const [emailSending, setEmailSending] = useState(false);
  const [emailResult, setEmailResult] = useState<{ success: boolean; message: string } | null>(null);

  if (!report) return null;

  const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';
  const isPremium = report.tier === 'premium';

  const handleDownloadPdf = async () => {
    setPdfLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/export/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `WAIO_Audit_${report.url.replace(/https?:\/\//, '').replace(/\//g, '_').replace(/_$/, '')}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error(err);
    } finally {
      setPdfLoading(false);
    }
  };

  const handleDownloadMd = async () => {
    setMdLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/export/md`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report }),
      });
      if (!res.ok) throw new Error('Markdown generation failed');
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `WAIO_Audit_${report.url.replace(/https?:\/\//, '').replace(/\//g, '_').replace(/_$/, '')}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error(err);
    } finally {
      setMdLoading(false);
    }
  };

  const handleSendEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setEmailSending(true);
    setEmailResult(null);
    try {
      const res = await fetch(`${apiBase}/api/send-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, report }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to send');
      }
      setEmailResult({ success: true, message: `Report sent to ${email}` });
      setEmail('');
    } catch (err: any) {
      setEmailResult({ success: false, message: err.message || 'Failed to send email' });
    } finally {
      setEmailSending(false);
    }
  };

  return (
    <div className="bg-surface min-h-screen">
      {/* Report Header */}
      <div className="bg-surface-raised border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <span className="text-xs font-semibold text-text-muted uppercase tracking-widest">Audit Report</span>
                <span className="text-xs text-text-muted">
                  {new Date(report.audit_timestamp).toLocaleDateString('en-US', {
                    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                  })}
                </span>
              </div>
              <a
                href={report.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xl md:text-2xl font-bold text-text hover:text-accent transition-colors inline-flex items-center gap-2"
              >
                {report.url}
                <ExternalLink size={16} className="text-text-muted" />
              </a>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={handleDownloadPdf}
                disabled={pdfLoading}
                className="flex items-center gap-2 bg-surface-overlay hover:bg-surface-raised border border-border text-text font-semibold px-3.5 py-2.5 rounded-xl transition-all text-sm disabled:opacity-50"
              >
                {pdfLoading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                PDF
              </button>
              <button
                onClick={handleDownloadMd}
                disabled={mdLoading}
                className="flex items-center gap-2 bg-surface-overlay hover:bg-surface-raised border border-border text-text font-semibold px-3.5 py-2.5 rounded-xl transition-all text-sm disabled:opacity-50"
              >
                {mdLoading ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
                Markdown
              </button>
              <button
                onClick={() => { setShowEmailModal(!showEmailModal); setEmailResult(null); }}
                className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white font-semibold px-4 py-2.5 rounded-xl transition-all text-sm"
              >
                <Mail size={14} />
                Email
              </button>
              <button
                onClick={onNewAudit}
                className="flex items-center gap-2 bg-surface-overlay hover:bg-surface-raised border border-border text-text font-semibold px-4 py-2.5 rounded-xl transition-all text-sm"
              >
                <ArrowLeft size={16} />
                New Audit
              </button>
              {onViewHistory && (
                <button
                  onClick={onViewHistory}
                  className="flex items-center gap-2 bg-surface-overlay hover:bg-surface-raised border border-border text-text font-semibold px-4 py-2.5 rounded-xl transition-all text-sm"
                >
                  <Layers size={14} />
                  History
                </button>
              )}
            </div>
          </div>

          {/* Email Modal */}
          <AnimatePresence>
            {showEmailModal && (
              <motion.div
                initial={{ opacity: 0, height: 0, marginTop: 0 }}
                animate={{ opacity: 1, height: 'auto', marginTop: 16 }}
                exit={{ opacity: 0, height: 0, marginTop: 0 }}
                className="overflow-hidden"
              >
                <div className="bg-surface-overlay border border-border rounded-2xl p-5 max-w-xl ml-auto">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Mail size={16} className="text-accent" />
                      <span className="text-sm font-bold text-text">Send Report via Email</span>
                    </div>
                    <button onClick={() => setShowEmailModal(false)} className="text-text-muted hover:text-text">
                      <X size={16} />
                    </button>
                  </div>
                  <form onSubmit={handleSendEmail} className="flex gap-2">
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="Enter email address..."
                      required
                      className="flex-1 bg-surface-raised border border-border rounded-xl px-4 py-2.5 text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent/30 focus:ring-2 focus:ring-accent/10"
                    />
                    <button
                      type="submit"
                      disabled={emailSending || !email}
                      className="bg-accent hover:bg-accent-hover text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-all disabled:opacity-50 flex items-center gap-2"
                    >
                      {emailSending ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />}
                      Send
                    </button>
                  </form>
                  {emailResult && (
                    <motion.div
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`mt-3 px-4 py-2.5 rounded-xl text-sm font-medium ${
                        emailResult.success
                          ? 'bg-severity-positive-bg text-success border border-success/20'
                          : 'bg-severity-critical-bg text-severity-critical border border-severity-critical/20'
                      }`}
                    >
                      {emailResult.message}
                    </motion.div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Dashboard Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Row 1: Score Gauge + Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-4"
        >
          <div className="lg:col-span-4 bg-surface-raised rounded-2xl p-8 flex flex-col items-center justify-center text-center relative overflow-hidden border border-border">
            <div className="absolute inset-0 bg-gradient-to-br from-accent/10 to-transparent pointer-events-none" />
            <div className="relative z-10">
              <ScoreGauge score={report.overall_score} label={report.overall_label} size={160} />
              <div className="mt-4">
                <div className={`text-sm font-bold uppercase tracking-widest ${scoreColorClass(report.overall_label)}`}>
                  {report.overall_label}
                </div>
                <div className="text-xs text-text-muted mt-1">Overall Health Score</div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-8 grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Total Issues" value={report.summary.total_findings} color="text-text" />
            <StatCard label="Critical" value={report.summary.critical} color="text-severity-critical" accent="severity-critical" />
            <StatCard label="High" value={report.summary.high} color="text-severity-high" accent="severity-high" />
            <StatCard label="Medium" value={report.summary.medium} color="text-severity-medium" accent="severity-medium" />
          </div>
        </motion.div>

        {/* Pillar Score Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-4"
        >
          {Object.entries(report.categories).map(([key, cat]: [string, any]) => {
            const meta = pillarMeta[key];
            if (!meta || !cat) return null;
            return <PillarMiniCard key={key} icon={meta.icon} label={meta.label} catVal={cat} />;
          })}
        </motion.div>

        {/* Executive Summary (premium only) */}
        {report.executive_summary && <ExecutiveSummary markdown={report.executive_summary} />}

        {/* Competitive Ranking (premium) */}
        {report.competitive_data?.rankings && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.12 }}
            className="bg-surface-raised border border-border rounded-2xl p-5 mb-4"
          >
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle size={16} className="text-warning" />
              <h3 className="text-sm font-bold text-text">Competitive Ranking</h3>
              <span className="text-xs text-text-muted ml-auto">{report.competitive_data.total_urls} sites compared</span>
            </div>
            <div className="space-y-2">
              {report.competitive_data.rankings.map((entry: any, idx: number) => {
                const isPrimary = entry.url === report.url || entry.url === report.competitive_data.primary_url;
                return (
                  <div key={entry.url} className={`flex items-center gap-3 px-3 py-2 rounded-lg ${isPrimary ? 'bg-accent-muted border border-accent/20' : ''}`}>
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${idx === 0 ? 'bg-warning text-surface' : 'bg-surface-overlay text-text-muted'}`}>
                      {idx + 1}
                    </span>
                    <span className={`text-sm truncate flex-1 ${isPrimary ? 'font-semibold text-text' : 'text-text-secondary'}`}>
                      {entry.url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                      {isPrimary && <span className="ml-2 text-xs text-accent font-semibold">(Your site)</span>}
                    </span>
                    <span className={`text-sm font-bold ${scoreColorClass(entry.overall_label || '')}`}>{entry.overall_score}</span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Link Graph (premium) */}
        {report.audit_id && isPremium && <LinkGraph auditId={report.audit_id} />}

        {/* Action Items + Positive Findings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4"
        >
          <ActionItems priorities={report.summary.top_priorities} />
          <PositiveFindings findings={report.positive_findings} />
        </motion.div>

        {/* Detailed Findings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <DetailedFindings categories={report.categories} webflowFixes={report.webflow_fixes} />
        </motion.div>

        {/* Blurred Premium Preview (free tier only) */}
        {!isPremium && <PremiumPreview />}
      </div>
    </div>
  );
};

/* ─── Score Gauge ─── */
const ScoreGauge: React.FC<{ score: number; label: string; size: number }> = ({ score, label, size }) => {
  const color = scoreColor(label);
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (circumference * score) / 100;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
        <motion.circle
          cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span className="text-5xl font-extrabold text-text" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
          {score}
        </motion.span>
      </div>
    </div>
  );
};

/* ─── Stat Card ─── */
const StatCard: React.FC<{ label: string; value: number; color: string; accent?: string }> = ({ label, value, color, accent }) => (
  <div className={`bg-surface-raised rounded-2xl p-5 border border-border flex flex-col justify-between ${accent ? `border-l-4 border-l-${accent}` : ''}`}>
    <div className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mb-3">{label}</div>
    <div className={`text-3xl font-extrabold ${color}`}>{value}</div>
  </div>
);

/* ─── Pillar Mini Card ─── */
const PillarMiniCard: React.FC<{ icon: any; label: string; catVal: any }> = ({ icon: Icon, label, catVal }) => {
  const score = catVal.score;
  const scoreLabel = catVal.label;

  const findings: any[] = [];
  Object.values(catVal.checks || {}).forEach((chk: any) => {
    if (chk.findings) chk.findings.forEach((f: any) => findings.push(f));
  });

  return (
    <div className="bg-surface-raised rounded-2xl p-5 border border-border flex flex-col justify-between hover:border-accent/20 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="w-8 h-8 rounded-lg bg-surface-overlay flex items-center justify-center">
          <Icon size={15} className="text-text-muted" />
        </div>
        <div className="text-right">
          <div className="flex items-baseline justify-end gap-1">
            <span className={`text-2xl font-extrabold ${scoreColorClass(scoreLabel)}`}>{score}</span>
            <span className="text-[10px] text-text-muted font-bold">/100</span>
          </div>
          {findings.length > 0 && (
            <div className="text-[10px] font-semibold text-text-muted mt-1">{findings.length} issues</div>
          )}
        </div>
      </div>
      <div>
        <div className="text-xs font-semibold text-text">{label}</div>
        <div className={`text-[10px] font-bold uppercase tracking-wider ${scoreColorClass(scoreLabel)}`}>{scoreLabel}</div>
      </div>
    </div>
  );
};

/* ─── Action Items ─── */
const ActionItems: React.FC<{ priorities: string[] }> = ({ priorities }) => {
  if (!priorities?.length) return null;
  return (
    <div className="bg-surface-raised rounded-2xl border border-border p-6">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="w-8 h-8 rounded-lg bg-severity-high-bg flex items-center justify-center">
          <AlertTriangle size={15} className="text-severity-high" />
        </div>
        <h3 className="text-base font-bold text-text">Top Priorities</h3>
      </div>
      <div className="space-y-2.5">
        {priorities.map((p, i) => (
          <div key={i} className="flex gap-3 items-start">
            <span className="w-5 h-5 rounded-md bg-severity-high-bg text-severity-high text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
              {i + 1}
            </span>
            <p className="text-sm text-text-secondary leading-relaxed">{p}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

/* ─── Positive Findings ─── */
const PositiveFindings: React.FC<{ findings: any[] }> = ({ findings }) => {
  if (!findings?.length) return null;
  return (
    <div className="bg-surface-raised rounded-2xl border border-border p-6">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="w-8 h-8 rounded-lg bg-severity-positive-bg flex items-center justify-center">
          <CheckCircle2 size={15} className="text-success" />
        </div>
        <h3 className="text-base font-bold text-text">What's Working Well</h3>
      </div>
      <div className="space-y-2.5">
        {findings.slice(0, 8).map((f, i) => {
          const text = typeof f === 'string' ? f : f.text;
          const anchor = typeof f === 'object' ? f.credibility_anchor : null;
          return (
            <div key={i} className="flex flex-col gap-1">
              <div className="flex gap-3 items-start">
                <CheckCircle2 size={14} className="text-success flex-shrink-0 mt-1" />
                <p className="text-sm text-text-secondary leading-relaxed">{text}</p>
              </div>
              {anchor && (
                <div className="ml-7 mt-1 border-l-2 border-accent/30 bg-accent-muted rounded-r-lg px-3 py-1.5">
                  <p className="text-[11px] italic text-text-muted leading-relaxed">{anchor}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ─── Detailed Findings (Sitebulb-style hint cards) ─── */
const escapeHtml = (str: string): string =>
  str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const DetailedFindings: React.FC<{ categories: any; webflowFixes?: Record<string, any> }> = ({ categories, webflowFixes }) => {
  const [expandedFix, setExpandedFix] = useState<string | null>(null);
  const [expandedElements, setExpandedElements] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<Set<string>>(new Set(['critical', 'high', 'medium']));

  // Flatten all findings with category metadata
  const allFindings = useMemo(() => {
    const flat: any[] = [];
    Object.entries(categories).forEach(([catKey, catVal]: [string, any]) => {
      Object.entries(catVal.checks || {}).forEach(([checkName, chk]: [string, any]) => {
        if (chk.findings) {
          chk.findings.forEach((f: any) =>
            flat.push({ ...f, _check_name: checkName, _catKey: catKey })
          );
        }
      });
    });
    return flat.sort(
      (a, b) =>
        ({ critical: 0, high: 1, medium: 2 }[a.severity as string] ?? 3) -
        ({ critical: 0, high: 1, medium: 2 }[b.severity as string] ?? 3)
    );
  }, [categories]);

  const filteredFindings = useMemo(
    () => allFindings.filter((f) => severityFilter.has(f.severity)),
    [allFindings, severityFilter]
  );

  const toggleSeverity = (sev: string) => {
    setSeverityFilter((prev) => {
      const next = new Set(prev);
      if (next.has(sev)) next.delete(sev);
      else next.add(sev);
      return next;
    });
  };

  const critCount = allFindings.filter((f) => f.severity === 'critical').length;
  const highCount = allFindings.filter((f) => f.severity === 'high').length;
  const medCount = allFindings.filter((f) => f.severity === 'medium').length;

  if (allFindings.length === 0) {
    return (
      <div className="bg-surface-raised rounded-2xl border border-border p-12 text-center">
        <CheckCircle2 size={48} className="mx-auto mb-4 text-success opacity-40" />
        <p className="text-lg font-bold text-text">No issues found across all pillars.</p>
        <p className="text-sm text-text-muted mt-1">Your site is in excellent shape.</p>
      </div>
    );
  }

  // Group filtered findings by category
  const grouped: Record<string, any[]> = {};
  filteredFindings.forEach((f) => {
    if (!grouped[f._catKey]) grouped[f._catKey] = [];
    grouped[f._catKey].push(f);
  });

  return (
    <div className="space-y-4">
      {/* Header + Filter Chips */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <h3 className="text-base font-bold text-text">
          Detailed Findings
          <span className="ml-2 text-xs font-bold text-text-muted bg-surface-overlay px-3 py-1 rounded-full">
            {filteredFindings.length} of {allFindings.length}
          </span>
        </h3>
        <div className="flex gap-2">
          {[
            { key: 'critical', label: 'Critical', count: critCount, color: 'severity-critical' },
            { key: 'high', label: 'High', count: highCount, color: 'severity-high' },
            { key: 'medium', label: 'Medium', count: medCount, color: 'severity-medium' },
          ].map((s) => (
            <button
              key={s.key}
              onClick={() => toggleSeverity(s.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                severityFilter.has(s.key)
                  ? `bg-${s.color}-bg border-${s.color}/30 text-${s.color}`
                  : 'bg-surface-raised border-border text-text-muted'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${severityFilter.has(s.key) ? `bg-${s.color}` : 'bg-text-muted'}`} />
              {s.label} ({s.count})
            </button>
          ))}
        </div>
      </div>

      {/* Findings grouped by category */}
      {Object.entries(grouped).map(([catKey, findings]) => {
        const meta = pillarMeta[catKey];
        if (!meta) return null;

        return (
          <div key={catKey} className="space-y-3">
            <div className="flex items-center gap-2 pt-2">
              <meta.icon size={14} className="text-text-muted" />
              <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">{meta.label}</span>
              <div className="flex-1 h-px bg-border" />
            </div>

            {findings.map((f, i) => {
              const sev = severityStyles[f.severity] || severityStyles.medium;
              const fixId = `${catKey}-${f._check_name}-${i}`;
              const elId = `${catKey}-elements-${i}`;

              return (
                <div key={i} className={`${sev.bg} border-l-4 ${sev.border} rounded-lg p-4`}>
                  <div className="flex items-start gap-3">
                    {/* Severity Badge */}
                    <span className={`${sev.badge} text-white text-[10px] font-bold uppercase px-2 py-0.5 rounded flex-shrink-0 mt-0.5`}>
                      {f.severity}
                    </span>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-text mb-2">{f.description}</p>

                      {/* Recommendation */}
                      <div className="bg-surface-overlay rounded-lg p-3 mt-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-accent">Recommendation</span>
                        <p className="text-xs text-text-secondary mt-1 leading-relaxed">{f.recommendation}</p>
                      </div>

                      {/* Reference */}
                      {f.reference && (
                        <a
                          href={f.reference}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-text-muted hover:text-accent mt-2 transition-colors"
                        >
                          Reference <ExternalLink size={10} />
                        </a>
                      )}

                      {/* Credibility Anchor */}
                      {f.credibility_anchor && (
                        <div className="mt-3 border-l-[3px] border-accent bg-accent-muted rounded-r-lg px-3 py-2">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-accent block mb-0.5">Why this matters</span>
                          <p className="text-[11px] italic text-text-secondary leading-relaxed">{f.credibility_anchor}</p>
                        </div>
                      )}

                      {/* Webflow Fix */}
                      {webflowFixes && f._check_name && webflowFixes[f._check_name] && (() => {
                        const fix = webflowFixes[f._check_name];
                        const isFixOpen = expandedFix === fixId;
                        return (
                          <div className="mt-3">
                            <button
                              onClick={() => setExpandedFix(isFixOpen ? null : fixId)}
                              className="inline-flex items-center gap-1.5 text-[11px] font-bold text-accent hover:text-accent-hover transition-colors"
                            >
                              <Wrench size={12} />
                              {isFixOpen ? 'Hide' : 'How to Fix in Webflow'}
                              <span className="text-[10px] font-normal text-text-muted ml-1">
                                {fix.difficulty} &middot; {fix.estimated_time}
                              </span>
                            </button>
                            <AnimatePresence>
                              {isFixOpen && (
                                <motion.div
                                  initial={{ opacity: 0, height: 0 }}
                                  animate={{ opacity: 1, height: 'auto' }}
                                  exit={{ opacity: 0, height: 0 }}
                                  className="overflow-hidden"
                                >
                                  <div className="mt-2 bg-surface-overlay rounded-lg border border-border p-4">
                                    <h4 className="text-xs font-bold text-text mb-2">{fix.title}</h4>
                                    <div className="text-xs text-text-secondary leading-relaxed whitespace-pre-line">{fix.steps_markdown}</div>
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        );
                      })()}

                      {/* Affected Elements */}
                      {f.elements?.length > 0 && (() => {
                        const isElOpen = expandedElements === elId;
                        return (
                          <div className="mt-3">
                            <button
                              onClick={() => setExpandedElements(isElOpen ? null : elId)}
                              className="inline-flex items-center gap-1.5 text-[11px] font-bold text-text-muted hover:text-text transition-colors"
                            >
                              <Code2 size={12} />
                              {isElOpen ? 'Hide affected elements' : `Show affected elements (${f.elements.length})`}
                            </button>
                            <AnimatePresence>
                              {isElOpen && (
                                <motion.div
                                  initial={{ opacity: 0, height: 0 }}
                                  animate={{ opacity: 1, height: 'auto' }}
                                  exit={{ opacity: 0, height: 0 }}
                                  className="overflow-hidden"
                                >
                                  <div className="mt-2 space-y-2">
                                    {f.elements.map((el: { selector: string; html_snippet: string; location: string }, elIdx: number) => (
                                      <div key={elIdx} className="bg-surface-overlay rounded-lg border border-border p-3">
                                        <span className="text-[10px] font-medium text-text-muted block mb-1.5">{el.location}</span>
                                        <div className="text-[11px] font-mono text-accent mb-1.5 break-all">{el.selector}</div>
                                        <pre className="text-[11px] font-mono text-text-secondary bg-surface rounded-md px-3 py-2 overflow-x-auto whitespace-pre-wrap break-all leading-relaxed border border-border">
                                          {escapeHtml(el.html_snippet)}
                                        </pre>
                                      </div>
                                    ))}
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};

/* ─── Blurred Premium Preview ─── */
const PremiumPreview: React.FC = () => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5, delay: 0.4 }}
    className="mt-8 relative rounded-2xl overflow-hidden border border-border"
  >
    {/* Blurred mock content */}
    <div className="blur-sm pointer-events-none select-none p-8 bg-surface-raised space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-surface-overlay" />
        <div>
          <div className="h-4 w-48 bg-surface-overlay rounded" />
          <div className="h-3 w-32 bg-surface-overlay rounded mt-2" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((n) => (
          <div key={n} className="h-24 bg-surface-overlay rounded-xl" />
        ))}
      </div>
      <div className="space-y-3">
        {[1, 2, 3, 4].map((n) => (
          <div key={n} className="h-16 bg-surface-overlay rounded-lg" />
        ))}
      </div>
    </div>

    {/* Gradient overlay + CTA */}
    <div className="absolute inset-0 bg-gradient-to-t from-surface via-surface/80 to-surface/40 flex items-center justify-center">
      <div className="text-center px-6">
        <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-accent/10 flex items-center justify-center">
          <Crown size={28} className="text-accent" />
        </div>
        <p className="text-lg font-bold text-text mb-1 font-heading">Unlock Premium Insights</p>
        <p className="text-text-muted text-sm mb-6 max-w-md mx-auto">
          Executive summary, Webflow fix instructions, link graph visualization, WDF*IDF content gaps, and competitor benchmarking.
        </p>
        <div className="flex items-center justify-center gap-3">
          <button className="bg-accent hover:bg-accent-hover text-white px-6 py-2.5 rounded-xl font-semibold transition-all hover:shadow-glow-accent flex items-center gap-2">
            <Lock size={14} />
            Upgrade to Premium
          </button>
        </div>
      </div>
    </div>
  </motion.div>
);
