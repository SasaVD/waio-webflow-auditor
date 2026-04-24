import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { motion } from 'framer-motion';
import { Eye, ChevronRight, Loader2, Target, AlertCircle, AlertTriangle } from 'lucide-react';
import { useAIVisibilityStore } from '../../stores/aiVisibilityStore';
import { AIVisibilityModal } from './AIVisibilityModal';

interface AIVisibilityKpiCardProps {
  auditId: string;
}

export function AIVisibilityKpiCard({ auditId }: AIVisibilityKpiCardProps) {
  const { data, status, fetchStatus } = useAIVisibilityStore();
  const [modalOpen, setModalOpen] = useState(false);

  // Workstream D3: resolved industry block — feeds the modal so users can
  // confirm/edit before running. `null` (or missing block) triggers the
  // needs-attention state both here and inside the modal.
  const industry = data?.industry ?? null;

  useEffect(() => {
    fetchStatus(auditId);
    return () => {
      useAIVisibilityStore.getState().stopPolling();
    };
  }, [auditId, fetchStatus]);

  // Not computed — show CTA
  if (status === 'not_computed' || status === 'idle') {
    return (
      <>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.26 }}
        >
          <button
            onClick={() => setModalOpen(true)}
            className="w-full text-left bg-surface-raised border border-border border-dashed rounded-xl p-5 hover:border-accent/30 transition-all group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center group-hover:bg-accent/20 transition-all">
                  <Eye size={18} className="text-accent" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-text">AI Visibility</h2>
                  <p className="text-xs text-text-muted mt-0.5">
                    Not yet computed.{' '}
                    <span className="text-accent font-semibold">
                      Run Analysis →
                    </span>
                  </p>
                </div>
              </div>
            </div>
          </button>
        </motion.div>
        <AIVisibilityModal
          auditId={auditId}
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          initialIndustry={industry}
        />
      </>
    );
  }

  // Needs industry confirmation (Workstream D3) — neither the user nor NLP
  // provided an industry, so the engine short-circuited before running
  // prompts. Render an amber-bordered CTA card instead of bogus benchmarks.
  if (status === 'needs_industry_confirmation') {
    return (
      <>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.26 }}
        >
          <button
            onClick={() => setModalOpen(true)}
            className="w-full text-left bg-surface-raised border border-amber-500/40 rounded-xl p-5 hover:border-amber-500/60 transition-all group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-amber-500/10 rounded-xl flex items-center justify-center">
                  <AlertTriangle size={18} className="text-amber-400" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-text">AI Visibility</h2>
                  <p className="text-xs text-text-muted mt-0.5">
                    Industry not detected.{' '}
                    <span className="text-amber-400 font-semibold">
                      Specify industry →
                    </span>
                  </p>
                </div>
              </div>
            </div>
          </button>
        </motion.div>
        <AIVisibilityModal
          auditId={auditId}
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          initialIndustry={industry}
        />
      </>
    );
  }

  // Running — show spinner
  if (status === 'running' || status === 'loading') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.26 }}
        className="bg-surface-raised border border-border rounded-xl p-5"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center">
            <Loader2 size={18} className="text-accent animate-spin" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-text">AI Visibility</h2>
            <p className="text-xs text-text-muted mt-0.5">
              Running analysis across 4 AI engines... ~45s
            </p>
          </div>
        </div>
      </motion.div>
    );
  }

  // Failed — analysis errored out, data shape is incomplete (no mentions_database / live_test)
  if (status === 'failed' || !data?.mentions_database || !data?.live_test) {
    return (
      <>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.26 }}
        >
          <button
            onClick={() => setModalOpen(true)}
            className="w-full text-left bg-surface-raised border border-amber-500/30 rounded-xl p-5 hover:border-amber-500/50 transition-all group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-amber-500/10 rounded-xl flex items-center justify-center">
                  <AlertCircle size={18} className="text-amber-400" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-text">AI Visibility</h2>
                  <p className="text-xs text-text-muted mt-0.5">
                    Last run failed.{' '}
                    <span className="text-amber-400 font-semibold">Retry →</span>
                  </p>
                </div>
              </div>
            </div>
          </button>
        </motion.div>
        <AIVisibilityModal
          auditId={auditId}
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          initialIndustry={industry}
        />
      </>
    );
  }

  // Has data — determine which variant to show
  const hasMentions = data.mentions_database.total > 0;
  const engineCount = Object.keys(data.live_test.engines).length;
  const okEngines = Object.values(data.live_test.engines).filter((e) => e.status === 'ok').length;

  // Computed with data
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.26 }}
    >
      <Link
        to={`/dashboard/${auditId}/ai-visibility`}
        className="block bg-surface-raised border border-border rounded-xl p-5 hover:border-accent/30 transition-all group"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center group-hover:bg-accent/20 transition-all">
              {hasMentions ? (
                <Eye size={18} className="text-accent" />
              ) : (
                <Target size={18} className="text-amber-400" />
              )}
            </div>
            <div>
              <h2 className="text-sm font-bold text-text">AI Visibility</h2>
              <p className="text-xs text-text-muted mt-0.5">
                {hasMentions ? (
                  <>
                    {data!.mentions_database.total} mentions across AI platforms
                  </>
                ) : (
                  <>
                    Not yet indexed — untapped opportunity
                  </>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <div className="text-lg font-bold text-text font-heading">
                {okEngines}/{engineCount}
              </div>
              <div className="text-[10px] text-text-muted">Engines</div>
            </div>
            {data?.last_computed_at && (
              <div className="text-right hidden md:block">
                <div className="text-xs font-semibold text-text-secondary">
                  {formatTimeAgo(data.last_computed_at)}
                </div>
                <div className="text-[10px] text-text-muted">Last run</div>
              </div>
            )}
            <ChevronRight
              size={16}
              className="text-text-muted group-hover:text-accent transition-colors"
            />
          </div>
        </div>
      </Link>
    </motion.div>
  );
}

function formatTimeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
