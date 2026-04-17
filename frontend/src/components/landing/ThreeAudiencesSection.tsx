import { motion } from 'framer-motion';
import { Users, Search, Sparkles } from 'lucide-react';

const audiences = [
  {
    icon: Users,
    label: 'Humans',
    headline: 'Your visitors expect it to just work.',
    body: 'Fast page loads, clean typography, inclusive markup. We measure Core Web Vitals, accessibility against WCAG 2.1, and CSS/JS bloat that slows down real devices.',
    footerLabel: 'Accessibility · Performance · UX',
    color: 'text-secondary-blue',
    ring: 'ring-secondary-blue/10',
  },
  {
    icon: Search,
    label: 'Search Engines',
    headline: "Google still pays the bills.",
    body: 'Structured data, semantic HTML, internal linking, clean site architecture. We audit the deterministic signals Google and Bing use to understand and rank content.',
    footerLabel: 'Schema.org · Semantic HTML · Internal Linking',
    color: 'text-accent',
    ring: 'ring-accent/10',
  },
  {
    icon: Sparkles,
    label: 'AI Systems & Agents',
    headline: 'The next search interface is already here.',
    body: 'ChatGPT, Claude, Perplexity, Gemini and Google AI Overview cite sites with clean AEO content, RAG-ready structure, and agent-readable protocols (llms.txt, robots directives).',
    footerLabel: 'AEO · RAG Readiness · Agentic Protocols',
    color: 'text-secondary-cyan',
    ring: 'ring-secondary-cyan/10',
  },
];

export function ThreeAudiencesSection() {
  return (
    <section className="relative bg-surface-raised border-y border-border">
      <div className="max-w-6xl mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-2xl mx-auto mb-14"
        >
          <div className="text-xs font-bold text-accent uppercase tracking-widest mb-4">
            Built for three audiences
          </div>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-text leading-tight font-heading">
            Most audits optimize for one.
            <br />
            WAIO measures all three.
          </h2>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-5">
          {audiences.map((a, i) => (
            <motion.div
              key={a.label}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="bg-surface border border-border rounded-2xl p-6 hover:shadow-card-hover transition-all"
            >
              <div
                className={`w-11 h-11 rounded-xl bg-surface-raised ring-4 ${a.ring} flex items-center justify-center mb-5`}
              >
                <a.icon size={20} className={a.color} />
              </div>
              <div className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2">
                {a.label}
              </div>
              <h3 className="text-xl font-bold text-text mb-3 font-heading leading-snug">
                {a.headline}
              </h3>
              <p className="text-sm text-text-secondary leading-relaxed mb-5">
                {a.body}
              </p>
              <div className="pt-4 border-t border-border">
                <div className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
                  {a.footerLabel}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
