import { motion } from 'framer-motion';
import { CheckCircle2, Loader2, Circle } from 'lucide-react';
import { useAuditStream, STAGES } from '../../hooks/useAuditStream';

interface AuditProgressProps {
  isLoading: boolean;
  auditId?: string;
}

export const AuditProgress: React.FC<AuditProgressProps> = ({
  isLoading,
  auditId,
}) => {
  const { progress, currentStage, stageIndex, findings } = useAuditStream(
    isLoading,
    auditId
  );

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-10"
      >
        {/* Pulsing indicator */}
        <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-accent/10 flex items-center justify-center">
          <Loader2 size={28} className="text-accent animate-spin" />
        </div>

        <h2 className="text-2xl font-bold text-text font-heading mb-2">
          Analyzing your site
        </h2>
        <p className="text-text-secondary text-sm">{currentStage}</p>
      </motion.div>

      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-text-muted">
            Progress
          </span>
          <span className="text-xs font-bold text-accent">{progress}%</span>
        </div>
        <div className="h-2 bg-surface-overlay rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-accent rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Live counters */}
      <div className="grid grid-cols-2 gap-4 mb-10">
        <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
          <motion.div
            key={stageIndex}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-2xl font-extrabold text-text font-heading"
          >
            {stageIndex + 1}/{STAGES.length}
          </motion.div>
          <div className="text-xs text-text-muted mt-1">Stages Complete</div>
        </div>
        <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
          <motion.div
            key={findings}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-2xl font-extrabold text-text font-heading"
          >
            {findings}
          </motion.div>
          <div className="text-xs text-text-muted mt-1">Issues Found</div>
        </div>
      </div>

      {/* Stage steps */}
      <div className="space-y-1">
        {STAGES.map((stage, i) => {
          const isActive = i === stageIndex;
          const isDone = i < stageIndex;

          return (
            <motion.div
              key={stage.key}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              className={`flex items-center gap-3 px-4 py-2 rounded-lg text-sm transition-all ${
                isActive
                  ? 'bg-accent/10 text-accent font-medium'
                  : isDone
                    ? 'text-text-secondary'
                    : 'text-text-muted'
              }`}
            >
              {isDone ? (
                <CheckCircle2 size={14} className="text-success flex-shrink-0" />
              ) : isActive ? (
                <Loader2
                  size={14}
                  className="text-accent animate-spin flex-shrink-0"
                />
              ) : (
                <Circle size={14} className="flex-shrink-0 opacity-30" />
              )}
              {stage.label}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
