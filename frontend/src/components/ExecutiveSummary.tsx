import { motion } from 'framer-motion';
import {
  FileText, AlertTriangle, TrendingUp, Target, Trophy, Users
} from 'lucide-react';

interface ExecutiveSummaryProps {
  markdown: string;
}

interface Section {
  title: string;
  icon: React.ElementType;
  content: string;
}

function parseMarkdownSections(md: string): Section[] {
  const iconMap: Record<string, React.ElementType> = {
    'Overall Assessment': FileText,
    'Top Strategic Risks': AlertTriangle,
    'Top Strengths': Trophy,
    'ROI Projection': TrendingUp,
    'Prioritized Action Plan': Target,
    'Competitor Context': Users,
  };

  const parts = md.split(/^## /gm).filter(Boolean);
  return parts.map((part) => {
    const newlineIdx = part.indexOf('\n');
    const title = part.slice(0, newlineIdx).trim();
    const content = part.slice(newlineIdx + 1).trim();
    return { title, icon: iconMap[title] || FileText, content };
  });
}

function renderInlineMarkdown(text: string): React.ReactNode[] {
  // Split on bold markers **...**
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-semibold text-text-primary">{part.slice(2, -2)}</strong>;
    }
    // Handle italic *...*
    if (part.startsWith('*') && part.endsWith('*') && !part.startsWith('**')) {
      return <em key={i} className="text-text-muted text-sm">{part.slice(1, -1)}</em>;
    }
    return <span key={i}>{part}</span>;
  });
}

function renderMarkdownTable(lines: string[]): React.ReactNode {
  const headerLine = lines[0];
  const dataLines = lines.slice(2); // skip separator
  const headers = headerLine.split('|').map(h => h.trim()).filter(Boolean);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-border">
            {headers.map((h, i) => (
              <th key={i} className="text-left py-2 px-3 font-semibold text-text-primary">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataLines.map((line, rowIdx) => {
            const cells = line.split('|').map(c => c.trim()).filter(Boolean);
            return (
              <tr key={rowIdx} className="border-b border-border-light hover:bg-surface-secondary/50 transition-colors">
                {cells.map((cell, colIdx) => (
                  <td key={colIdx} className="py-2 px-3 text-text-secondary">
                    {renderInlineMarkdown(cell)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SectionContent({ content }: { content: string }) {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Table detection
    if (line.startsWith('|') && i + 1 < lines.length && lines[i + 1].startsWith('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].startsWith('|')) {
        tableLines.push(lines[i]);
        i++;
      }
      elements.push(<div key={`table-${i}`} className="mt-3">{renderMarkdownTable(tableLines)}</div>);
      continue;
    }

    // Blank line
    if (!line.trim()) {
      i++;
      continue;
    }

    // List item
    if (line.startsWith('- ')) {
      const listItems: string[] = [];
      while (i < lines.length && lines[i].startsWith('- ')) {
        listItems.push(lines[i].slice(2));
        i++;
      }
      elements.push(
        <ul key={`list-${i}`} className="space-y-1.5 mt-2">
          {listItems.map((item, idx) => (
            <li key={idx} className="flex gap-2 text-sm text-text-secondary">
              <span className="text-primary mt-1">&#x2022;</span>
              <span>{renderInlineMarkdown(item)}</span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Indented italic line (credibility anchor)
    if (line.startsWith('   *') && line.endsWith('*')) {
      elements.push(
        <p key={`anchor-${i}`} className="text-xs text-text-muted italic ml-4 -mt-1 mb-2">
          {line.trim().slice(1, -1)}
        </p>
      );
      i++;
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={`p-${i}`} className="text-sm text-text-secondary leading-relaxed mt-2">
        {renderInlineMarkdown(line)}
      </p>
    );
    i++;
  }

  return <>{elements}</>;
}

export const ExecutiveSummary: React.FC<ExecutiveSummaryProps> = ({ markdown }) => {
  const sections = parseMarkdownSections(markdown);

  if (!sections.length) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.12 }}
      className="mb-4"
    >
      <div className="bg-white rounded-2xl border border-border-light overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-primary/5 to-accent/5 border-b border-border-light px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <FileText className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-text-primary">Executive Summary</h2>
              <p className="text-xs text-text-muted">Premium diagnostic overview</p>
            </div>
          </div>
        </div>

        {/* Sections */}
        <div className="divide-y divide-border-light">
          {sections.map((section, idx) => (
            <div key={idx} className="px-6 py-5">
              <div className="flex items-center gap-2 mb-3">
                <section.icon className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-bold text-text-primary uppercase tracking-wide">
                  {section.title}
                </h3>
              </div>
              <SectionContent content={section.content} />
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
};
