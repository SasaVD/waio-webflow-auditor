import { useMemo } from 'react';
import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import { ArrowLeft, FolderTree, Info } from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';

interface Cluster {
  path: string;
  page_count: number;
  pillar_url?: string;
  cohesion_score?: number;
  nlp_category?: string;
}

const cohesionColor = (score: number): string => {
  if (score >= 0.8) return '#22C55E';
  if (score >= 0.6) return '#EAB308';
  return '#EF4444';
};

export default function DashboardClustersPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);

  const clusters = useMemo(() => {
    // Clusters can come from link_analysis or a dedicated clusters field
    const raw =
      report?.link_analysis?.clusters ??
      report?.clusters ??
      report?.topic_clusters ??
      null;
    if (!raw || (Array.isArray(raw) && raw.length === 0)) return null;
    if (Array.isArray(raw)) return raw as Cluster[];
    // If it's an object keyed by path
    return Object.entries(raw).map(([path, data]) => ({
      path,
      ...(data as Record<string, unknown>),
    })) as Cluster[];
  }, [report]);

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
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
            <FolderTree size={20} className="text-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text font-heading">
              Topic Clusters
            </h1>
            <p className="text-sm text-text-secondary mt-0.5">
              How your content is organized into topical groups.
            </p>
          </div>
        </div>
      </motion.div>

      {clusters && clusters.length > 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-3"
        >
          {clusters.map((cluster, idx) => (
            <motion.div
              key={cluster.path}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * idx }}
              className="bg-surface-raised border border-border rounded-xl p-5"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-text truncate">
                    {cluster.path}
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-text-muted">
                      {cluster.page_count ?? '?'} pages
                    </span>
                    {cluster.nlp_category && (
                      <span className="text-[10px] font-semibold text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                        {cluster.nlp_category}
                      </span>
                    )}
                    {cluster.pillar_url && (
                      <span className="text-[10px] text-text-muted truncate max-w-[200px]">
                        Pillar: {cluster.pillar_url}
                      </span>
                    )}
                  </div>
                </div>

                {cluster.cohesion_score != null && (
                  <div className="text-right flex-shrink-0">
                    <div
                      className="text-lg font-extrabold font-heading"
                      style={{ color: cohesionColor(cluster.cohesion_score) }}
                    >
                      {Math.round(cluster.cohesion_score * 100)}%
                    </div>
                    <div className="text-[10px] text-text-muted font-semibold uppercase tracking-wider">
                      Cohesion
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-surface-raised border border-border rounded-xl p-8 text-center"
        >
          <div className="w-12 h-12 mx-auto mb-4 bg-surface-overlay rounded-xl flex items-center justify-center">
            <Info size={20} className="text-text-muted" />
          </div>
          <p className="text-sm font-semibold text-text mb-1">
            Topic Clusters Not Available
          </p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Topic clusters will be detected after a full site crawl. Run a
            Comprehensive Audit with DataForSEO configured to analyze your
            content architecture.
          </p>
        </motion.div>
      )}
    </div>
  );
}
