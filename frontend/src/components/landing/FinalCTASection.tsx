import { motion } from 'framer-motion';
import { ArrowRight, Crown } from 'lucide-react';

export function FinalCTASection() {
  return (
    <section className="relative bg-surface-raised border-t border-border">
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6 }}
        >
          <div className="text-xs font-bold text-accent uppercase tracking-widest mb-4">
            Start free · Upgrade when you're ready
          </div>
          <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-text leading-[1.1] font-heading mb-5">
            See where your site stands
            <br />
            <span className="text-accent">in under 60 seconds.</span>
          </h2>
          <p className="text-base md:text-lg text-text-secondary leading-relaxed max-w-2xl mx-auto mb-10">
            Paste a URL, get a full 10-pillar diagnostic with specific findings,
            severity ratings, and credibility-anchored recommendations. No
            signup, no credit card, no email wall.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-6">
            <a
              href="#audit-form"
              className="bg-accent hover:bg-accent-hover text-white font-semibold px-7 py-3.5 rounded-xl flex items-center gap-2 transition-all hover:shadow-glow-accent"
            >
              Run a free audit
              <ArrowRight size={16} />
            </a>
            <a
              href="mailto:sasa@vezadigital.com?subject=WAIO%20Premium%20Audit%20Inquiry"
              className="bg-surface border border-border hover:border-accent text-text font-semibold px-7 py-3.5 rounded-xl flex items-center gap-2 transition-all"
            >
              <Crown size={14} />
              Inquire about Premium
            </a>
          </div>

          <p className="text-xs text-text-muted">
            Validated against W3C · WCAG 2.1 · Schema.org · Google Web Vitals
          </p>
        </motion.div>
      </div>
    </section>
  );
}
