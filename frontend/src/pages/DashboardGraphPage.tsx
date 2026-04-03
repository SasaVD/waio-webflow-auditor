import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';
import { LinkGraph } from '../components/LinkGraph';

export default function DashboardGraphPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);

  const graphData = report?.link_analysis ?? null;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
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
        <h1 className="text-2xl font-bold text-text font-heading">
          Link Graph
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          Interactive visualization of your site's internal link architecture.
        </p>
      </motion.div>

      <LinkGraph auditId={auditId ?? ''} data={graphData} />
    </div>
  );
}
