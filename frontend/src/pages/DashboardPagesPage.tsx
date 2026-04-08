import { useMemo, useState, useEffect } from 'react';
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
  RefreshCw,
  FileSearch,
} from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';
import { useEnrichmentPolling } from '../hooks/useEnrichmentPolling';

const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

interface PageNode {
  id: string;
  label: string;
  cluster: number;
  inbound: number;
  outbound: number;
  depth: number | null;
  is_orphan: boolean;
}

interface PageAuditRef {
  audit_id: string;
  score: number;
  label: string;
}

const scoreBadgeColor = (score: number): string => {
  if (score >= 85) return 'text-green-700 bg-green-50 border-green-200';
  if (score >= 70) return 'text-yellow-700 bg-yellow-50 border-yellow-200';
  if (score >= 50) return 'text-orange-700 bg-orange-50 border-orange-200';
  return 'text-red-700 bg-red-50 border-red-200';
};

type SortField = 'url' | 'inbound' | 'outbound' | 'depth' | 'pr_score' | 'tipr_rank';
type SortDir = 'asc' | 'desc';

interface TiprPageInfo {
  pagerank_score: number;
  cheirank_score: number;
  tipr_rank: number;
  classification: string;
}

const CLASSIFICATION_BADGE: Record<string, string> = {
  star: 'text-green-700 bg-green-50 border-green-200',
  hoarder: 'text-amber-700 bg-amber-50 border-amber-200',
  waster: 'text-red-700 bg-red-50 border-red-200',
  dead_weight: 'text-gray-600 bg-gray-50 border-gray-200',
};

