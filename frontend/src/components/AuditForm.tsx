import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Shield, Code2, FileJson, Accessibility, Paintbrush, BookOpen, Layers, Radio, ShieldCheck, Link2, Plus } from 'lucide-react';

interface AuditFormProps {
  onRunAudit: (url: string, auditType: 'single' | 'site' | 'competitive', competitorUrls?: string[]) => void;
  isLoading: boolean;
  error: string | null;
}

const pillars = [
  { icon: Code2, label: 'Semantic HTML', desc: 'W3C structure validation' },
  { icon: FileJson, label: 'Structured Data', desc: 'JSON-LD & Microdata' },
  { icon: BookOpen, label: 'AEO Content', desc: 'AI citation & structure audit' },
  { icon: Paintbrush, label: 'CSS Quality', desc: 'Framework & naming audit' },
  { icon: Shield, label: 'JS Bloat', desc: 'Webflow script analysis' },
  { icon: Accessibility, label: 'Accessibility', desc: 'WCAG 2.1 AA compliance' },
  { icon: Layers, label: 'RAG Readiness', desc: 'Chunk & context quality' },
  { icon: Radio, label: 'Agentic Protocols', desc: 'MCP/A2A readiness' },
  { icon: ShieldCheck, label: 'Data Integrity', desc: 'Conflict detection' },
  { icon: Link2, label: 'Internal Linking', desc: 'Link depth & distribution' },
];

