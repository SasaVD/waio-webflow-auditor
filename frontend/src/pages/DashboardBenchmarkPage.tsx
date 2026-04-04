import { useMemo } from 'react';
import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import { ArrowLeft, BarChart3, Info, Trophy, Zap, AlertTriangle } from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';

const scoreColor = (score: number): string => {
  if (score >= 90) return '#22C55E';
  if (score >= 75) return '#84CC16';
  if (score >= 55) return '#EAB308';
  if (score >= 35) return '#F97316';
  return '#EF4444';
};

export default function DashboardBenchmarkPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);

  const competitive = report?.competitive_data ?? null;

  const rankings = useMemo(() => {
    if (!competitive?.rankings) return [];
    return competitive.rankings as Array<{
      url: string;
      overall_score: number;
      overall_label: string;
    }>;
  }, [competitive]);

  const advantages = (competitive?.advantages ?? []) as Array<{
    key: string;
    pillar: string;
    score: number;
    diff: number;
  }>;

  const weaknesses = (competitive?.weaknesses ?? []) as Array<{
    key: string;
    pillar: string;
    score: number;
    diff: number;
  }>;

  const primaryUrl = competitive?.primary_url ?? report?.url ?? '';

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
            <BarChart3 size={20} className="text-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text font-heading">
              Competitor Benchmark
            </h1>
            <p className="text-sm text-text-secondary mt-0.5">
              How your site compares against competitors across all pillars.
            </p>
          </div>
        </div>
      </motion.div>

      {rankings.length > 0 ? (
        <div className="space-y-8">
          {/* Leaderboard */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3 flex items-center gap-2">
              <Trophy size={14} /> Leaderboard
            </h2>
            <div className="space-y-2">
              {rankings.map((r, idx) => {
                const isPrimary = r.url === primaryUrl;
                return (
                  <motion.div
                    key={r.url}
                    initial={{ opacity: 0, x: -16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.05 * idx }}
                    className={`flex items-center justify-between gap-4 px-5 py-4 rounded-xl border transition-all ${
                      isPrimary
                        ? 'bg-accent/5 border-accent/20'
                        : 'bg-surface-raised border-border'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                          idx === 0
                            ? 'bg-accent text-white'
                            : idx === 1
                              ? 'bg-text-muted/20 text-text'
                              : idx === 2
                                ? 'bg-warning/20 text-warning'
                                : 'bg-surface-overlay text-text-muted'
                        }`}
                      >
                        {idx + 1}
                      </div>
                      <div className="truncate">
                        <div
                          className={`text-sm font-semibold truncate ${isPrimary ? 'text-accent' : 'text-text'}`}
                        >
                          {r.url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                        </div>
                        {isPrimary && (
                          <span className="text-[10px] font-bold text-accent uppercase tracking-wider">
                            Your Site
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div
                        className="text-xl font-extrabold font-heading"
                        style={{ color: scoreColor(r.overall_score) }}
                      >
                        {r.overall_score}
                      </div>
                      <div className="text-[10px] text-text-muted font-bold uppercase tracking-widest">
                        {r.overall_label}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>

          {/* Advantages & Weaknesses */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="bg-surface-raised border border-border rounded-xl p-6"
            >
              <h2 className="text-sm font-bold text-text mb-4 flex items-center gap-2">
                <Zap size={14} className="text-success" /> Competitive Advantages
              </h2>
              {advantages.length > 0 ? (
                <div className="space-y-4">
                  {advantages.map((a) => (
                    <div key={a.key}>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-semibold text-text">
                          {a.pillar}
                        </span>
                        <span className="text-xs font-bold text-success">
                          +{a.diff} pts vs avg
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-surface-overlay rounded-full overflow-hidden">
                          <div
                            className="h-full bg-success rounded-full"
                            style={{ width: `${a.score}%` }}
                          />
                        </div>
                        <span className="text-[10px] font-bold text-text-muted w-6 text-right">
                          {a.score}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-text-muted py-4 text-center">
                  No clear advantages detected
                </p>
              )}
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-surface-raised border border-border rounded-xl p-6"
            >
              <h2 className="text-sm font-bold text-text mb-4 flex items-center gap-2">
                <AlertTriangle size={14} className="text-severity-high" />{' '}
                Areas to Improve
              </h2>
              {weaknesses.length > 0 ? (
                <div className="space-y-4">
                  {weaknesses.map((w) => (
                    <div key={w.key}>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-semibold text-text">
                          {w.pillar}
                        </span>
                        <span className="text-xs font-bold text-severity-high">
                          {w.diff} pts vs avg
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-surface-overlay rounded-full overflow-hidden">
                          <div
                            className="h-full bg-severity-high rounded-full"
                            style={{ width: `${w.score}%` }}
                          />
                        </div>
                        <span className="text-[10px] font-bold text-text-muted w-6 text-right">
                          {w.score}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-text-muted py-4 text-center">
                  No weaknesses detected
                </p>
              )}
            </motion.div>
          </div>
        </div>
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
            Benchmark Data Not Available
          </p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Add competitor URLs when running a Comprehensive Audit to see
            benchmarks. You can add up to 4 competitor sites for comparison.
          </p>
        </motion.div>
      )}
    </div>
  );
}
