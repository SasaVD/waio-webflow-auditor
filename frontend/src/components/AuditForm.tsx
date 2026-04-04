import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as Tabs from '@radix-ui/react-tabs';
import {
  ArrowRight,
  Shield,
  Code2,
  FileJson,
  Accessibility,
  Paintbrush,
  BookOpen,
  Layers,
  Radio,
  ShieldCheck,
  Link2,
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
    tier?: 'free' | 'premium'
  ) => void;
  isLoading: boolean;
  error: string | null;
}

const pillars = [
  { icon: Code2, label: 'Search Engine Clarity', desc: 'How clearly search engines read your site' },
  { icon: FileJson, label: 'Rich Search Presence', desc: 'Stand out with rich results in Google' },
  { icon: BookOpen, label: 'AI Answer Readiness', desc: 'Get cited by ChatGPT & AI assistants' },
  { icon: Paintbrush, label: 'Visual Consistency', desc: 'Clean, maintainable styling' },
  { icon: Shield, label: 'Page Speed & Load Time', desc: 'How fast your pages load' },
  { icon: Accessibility, label: 'Inclusive Reach', desc: 'Accessible to every visitor' },
  { icon: Layers, label: 'AI Retrieval Readiness', desc: 'Ready for AI-powered search' },
  { icon: Radio, label: 'AI Agent Compatibility', desc: 'Works with AI agents & tools' },
  { icon: ShieldCheck, label: 'Tracking & Analytics Accuracy', desc: 'Reliable data you can trust' },
  { icon: Link2, label: 'Content Architecture', desc: 'How well your pages connect' },
];

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
      // Full Site tab — competitive if competitors provided, otherwise site crawl
      const validCompetitors = competitors
        .filter((c) => c.trim())
        .map((c) => normalizeUrl(c));

      if (validCompetitors.length > 0) {
        onRunAudit(submitUrl, 'competitive', validCompetitors, 'premium');
      } else {
        onRunAudit(submitUrl, 'site', [], 'premium');
      }
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
              Free website intelligence report
            </span>
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-text leading-[1.05] mb-6 font-heading">
            See what your website
            <br />
            is <span className="text-accent">costing you</span>
          </h1>

          <p className="text-lg md:text-xl text-text-secondary max-w-2xl mx-auto mb-12 leading-relaxed">
            Get a free, instant analysis across 10 critical performance
            dimensions — from search visibility and page speed to accessibility
            and AI readiness.
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

      {/* Pillar Cards */}
      <div className="max-w-5xl mx-auto px-6 pb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="grid grid-cols-2 md:grid-cols-5 gap-3"
        >
          {pillars.map((p, i) => (
            <motion.div
              key={p.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.5 + i * 0.06 }}
              className="group bg-surface-raised border border-border hover:border-accent/20 rounded-xl p-4 text-center transition-all"
            >
              <div className="w-10 h-10 mx-auto mb-3 rounded-lg bg-surface-overlay group-hover:bg-accent/10 flex items-center justify-center transition-all">
                <p.icon
                  size={18}
                  className="text-text-muted group-hover:text-accent transition-colors"
                />
              </div>
              <div className="text-sm font-semibold text-text mb-0.5">
                {p.label}
              </div>
              <div className="text-[11px] text-text-muted leading-tight">
                {p.desc}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  );
};
