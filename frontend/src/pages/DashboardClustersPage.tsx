import { useMemo, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, FolderTree, Info, Loader2, AlertCircle, RefreshCw,
  ChevronDown, ChevronRight, Link2, Unlink, ExternalLink,
  Target, Layers, BarChart3, BookOpen, Sparkles,
} from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';
import { useEnrichmentPolling } from '../hooks/useEnrichmentPolling';
import TopicClusterGraph from '../components/TopicClusterGraph';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SemanticCluster {
  id: number;
  label: string;
  label_quality?: 'high' | 'medium' | 'low';
  color: string;
  top_entities: [string, number][];
  pillar: {
    url: string;
    title: string;
    score: number;
    word_count: number;
    inlinks_from_cluster?: number;
    entity_coverage?: number;
  } | null;
  pages: {
    url: string;
    title: string;
    links_to_pillar: boolean | null;
    pillar_links_here: boolean | null;
    entity_overlap: number;
    word_count: number;
    entity_data: boolean;
  }[];
  size: number;
  link_health: {
    pages_linking_to_pillar: number;
    pillar_links_to_pages: number;
    bidirectional: number;
    unlinked: number;
    health_pct: number;
    page_details?: unknown[];
  };
  content_gaps: {
    entity: string;
    mentioned_in: number;
    total_pages: number;
    in_pillar: boolean;
  }[];
  silhouette: number;
}

interface SemanticClusters {
  version: string;
  method: string;
  n_clusters: number;
  silhouette_score: number;
  quality: string;
  detection_method: string;
  entity_data_coverage: string;
  total_missing_links?: number;
  healthy_clusters?: number;
  clusters: SemanticCluster[];
  uncategorized_pages: unknown[];
  link_recommendations: {
    type: string;
    source_url: string;
    target_url: string;
    cluster_label: string;
    reason: string;
    suggested_anchors?: string[];
  }[];
}

