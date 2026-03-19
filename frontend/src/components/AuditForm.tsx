import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Shield, Code2, FileJson, Accessibility, Paintbrush, BookOpen, Layers, Radio, ShieldCheck } from 'lucide-react';

interface AuditFormProps {
  onRunAudit: (url: string) => void;
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
];

export const AuditForm: React.FC<AuditFormProps> = ({ onRunAudit, isLoading, error }) => {
  const [url, setUrl] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;
    let submitUrl = url.trim();
    if (!submitUrl.startsWith('http://') && !submitUrl.startsWith('https://')) {
      submitUrl = 'https://' + submitUrl;
    }
    onRunAudit(submitUrl);
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
              9-Pillar Deterministic Analysis
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
            <div className="relative bg-white rounded-2xl border border-gray-200 shadow-[0_4px_24px_rgba(0,0,0,0.06)] p-2 flex items-center gap-2 transition-shadow hover:shadow-[0_8px_32px_rgba(40,32,255,0.08)] focus-within:shadow-[0_8px_32px_rgba(40,32,255,0.12)] focus-within:border-primary/20">
              <input
                type="text"
                className="flex-1 bg-transparent px-4 py-3.5 text-base font-medium text-text-primary placeholder:text-text-muted focus:outline-none"
                placeholder="Enter your Webflow site URL..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isLoading}
                required
              />
              <button
                type="submit"
                disabled={isLoading || !url}
                className="bg-primary hover:bg-primary-hover text-white font-semibold px-6 py-3.5 rounded-xl flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
              >
                Run Audit
                <ArrowRight size={16} />
              </button>
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
