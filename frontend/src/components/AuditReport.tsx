import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, ExternalLink, FileCode, FileJson, Paintbrush, Zap, Accessibility,
  AlertTriangle, AlertCircle, XCircle, Info, CheckCircle2, ChevronDown, ChevronUp,
  BookOpen, Layers, Radio, ShieldCheck, Download, Mail, FileText, Loader2, X, Link2
} from 'lucide-react';

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

const severityConfig: Record<string, { bg: string; text: string; border: string; icon: any }> = {
  critical: { bg: 'bg-red-50', text: 'text-red-600', border: 'border-red-100', icon: XCircle },
  high: { bg: 'bg-orange-50', text: 'text-orange-600', border: 'border-orange-100', icon: AlertCircle },
  medium: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-100', icon: Info },
};

const pillarMeta: Record<string, { icon: any; label: string }> = {
  semantic_html: { icon: FileCode, label: 'Semantic HTML' },
  structured_data: { icon: FileJson, label: 'Structured Data' },
  aeo_content: { icon: BookOpen, label: 'AEO Content' },
  css_quality: { icon: Paintbrush, label: 'CSS Quality' },
  js_bloat: { icon: Zap, label: 'JS Bloat' },
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
  const [emailResult, setEmailResult] = useState<{success: boolean; message: string} | null>(null);

  if (!report) return null;

  const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

  const handleDownloadPdf = async () => {
    setPdfLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/export/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report })
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
        body: JSON.stringify({ report })
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
        body: JSON.stringify({ email, report })
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
    <div className="bg-surface-secondary min-h-screen">
      {/* Report Header */}
      <div className="bg-white border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <span className="text-xs font-semibold text-text-muted uppercase tracking-widest">Audit Report</span>
                <span className="text-xs text-text-muted">
                  {new Date(report.audit_timestamp).toLocaleDateString('en-US', {
                    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                  })}
                </span>
              </div>
              <a
                href={report.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xl md:text-2xl font-bold text-text-primary hover:text-primary transition-colors inline-flex items-center gap-2"
              >
                {report.url}
                <ExternalLink size={16} className="text-text-muted" />
              </a>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={handleDownloadPdf}
                disabled={pdfLoading}
                className="flex items-center gap-2 bg-white hover:bg-surface-secondary border border-border text-text-primary font-semibold px-3.5 py-2.5 rounded-xl transition-all text-sm disabled:opacity-50"
              >
                {pdfLoading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                PDF
              </button>
              <button
                onClick={handleDownloadMd}
                disabled={mdLoading}
                className="flex items-center gap-2 bg-white hover:bg-surface-secondary border border-border text-text-primary font-semibold px-3.5 py-2.5 rounded-xl transition-all text-sm disabled:opacity-50"
              >
                {mdLoading ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
                Markdown
              </button>
              <button
                onClick={() => { setShowEmailModal(!showEmailModal); setEmailResult(null); }}
                className="flex items-center gap-2 bg-primary hover:bg-primary-hover text-white font-semibold px-4 py-2.5 rounded-xl transition-all text-sm"
              >
                <Mail size={14} />
                Email Report
              </button>
              <button
                onClick={onNewAudit}
                className="flex items-center gap-2 bg-white hover:bg-surface-secondary border border-border text-text-primary font-semibold px-4 py-2.5 rounded-xl transition-all text-sm"
              >
                <ArrowLeft size={16} />
                New Audit
              </button>
              {onViewHistory && (
                <button
                  onClick={onViewHistory}
                  className="flex items-center gap-2 bg-surface-secondary hover:bg-gray-200 border border-border text-text-primary font-semibold px-4 py-2.5 rounded-xl transition-all text-sm"
                >
                  <Layers size={14} />
                  View History
                </button>
              )}
            </div>
          </div>

          {/* Email Modal (inline dropdown) */}
          <AnimatePresence>
            {showEmailModal && (
              <motion.div
                initial={{ opacity: 0, height: 0, marginTop: 0 }}
                animate={{ opacity: 1, height: 'auto', marginTop: 16 }}
                exit={{ opacity: 0, height: 0, marginTop: 0 }}
                className="overflow-hidden"
              >
                <div className="bg-surface-secondary border border-border rounded-2xl p-5 max-w-xl ml-auto">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Mail size={16} className="text-primary" />
                      <span className="text-sm font-bold text-text-primary">Send Report via Email</span>
                    </div>
                    <button onClick={() => setShowEmailModal(false)} className="text-text-muted hover:text-text-primary">
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
                      className="flex-1 bg-white border border-border-light rounded-xl px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary/30 focus:ring-2 focus:ring-primary/10"
                    />
                    <button
                      type="submit"
                      disabled={emailSending || !email}
                      className="bg-primary hover:bg-primary-hover text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-all disabled:opacity-50 flex items-center gap-2"
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
                          ? 'bg-accent-light text-accent border border-accent/10'
                          : 'bg-severity-critical-bg text-severity-critical border border-severity-critical/10'
                      }`}
                    >
                      {emailResult.success ? '✓' : '✗'} {emailResult.message}
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
        {/* Row 1: Overall Score + Summary Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-4"
        >
          {/* Overall Score - Dark Card */}
          <div className="lg:col-span-4 bg-surface-dark rounded-2xl p-8 flex flex-col items-center justify-center text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent pointer-events-none" />
            <div className="relative z-10">
              <ScoreGauge score={report.overall_score} label={report.overall_label} size={160} />
              <div className="mt-4">
                <div className={`text-sm font-bold uppercase tracking-widest ${scoreColorClass(report.overall_label)}`}>
                  {report.overall_label}
                </div>
                <div className="text-xs text-text-on-dark-muted mt-1">Overall Health Score</div>
              </div>
            </div>
          </div>

          {/* Summary Stats */}
          <div className="lg:col-span-8 grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              label="Total Issues"
              value={report.summary.total_findings}
              color="text-text-primary"
              bgColor="bg-white"
            />
            <StatCard
              label="Critical"
              value={report.summary.critical}
              color="text-severity-critical"
              bgColor="bg-severity-critical-bg"
              borderColor="border-severity-critical/10"
            />
            <StatCard
              label="High"
              value={report.summary.high}
              color="text-severity-high"
              bgColor="bg-severity-high-bg"
              borderColor="border-severity-high/10"
            />
            <StatCard
              label="Medium"
              value={report.summary.medium}
              color="text-severity-medium"
              bgColor="bg-severity-medium-bg"
              borderColor="border-severity-medium/10"
            />
          </div>
        </motion.div>

        {/* Row 1b: Pillar Score Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-4"
        >
            {Object.entries(report.categories).map(([key, cat]: [string, any]) => {
              const meta = pillarMeta[key];
              if (!meta || !cat) return null;
              return (
                <PillarMiniCard
                  key={key}
                  icon={meta.icon}
                  label={meta.label}
                  catVal={cat}
                />
              );
            })}
        </motion.div>

        {/* Row 2: Action Items + Positive Findings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4"
        >
          <ActionItems priorities={report.summary.top_priorities} />
          <PositiveFindings findings={report.positive_findings} />
        </motion.div>

        {/* Row 3: Detailed Findings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <DetailedFindings categories={report.categories} />
        </motion.div>
      </div>
    </div>
  );
};

/* ─── Score Gauge (SVG) ─── */
const ScoreGauge: React.FC<{ score: number; label: string; size: number }> = ({ score, label, size }) => {
  const color = scoreColor(label);
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (circumference * score) / 100;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="10"
        />
        {/* Score arc */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="text-5xl font-extrabold text-text-on-dark"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          {score}
        </motion.span>
      </div>
    </div>
  );
};

/* ─── Stat Card ─── */
const StatCard: React.FC<{
  label: string;
  value: number;
  color: string;
  bgColor: string;
  borderColor?: string;
}> = ({ label, value, color, bgColor, borderColor }) => (
  <div className={`${bgColor} rounded-2xl p-5 border ${borderColor || 'border-border-light'} flex flex-col justify-between`}>
    <div className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mb-3">{label}</div>
    <div className={`text-3xl font-extrabold ${color}`}>{value}</div>
  </div>
);

/* ─── Pillar Mini Card ─── */
const PillarMiniCard: React.FC<{
  icon: any;
  label: string;
  catVal: any;
}> = ({ icon: Icon, label, catVal }) => {
  const score = catVal.score;
  const scoreLabel = catVal.label;
  
  const findings: any[] = [];
  Object.values(catVal.checks || {}).forEach((chk: any) => {
    if (chk.findings) {
      chk.findings.forEach((f: any) => findings.push(f));
    }
  });
  
  const totalIssues = findings.length;

  return (
    <div className="bg-white rounded-2xl p-5 border border-border-light flex flex-col justify-between hover:border-primary/10 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="w-8 h-8 rounded-lg bg-surface-secondary flex items-center justify-center">
          <Icon size={15} className="text-text-muted" />
        </div>
        <div className="text-right">
          <div className="flex items-baseline justify-end gap-1">
             <span className={`text-2xl font-extrabold ${scoreColorClass(scoreLabel)}`}>{score}</span>
             <span className="text-[10px] text-text-muted font-bold">/100</span>
          </div>
          {totalIssues > 0 && (
             <div className="text-[10px] font-semibold text-text-muted mt-1">
               {totalIssues} issues
             </div>
          )}
        </div>
      </div>
      <div>
        <div className="text-xs font-semibold text-text-primary">{label}</div>
        <div className={`text-[10px] font-bold uppercase tracking-wider ${scoreColorClass(scoreLabel)}`}>
          {scoreLabel}
        </div>
      </div>
    </div>
  );
};

/* ─── Action Items ─── */
const ActionItems: React.FC<{ priorities: string[] }> = ({ priorities }) => {
  if (!priorities?.length) return null;
  return (
    <div className="bg-white rounded-2xl border border-border-light p-6">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="w-8 h-8 rounded-lg bg-severity-high-bg flex items-center justify-center">
          <AlertTriangle size={15} className="text-severity-high" />
        </div>
        <h3 className="text-base font-bold text-text-primary">Top Priorities</h3>
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
    <div className="bg-white rounded-2xl border border-border-light p-6">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="w-8 h-8 rounded-lg bg-accent-light flex items-center justify-center">
          <CheckCircle2 size={15} className="text-accent" />
        </div>
        <h3 className="text-base font-bold text-text-primary">What's Working Well</h3>
      </div>
      <div className="space-y-2.5">
        {findings.slice(0, 8).map((f, i) => {
          const text = typeof f === 'string' ? f : f.text;
          const anchor = typeof f === 'object' ? f.credibility_anchor : null;
          return (
            <div key={i} className="flex flex-col gap-1">
              <div className="flex gap-3 items-start">
                <CheckCircle2 size={14} className="text-accent flex-shrink-0 mt-1" />
                <p className="text-sm text-text-secondary leading-relaxed">{text}</p>
              </div>
              {anchor && (
                <div className="ml-7 mt-1 border-l-2 border-primary/30 bg-[#F0F1FF] rounded-r-lg px-3 py-1.5">
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

/* ─── Detailed Findings ─── */
const DetailedFindings: React.FC<{ categories: any }> = ({ categories }) => {
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  // Group findings by category
  const categoryFindings: Record<string, any[]> = {};
  Object.entries(categories).forEach(([catKey, catVal]: [string, any]) => {
    const findings: any[] = [];
    Object.values(catVal.checks || {}).forEach((chk: any) => {
      if (chk.findings) {
        chk.findings.forEach((f: any) => findings.push(f));
      }
    });
    if (findings.length > 0) {
      categoryFindings[catKey] = findings.sort((a, _b) =>
        ({ critical: 0, high: 1, medium: 2 }[a.severity as string] ?? 3) -
        ({ critical: 0, high: 1, medium: 2 }[_b.severity as string] ?? 3)
      );
    }
  });

  const totalFindings = Object.values(categoryFindings).reduce((sum, f) => sum + f.length, 0);

  if (totalFindings === 0) {
    return (
      <div className="bg-white rounded-2xl border border-border-light p-12 text-center">
        <CheckCircle2 size={48} className="mx-auto mb-4 text-accent opacity-40" />
        <p className="text-lg font-bold text-text-primary">No issues found across all pillars.</p>
        <p className="text-sm text-text-muted mt-1">Your site is in excellent shape.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-border-light overflow-hidden">
      <div className="px-6 py-5 border-b border-border-light flex items-center justify-between">
        <h3 className="text-base font-bold text-text-primary">Detailed Findings</h3>
        <span className="text-xs font-bold text-text-muted bg-surface-secondary px-3 py-1 rounded-full">
          {totalFindings} issues
        </span>
      </div>

      {Object.entries(categoryFindings).map(([catKey, findings]) => {
        const meta = pillarMeta[catKey];
        if (!meta) return null;
        const isExpanded = expandedCategory === catKey;
        const critCount = findings.filter(f => f.severity === 'critical').length;
        const highCount = findings.filter(f => f.severity === 'high').length;
        const medCount = findings.filter(f => f.severity === 'medium').length;

        return (
          <div key={catKey} className="border-b border-border-light last:border-b-0">
            {/* Category Header */}
            <button
              onClick={() => setExpandedCategory(isExpanded ? null : catKey)}
              className="w-full px-6 py-4 flex items-center justify-between hover:bg-surface-secondary/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <meta.icon size={16} className="text-text-muted" />
                <span className="text-sm font-semibold text-text-primary">{meta.label}</span>
                <div className="flex items-center gap-1.5 ml-2">
                  {critCount > 0 && (
                    <span className="text-[10px] font-bold bg-red-50 text-red-600 px-1.5 py-0.5 rounded">
                      {critCount} critical
                    </span>
                  )}
                  {highCount > 0 && (
                    <span className="text-[10px] font-bold bg-orange-50 text-orange-600 px-1.5 py-0.5 rounded">
                      {highCount} high
                    </span>
                  )}
                  {medCount > 0 && (
                    <span className="text-[10px] font-bold bg-yellow-50 text-yellow-700 px-1.5 py-0.5 rounded">
                      {medCount} medium
                    </span>
                  )}
                </div>
              </div>
              {isExpanded ? (
                <ChevronUp size={16} className="text-text-muted" />
              ) : (
                <ChevronDown size={16} className="text-text-muted" />
              )}
            </button>

            {/* Expanded Findings */}
            {isExpanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="px-6 pb-4"
              >
                <div className="space-y-3">
                  {findings.map((f, i) => {
                    const sev = severityConfig[f.severity] || severityConfig.medium;
                    const SevIcon = sev.icon;
                    return (
                      <div
                        key={i}
                        className={`${sev.bg} border ${sev.border} rounded-xl p-4`}
                      >
                        <div className="flex items-start gap-3">
                          <SevIcon size={16} className={`${sev.text} flex-shrink-0 mt-0.5`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-[10px] font-bold uppercase tracking-wider ${sev.text}`}>
                                {f.severity}
                              </span>
                            </div>
                            <p className="text-sm font-medium text-text-primary mb-2">{f.description}</p>
                            <div className="bg-white/60 rounded-lg p-3 mt-2">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-primary">Recommendation</span>
                              <p className="text-xs text-text-secondary mt-1 leading-relaxed">{f.recommendation}</p>
                            </div>
                            {f.reference && (
                              <a
                                href={f.reference}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-[11px] font-semibold text-text-muted hover:text-primary mt-2 transition-colors"
                              >
                                Reference <ExternalLink size={10} />
                              </a>
                            )}
                            {f.credibility_anchor && (
                              <div className="mt-3 border-l-[3px] border-primary bg-[#F0F1FF] rounded-r-lg px-3 py-2">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-primary block mb-0.5">Why this matters</span>
                                <p className="text-[11px] italic text-text-secondary leading-relaxed">{f.credibility_anchor}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </div>
        );
      })}
    </div>
  );
};
