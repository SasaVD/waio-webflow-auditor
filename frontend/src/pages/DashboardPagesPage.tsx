import { useMemo, useState } from 'react';
import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Globe,
  Info,
  Loader2,
  AlertCircle,
  ExternalLink,
  Search,
  ArrowUpDown,
  AlertTriangle,
} from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';
import { useEnrichmentPolling } from '../hooks/useEnrichmentPolling';

interface PageNode {
  id: string;
  label: string;
  cluster: number;
  inbound: number;
  outbound: number;
  depth: number | null;
  is_orphan: boolean;
}

type SortField = 'url' | 'inbound' | 'outbound' | 'depth';
type SortDir = 'asc' | 'desc';

export default function DashboardPagesPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);
  const enrichment = useEnrichmentPolling(auditId);

  const [search, setSearch] = useState('');
  const [sortField, setSortField] = useState<SortField>('inbound');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [filterOrphans, setFilterOrphans] = useState(false);

  const nodes: PageNode[] = useMemo(() => {
    const graph = report?.link_analysis?.graph;
    if (!graph?.nodes) return [];
    return graph.nodes as PageNode[];
  }, [report]);

  const crawlStats = report?.crawl_stats as Record<string, number> | null;
  const hasData = nodes.length > 0;

  // Filter and sort
  const filteredNodes = useMemo(() => {
    let result = nodes;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (n) => n.id.toLowerCase().includes(q) || n.label.toLowerCase().includes(q)
      );
    }
    if (filterOrphans) {
      result = result.filter((n) => n.is_orphan);
    }
    result = [...result].sort((a, b) => {
      let av: number | string, bv: number | string;
      switch (sortField) {
        case 'url':
          av = a.id;
          bv = b.id;
          break;
        case 'inbound':
          av = a.inbound;
          bv = b.inbound;
          break;
        case 'outbound':
          av = a.outbound;
          bv = b.outbound;
          break;
        case 'depth':
          av = a.depth ?? 999;
          bv = b.depth ?? 999;
          break;
        default:
          return 0;
      }
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return result;
  }, [nodes, search, filterOrphans, sortField, sortDir]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const orphanCount = nodes.filter((n) => n.is_orphan).length;

  // Extract path from full URL
  const urlPath = (url: string) => {
    try {
      return new URL(url).pathname || '/';
    } catch {
      return url;
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <Link
          to={`/dashboard/${auditId}`}
          className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text transition-colors mb-4"
        >
          <ArrowLeft size={12} />
          Back to Overview
        </Link>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center">
            <Globe size={20} className="text-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text font-heading">Crawled Pages</h1>
            <p className="text-sm text-text-secondary mt-0.5">
              All pages discovered during the DataForSEO site crawl.
            </p>
          </div>
        </div>
      </motion.div>

      {/* Loading state */}
      {!hasData && enrichment.status === 'polling' ? (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-raised border border-border rounded-xl p-10 text-center"
        >
          <Loader2 size={32} className="text-indigo-500 animate-spin mx-auto mb-4" />
          <p className="text-sm font-semibold text-text mb-1">
            Site crawl in progress
          </p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Page data will appear once the DataForSEO crawl completes. This typically takes 2-5 minutes.
          </p>
          {enrichment.progress && (
            <p className="text-xs text-indigo-600 mt-3">{enrichment.progress}</p>
          )}
        </motion.div>
      ) : !hasData && enrichment.status === 'failed' ? (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-raised border border-border rounded-xl p-10 text-center"
        >
          <AlertCircle size={32} className="text-amber-500 mx-auto mb-4" />
          <p className="text-sm font-semibold text-text mb-1">
            Crawl data could not be generated
          </p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Please try running the audit again.
          </p>
        </motion.div>
      ) : hasData ? (
        <>
          {/* Stats row */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="grid grid-cols-2 sm:grid-cols-4 gap-3"
          >
            <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-text font-heading">{nodes.length}</div>
              <div className="text-[10px] text-text-muted uppercase tracking-wider mt-1">Pages Found</div>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-text font-heading">
                {crawlStats?.internal_links?.toLocaleString() ?? '—'}
              </div>
              <div className="text-[10px] text-text-muted uppercase tracking-wider mt-1">Internal Links</div>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
              <div className={`text-2xl font-bold font-heading ${orphanCount > 0 ? 'text-amber-600' : 'text-success'}`}>
                {orphanCount}
              </div>
              <div className="text-[10px] text-text-muted uppercase tracking-wider mt-1">Orphan Pages</div>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-text font-heading">
                {crawlStats?.broken_links ?? 0}
              </div>
              <div className="text-[10px] text-text-muted uppercase tracking-wider mt-1">Broken Links</div>
            </div>
          </motion.div>

          {/* Search & filters */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="flex flex-col sm:flex-row gap-3"
          >
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                placeholder="Search pages..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2.5 bg-surface-raised border border-border rounded-lg text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
              />
            </div>
            <button
              onClick={() => setFilterOrphans(!filterOrphans)}
              className={`px-4 py-2.5 rounded-lg text-xs font-semibold border transition-all flex items-center gap-1.5 ${
                filterOrphans
                  ? 'bg-amber-50 border-amber-200 text-amber-700'
                  : 'bg-surface-raised border-border text-text-muted hover:text-text'
              }`}
            >
              <AlertTriangle size={12} />
              Orphans Only {filterOrphans && `(${orphanCount})`}
            </button>
          </motion.div>

          {/* Table */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="bg-surface-raised border border-border rounded-xl overflow-hidden"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                      <button onClick={() => toggleSort('url')} className="flex items-center gap-1 hover:text-text">
                        URL Path
                        <ArrowUpDown size={10} />
                      </button>
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-wider hidden sm:table-cell">
                      Title
                    </th>
                    <th className="text-center px-3 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                      <button onClick={() => toggleSort('depth')} className="flex items-center gap-1 hover:text-text mx-auto">
                        Depth
                        <ArrowUpDown size={10} />
                      </button>
                    </th>
                    <th className="text-center px-3 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                      <button onClick={() => toggleSort('inbound')} className="flex items-center gap-1 hover:text-text mx-auto">
                        In
                        <ArrowUpDown size={10} />
                      </button>
                    </th>
                    <th className="text-center px-3 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                      <button onClick={() => toggleSort('outbound')} className="flex items-center gap-1 hover:text-text mx-auto">
                        Out
                        <ArrowUpDown size={10} />
                      </button>
                    </th>
                    <th className="text-center px-3 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredNodes.slice(0, 200).map((node) => (
                    <tr
                      key={node.id}
                      className="border-b border-border/50 hover:bg-surface-overlay/50 transition-colors"
                    >
                      <td className="px-4 py-2.5">
                        <a
                          href={node.id}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-accent hover:text-accent-hover font-medium inline-flex items-center gap-1 max-w-xs truncate"
                        >
                          {urlPath(node.id)}
                          <ExternalLink size={10} className="flex-shrink-0 opacity-50" />
                        </a>
                      </td>
                      <td className="px-4 py-2.5 text-text-secondary text-xs truncate max-w-[200px] hidden sm:table-cell">
                        {node.label}
                      </td>
                      <td className="px-3 py-2.5 text-center text-xs text-text-secondary">
                        {node.depth ?? '—'}
                      </td>
                      <td className="px-3 py-2.5 text-center text-xs font-semibold text-text">
                        {node.inbound}
                      </td>
                      <td className="px-3 py-2.5 text-center text-xs text-text-secondary">
                        {node.outbound}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        {node.is_orphan ? (
                          <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full">
                            Orphan
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold text-success bg-success/10 px-2 py-0.5 rounded-full">
                            OK
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filteredNodes.length > 200 && (
              <div className="px-4 py-3 border-t border-border text-xs text-text-muted text-center">
                Showing 200 of {filteredNodes.length} pages. Use search to filter.
              </div>
            )}
            {filteredNodes.length === 0 && (
              <div className="px-4 py-8 text-center text-sm text-text-muted">
                {search ? 'No pages match your search.' : 'No pages found.'}
              </div>
            )}
          </motion.div>
        </>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-surface-raised border border-border rounded-xl p-8 text-center"
        >
          <div className="w-12 h-12 mx-auto mb-4 bg-surface-overlay rounded-xl flex items-center justify-center">
            <Info size={20} className="text-text-muted" />
          </div>
          <p className="text-sm font-semibold text-text mb-1">
            Page Data Not Available
          </p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Page-level crawl data will be available after a premium audit with DataForSEO configured.
          </p>
        </motion.div>
      )}
    </div>
  );
}
