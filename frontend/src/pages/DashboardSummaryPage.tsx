import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import { ArrowLeft, FileText, Info } from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';

export default function DashboardSummaryPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);

  const summary: string | null = report?.executive_summary ?? null;

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
            <div className="prose prose-invert max-w-none text-text text-sm leading-relaxed whitespace-pre-wrap">
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
    </div>
  );
}
