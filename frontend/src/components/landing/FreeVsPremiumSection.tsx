import { motion } from 'framer-motion';
import { Check, X, Crown, ArrowRight } from 'lucide-react';

interface ComparisonRow {
  feature: string;
  description?: string;
  free: string | boolean;
  premium: string | boolean;
  highlight?: boolean;
}

const rows: ComparisonRow[] = [
  {
    feature: '10-pillar audit engine',
    description: 'Every deterministic check, every pillar',
    free: 'Single page',
    premium: 'Full site · up to 2,000 pages',
  },
  {
    feature: 'Findings + recommendations',
    free: true,
    premium: true,
  },
  {
    feature: 'Score breakdown + credibility anchors',
    free: true,
    premium: true,
  },
  {
    feature: 'PDF / Markdown export',
    free: true,
    premium: true,
  },
  {
    feature: 'Executive summary',
    description: 'Strategic diagnostic brief, zero LLM guessing',
    free: false,
    premium: true,
  },
  {
    feature: 'TIPR internal-linking framework',
    description: 'Star · Question Mark · Orphan classification + link-equity flow',
    free: false,
    premium: true,
    highlight: true,
  },
  {
    feature: 'AI Visibility across 5 platforms',
    description: 'ChatGPT · Claude · Perplexity · Gemini · Google AI Overview',
    free: false,
    premium: true,
    highlight: true,
  },
  {
    feature: 'WDF*IDF content gap analysis',
    description: 'Competitor-scraped term gaps + AI-generic filler detection',
    free: false,
    premium: true,
    highlight: true,
  },
  {
    feature: 'Topic cluster detection',
    description: 'Google NLP entity + category classification',
    free: false,
    premium: true,
  },
  {
    feature: 'Link graph visualization',
    description: 'Interactive force-directed graph of your whole site',
    free: false,
    premium: true,
  },
  {
    feature: 'Webflow fix instructions',
    description: '54 curated step-by-step guides mapped to findings',
    free: false,
    premium: true,
  },
  {
    feature: 'CMS migration assessment',
    description: 'WordPress · Shopify · Wix · Squarespace · Framer intelligence',
    free: false,
    premium: true,
  },
  {
    feature: 'Competitor benchmarking',
    description: 'Side-by-side audit of up to 4 competitors',
    free: false,
    premium: true,
  },
];

function Cell({ value }: { value: string | boolean }) {
  if (value === true) {
    return (
      <div className="flex justify-center">
        <div className="w-6 h-6 rounded-full bg-success/10 flex items-center justify-center">
          <Check size={14} className="text-success" strokeWidth={3} />
        </div>
      </div>
    );
  }
  if (value === false) {
    return (
      <div className="flex justify-center">
        <div className="w-6 h-6 rounded-full bg-surface-overlay flex items-center justify-center">
          <X size={14} className="text-text-muted" />
        </div>
      </div>
    );
  }
  return (
    <div className="text-center text-sm font-semibold text-text">{value}</div>
  );
}

export function FreeVsPremiumSection() {
  return (
    <section className="relative bg-surface-raised border-y border-border">
      <div className="max-w-6xl mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-2xl mx-auto mb-12"
        >
          <div className="text-xs font-bold text-accent uppercase tracking-widest mb-4">
            Free vs Premium
          </div>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-text leading-tight font-heading mb-4">
            Same engine. Premium unlocks the intelligence layers.
          </h2>
          <p className="text-base text-text-secondary leading-relaxed">
            The free tier is a full 10-pillar diagnostic — not a teaser. Premium
            adds the cross-page intelligence that turns findings into a
            strategy.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-40px' }}
          transition={{ duration: 0.6 }}
          className="bg-surface border border-border rounded-2xl overflow-hidden shadow-card"
        >
          {/* Header */}
          <div className="grid grid-cols-[1fr_160px_180px] md:grid-cols-[1.6fr_180px_200px] border-b border-border bg-surface-overlay">
            <div className="px-4 md:px-6 py-5">
              <div className="text-xs font-bold text-text-muted uppercase tracking-widest">
                Capability
              </div>
            </div>
            <div className="px-3 md:px-4 py-5 border-l border-border text-center">
              <div className="text-xs font-bold text-text-muted uppercase tracking-widest mb-1">
                Free
              </div>
              <div className="text-sm font-bold text-text">$0</div>
            </div>
            <div className="px-3 md:px-4 py-5 border-l border-border text-center bg-accent/5 relative">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <Crown size={12} className="text-accent" />
                <div className="text-xs font-bold text-accent uppercase tracking-widest">
                  Premium
                </div>
              </div>
              <div className="text-sm font-bold text-text">$4,500 / audit</div>
            </div>
          </div>

          {/* Rows */}
          <div className="divide-y divide-border">
            {rows.map((row) => (
              <div
                key={row.feature}
                className={`grid grid-cols-[1fr_160px_180px] md:grid-cols-[1.6fr_180px_200px] ${
                  row.highlight ? 'bg-accent/[0.02]' : ''
                }`}
              >
                <div className="px-4 md:px-6 py-4">
                  <div
                    className={`text-sm ${
                      row.highlight
                        ? 'font-bold text-text'
                        : 'font-semibold text-text'
                    }`}
                  >
                    {row.feature}
                    {row.highlight && (
                      <span className="ml-2 text-[10px] font-bold text-accent uppercase tracking-wider">
                        Key differentiator
                      </span>
                    )}
                  </div>
                  {row.description && (
                    <div className="text-xs text-text-muted mt-1 leading-relaxed">
                      {row.description}
                    </div>
                  )}
                </div>
                <div className="px-3 md:px-4 py-4 border-l border-border flex items-center justify-center">
                  <Cell value={row.free} />
                </div>
                <div className="px-3 md:px-4 py-4 border-l border-border flex items-center justify-center bg-accent/[0.02]">
                  <Cell value={row.premium} />
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* CTA row */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-40px' }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="flex flex-col md:flex-row items-center justify-center gap-3 mt-8"
        >
          <a
            href="#audit-form"
            className="bg-surface border border-border hover:border-accent text-text font-semibold px-6 py-3 rounded-xl flex items-center gap-2 transition-all"
          >
            Run a free audit
            <ArrowRight size={14} />
          </a>
          <a
            href="mailto:sasa@vezadigital.com?subject=WAIO%20Premium%20Audit%20Inquiry"
            className="bg-accent hover:bg-accent-hover text-white font-semibold px-6 py-3 rounded-xl flex items-center gap-2 transition-all hover:shadow-glow-accent"
          >
            <Crown size={14} />
            Request Premium audit
          </a>
        </motion.div>
      </div>
    </section>
  );
}