export const AuditForm: React.FC<AuditFormProps> = ({ onRunAudit, isLoading, error }) => {
  const [url, setUrl] = useState('');
  const [auditType, setAuditType] = useState<'single' | 'site' | 'competitive'>('single');
  const [competitors, setCompetitors] = useState<string[]>(['']);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;
    let submitUrl = url.trim();
    if (!submitUrl.startsWith('http://') && !submitUrl.startsWith('https://')) {
      submitUrl = 'https://' + submitUrl;
    }
    
    const competitorUrls = auditType === 'competitive' 
      ? competitors.filter(c => c.trim()).map(c => c.trim().startsWith('http') ? c.trim() : 'https://' + c.trim())
      : [];

    onRunAudit(submitUrl, auditType, competitorUrls);
  };

  const addCompetitor = () => {
    if (competitors.length < 4) {
      setCompetitors([...competitors, '']);
    }
  };

  const removeCompetitor = (index: number) => {
    setCompetitors(competitors.filter((_, i) => i !== index));
  };

  const updateCompetitor = (index: number, value: string) => {
    const newCompetitors = [...competitors];
    newCompetitors[index] = value;
    setCompetitors(newCompetitors);
  };

  return (
    <div className="relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full bg-primary/[0.03]" />
        <div className="absolute -bottom-60 -left-40 w-[500px] h-[500px] rounded-full bg-primary/[0.02]" />
      </div>

      {/* Hero Section */}
      <div className="relative max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 bg-surface-secondary border border-border rounded-full px-4 py-1.5 mb-8">
            <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              10-Pillar Deterministic Analysis
            </span>
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-text-primary leading-[1.05] mb-6">
            Audit your Webflow
            <br />
            <span className="text-primary">site foundation</span>
          </h1>

          <p className="text-lg md:text-xl text-text-secondary max-w-2xl mx-auto mb-12 leading-relaxed">
            Programmatic analysis against W3C, Schema.org, AEO Content standards, and WCAG 2.1.
            <br className="hidden md:block" />
            Zero AI dependency. Evidence-based results only.
          </p>
        </motion.div>

        {/* URL Input - Liquid Glass Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <form
            onSubmit={handleSubmit}
            className="relative max-w-2xl mx-auto"
          >
            <div className="flex justify-center mb-6">
              <div className="bg-surface-secondary border border-border p-1 rounded-xl flex gap-1 shadow-sm">
                <button
                  type="button"
                  onClick={() => setAuditType('single')}
                  className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                    auditType === 'single'
                      ? 'bg-white shadow-[0_2px_8px_rgba(0,0,0,0.04)] border border-border-light text-text-primary'
                      : 'text-text-secondary hover:text-text-primary'
                  }`}
                >
                  Single Page
                </button>
                <button
                  type="button"
                  onClick={() => setAuditType('site')}
                  className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                    auditType === 'site'
                      ? 'bg-white shadow-[0_2px_8px_rgba(0,0,0,0.04)] border border-border-light text-text-primary'
                      : 'text-text-secondary hover:text-text-primary'
                  }`}
                >
                  Full Site
                </button>
                <button
                  type="button"
                  onClick={() => setAuditType('competitive')}
                  className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                    auditType === 'competitive'
                      ? 'bg-white shadow-[0_2px_8px_rgba(0,0,0,0.04)] border border-border-light text-text-primary'
                      : 'text-text-secondary hover:text-text-primary'
                  }`}
                >
                  Competitive
                </button>
              </div>
            </div>

            <div className="space-y-3">
              <div className="relative bg-white rounded-2xl border border-gray-200 shadow-[0_4px_24px_rgba(0,0,0,0.06)] p-2 flex items-center gap-2 transition-shadow hover:shadow-[0_8px_32px_rgba(40,32,255,0.08)] focus-within:shadow-[0_8px_32px_rgba(40,32,255,0.12)] focus-within:border-primary/20">
                <div className="pl-4 text-xs font-bold text-primary uppercase tracking-wider whitespace-nowrap">Primary</div>
                <input
                  type="text"
                  className="flex-1 bg-transparent px-2 py-3.5 text-base font-medium text-text-primary placeholder:text-text-muted focus:outline-none"
                  placeholder="Enter primary Webflow URL..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={isLoading}
                  required
                />
                {!isLoading && auditType !== 'competitive' && (
                  <button
                    type="submit"
                    disabled={!url}
                    className="bg-primary hover:bg-primary-hover text-white font-semibold px-6 py-3.5 rounded-xl flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                  >
                    Run Audit
                    <ArrowRight size={16} />
                  </button>
                )}
              </div>

              {auditType === 'competitive' && (
                <div className="space-y-3 mt-4">
                  <div className="text-left px-2">
                    <span className="text-xs font-bold text-text-muted uppercase tracking-widest">Competitors (max 4)</span>
                  </div>
                  {competitors.map((comp, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="relative bg-white/60 backdrop-blur-sm rounded-xl border border-border-light p-1.5 flex items-center gap-2"
                    >
                      <input
                        type="text"
                        className="flex-1 bg-transparent px-3 py-2 text-sm font-medium text-text-primary placeholder:text-text-muted focus:outline-none"
                        placeholder="Competitor URL..."
                        value={comp}
                        onChange={(e) => updateCompetitor(idx, e.target.value)}
                        disabled={isLoading}
                      />
                      {competitors.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeCompetitor(idx)}
                          className="p-2 text-text-muted hover:text-severity-critical transition-colors"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                        </button>
                      )}
                    </motion.div>
                  ))}
                  
                  <div className="flex gap-2 pt-2">
                    {competitors.length < 4 && (
                      <button
                        type="button"
                        onClick={addCompetitor}
                        className="text-xs font-bold text-primary hover:text-primary-hover flex items-center gap-1 px-2 py-1 transition-colors"
                      >
                        <Plus size={14} /> Add Competitor
                      </button>
                    )}
                    <div className="flex-1" />
                    <button
                      type="submit"
                      disabled={isLoading || !url}
                      className="bg-primary hover:bg-primary-hover text-white font-semibold px-8 py-3 rounded-xl flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_8px_16px_rgba(40,32,255,0.2)] hover:scale-[1.02] active:scale-[0.98]"
                    >
                      Compare AI-Readiness
                      <ArrowRight size={16} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </form>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-2xl mx-auto mt-4"
            >
              <div className="bg-severity-critical-bg text-severity-critical px-4 py-3 rounded-xl text-sm font-medium border border-severity-critical/10">
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
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-3"
        >
          {pillars.map((p, i) => (
            <motion.div
              key={p.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.5 + i * 0.08 }}
              className="group bg-surface-secondary hover:bg-white border border-border-light hover:border-primary/10 rounded-xl p-4 text-center transition-all hover:shadow-[0_4px_16px_rgba(40,32,255,0.06)]"
            >
              <div className="w-10 h-10 mx-auto mb-3 rounded-lg bg-white group-hover:bg-primary/5 border border-border-light group-hover:border-primary/10 flex items-center justify-center transition-all">
                <p.icon size={18} className="text-text-muted group-hover:text-primary transition-colors" />
              </div>
              <div className="text-sm font-semibold text-text-primary mb-0.5">{p.label}</div>
              <div className="text-[11px] text-text-muted leading-tight">{p.desc}</div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  );
};