interface DirectoryCluster {
  prefix: string;
  page_count: number;
  urls?: string[];
  dominant_category?: string;
  coherence_score?: number;
  category_breakdown?: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const CLUSTER_COLORS = [
  '#6366F1', '#22D3EE', '#F472B6', '#34D399', '#FBBF24',
  '#A78BFA', '#FB923C', '#60A5FA', '#4ADE80', '#F87171',
  '#818CF8', '#2DD4BF',
];

const healthColor = (pct: number): string => {
  if (pct >= 80) return '#16a34a';
  if (pct >= 60) return '#22c55e';
  if (pct >= 40) return '#eab308';
  if (pct >= 20) return '#f97316';
  return '#ef4444';
};

const healthLabel = (pct: number): string => {
  if (pct >= 80) return 'Excellent';
  if (pct >= 60) return 'Good';
  if (pct >= 40) return 'Moderate';
  if (pct >= 20) return 'Needs Work';
  return 'Critical';
};

const qualityBadge = (q: string): { label: string; color: string } => {
  switch (q) {
    case 'excellent': return { label: 'Excellent', color: '#22C55E' };
    case 'good': return { label: 'Good', color: '#84CC16' };
    case 'fair': return { label: 'Fair', color: '#EAB308' };
    default: return { label: 'Low', color: '#EF4444' };
  }
};

const cohesionColor = (score: number): string => {
  if (score >= 0.8) return '#22C55E';
  if (score >= 0.6) return '#EAB308';
  return '#EF4444';
};

function shortenUrl(url: string): string {
  try {
    const u = new URL(url);
    return u.pathname.length > 60
      ? u.pathname.slice(0, 57) + '...'
      : u.pathname || '/';
  } catch {
    return url.length > 60 ? url.slice(0, 57) + '...' : url;
  }
}

// ---------------------------------------------------------------------------
// Semantic Cluster Card
// ---------------------------------------------------------------------------

function SemanticClusterCard({
  cluster,
  isExpanded,
  onToggle,
}: {
  cluster: SemanticCluster;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const lh = cluster.link_health;
  const healthPct = lh?.health_pct ?? 0;
  const pillar = cluster.pillar;
  const gaps = cluster.content_gaps || [];
  const pages = cluster.pages || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface-raised border border-border rounded-xl overflow-hidden"
    >
      {/* Card header */}
      <button
        onClick={onToggle}
        className="w-full text-left p-5 hover:bg-surface-overlay/30 transition-colors"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2.5">
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: cluster.color }}
              />
              <span className="text-sm font-bold text-text">
                {cluster.label}
              </span>
              {cluster.label_quality === 'low' && (
                <span className="text-[8px] font-semibold text-text-muted bg-surface-overlay px-1.5 py-0.5 rounded-full flex-shrink-0">
                  auto
                </span>
              )}
              {isExpanded ? (
                <ChevronDown size={14} className="text-text-muted flex-shrink-0" />
              ) : (
                <ChevronRight size={14} className="text-text-muted flex-shrink-0" />
              )}
            </div>
            <div className="flex items-center gap-3 mt-2 ml-5.5 flex-wrap">
              <span className="text-xs text-text-muted">
                {cluster.size} pages
              </span>
              {pillar && (
                <span className="text-[10px] font-semibold text-accent bg-accent/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Target size={9} />
                  Pillar: {shortenUrl(pillar.url)}
                </span>
              )}
              {cluster.top_entities.slice(0, 3).map(([name]) => (
                <span
                  key={name}
                  className="text-[10px] text-text-muted bg-surface-overlay px-2 py-0.5 rounded-full"
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-4 flex-shrink-0">
            {/* Link health */}
            {lh && Object.keys(lh).length > 0 && (
              <div className="text-right">
                <div
                  className="text-lg font-extrabold font-heading"
                  style={{ color: healthColor(healthPct) }}
                >
                  {healthPct}%
                </div>
                <div className="text-[10px] text-text-muted font-semibold uppercase tracking-wider">
                  Link Health
                </div>
              </div>
            )}
            {/* Content gaps count */}
            {gaps.length > 0 && (
              <div className="text-right hidden sm:block">
                <div className="text-lg font-extrabold font-heading text-amber-500">
                  {gaps.length}
                </div>
                <div className="text-[10px] text-text-muted font-semibold uppercase tracking-wider">
                  Gaps
                </div>
              </div>
            )}
          </div>
        </div>
        {/* Link health mini bar */}
        {lh && Object.keys(lh).length > 0 && (
          <div className="mt-3 ml-5.5 h-1.5 bg-surface-overlay rounded-full overflow-hidden max-w-sm">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.max(4, healthPct)}%`,
                backgroundColor: healthColor(healthPct),
              }}
            />
          </div>
        )}
      </button>

      {/* Expanded details */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-5 pb-5 space-y-5">
              {/* Pillar page section */}
              {pillar && (
                <div className="mt-4">
                  <h4 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-2 flex items-center gap-1.5">
                    <Target size={12} /> Pillar Page
                  </h4>
                  <div className="bg-surface-overlay/50 rounded-lg p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-text truncate">{pillar.title || shortenUrl(pillar.url)}</p>
                        <p className="text-xs text-text-muted mt-0.5 truncate">{shortenUrl(pillar.url)}</p>
                      </div>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-accent/10 text-accent flex-shrink-0">
                        Score: {Math.round(pillar.score * 100)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-[10px] text-text-muted">
                      {pillar.word_count > 0 && <span>{pillar.word_count.toLocaleString()} words</span>}
                      {pillar.entity_coverage != null && (
                        <span>Entity coverage: {Math.round(pillar.entity_coverage * 100)}%</span>
                      )}
                      {pillar.inlinks_from_cluster != null && (
                        <span>{pillar.inlinks_from_cluster} inlinks from cluster</span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Supporting pages table */}
              {pages.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-2 flex items-center gap-1.5">
                    <BookOpen size={12} /> Supporting Pages ({pages.length})
                  </h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-text-muted border-b border-border">
                          <th className="text-left py-2 pr-3 font-semibold">Page</th>
                          <th className="text-center py-2 px-2 font-semibold w-20">→ Pillar</th>
                          <th className="text-center py-2 px-2 font-semibold w-20">Pillar →</th>
                          <th className="text-right py-2 px-2 font-semibold w-20">Overlap</th>
                          <th className="text-right py-2 pl-2 font-semibold w-16">Words</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pages
                          .filter(p => p.url !== pillar?.url)
                          .slice(0, 30)
                          .map((p) => (
                          <tr key={p.url} className="border-b border-border/50 hover:bg-surface-overlay/30">
                            <td className="py-2 pr-3 max-w-[300px]">
                              <p className="text-text font-medium truncate">{p.title || shortenUrl(p.url)}</p>
                              <p className="text-text-muted truncate text-[10px]">{shortenUrl(p.url)}</p>
                            </td>
                            <td className="text-center py-2 px-2">
                              {p.links_to_pillar === true ? (
                                <Link2 size={14} className="text-green-500 mx-auto" />
                              ) : p.links_to_pillar === false ? (
                                <Unlink size={14} className="text-red-400 mx-auto" />
                              ) : (
                                <span className="text-text-muted">—</span>
                              )}
                            </td>
                            <td className="text-center py-2 px-2">
                              {p.pillar_links_here === true ? (
                                <Link2 size={14} className="text-green-500 mx-auto" />
                              ) : p.pillar_links_here === false ? (
                                <Unlink size={14} className="text-red-400 mx-auto" />
                              ) : (
                                <span className="text-text-muted">—</span>
                              )}
                            </td>
                            <td className="text-right py-2 px-2">
                              <span style={{
                                color: p.entity_overlap >= 0.5 ? '#22C55E'
                                  : p.entity_overlap >= 0.25 ? '#EAB308'
                                  : '#9CA3AF',
                              }}>
                                {Math.round(p.entity_overlap * 100)}%
                              </span>
                            </td>
                            <td className="text-right py-2 pl-2 text-text-muted">
                              {p.word_count > 0 ? p.word_count.toLocaleString() : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {pages.filter(p => p.url !== pillar?.url).length > 30 && (
                      <p className="text-[10px] text-text-muted mt-2 text-center">
                        Showing 30 of {pages.filter(p => p.url !== pillar?.url).length} pages
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Content Gaps */}
              {gaps.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-2 flex items-center gap-1.5">
                    <Sparkles size={12} /> Content Gaps
                  </h4>
                  <div className="space-y-1.5">
                    {gaps.slice(0, 10).map((gap) => (
                      <div
                        key={gap.entity}
                        className="flex items-center justify-between bg-surface-overlay/50 rounded-lg px-3 py-2"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-xs font-semibold text-text truncate">{gap.entity}</span>
                          {!gap.in_pillar && (
                            <span className="text-[9px] font-bold text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded-full flex-shrink-0">
                              Missing from pillar
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-text-muted flex-shrink-0">
                          on {gap.mentioned_in} of {gap.total_pages} pages
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Link Health Summary */}
              {lh && Object.keys(lh).length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="bg-surface-overlay/50 rounded-lg p-2.5 text-center">
                    <div className="text-sm font-bold text-text">{lh.pages_linking_to_pillar}</div>
                    <div className="text-[9px] text-text-muted">→ Pillar</div>
                  </div>
                  <div className="bg-surface-overlay/50 rounded-lg p-2.5 text-center">
                    <div className="text-sm font-bold text-text">{lh.pillar_links_to_pages}</div>
                    <div className="text-[9px] text-text-muted">Pillar →</div>
                  </div>
                  <div className="bg-surface-overlay/50 rounded-lg p-2.5 text-center">
                    <div className="text-sm font-bold text-green-400">{lh.bidirectional}</div>
                    <div className="text-[9px] text-text-muted">Bidirectional</div>
                  </div>
                  <div className="bg-surface-overlay/50 rounded-lg p-2.5 text-center">
                    <div className="text-sm font-bold text-red-400">{lh.unlinked}</div>
                    <div className="text-[9px] text-text-muted">Unlinked</div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Directory Structure (old view — secondary tab)
// ---------------------------------------------------------------------------

function DirectoryView({ clusters }: { clusters: DirectoryCluster[] }) {
  const maxPageCount = Math.max(...clusters.map(c => c.page_count || 0), 1);
  return (
    <div className="space-y-3">
      {clusters.map((cluster, idx) => (
        <div
          key={cluster.prefix}
          className="bg-surface-raised border border-border rounded-xl p-5"
        >
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2.5">
                <span
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: CLUSTER_COLORS[idx % CLUSTER_COLORS.length] }}
                />
                <span className="text-sm font-semibold text-text truncate">
                  {cluster.prefix}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-2 ml-5.5">
                <span className="text-xs text-text-muted">
                  {cluster.page_count ?? '?'} pages
                </span>
                {cluster.dominant_category && (
                  <span className="text-[10px] font-semibold text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                    {cluster.dominant_category}
                  </span>
                )}
              </div>
              <div className="mt-3 ml-5.5 h-2 bg-surface-overlay rounded-full overflow-hidden max-w-sm">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.max(4, (cluster.page_count / maxPageCount) * 100)}%`,
                    backgroundColor: CLUSTER_COLORS[idx % CLUSTER_COLORS.length],
                  }}
                />
              </div>
            </div>
            {cluster.coherence_score != null && (
              <div className="text-right flex-shrink-0">
                <div
                  className="text-lg font-extrabold font-heading"
                  style={{ color: cohesionColor(cluster.coherence_score) }}
                >
                  {Math.round(cluster.coherence_score * 100)}%
                </div>
                <div className="text-[10px] text-text-muted font-semibold uppercase tracking-wider">
                  Coherence
                </div>
              </div>
            )}
          </div>
          {cluster.category_breakdown && Object.keys(cluster.category_breakdown).length > 1 && (
            <div className="mt-3 ml-5.5 flex flex-wrap gap-1.5">
              {Object.entries(cluster.category_breakdown)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([cat, count]) => (
                  <span
                    key={cat}
                    className="text-[10px] text-text-muted bg-surface-overlay px-2 py-0.5 rounded-full"
                  >
                    {cat}: {count}
                  </span>
                ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Cluster Comparison Table
// ---------------------------------------------------------------------------

function ClusterComparisonTable({ clusters }: { clusters: SemanticCluster[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-text-muted border-b border-border">
            <th className="text-left py-2 pr-3 font-semibold">Cluster</th>
            <th className="text-right py-2 px-2 font-semibold w-16">Pages</th>
            <th className="text-left py-2 px-2 font-semibold">Pillar</th>
            <th className="text-center py-2 px-2 font-semibold w-24">Link Health</th>
            <th className="text-right py-2 px-2 font-semibold w-16">Gaps</th>
          </tr>
        </thead>
        <tbody>
          {clusters.map((c) => {
            const hp = c.link_health?.health_pct ?? 0;
            return (
              <tr key={c.id} className="border-b border-border/50 hover:bg-surface-overlay/30">
                <td className="py-2.5 pr-3">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: c.color }} />
                    <span className="text-text font-medium truncate max-w-[200px]">{c.label}</span>
                  </div>
                </td>
                <td className="text-right py-2.5 px-2 text-text">{c.size}</td>
                <td className="py-2.5 px-2 text-text-muted truncate max-w-[180px]">
                  {c.pillar ? shortenUrl(c.pillar.url) : '—'}
                </td>
                <td className="text-center py-2.5 px-2">
                  {c.link_health && Object.keys(c.link_health).length > 0 ? (
                    <span
                      className="inline-flex items-center gap-1 font-bold"
                      style={{ color: healthColor(hp) }}
                    >
                      {hp}%
                      <span className="text-[9px] font-normal text-text-muted">{healthLabel(hp)}</span>
                    </span>
                  ) : '—'}
                </td>
                <td className="text-right py-2.5 px-2">
                  {c.content_gaps.length > 0 ? (
                    <span className="text-amber-500 font-bold">{c.content_gaps.length}</span>
                  ) : (
                    <span className="text-green-500">0</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export default function DashboardClustersPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);
  const enrichment = useEnrichmentPolling(auditId);

  const [activeTab, setActiveTab] = useState<'semantic' | 'directory'>('semantic');
  const [expandedCluster, setExpandedCluster] = useState<number | null>(null);
  const [showComparison, setShowComparison] = useState(false);

  // Semantic clusters (new)
  const semanticData = useMemo<SemanticClusters | null>(() => {
    return (report?.semantic_clusters as SemanticClusters) ?? null;
  }, [report]);

  // Directory clusters (legacy, for secondary tab)
  const directoryClusters = useMemo<DirectoryCluster[] | null>(() => {
    const raw =
      report?.link_analysis?.clusters ??
      report?.clusters ??
      report?.topic_clusters ??
      null;
    if (!raw || (Array.isArray(raw) && raw.length === 0)) return null;
    if (Array.isArray(raw)) return raw as DirectoryCluster[];
    return Object.entries(raw).map(([prefix, data]) => ({
      prefix,
      ...(data as Record<string, unknown>),
    })) as DirectoryCluster[];
  }, [report]);

  const hasData = !!(semanticData || directoryClusters);

  const toggleCluster = useCallback((id: number) => {
    setExpandedCluster(prev => prev === id ? null : id);
  }, []);

  // Summary stats for semantic clusters
  const stats = useMemo(() => {
    if (!semanticData) return null;
    const clusters = semanticData.clusters;
    const totalClustered = clusters.reduce((s, c) => s + c.size, 0);
    const totalPages = report?.link_analysis?.stats?.total_pages ?? totalClustered;
    const avgHealth = clusters.length > 0
      ? Math.round(clusters.reduce((s, c) => s + (c.link_health?.health_pct ?? 0), 0) / clusters.length)
      : 0;
    const totalGaps = clusters.reduce((s, c) => s + c.content_gaps.length, 0);
    const weakest = [...clusters].sort((a, b) => (a.link_health?.health_pct ?? 0) - (b.link_health?.health_pct ?? 0))[0];
    const strongest = [...clusters].sort((a, b) => (b.link_health?.health_pct ?? 0) - (a.link_health?.health_pct ?? 0))[0];
    const totalMissingLinks = semanticData.total_missing_links ?? 0;
    const healthyClusters = semanticData.healthy_clusters ?? 0;
    return {
      totalClusters: clusters.length,
      totalClustered,
      totalPages,
      uncategorized: Math.max(0, totalPages - totalClustered),
      avgHealth,
      totalGaps,
      totalRecs: semanticData.link_recommendations.length,
      totalMissingLinks,
      healthyClusters,
      weakest,
      strongest,
    };
  }, [semanticData, report]);

  // Graph links from link_analysis for visualization
  const graphLinks = useMemo(() => {
    const rawLinks = report?.link_analysis?.graph?.links ?? [];
    return rawLinks.map((l: any) => ({
      source: typeof l.source === 'object' ? l.source.id : l.source,
      target: typeof l.target === 'object' ? l.target.id : l.target,
    }));
  }, [report]);

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
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
            <FolderTree size={20} className="text-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text font-heading">Topic Clusters</h1>
            <p className="text-sm text-text-secondary mt-0.5">
              How your content is organized by topic and linking structure.
            </p>
          </div>
        </div>
      </motion.div>

      {/* Tab selector */}
      {hasData && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.03 }}
          className="flex items-center gap-1 bg-surface-raised border border-border rounded-xl p-1"
        >
          <button
            onClick={() => setActiveTab('semantic')}
            className={`flex-1 flex items-center justify-center gap-1.5 text-xs font-semibold py-2 px-3 rounded-lg transition-all ${
              activeTab === 'semantic'
                ? 'bg-accent/10 text-accent shadow-sm'
                : 'text-text-muted hover:text-text'
            }`}
          >
            <Layers size={13} />
            Topic Clusters
            {semanticData && (
              <span className="text-[9px] bg-accent/20 text-accent px-1.5 py-0.5 rounded-full font-bold">
                {semanticData.n_clusters}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('directory')}
            className={`flex-1 flex items-center justify-center gap-1.5 text-xs font-semibold py-2 px-3 rounded-lg transition-all ${
              activeTab === 'directory'
                ? 'bg-accent/10 text-accent shadow-sm'
                : 'text-text-muted hover:text-text'
            }`}
          >
            <FolderTree size={13} />
            Directory Structure
            {directoryClusters && (
              <span className="text-[9px] bg-surface-overlay text-text-muted px-1.5 py-0.5 rounded-full font-bold">
                {directoryClusters.length}
              </span>
            )}
          </button>
        </motion.div>
      )}

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
              : 'Topic clusters are being generated'}
          </p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            {enrichment.status === 'timed_out'
              ? 'This can take up to 20 minutes for larger sites. Clusters will appear automatically when ready.'
              : 'Pages are being analyzed and clustered by topic. This typically takes 2-5 minutes.'}
          </p>
          {enrichment.progress && (
            <p className="text-xs text-indigo-400 mt-3">{enrichment.progress}</p>
          )}
          {enrichment.status === 'timed_out' && (
            <button
              onClick={() => enrichment.refreshNow()}
              disabled={enrichment.isRefreshing}
              className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-accent hover:text-accent-hover bg-accent/10 hover:bg-accent/20 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
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
          <p className="text-sm font-semibold text-text mb-1">Crawl data could not be generated</p>
          <p className="text-xs text-text-muted max-w-md mx-auto">Please try running the audit again.</p>
        </motion.div>
      ) : !hasData && enrichment.status === 'no_data' ? (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-raised border border-border rounded-xl p-10 text-center"
        >
          <AlertCircle size={32} className="text-amber-500 mx-auto mb-4" />
          <p className="text-sm font-semibold text-text mb-1">Topic clusters unavailable for this site</p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            {enrichment.progress || 'The site blocks automated crawlers (Cloudflare or similar), so no pages were returned. Topic clusters require a successful multi-page crawl.'}
          </p>
        </motion.div>

      /* ============== SEMANTIC TAB ============== */
      ) : activeTab === 'semantic' && semanticData ? (
        <>
          {/* Detection method badge */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.04 }}
            className="flex items-start gap-3 bg-surface-raised border border-border rounded-xl p-4"
          >
            <Info size={16} className="text-accent flex-shrink-0 mt-0.5" />
            <div className="text-xs text-text-secondary">
              <span className="font-semibold text-text">
                {semanticData.detection_method === 'service_driven'
                  ? 'Clusters detected from site services & entity analysis.'
                  : semanticData.detection_method === 'manual'
                    ? 'Manual cluster count.'
                    : 'Clusters detected from content analysis (fallback).'}
              </span>{' '}
              Pages are grouped by topic — what they&apos;re about, not where they are in the URL structure.
              Each cluster represents a core service, product, or content theme.
              <span className="ml-2 inline-flex items-center gap-1">
                Quality:
                <span
                  className="font-bold"
                  style={{ color: qualityBadge(semanticData.quality).color }}
                >
                  {qualityBadge(semanticData.quality).label}
                </span>
                <span className="text-text-muted">
                  (silhouette {semanticData.silhouette_score.toFixed(2)})
                </span>
              </span>
              <span className="ml-2 text-text-muted">
                · Entity data: {semanticData.entity_data_coverage} pages
              </span>
            </div>
          </motion.div>

          {/* KPI cards */}
          {stats && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.06 }}
              className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-3"
            >
              <div className="bg-surface-raised border border-border rounded-xl p-3 text-center">
                <div className="text-xl font-bold text-text font-heading">{stats.totalClusters}</div>
                <div className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Clusters</div>
              </div>
              <div className="bg-surface-raised border border-border rounded-xl p-3 text-center">
                <div className="text-xl font-bold text-text font-heading">{stats.totalClustered}</div>
                <div className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Clustered</div>
              </div>
              <div className="bg-surface-raised border border-border rounded-xl p-3 text-center">
                <div className="text-xl font-bold font-heading" style={{ color: healthColor(stats.avgHealth) }}>
                  {stats.avgHealth}%
                </div>
                <div className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Avg Health</div>
              </div>
              <div className="bg-surface-raised border border-border rounded-xl p-3 text-center">
                <div className="text-xl font-bold text-green-500 font-heading">{stats.healthyClusters}</div>
                <div className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Healthy</div>
              </div>
              <div className="bg-surface-raised border border-border rounded-xl p-3 text-center">
                <div className="text-xl font-bold text-red-400 font-heading">{stats.totalMissingLinks}</div>
                <div className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Missing Links</div>
              </div>
              <div className="bg-surface-raised border border-border rounded-xl p-3 text-center">
                <div className="text-xl font-bold text-amber-500 font-heading">{stats.totalGaps}</div>
                <div className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Content Gaps</div>
              </div>
              <div className="bg-surface-raised border border-border rounded-xl p-3 text-center">
                <div className={`text-xl font-bold font-heading ${stats.uncategorized > 0 ? 'text-amber-500' : 'text-text'}`}>
                  {stats.uncategorized}
                </div>
                <div className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Uncategorized</div>
              </div>
              <div className="bg-surface-raised border border-border rounded-xl p-3 text-center">
                <div className="text-xl font-bold text-text font-heading">{stats.totalPages}</div>
                <div className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Total Pages</div>
              </div>
            </motion.div>
          )}

          {/* Link Health Summary */}
          {stats && stats.totalMissingLinks > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.07 }}
              className="bg-red-500/5 border border-red-500/20 rounded-xl px-4 py-3 flex items-center gap-3"
            >
              <Unlink size={16} className="text-red-400 flex-shrink-0" />
              <div className="text-xs text-text-secondary">
                <span className="font-semibold text-red-400">{stats.totalMissingLinks} missing links</span>{' '}
                detected across {stats.totalClusters} clusters.{' '}
                {stats.healthyClusters} of {stats.totalClusters} clusters have healthy linking (&ge;50%).{' '}
                <span className="text-text-muted">
                  Fixing these would strengthen your site&apos;s topical authority structure.
                </span>
              </div>
            </motion.div>
          )}

          {/* Hub-and-spoke cluster visualization */}
          {semanticData.clusters.length > 0 && graphLinks.length > 0 && (
            <TopicClusterGraph
              clusters={semanticData.clusters}
              graphLinks={graphLinks}
              linkRecommendations={semanticData.link_recommendations}
            />
          )}

          {/* Comparison toggle */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 }}
            className="flex items-center justify-between"
          >
            <h2 className="text-sm font-bold text-text uppercase tracking-widest">
              Clusters ({semanticData.clusters.length})
            </h2>
            <button
              onClick={() => setShowComparison(!showComparison)}
              className="text-[10px] font-semibold text-text-muted hover:text-accent transition-colors flex items-center gap-1"
            >
              <BarChart3 size={12} />
              {showComparison ? 'Card View' : 'Comparison Table'}
            </button>
          </motion.div>

          {/* Comparison table OR cluster cards */}
          <AnimatePresence mode="wait">
            {showComparison ? (
              <motion.div
                key="table"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="bg-surface-raised border border-border rounded-xl p-4"
              >
                <ClusterComparisonTable clusters={semanticData.clusters} />
              </motion.div>
            ) : (
              <motion.div
                key="cards"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-3"
              >
                {semanticData.clusters.map((cluster) => (
                  <SemanticClusterCard
                    key={cluster.id}
                    cluster={cluster}
                    isExpanded={expandedCluster === cluster.id}
                    onToggle={() => toggleCluster(cluster.id)}
                  />
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Link Recommendations summary */}
          {semanticData.link_recommendations.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.12 }}
              className="bg-surface-raised border border-border rounded-xl p-5"
            >
              <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-3 flex items-center gap-1.5">
                <ExternalLink size={12} />
                Cluster Link Recommendations ({semanticData.link_recommendations.length})
              </h3>
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {semanticData.link_recommendations.slice(0, 25).map((rec, i) => (
                  <div key={i} className="flex items-start gap-3 bg-surface-overlay/50 rounded-lg px-3 py-2.5">
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full flex-shrink-0 mt-0.5 ${
                      rec.type === 'missing_pillar_link'
                        ? 'bg-red-500/10 text-red-400'
                        : 'bg-amber-500/10 text-amber-500'
                    }`}>
                      {rec.type === 'missing_pillar_link' ? 'Missing → Pillar' : 'Pillar → Page'}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-text-secondary">{rec.reason}</p>
                      <p className="text-[10px] text-text-muted mt-0.5 truncate">
                        {shortenUrl(rec.source_url)} → {shortenUrl(rec.target_url)}
                      </p>
                      {rec.suggested_anchors && rec.suggested_anchors.length > 0 && (
                        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                          <span className="text-[9px] text-text-muted">Anchor:</span>
                          {rec.suggested_anchors.map((anchor, j) => (
                            <span
                              key={j}
                              className="text-[9px] font-medium text-accent bg-accent/10 px-1.5 py-0.5 rounded"
                            >
                              {anchor}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {semanticData.link_recommendations.length > 25 && (
                  <p className="text-[10px] text-text-muted text-center pt-1">
                    + {semanticData.link_recommendations.length - 25} more recommendations
                  </p>
                )}
              </div>
            </motion.div>
          )}
        </>

      /* ============== DIRECTORY TAB ============== */
      ) : activeTab === 'directory' && directoryClusters && directoryClusters.length > 0 ? (
        <>
          {/* Directory summary */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-3"
          >
            <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-text font-heading">{directoryClusters.length}</div>
              <div className="text-[10px] text-text-muted uppercase tracking-wider mt-1">Directories</div>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-text font-heading">
                {directoryClusters.reduce((s, c) => s + (c.page_count || 0), 0)}
              </div>
              <div className="text-[10px] text-text-muted uppercase tracking-wider mt-1">Pages</div>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-text font-heading">
                {report?.link_analysis?.stats?.total_pages ?? 0}
              </div>
              <div className="text-[10px] text-text-muted uppercase tracking-wider mt-1">Total</div>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-text font-heading">
                {Math.max(0, (report?.link_analysis?.stats?.total_pages ?? 0) - directoryClusters.reduce((s, c) => s + (c.page_count || 0), 0))}
              </div>
              <div className="text-[10px] text-text-muted uppercase tracking-wider mt-1">Root</div>
            </div>
          </motion.div>
          <DirectoryView clusters={directoryClusters} />
        </>

      /* ============== SEMANTIC TAB BUT NO DATA YET ============== */
      ) : activeTab === 'semantic' && !semanticData && directoryClusters ? (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-raised border border-border rounded-xl p-8 text-center"
        >
          <Layers size={28} className="text-text-muted mx-auto mb-3" />
          <p className="text-sm font-semibold text-text mb-1">Semantic Clusters Not Available</p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Semantic topic clustering requires 20+ pages. Check the Directory Structure tab for URL-based grouping.
          </p>
        </motion.div>

      /* ============== NO DATA AT ALL ============== */
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
          <p className="text-sm font-semibold text-text mb-1">Topic Clusters Not Available</p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Topic clusters will be detected after a full site crawl. Run a Comprehensive
            Audit with DataForSEO configured to analyze your content architecture.
          </p>
        </motion.div>
      )}
    </div>
  );
}