export default function DashboardPagesPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);
  const enrichment = useEnrichmentPolling(auditId);

  const [search, setSearch] = useState('');
  const [sortField, setSortField] = useState<SortField>('inbound');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [filterOrphans, setFilterOrphans] = useState(false);

  // Page audit tracking
  const [pageAudits, setPageAudits] = useState<Record<string, PageAuditRef>>({});
  const [runningAudits, setRunningAudits] = useState<Set<string>>(new Set());

  // Load existing page audits from the parent report
  useEffect(() => {
    const pa = report?.page_audits as Record<string, PageAuditRef> | undefined;
    if (pa) setPageAudits(pa);
  }, [report?.page_audits]);

  // Also fetch from API to get the latest (covers case where report was cached before audit ran)
  useEffect(() => {
    if (!auditId) return;
    fetch(`${apiBase}/api/audit/${auditId}/page-audits`, { credentials: 'include' })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data?.page_audits) {
          setPageAudits((prev) => ({ ...prev, ...data.page_audits }));
        }
      })
      .catch(() => {});
  }, [auditId]);

  const handleRunAudit = async (url: string) => {
    setRunningAudits((prev) => new Set(prev).add(url));
    try {
      const res = await fetch(`${apiBase}/api/audit/page`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ url, parent_audit_id: auditId }),
      });
      if (res.ok) {
        const data = await res.json();
        setPageAudits((prev) => ({
          ...prev,
          [url]: {
            audit_id: data.audit_id,
            score: data.overall_score ?? 0,
            label: data.overall_label ?? '',
          },
        }));
      }
    } catch {
      // Silently fail — user can retry
    } finally {
      setRunningAudits((prev) => {
        const next = new Set(prev);
        next.delete(url);
        return next;
      });
    }
  };

  const nodes: PageNode[] = useMemo(() => {
    const graph = report?.link_analysis?.graph;
    if (!graph?.nodes) return [];
    return graph.nodes as PageNode[];
  }, [report]);

  const tiprLookup = useMemo(() => {
    const tipr = report?.tipr_analysis as Record<string, any> | null;
    if (!tipr?.pages) return new Map<string, TiprPageInfo>();
    return new Map(
      (tipr.pages as any[]).map((p: any) => [
        p.url,
        {
          pagerank_score: p.pagerank_score ?? 0,
          cheirank_score: p.cheirank_score ?? 0,
          tipr_rank: p.tipr_rank ?? 0,
          classification: p.classification ?? '',
        },
      ])
    );
  }, [report]);
  const hasTipr = tiprLookup.size > 0;

  const crawlStats = report?.crawl_stats as Record<string, number> | null;
  const hasData = nodes.length > 0;

  // Compute link stats from graph data when crawl_stats is missing or zero
  const linkStats = useMemo(() => {
    const graphLinks = (report?.link_analysis as Record<string, any>)?.graph?.links;
    const computedLinkCount = Array.isArray(graphLinks) ? graphLinks.length : 0;
    const computedBroken = nodes.filter((n) => {
      const status = (n as Record<string, any>).status_code;
      return status && status !== 200;
    }).length;
    return {
      internalLinks: crawlStats?.internal_links || computedLinkCount,
      brokenLinks: crawlStats?.broken_links ?? computedBroken,
    };
  }, [report, nodes, crawlStats]);

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
        case 'pr_score':
          av = tiprLookup.get(a.id)?.pagerank_score ?? -1;
          bv = tiprLookup.get(b.id)?.pagerank_score ?? -1;
          break;
        case 'tipr_rank':
          av = tiprLookup.get(a.id)?.tipr_rank ?? 99999;
          bv = tiprLookup.get(b.id)?.tipr_rank ?? 99999;
          break;
        default:
          return 0;
      }
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return result;
  }, [nodes, search, filterOrphans, sortField, sortDir, tiprLookup]);

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
      {!hasData && (enrichment.status === 'polling' || enrichment.status === 'timed_out') ? (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-raised border border-border rounded-xl p-10 text-center"
        >
          <Loader2 size={32} className="text-indigo-500 animate-spin mx-auto mb-4" />
          <p className="text-sm font-semibold text-text mb-1">
            {enrichment.status === 'timed_out'
              ? 'The site crawl is still processing'
              : 'Site crawl in progress'}
          </p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            {enrichment.status === 'timed_out'
              ? 'This can take up to 20 minutes for larger sites. Page data will appear automatically when ready.'
              : 'Page data will appear once the DataForSEO crawl completes. This typically takes 2-5 minutes.'}
          </p>
          {enrichment.progress && (
            <p className="text-xs text-indigo-600 mt-3">{enrichment.progress}</p>
          )}
          {enrichment.status === 'timed_out' && (
            <button
              onClick={() => enrichment.refreshNow()}
              disabled={enrichment.isRefreshing}
              className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-700 hover:text-indigo-900 bg-indigo-100 hover:bg-indigo-200 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw size={12} className={enrichment.isRefreshing ? 'animate-spin' : ''} />
              {enrichment.isRefreshing ? 'Checking...' : 'Refresh now'}
            </button>
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
                {linkStats.internalLinks > 0 ? linkStats.internalLinks.toLocaleString() : '—'}
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
                {linkStats.brokenLinks}
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
                    {hasTipr && (
                      <th className="text-center px-3 py-3 text-xs font-bold text-text-muted uppercase tracking-wider hidden lg:table-cell">
                        <button onClick={() => toggleSort('pr_score')} className="flex items-center gap-1 hover:text-text mx-auto">
                          PR
                          <ArrowUpDown size={10} />
                        </button>
                      </th>
                    )}
                    {hasTipr && (
                      <th className="text-center px-3 py-3 text-xs font-bold text-text-muted uppercase tracking-wider hidden lg:table-cell">
                        <button onClick={() => toggleSort('tipr_rank')} className="flex items-center gap-1 hover:text-text mx-auto">
                          TIPR
                          <ArrowUpDown size={10} />
                        </button>
                      </th>
                    )}
                    {hasTipr && (
                      <th className="text-center px-3 py-3 text-xs font-bold text-text-muted uppercase tracking-wider hidden xl:table-cell">
                        Type
                      </th>
                    )}
                    <th className="text-center px-3 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                      Status
                    </th>
                    <th className="text-center px-3 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                      Audit
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredNodes.slice(0, 200).map((node) => {
                    const pa = pageAudits[node.id];
                    const isRunning = runningAudits.has(node.id);
                    return (
                    <tr
                      key={node.id}
                      className="border-b border-border/50 hover:bg-surface-overlay/50 transition-colors"
                    >
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-1.5 max-w-xs">
                          <Link
                            to={`/dashboard/${auditId}/page-audit?url=${encodeURIComponent(node.id)}`}
                            className="text-sm text-accent hover:text-accent-hover font-medium truncate"
                          >
                            {urlPath(node.id)}
                          </Link>
                          <a
                            href={node.id}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex-shrink-0 text-text-muted hover:text-text-secondary transition-colors"
                            title="Open in new tab"
                          >
                            <ExternalLink size={10} />
                          </a>
                        </div>
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
                      {hasTipr && (() => {
                        const tp = tiprLookup.get(node.id);
                        return (
                          <>
                            <td className="px-3 py-2.5 text-center text-xs font-semibold text-text hidden lg:table-cell">
                              {tp ? tp.pagerank_score.toFixed(0) : '—'}
                            </td>
                            <td className="px-3 py-2.5 text-center text-xs text-text-muted hidden lg:table-cell">
                              {tp ? `#${tp.tipr_rank}` : '—'}
                            </td>
                            <td className="px-3 py-2.5 text-center hidden xl:table-cell">
                              {tp ? (
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border capitalize ${CLASSIFICATION_BADGE[tp.classification] ?? 'text-gray-600 bg-gray-50 border-gray-200'}`}>
                                  {tp.classification.replace('_', ' ')}
                                </span>
                              ) : '—'}
                            </td>
                          </>
                        );
                      })()}
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
                      <td className="px-3 py-2.5 text-center">
                        {isRunning ? (
                          <Loader2 size={14} className="text-accent animate-spin mx-auto" />
                        ) : pa ? (
                          <Link
                            to={`/dashboard/${auditId}/page-audit?url=${encodeURIComponent(node.id)}`}
                            className={`inline-block text-[11px] font-bold px-2 py-0.5 rounded-full border ${scoreBadgeColor(pa.score)}`}
                            title={`Score: ${pa.score} — Click to view results`}
                          >
                            {pa.score}
                          </Link>
                        ) : (
                          <button
                            onClick={() => handleRunAudit(node.id)}
                            className="inline-flex items-center gap-1 text-[10px] font-semibold text-accent hover:text-accent-hover bg-accent/5 hover:bg-accent/10 px-2 py-1 rounded-lg transition-colors"
                            title="Run 10-pillar audit on this page"
                          >
                            <FileSearch size={10} />
                            Audit
                          </button>
                        )}
                      </td>
                    </tr>
                    );
                  })}
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
