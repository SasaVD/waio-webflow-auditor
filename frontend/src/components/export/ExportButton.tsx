import { useState, useRef, useEffect } from 'react';
import { Download, FileText, Table, FileCode2, Loader2 } from 'lucide-react';
import { generateExcel } from '../../utils/generateExcel';
import { downloadMarkdown } from '../../utils/generateMarkdown';

interface ExportButtonProps {
  report: Record<string, any>;
}

export const ExportButton: React.FC<ExportButtonProps> = ({ report }) => {
  const [open, setOpen] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handlePdf = async () => {
    setPdfLoading(true);
    setOpen(false);
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
      const domain = report.url
        ?.replace(/https?:\/\//, '')
        .replace(/\//g, '_')
        .replace(/_$/, '');
      const date = new Date().toISOString().slice(0, 10);
      a.href = blobUrl;
      a.download = `WAIO-Intelligence-Report-${domain}-${date}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error('PDF export failed:', err);
    } finally {
      setPdfLoading(false);
    }
  };

  const handleExcel = () => {
    setOpen(false);
    generateExcel(report);
  };

  const handleMarkdown = () => {
    setOpen(false);
    downloadMarkdown(report);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={pdfLoading}
        className="flex items-center gap-2 bg-surface-overlay hover:bg-surface-raised border border-border text-text font-semibold px-4 py-2.5 rounded-xl transition-all text-sm disabled:opacity-50"
      >
        {pdfLoading ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Download size={14} />
        )}
        Export
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-48 bg-surface-raised border border-border rounded-xl shadow-card overflow-hidden z-50">
          <button
            onClick={handlePdf}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm text-text hover:bg-surface-overlay transition-colors"
          >
            <FileText size={15} className="text-severity-high" />
            PDF Report
          </button>
          <button
            onClick={handleExcel}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm text-text hover:bg-surface-overlay transition-colors"
          >
            <Table size={15} className="text-success" />
            Excel Spreadsheet
          </button>
          <button
            onClick={handleMarkdown}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm text-text hover:bg-surface-overlay transition-colors"
          >
            <FileCode2 size={15} className="text-secondary-blue" />
            Markdown
          </button>
        </div>
      )}
    </div>
  );
};
