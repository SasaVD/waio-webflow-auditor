import { useMemo } from 'react';
import { Link } from 'react-router';
import { motion } from 'framer-motion';
import { BarChart3, ChevronRight, Play } from 'lucide-react';
import { useAuditStore } from '../../stores/auditStore';

export function ContentOptimizerKpiCard({ auditId }: { auditId: string }) {
  const report = useAuditStore((s) => s.report);

  const info = useMemo(() => {
    const co = report?.content_optimizer as Record<string, any> | null;
    if (!co?.analyses) return null;
    const analyses = co.analyses as Record<string, any>;
    const entries = Object.values(analyses).filter(
      (a: any) => a?.status === 'ok' && a?.result
    );
    if (!entries.length) return null;

    const avgGap = entries.reduce(
      (sum: number, a: any) => sum + (a.result?.summary?.content_gap_score ?? 0),
      0
    ) / entries.length;

    const totalRecs = entries.reduce(
      (sum: number, a: any) => {
        const rc = a.result?.summary?.recommendations_count;
        return sum + (rc?.add ?? 0) + (rc?.increase ?? 0);
      },
      0
    );

    return {
      count: entries.length,
      avgGap: Math.round(avgGap),
      totalRecs,
    };
  }, [report]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.26 }}
    >
      <Link
        to={`/dashboard/${auditId}/content-optimizer`}
        className="block bg-surface-raised border border-border rounded-xl p-5 hover:border-accent/30 transition-all group"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-cyan-500/10 rounded-xl flex items-center justify-center group-hover:bg-cyan-500/20 transition-all">
              <BarChart3 size={18} className="text-cyan-400" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-text">Content Optimizer</h2>
              {info ? (
                <p className="text-xs text-text-muted mt-0.5">
                  {info.count} page{info.count !== 1 ? 's' : ''} analyzed &middot;{' '}
                  Average content gap: <strong className="text-text-secondary">{info.avgGap}%</strong>
                </p>
              ) : (
                <p className="text-xs text-text-muted mt-0.5">
                  Analyze how your pages compare to top-ranking competitors for any keyword
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-4">
            {info ? (
              <div className="text-right hidden sm:block">
                <div className="text-lg font-bold text-text font-heading">{info.totalRecs}</div>
                <div className="text-[10px] text-text-muted">Term gaps</div>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-xs font-semibold text-accent hidden sm:flex">
                <Play size={12} />
                Run Analysis
              </div>
            )}
            <ChevronRight size={16} className="text-text-muted group-hover:text-accent transition-colors" />
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
