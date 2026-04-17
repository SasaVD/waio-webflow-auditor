import { motion } from 'framer-motion';
import { Network, Bot, FileSearch } from 'lucide-react';

const differentiators = [
  {
    icon: Network,
    label: 'TIPR Framework',
    tagline: 'Link equity as a diagnostic',
    body: 'Every page classified: Star (high authority + high traffic), Question Mark (high traffic, low authority), Money Page (conversion-critical), or Orphan (zero inbound links). Turn your internal-link graph into a prioritized action list instead of a spreadsheet of URLs.',
    bullets: [
      'Star / Question Mark / Money / Orphan classification',
      'Authority + traffic cross-analysis per page',
      'Top 50 interlinking opportunities surfaced with anchor text',
    ],
    accentClass: 'text-accent',
    bgClass: 'bg-accent/[0.04]',
    ringClass: 'ring-accent/10',
  },
  {
    icon: Bot,
    label: 'AI Visibility (5 platforms)',
    tagline: 'Measure AI citations, not guesses',
    body: 'We test your brand against ChatGPT, Claude, Perplexity, Gemini, and Google AI Overview using real prompts. See exactly which AI engines mention you, which cite competitors instead, and which surface you in discovery prompts where you could be — but aren\'t.',
    bullets: [
      'Live mentions database across all 5 platforms',
      'Share of Voice vs competitor brands',
      'Discovery-prompt intelligence (who gets cited when you don\'t)',
    ],
    accentClass: 'text-secondary-cyan',
    bgClass: 'bg-secondary-cyan/[0.06]',
    ringClass: 'ring-secondary-cyan/15',
  },
  {
    icon: FileSearch,
    label: 'WDF*IDF + AI Filler',
    tagline: 'Content intelligence at term level',
    body: 'Scrape the top-ranking pages for your target query, run WDF*IDF against your own content, and flag (a) the exact terms competitors use that you don\'t, and (b) the AI-generic filler ("cutting-edge", "leverage", "robust") that weakens your SEO signal without adding substance.',
    bullets: [
      'Term-level gap analysis vs live competitor content',
      'AI-filler detector with add / increase / reduce / remove actions',
      'Content gap score + missing core term list per page',
    ],
    accentClass: 'text-success',
    bgClass: 'bg-success/[0.06]',
    ringClass: 'ring-success/15',
  },
];

export function DifferentiatorsSection() {
  return (
    <section className="relative">
      <div className="max-w-6xl mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-2xl mx-auto mb-14"
        >
          <div className="text-xs font-bold text-accent uppercase tracking-widest mb-4">
            What only WAIO Premium does
          </div>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-text leading-tight font-heading mb-4">
            Three intelligence layers
            <br />
            you won't find in any other audit tool
          </h2>
        </motion.div>

        <div className="space-y-6">
          {differentiators.map((d, i) => (
            <motion.div
              key={d.label}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className={`${d.bgClass} border border-border rounded-2xl p-6 md:p-8 grid md:grid-cols-[auto_1fr] gap-6 md:gap-8`}
            >
              <div
                className={`w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-surface ring-4 ${d.ringClass} flex items-center justify-center flex-shrink-0`}
              >
                <d.icon size={26} className={d.accentClass} />
              </div>
              <div>
                <div className="flex flex-col md:flex-row md:items-baseline md:gap-3 mb-3">
                  <h3 className="text-xl md:text-2xl font-extrabold text-text font-heading">
                    {d.label}
                  </h3>
                  <span
                    className={`text-sm font-semibold ${d.accentClass}`}
                  >
                    {d.tagline}
                  </span>
                </div>
                <p className="text-base text-text-secondary leading-relaxed mb-5">
                  {d.body}
                </p>
                <ul className="space-y-2">
                  {d.bullets.map((b) => (
                    <li
                      key={b}
                      className="flex items-start gap-2.5 text-sm text-text"
                    >
                      <span
                        className={`mt-1.5 w-1.5 h-1.5 rounded-full ${d.accentClass.replace('text-', 'bg-')} flex-shrink-0`}
                      />
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
