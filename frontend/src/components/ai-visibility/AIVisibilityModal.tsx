import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Eye, AlertTriangle, DollarSign } from 'lucide-react';
import { useAIVisibilityStore } from '../../stores/aiVisibilityStore';

interface AIVisibilityModalProps {
  auditId: string;
  open: boolean;
  onClose: () => void;
}

// Mirror of backend AMBIGUOUS_COMMON_WORDS in ai_visibility/brand_resolver.py.
// Keep both lists in sync.
const AMBIGUOUS_COMMON_WORDS = new Set([
  'your', 'this', 'that', 'them', 'they',
  'home', 'work', 'team', 'test', 'demo', 'site', 'page', 'data',
  'name', 'user', 'info', 'main', 'news', 'brand', 'company',
  'business', 'website', 'service', 'product', 'client', 'customer',
]);

// Advisory only — short acronyms (IBM, NIO, HP) and generic words can be
// legitimate brands, and exposing the collision is itself strategic signal.
// Returns a warning to display; submit stays enabled.
function checkBrandAmbiguity(raw: string): string | null {
  const s = raw.trim();
  if (!s) return null;
  if (s.length <= 3) {
    return `"${s}" is a short token (${s.length} character${s.length === 1 ? '' : 's'}). Short acronyms often match unrelated entities in AI response corpora (e.g. "VAN" matches Van Gogh, Beethoven, Van Halen). Results may include noise — which can itself reveal a positioning conflict worth addressing.`;
  }
  if (AMBIGUOUS_COMMON_WORDS.has(s.toLowerCase())) {
    return `"${s}" is a generic word that may collide with unrelated entities in AI response corpora. Results may include noise.`;
  }
  return null;
}

export function AIVisibilityModal({ auditId, open, onClose }: AIVisibilityModalProps) {
  const { brandPreview, fetchBrandPreview, startRecompute, error } = useAIVisibilityStore();
  const [brandName, setBrandName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      fetchBrandPreview(auditId);
    }
  }, [open, auditId, fetchBrandPreview]);

  useEffect(() => {
    if (brandPreview) {
      setBrandName(
        brandPreview.override || brandPreview.auto_extracted || ''
      );
    }
  }, [brandPreview]);

  const ambiguityWarning = checkBrandAmbiguity(brandName);

  const handleSubmit = async () => {
    if (!brandName.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    const result = await startRecompute(auditId, brandName.trim());
    setSubmitting(false);
    if (result.ok) {
      onClose();
    } else {
      setSubmitError(result.error || 'Failed to start analysis');
    }
  };

  const industryLeaf = brandPreview?.detected_industry
    ?.split('/')
    .filter(Boolean)
    .pop();

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={onClose}
          />
          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              className="bg-surface-raised border border-border rounded-2xl shadow-2xl w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-5 border-b border-border">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-accent/10 flex items-center justify-center">
                    <Eye size={18} className="text-accent" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-text font-heading">
                      AI Visibility Analysis
                    </h2>
                    <p className="text-xs text-text-muted">
                      Test your brand across 4 AI engines
                    </p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="w-8 h-8 rounded-lg hover:bg-surface-overlay flex items-center justify-center transition-colors"
                >
                  <X size={16} className="text-text-muted" />
                </button>
              </div>

              {/* Body */}
              <div className="p-5 space-y-4">
                {/* Brand name input */}
                <div>
                  <label className="text-xs font-semibold text-text-muted uppercase tracking-widest block mb-1.5">
                    Brand Name
                  </label>
                  <input
                    type="text"
                    value={brandName}
                    onChange={(e) => setBrandName(e.target.value)}
                    placeholder="Enter your brand name"
                    className="w-full px-3 py-2.5 bg-surface-overlay border border-border rounded-xl text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-all"
                  />
                  {ambiguityWarning && brandName.trim() && (
                    <p className="text-[11px] text-amber-400 mt-1.5 leading-snug">
                      {ambiguityWarning}
                    </p>
                  )}
                  {!ambiguityWarning && brandPreview?.override && (
                    <p className="text-[10px] text-text-muted mt-1">
                      Using manually set brand name from previous run
                    </p>
                  )}
                  {!ambiguityWarning && !brandPreview?.override && brandPreview?.auto_extracted && (
                    <p className="text-[10px] text-text-muted mt-1">
                      Auto-detected from NLP analysis (salience{' '}
                      {brandPreview.auto_extracted_salience
                        ? `${Math.round(brandPreview.auto_extracted_salience * 100)}%`
                        : 'n/a'}
                      )
                    </p>
                  )}
                </div>

                {/* Industry (read-only) */}
                {industryLeaf && (
                  <div>
                    <label className="text-xs font-semibold text-text-muted uppercase tracking-widest block mb-1.5">
                      Detected Industry
                    </label>
                    <div className="px-3 py-2.5 bg-surface-overlay border border-border rounded-xl text-sm text-text-secondary">
                      {industryLeaf}
                    </div>
                  </div>
                )}

                {/* Cost disclaimer */}
                <div className="flex items-start gap-3 p-3 bg-amber-500/5 border border-amber-500/20 rounded-xl">
                  <DollarSign size={16} className="text-amber-400 mt-0.5 flex-shrink-0" />
                  <div className="text-xs text-text-secondary">
                    {brandPreview && brandPreview.run_count > 0 ? (
                      <>
                        Previous runs total:{' '}
                        <strong className="text-text">
                          ${brandPreview.cumulative_cost_usd.toFixed(2)}
                        </strong>
                        . This run will add ~$0.25.
                      </>
                    ) : (
                      <>Estimated cost: ~$0.25 per analysis run.</>
                    )}
                  </div>
                </div>

                {/* Error display */}
                {(submitError || error) && (
                  <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
                    <AlertTriangle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-red-300">{submitError || error}</p>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="p-5 border-t border-border flex justify-end gap-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-semibold text-text-secondary hover:text-text rounded-xl hover:bg-surface-overlay transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={submitting || !brandName.trim()}
                  className="px-5 py-2 text-sm font-bold text-white bg-accent hover:bg-accent-hover rounded-xl shadow-glow-accent/20 hover:shadow-glow-accent transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? 'Starting...' : ambiguityWarning ? 'Run Anyway' : 'Run Analysis'}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
