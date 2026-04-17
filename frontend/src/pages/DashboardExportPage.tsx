import { useState } from 'react';
import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Download,
  FileText,
  Table,
  FileCode2,
  Loader2,
  CheckCircle2,
  Network,
  Crown,
} from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';
import { generateExcel } from '../utils/generateExcel';
import { downloadMarkdown } from '../utils/generateMarkdown';

export default function DashboardExportPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfDone, setPdfDone] = useState(false);
  const [excelDone, setExcelDone] = useState(false);
  const [mdDone, setMdDone] = useState(false);
  const [linkXlsxLoading, setLinkXlsxLoading] = useState(false);
  const [linkXlsxDone, setLinkXlsxDone] = useState(false);
  const [linkCsvLoading, setLinkCsvLoading] = useState(false);
  const [linkCsvDone, setLinkCsvDone] = useState(false);
  const [brandedPdfLoading, setBrandedPdfLoading] = useState(false);
  const [brandedPdfDone, setBrandedPdfDone] = useState(false);
  const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

  const domain = report?.url
    ?.replace(/https?:\/\//, '')
    .replace(/\//g, '_')
    .replace(/_$/, '');
  const date = new Date().toISOString().slice(0, 10);

  const handlePdf = async () => {
    if (!report) return;
    setPdfLoading(true);
    setPdfDone(false);
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
      a.download = `WAIO-Intelligence-Report-${domain}-${date}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
      setPdfDone(true);
    } catch (err) {
      console.error('PDF export failed:', err);
    } finally {
      setPdfLoading(false);
    }
  };

  const handleBrandedPdf = async () => {
    if (!auditId) return;
    setBrandedPdfLoading(true);
    setBrandedPdfDone(false);
    try {
      const res = await fetch(`${apiBase}/api/audit/${auditId}/export/pdf`);
      if (!res.ok) throw new Error('Branded PDF generation failed');
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `WAIO-Intelligence-Report-${domain}-${date}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
      setBrandedPdfDone(true);
    } catch (err) {
      console.error('Branded PDF export failed:', err);
    } finally {
      setBrandedPdfLoading(false);
    }
  };

  const handleExcel = () => {
    if (!report) return;
    generateExcel(report);
    setExcelDone(true);
  };

  const handleMarkdown = () => {
    if (!report) return;
    downloadMarkdown(report);
    setMdDone(true);
  };

  const hasLinkData = !!(report?.link_analysis?.graph?.nodes?.length);

  const handleLinkExport = async (fmt: 'xlsx' | 'csv') => {
    if (!auditId) return;
    const setLoading = fmt === 'xlsx' ? setLinkXlsxLoading : setLinkCsvLoading;
    const setDone = fmt === 'xlsx' ? setLinkXlsxDone : setLinkCsvDone;
    setLoading(true);
    setDone(false);
    try {
      const res = await fetch(`${apiBase}/api/export/link-data/${auditId}?format=${fmt}`);
      if (!res.ok) throw new Error('Link data export failed');
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = fmt === 'xlsx'
        ? `WAIO-Link-Data-${domain}-${date}.xlsx`
        : `WAIO-Link-Data-${domain}-${date}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
      setDone(true);
    } catch (err) {
      console.error('Link data export failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const formats = [
    {
      id: 'pdf',
      icon: FileText,
      label: 'PDF Report',
      description:
        'Branded PDF with health score, pillar breakdown, all findings, and executive summary. Ideal for sharing with stakeholders.',
      color: 'text-severity-high',
      colorBg: 'bg-severity-high/10',
      filename: `WAIO-Intelligence-Report-${domain}-${date}.pdf`,
      handler: handlePdf,
      loading: pdfLoading,
      done: pdfDone,
    },
    {
      id: 'excel',
      icon: Table,
      label: 'Excel Spreadsheet',
      description:
        'Structured spreadsheet with summary, findings by pillar, page metrics, and competitor data. Great for filtering and analysis.',
      color: 'text-success',
      colorBg: 'bg-success/10',
      filename: `WAIO-Report-${domain}-${date}.xlsx`,
      handler: handleExcel,
      loading: false,
      done: excelDone,
    },
    {
      id: 'markdown',
      icon: FileCode2,
      label: 'Markdown',
      description:
        'Clean markdown document with all findings, recommendations, and scores. Suitable for documentation or CMS import.',
      color: 'text-secondary-blue',
      colorBg: 'bg-secondary-blue/10',
      filename: `WAIO-Report-${domain}-${date}.md`,
      handler: handleMarkdown,
      loading: false,
      done: mdDone,
    },
  ];

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
            <Download size={20} className="text-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text font-heading">
              Export Report
            </h1>
            <p className="text-sm text-text-secondary mt-0.5">
              Download your audit results in multiple formats.
            </p>
          </div>
        </div>
      </motion.div>

      {/* Report Preview Summary */}
      {report && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="bg-surface-raised border border-border rounded-xl p-5 flex items-center justify-between gap-4"
        >
          <div>
            <div className="text-sm font-semibold text-text truncate max-w-[400px]">
              {report.url}
            </div>
            <div className="text-xs text-text-muted mt-0.5">
              Score: {report.overall_score}/100 &middot;{' '}
              {report.summary?.total_findings ?? 0} findings &middot;{' '}
              {report.tier === 'premium' ? 'Premium' : 'Free'} tier
            </div>
          </div>
          <div
            className="text-2xl font-extrabold font-heading"
            style={{
              color:
                (report.overall_score ?? 0) >= 75
                  ? '#22C55E'
                  : (report.overall_score ?? 0) >= 55
                    ? '#EAB308'
                    : '#EF4444',
            }}
          >
            {report.overall_score}
          </div>
        </motion.div>
      )}

      {/* Branded Intelligence Report — hero card */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.08 }}
        className="bg-accent/5 border border-accent/30 rounded-xl p-5 flex items-center justify-between gap-4 shadow-glow-accent"
      >
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 bg-accent/15">
            <Crown size={18} className="text-accent" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <div className="text-sm font-semibold text-text">
                Branded Intelligence Report (PDF)
              </div>
              <span className="text-[10px] font-bold tracking-wider uppercase bg-accent/20 text-accent px-2 py-0.5 rounded-full">
                Premium
              </span>
            </div>
            <div className="text-xs text-text-muted mt-1 max-w-xl leading-relaxed">
              Premium 10-section PDF with executive summary, pillar scorecard grouped by
              weight, link intelligence, AI visibility across 5 platforms, content optimizer
              results, and priority actions. Designed for stakeholder delivery.
            </div>
            <div className="text-[10px] text-text-muted mt-1.5 font-mono">
              WAIO-Intelligence-Report-{domain}-{date}.pdf
            </div>
          </div>
        </div>
        <button
          onClick={handleBrandedPdf}
          disabled={!auditId || brandedPdfLoading}
          className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white font-semibold px-4 py-2.5 rounded-xl transition-all text-sm disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
        >
          {brandedPdfLoading ? (
            <Loader2 size={14} className="animate-spin" />
          ) : brandedPdfDone ? (
            <CheckCircle2 size={14} />
          ) : (
            <Download size={14} />
          )}
          {brandedPdfLoading
            ? 'Generating...'
            : brandedPdfDone
              ? 'Downloaded'
              : 'Download Branded PDF'}
        </button>
      </motion.div>

      {/* Export Format Cards */}
      <div className="space-y-3">
        {formats.map((fmt, idx) => {
          const Icon = fmt.icon;
          return (
            <motion.div
              key={fmt.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + idx * 0.05 }}
              className="bg-surface-raised border border-border rounded-xl p-5 flex items-center justify-between gap-4 hover:border-accent/20 transition-all"
            >
              <div className="flex items-start gap-4">
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${fmt.colorBg}`}
                >
                  <Icon size={18} className={fmt.color} />
                </div>
                <div>
                  <div className="text-sm font-semibold text-text">
                    {fmt.label}
                  </div>
                  <div className="text-xs text-text-muted mt-0.5 max-w-md">
                    {fmt.description}
                  </div>
                  <div className="text-[10px] text-text-muted mt-1 font-mono">
                    {fmt.filename}
                  </div>
                </div>
              </div>

              <button
                onClick={fmt.handler}
                disabled={!report || fmt.loading}
                className="flex items-center gap-2 bg-surface-overlay hover:bg-accent/10 border border-border text-text font-semibold px-4 py-2.5 rounded-xl transition-all text-sm disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
              >
                {fmt.loading ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : fmt.done ? (
                  <CheckCircle2 size={14} className="text-success" />
                ) : (
                  <Download size={14} />
                )}
                {fmt.loading ? 'Generating...' : fmt.done ? 'Downloaded' : 'Download'}
              </button>
            </motion.div>
          );
        })}
      </div>

      {/* Link Intelligence Data Export */}
      {hasLinkData && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="bg-surface-raised border border-border rounded-xl p-5">
            <div className="flex items-start gap-4 mb-4">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 bg-amber-500/10">
                <Network size={18} className="text-amber-400" />
              </div>
              <div>
                <div className="text-sm font-semibold text-text">Link Intelligence Data</div>
                <div className="text-xs text-text-muted mt-0.5 max-w-md">
                  Complete internal link data with TIPR scores, recommendations, and edge lists.
                  Compatible with Google Sheets, Excel, and graph analysis tools like Gephi.
                </div>
              </div>
            </div>
            <div className="flex gap-3 ml-14">
              <button
                onClick={() => handleLinkExport('xlsx')}
                disabled={linkXlsxLoading}
                className="flex items-center gap-2 bg-surface-overlay hover:bg-accent/10 border border-border text-text font-semibold px-4 py-2.5 rounded-xl transition-all text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {linkXlsxLoading ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : linkXlsxDone ? (
                  <CheckCircle2 size={14} className="text-success" />
                ) : (
                  <Download size={14} />
                )}
                {linkXlsxLoading ? 'Generating...' : linkXlsxDone ? 'Downloaded' : 'Excel (.xlsx)'}
              </button>
              <button
                onClick={() => handleLinkExport('csv')}
                disabled={linkCsvLoading}
                className="flex items-center gap-2 bg-surface-overlay hover:bg-accent/10 border border-border text-text font-semibold px-4 py-2.5 rounded-xl transition-all text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {linkCsvLoading ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : linkCsvDone ? (
                  <CheckCircle2 size={14} className="text-success" />
                ) : (
                  <Download size={14} />
                )}
                {linkCsvLoading ? 'Generating...' : linkCsvDone ? 'Downloaded' : 'CSV (.zip)'}
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
