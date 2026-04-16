import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, XCircle, ChevronDown, Sparkles, Search, MessageSquare } from 'lucide-react';
import type { EngineResult } from '../../stores/aiVisibilityStore';

const ENGINE_LABELS: Record<string, string> = {
  chatgpt: 'ChatGPT',
  claude: 'Claude',
  gemini: 'Gemini',
  perplexity: 'Perplexity',
};

const ENGINE_COLORS: Record<string, string> = {
  chatgpt: 'bg-green-500/10 text-green-400',
  claude: 'bg-orange-500/10 text-orange-400',
  gemini: 'bg-blue-500/10 text-blue-400',
  perplexity: 'bg-purple-500/10 text-purple-400',
};

interface EngineCardProps {
  engineKey: string;
  engine: EngineResult;
  prompts: Array<{ id: number; text: string; category: string }>;
  totalPrompts: number;
}

export function EngineCard({ engineKey, engine, prompts, totalPrompts }: EngineCardProps) {
  const [expanded, setExpanded] = useState(false);

  const label = ENGINE_LABELS[engineKey] || engineKey;
  const colorClass = ENGINE_COLORS[engineKey] || 'bg-accent/10 text-accent';
  const isOk = engine.status === 'ok';

  // Build prompt lookup for category labels
  const promptMap = Object.fromEntries(prompts.map((p) => [String(p.id), p]));

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface-raised border border-border rounded-xl overflow-hidden"
    >
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-surface-overlay/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${colorClass}`}>
            <MessageSquare size={16} />
          </div>
          <div className="text-left">
            <div className="text-sm font-bold text-text">{label}</div>
            <div className="text-xs text-text-muted mt-0.5">
              {isOk ? (
                <>
                  Mentioned in{' '}
                  <strong className={engine.brand_mentioned_in > 0 ? 'text-success' : 'text-text-secondary'}>
                    {engine.brand_mentioned_in}/{totalPrompts}
                  </strong>{' '}
                  prompts
                </>
              ) : (
                <span className="text-red-400">{engine.error || 'Failed'}</span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Status pill */}
          {isOk ? (
            <span className="flex items-center gap-1 text-[10px] font-bold text-success bg-success/10 px-2 py-1 rounded-full">
              <CheckCircle2 size={10} />
              OK
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] font-bold text-red-400 bg-red-500/10 px-2 py-1 rounded-full">
              <XCircle size={10} />
              FAILED
            </span>
          )}
          {/* Cost */}
          <span className="text-[10px] text-text-muted font-mono">
            ${engine.cost_usd.toFixed(3)}
          </span>
          <ChevronDown
            size={14}
            className={`text-text-muted transition-transform ${expanded ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      {/* Expanded responses */}
      <AnimatePresence>
        {expanded && isOk && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border p-4 space-y-3">
              {Object.entries(engine.responses_by_prompt).map(([promptId, response]) => {
                const prompt = promptMap[promptId];
                const isReputation = prompt?.category === 'reputation';
                return (
                  <div key={promptId} className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      {isReputation ? (
                        <Sparkles size={12} className="text-accent" />
                      ) : (
                        <Search size={12} className="text-text-muted" />
                      )}
                      <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                        {isReputation ? 'Reputation' : 'Discovery'}
                      </span>
                      <span className="text-xs text-text-secondary truncate">
                        "{prompt?.text || `Prompt ${promptId}`}"
                      </span>
                      {response.mentioned && (
                        <span className="ml-auto text-[10px] font-bold text-success bg-success/10 px-1.5 py-0.5 rounded">
                          MENTIONED
                        </span>
                      )}
                    </div>
                    <div className="pl-5 text-xs text-text-secondary leading-relaxed max-h-32 overflow-y-auto bg-surface-overlay rounded-lg p-3">
                      {response.text.length > 600
                        ? response.text.slice(0, 600) + '…'
                        : response.text}
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
