import { useState, useMemo } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown, Search } from 'lucide-react';

interface TermData {
  term: string;
  classification: string;
  target_frequency: number;
  target_wdf_idf: number;
  competitor_avg_frequency: number;
  competitor_avg_wdf_idf: number;
  competitor_max_wdf_idf: number;
  docs_containing: number;
  filler_category?: string;
}

interface TermTableProps {
  terms: TermData[];
}

const CLASSIFICATION_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  core: { label: 'Core', color: 'text-green-400', bg: 'bg-green-500/15' },
  semantic: { label: 'Semantic', color: 'text-blue-400', bg: 'bg-blue-500/15' },
  auxiliary: { label: 'Auxiliary', color: 'text-gray-400', bg: 'bg-gray-500/15' },
  filler: { label: 'Filler', color: 'text-red-400', bg: 'bg-red-500/15' },
};

type SortKey = 'term' | 'classification' | 'target_frequency' | 'competitor_avg_frequency' | 'gap';
type SortDir = 'asc' | 'desc';

function getGapStatus(term: TermData): { icon: string; label: string; color: string } {
  if (term.classification === 'filler') {
    return { icon: '\uD83D\uDDD1\uFE0F', label: 'Remove', color: 'text-red-400' };
  }
  if (term.target_frequency === 0 && term.docs_containing >= 3) {
    return { icon: '\u274C', label: 'Missing', color: 'text-red-400' };
  }
  if (term.target_wdf_idf > 0 && term.competitor_max_wdf_idf > 0 &&
      term.target_wdf_idf > term.competitor_max_wdf_idf * 1.5) {
    return { icon: '\u2B07\uFE0F', label: 'Reduce', color: 'text-orange-400' };
  }
  if (term.target_wdf_idf > 0 && term.competitor_avg_wdf_idf > 0 &&
      term.target_wdf_idf < term.competitor_avg_wdf_idf * 0.5) {
    return { icon: '\u2B06\uFE0F', label: 'Increase', color: 'text-yellow-400' };
  }
  return { icon: '\u2705', label: 'OK', color: 'text-green-400' };
}

export function TermTable({ terms }: TermTableProps) {
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('competitor_avg_frequency');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const filtered = useMemo(() => {
    let result = terms;
    if (filter !== 'all') {
      result = result.filter((t) => t.classification === filter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((t) => t.term.toLowerCase().includes(q));
    }
    result = [...result].sort((a, b) => {
      let va: number | string;
      let vb: number | string;
      if (sortKey === 'term') {
        va = a.term;
        vb = b.term;
      } else if (sortKey === 'classification') {
        va = a.classification;
        vb = b.classification;
      } else if (sortKey === 'gap') {
        va = a.competitor_avg_wdf_idf - a.target_wdf_idf;
        vb = b.competitor_avg_wdf_idf - b.target_wdf_idf;
      } else {
        va = a[sortKey];
        vb = b[sortKey];
      }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return result;
  }, [terms, filter, search, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <ArrowUpDown size={12} className="text-text-muted" />;
    return sortDir === 'asc'
      ? <ArrowUp size={12} className="text-accent" />
      : <ArrowDown size={12} className="text-accent" />;
  };

  const filterCounts = useMemo(() => {
    const counts: Record<string, number> = { all: terms.length };
    for (const t of terms) {
      counts[t.classification] = (counts[t.classification] || 0) + 1;
    }
    return counts;
  }, [terms]);

  return (
    <div className="space-y-3">
      {/* Filter tabs + search */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1.5">
          {['all', 'core', 'semantic', 'auxiliary', 'filler'].map((f) => {
            const isActive = filter === f;
            const config = f === 'all' ? null : CLASSIFICATION_CONFIG[f];
            return (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`text-[11px] font-semibold px-2.5 py-1.5 rounded-lg transition-all ${
                  isActive
                    ? 'bg-accent/15 text-accent'
                    : 'bg-surface-overlay text-text-muted hover:text-text-secondary'
                }`}
              >
                {f === 'all' ? 'All' : config?.label}{' '}
                <span className="opacity-60">({filterCounts[f] || 0})</span>
              </button>
            );
          })}
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search terms..."
            className="pl-8 pr-3 py-1.5 text-xs bg-surface-overlay border border-border rounded-lg text-text placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent w-48"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-surface-overlay text-text-muted">
              <th className="text-left px-3 py-2.5 font-semibold">
                <button onClick={() => toggleSort('term')} className="flex items-center gap-1 hover:text-text transition-colors">
                  Term <SortIcon col="term" />
                </button>
              </th>
              <th className="text-left px-3 py-2.5 font-semibold">
                <button onClick={() => toggleSort('classification')} className="flex items-center gap-1 hover:text-text transition-colors">
                  Type <SortIcon col="classification" />
                </button>
              </th>
              <th className="text-right px-3 py-2.5 font-semibold">
                <button onClick={() => toggleSort('target_frequency')} className="flex items-center gap-1 justify-end hover:text-text transition-colors">
                  Your Usage <SortIcon col="target_frequency" />
                </button>
              </th>
              <th className="text-right px-3 py-2.5 font-semibold">
                <button onClick={() => toggleSort('competitor_avg_frequency')} className="flex items-center gap-1 justify-end hover:text-text transition-colors">
                  Comp. Avg <SortIcon col="competitor_avg_frequency" />
                </button>
              </th>
              <th className="text-right px-3 py-2.5 font-semibold hidden sm:table-cell">
                Comp. Max
              </th>
              <th className="text-center px-3 py-2.5 font-semibold">
                <button onClick={() => toggleSort('gap')} className="flex items-center gap-1 justify-center hover:text-text transition-colors">
                  Gap <SortIcon col="gap" />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((term, i) => {
              const config = CLASSIFICATION_CONFIG[term.classification] || CLASSIFICATION_CONFIG.auxiliary;
              const gap = getGapStatus(term);
              return (
                <tr
                  key={term.term}
                  className={`border-t border-border hover:bg-surface-overlay/50 transition-colors ${
                    i % 2 === 0 ? '' : 'bg-surface-overlay/20'
                  }`}
                >
                  <td className="px-3 py-2 font-medium text-text max-w-[200px] truncate">
                    {term.term}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${config.bg} ${config.color}`}>
                      {config.label}
                    </span>
                  </td>
                  <td className="text-right px-3 py-2 font-mono text-text-secondary">
                    {term.target_frequency}x
                  </td>
                  <td className="text-right px-3 py-2 font-mono text-text-secondary">
                    {term.competitor_avg_frequency.toFixed(1)}x
                  </td>
                  <td className="text-right px-3 py-2 font-mono text-text-secondary hidden sm:table-cell">
                    {term.competitor_max_wdf_idf.toFixed(4)}
                  </td>
                  <td className="text-center px-3 py-2">
                    <span className={`text-[10px] font-bold ${gap.color}`}>
                      {gap.icon} {gap.label}
                    </span>
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-8 text-text-muted">
                  No terms match your filters
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="text-[10px] text-text-muted text-right">
        Showing {filtered.length} of {terms.length} terms
      </div>
    </div>
  );
}
