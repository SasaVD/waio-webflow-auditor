import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as Tabs from '@radix-ui/react-tabs';
import {
  ArrowRight,
  Plus,
  Crown,
  X,
  Sparkles,
} from 'lucide-react';
import { useAuthStore } from '../stores/authStore';

interface AuditFormProps {
  onRunAudit: (
    url: string,
    auditType: 'single' | 'site' | 'competitive',
    competitorUrls?: string[],
    tier?: 'free' | 'premium',
    aiVisibilityOptIn?: boolean,
    brandName?: string,
    /**
     * Workstream D3: optional user-declared industry override. When empty,
     * the backend falls back to NLP detection; if that also yields nothing,
     * AI Visibility enters the "needs_industry_confirmation" state and the
     * modal prompts the user mid-session.
     */
    targetIndustry?: string,
  ) => void;
  isLoading: boolean;
  error: string | null;
}

export const AuditForm: React.FC<AuditFormProps> = ({
  onRunAudit,
  isLoading,
  error,
}) => {
  const { isAuthenticated, openLoginModal } = useAuthStore();
  const [url, setUrl] = useState('');
  const [activeTab, setActiveTab] = useState('single');
  const [competitors, setCompetitors] = useState<string[]>(['']);
  const [scope, setScope] = useState<'domain' | 'subdomain' | 'subfolder'>('domain');
  const [aiVisibility, setAiVisibility] = useState(true);
  const [brandName, setBrandName] = useState('');
  const [targetIndustry, setTargetIndustry] = useState('');

  const handleTabChange = (value: string) => {
    if (value === 'fullsite' && !isAuthenticated) {
      openLoginModal();
      return;
    }
    setActiveTab(value);
  };

  const normalizeUrl = (raw: string): string => {
    const trimmed = raw.trim();
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      return 'https://' + trimmed;
    }
    return trimmed;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;
    const submitUrl = normalizeUrl(url);

    if (activeTab === 'single') {
      onRunAudit(submitUrl, 'single', [], 'free');
    } else {
      // Comprehensive Audit tab — always uses premium endpoint
      const validCompetitors = competitors
        .filter((c) => c.trim())
        .map((c) => normalizeUrl(c));

      onRunAudit(
        submitUrl,
        'single',
        validCompetitors,
        'premium',
        aiVisibility,
        brandName.trim() || undefined,
        targetIndustry.trim() || undefined,
      );
    }
  };

  const addCompetitor = () => {
    if (competitors.length < 4) setCompetitors([...competitors, '']);
  };

  const removeCompetitor = (index: number) => {
    setCompetitors(competitors.filter((_, i) => i !== index));
  };

  const updateCompetitor = (index: number, value: string) => {
    const next = [...competitors];
    next[index] = value;
    setCompetitors(next);
  };

  return (
    <div className="relative overflow-hidden">
      {/* Background — grid pattern + gradient orbs */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden bg-grid-pattern">
        <div className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full bg-accent/[0.04] blur-3xl" />
        <div className="absolute -bottom-60 -left-40 w-[500px] h-[500px] rounded-full bg-secondary-blue/[0.03] blur-3xl" />
      </div>

      {/* Hero Section */}
      <div className="relative max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 bg-surface-raised border border-border rounded-full px-4 py-1.5 mb-8">
            <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              Three audiences · One audit engine
            </span>
          </div>

          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-text leading-[1.05] mb-6 font-heading">
            The only website audit built for
            <br />
            humans, search engines,
            <br />
            <span className="text-accent">AND</span> AI systems
          </h1>

          <p className="text-lg md:text-xl text-text-secondary max-w-3xl mx-auto mb-12 leading-relaxed">
            10 deterministic pillars. Zero AI guessing. Every finding backed by
            a verified statistic and a reproducible check — so every fix you
            ship has a measurable before/after.
          </p>
        </motion.div>

        {/* Form Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <Tabs.Root
            value={activeTab}
            onValueChange={handleTabChange}
            className="max-w-2xl mx-auto"
          >
            {/* Tab List */}
            <Tabs.List className="flex gap-1 bg-surface-raised border border-border rounded-xl p-1 mb-6">
              <Tabs.Trigger
                value="single"
                className="flex-1 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all data-[state=active]:bg-surface-overlay data-[state=active]:text-text data-[state=active]:shadow-[inset_0_-2px_0_0_var(--color-accent)] text-text-muted hover:text-text-secondary"
              >
                Quick Analysis
              </Tabs.Trigger>
              <Tabs.Trigger
                value="fullsite"
                className="flex-1 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all data-[state=active]:bg-surface-overlay data-[state=active]:text-text data-[state=active]:shadow-[inset_0_-2px_0_0_var(--color-accent)] text-text-muted hover:text-text-secondary flex items-center justify-center gap-2"
              >
                Comprehensive Audit
                <span className="bg-accent text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                  Pro
                </span>
              </Tabs.Trigger>
            </Tabs.List>

            {/* Single Page Form */}
            <Tabs.Content value="single" asChild>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="bg-surface-raised border border-border rounded-xl p-1.5 flex items-center gap-2 transition-all focus-within:ring-2 focus-within:ring-accent/30 focus-within:border-accent/30">
                  <input
                    type="text"
                    className="flex-1 bg-transparent px-4 py-3.5 text-base font-medium text-text placeholder:text-text-muted focus:outline-none"
                    placeholder="Enter your website URL"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={isLoading}
                    required
                  />
                  <button
                    type="submit"
                    disabled={!url || isLoading}
                    className="bg-accent hover:bg-accent-hover text-white font-semibold px-6 py-3 rounded-lg flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap hover:shadow-glow-accent"
                  >
                    Analyze My Website Free
                    <ArrowRight size={16} />
                  </button>
                </div>
              </form>
            </Tabs.Content>

            {/* Full Site Form */}
            <Tabs.Content value="fullsite" asChild>
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* URL Input */}
                <div className="bg-surface-raised border border-border rounded-xl p-1.5 transition-all focus-within:ring-2 focus-within:ring-accent/30 focus-within:border-accent/30">
                  <input
                    type="text"
                    className="w-full bg-transparent px-4 py-3.5 text-base font-medium text-text placeholder:text-text-muted focus:outline-none"
                    placeholder="Enter your website URL"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={isLoading}
                    required
                  />
                </div>

                {/* Scope Selector + Page Limit */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 px-1">
                  <div className="flex gap-1 bg-surface border border-border rounded-lg p-0.5">
                    {(['domain', 'subdomain', 'subfolder'] as const).map(
                      (s) => (
                        <button
                          key={s}
                          type="button"
                          onClick={() => setScope(s)}
                          className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all capitalize ${
                            scope === s
                              ? 'bg-surface-overlay text-text'
                              : 'text-text-muted hover:text-text-secondary'
                          }`}
                        >
                          {s}
                        </button>
                      )
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-text-muted">
                    <Sparkles size={12} className="text-accent" />
                    Up to 2,000 pages with JS rendering
                  </div>
                </div>

                {/* Competitor URLs */}
                <div className="space-y-2 pt-2">
                  <div className="flex items-center justify-between px-1">
                    <span className="text-xs font-bold text-text-muted uppercase tracking-widest">
                      Competitors (optional, max 4)
                    </span>
                  </div>
                  <AnimatePresence mode="popLayout">
                    {competitors.map((comp, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="bg-surface-raised border border-border rounded-lg p-1 flex items-center gap-2">
                          <input
                            type="text"
                            className="flex-1 bg-transparent px-3 py-2 text-sm font-medium text-text placeholder:text-text-muted focus:outline-none"
                            placeholder="Competitor URL..."
                            value={comp}
                            onChange={(e) =>
                              updateCompetitor(idx, e.target.value)
                            }
                            disabled={isLoading}
                          />
                          {competitors.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeCompetitor(idx)}
                              className="p-1.5 text-text-muted hover:text-error transition-colors rounded-md hover:bg-error/10"
                            >
                              <X size={14} />
                            </button>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>

                  {competitors.length < 4 && (
                    <button
                      type="button"
                      onClick={addCompetitor}
                      className="text-xs font-bold text-accent hover:text-accent-hover flex items-center gap-1 px-1 py-1 transition-colors"
                    >
                      <Plus size={14} /> Add Competitor
                    </button>
                  )}
                </div>

                {/* AI Visibility */}
                <div className="space-y-2 pt-2 border-t border-border">
                  <label className="flex items-center gap-3 px-1 py-2 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={aiVisibility}
                      onChange={(e) => setAiVisibility(e.target.checked)}
                      className="w-4 h-4 rounded border-border accent-accent"
                      disabled={isLoading}
                    />
                    <div className="flex-1">
                      <span className="text-sm font-semibold text-text group-hover:text-accent transition-colors">
                        Include AI Visibility Analysis
                      </span>
                      <span className="block text-[11px] text-text-muted mt-0.5">
                        Test brand presence across ChatGPT, Claude, Gemini & Perplexity (~$0.30)
                      </span>
                    </div>
                  </label>
                  <AnimatePresence>
                    {aiVisibility && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden space-y-2"
                      >
                        <div className="bg-surface-raised border border-border rounded-lg p-1">
                          <input
                            type="text"
                            className="w-full bg-transparent px-3 py-2 text-sm font-medium text-text placeholder:text-text-muted focus:outline-none"
                            placeholder="Brand name (optional — auto-detected if blank)"
                            value={brandName}
                            onChange={(e) => setBrandName(e.target.value)}
                            disabled={isLoading}
                          />
                        </div>
                        {/* Workstream D3: optional user-declared industry.
                            Leaving blank triggers NLP detection first, then
                            the "Needs attention" modal flow if that also
                            yields nothing. */}
                        <div className="bg-surface-raised border border-border rounded-lg p-1">
                          <input
                            type="text"
                            className="w-full bg-transparent px-3 py-2 text-sm font-medium text-text placeholder:text-text-muted focus:outline-none"
                            placeholder="Industry or niche (optional — e.g. Event management software, B2B SaaS, fintech)"
                            value={targetIndustry}
                            onChange={(e) => setTargetIndustry(e.target.value)}
                            disabled={isLoading}
                          />
                        </div>
                        <p className="text-[11px] text-text-muted px-1 leading-snug">
                          Leave blank to auto-detect from your content. Providing
                          this makes AI Visibility benchmarks more accurate.
                        </p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Submit */}
                <button
                  type="submit"
                  disabled={isLoading || !url}
                  className="w-full bg-accent hover:bg-accent-hover text-white font-semibold py-3.5 rounded-xl flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-glow-accent"
                >
                  <Crown size={16} />
                  Start Comprehensive Audit
                </button>
              </form>
            </Tabs.Content>
          </Tabs.Root>

          {/* Trust Bar */}
          <p className="text-xs text-text-muted mt-4 max-w-2xl mx-auto">
            Analysis validated against W3C · WCAG 2.1 · Schema.org · Google Web Vitals
          </p>

          {/* Error Display */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-2xl mx-auto mt-4"
            >
              <div className="bg-severity-critical-bg text-severity-critical px-4 py-3 rounded-xl text-sm font-medium border border-severity-critical/20">
                {error}
              </div>
            </motion.div>
          )}
        </motion.div>
      </div>

    </div>
  );
};
