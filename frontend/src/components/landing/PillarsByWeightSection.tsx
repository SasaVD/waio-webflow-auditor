import { motion } from 'framer-motion';
import {
  Code2,
  FileJson,
  Link2,
  BookOpen,
  Layers,
  Radio,
  Accessibility,
  ShieldCheck,
  Paintbrush,
  Zap,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface Pillar {
  icon: LucideIcon;
  label: string;
  weight: number;
  desc: string;
}

interface PillarGroup {
  label: string;
  subtitle: string;
  weight: number;
  accent: string;
  dot: string;
  pillars: Pillar[];
}

const groups: PillarGroup[] = [
  {
    label: 'Search & Discovery',
    subtitle: 'How Google understands and ranks your content',
    weight: 36,
    accent: 'text-accent',
    dot: 'bg-accent',
    pillars: [
      {
        icon: Code2,
        label: 'Semantic HTML',
        weight: 12,
        desc: 'Proper heading hierarchy, landmarks, and meaningful markup',
      },
      {
        icon: FileJson,
        label: 'Structured Data',
        weight: 12,
        desc: 'Schema.org JSON-LD for rich results and entity clarity',
      },
      {
        icon: Link2,
        label: 'Internal Linking',
        weight: 12,
        desc: 'Link equity flow, orphan pages, and site architecture',
      },
    ],
  },
  {
    label: 'AI Readiness',
    subtitle: 'Get cited by ChatGPT, Claude, Perplexity & Gemini',
    weight: 28,
    accent: 'text-secondary-cyan',
    dot: 'bg-secondary-cyan',
    pillars: [
      {
        icon: BookOpen,
        label: 'AEO Content',
        weight: 10,
        desc: 'Answer-engine-friendly structure, Q&A format, citations',
      },
      {
        icon: Layers,
        label: 'RAG Readiness',
        weight: 10,
        desc: 'Readable by retrieval-augmented generation pipelines',
      },
      {
        icon: Radio,
        label: 'Agentic Protocols',
        weight: 8,
        desc: 'llms.txt, robots directives, and AI agent compatibility',
      },
    ],
  },
  {
    label: 'Foundations',
    subtitle: 'Inclusive, compliant, and trustworthy',
    weight: 26,
    accent: 'text-success',
    dot: 'bg-success',
    pillars: [
      {
        icon: Accessibility,
        label: 'Accessibility',
        weight: 18,
        desc: 'WCAG 2.1 compliance — ARIA, contrast, keyboard, screen readers',
      },
      {
        icon: ShieldCheck,
        label: 'Data Integrity',
        weight: 8,
        desc: 'Tracking accuracy, canonical correctness, crawl directives',
      },
    ],
  },
  {
    label: 'UX & Performance',
    subtitle: 'Fast, clean code for real devices',
    weight: 10,
    accent: 'text-secondary-blue',
    dot: 'bg-secondary-blue',
    pillars: [
      {
        icon: Paintbrush,
        label: 'CSS Quality',
        weight: 5,
        desc: 'Maintainability, unused styles, and render-blocking CSS',
      },
      {
        icon: Zap,
        label: 'JS Performance',
        weight: 5,
        desc: 'Bundle size, render-blocking scripts, and third-party bloat',
      },
    ],
  },
];

export function PillarsByWeightSection() {
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
            The 10 pillars · weighted to reality
          </div>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-text leading-tight font-heading mb-4">
            Every score backed by a reproducible check
          </h2>
          <p className="text-base text-text-secondary leading-relaxed">
            Weights reflect how much each pillar actually moves the needle on
            visibility, discoverability, and compliance. No LLMs, no
            hand-waving — every finding cites a specific HTML element and a
            verified study.
          </p>
        </motion.div>

        <div className="space-y-8">
          {groups.map((group, gi) => (
            <motion.div
              key={group.label}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.5, delay: gi * 0.08 }}
              className="bg-surface-raised border border-border rounded-2xl p-6 md:p-8"
            >
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6 pb-5 border-b border-border">
                <div>
                  <div className="flex items-center gap-2.5 mb-1.5">
                    <span className={`w-2 h-2 rounded-full ${group.dot}`} />
                    <h3 className="text-lg font-bold text-text font-heading">
                      {group.label}
                    </h3>
                  </div>
                  <p className="text-sm text-text-secondary">
                    {group.subtitle}
                  </p>
                </div>
                <div className="flex items-baseline gap-1.5">
                  <span
                    className={`text-3xl font-extrabold font-heading ${group.accent}`}
                  >
                    {group.weight}%
                  </span>
                  <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                    of score
                  </span>
                </div>
              </div>

              <div
                className={`grid gap-3 ${
                  group.pillars.length === 3
                    ? 'md:grid-cols-3'
                    : 'md:grid-cols-2'
                }`}
              >
                {group.pillars.map((p) => (
                  <div
                    key={p.label}
                    className="group bg-surface border border-border hover:border-accent/30 rounded-xl p-4 transition-all"
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="w-9 h-9 rounded-lg bg-surface-raised flex items-center justify-center">
                        <p.icon size={16} className="text-text-secondary" />
                      </div>
                      <span className="text-[11px] font-bold text-text-muted uppercase tracking-wider">
                        {p.weight}%
                      </span>
                    </div>
                    <div className="text-sm font-bold text-text mb-1">
                      {p.label}
                    </div>
                    <p className="text-xs text-text-muted leading-relaxed">
                      {p.desc}
                    </p>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
