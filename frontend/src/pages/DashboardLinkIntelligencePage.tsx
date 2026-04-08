import { useMemo, useState } from 'react';
import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Zap,
  Star,
  AlertTriangle,
  Layers,
  ArrowRight,
  Download,
  ChevronDown,
  ChevronUp,
  Network,
  Target,
  GitBranch,
  Eye,
  Wrench,
  Info,
  CheckCircle2,
} from 'lucide-react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  ReferenceLine,
  Label,
} from 'recharts';
import { useAuditStore } from '../stores/auditStore';

/* ─── Types ─── */
interface TiprPage {
  url: string;
  pagerank: number;
  pagerank_score: number;
  cheirank: number;
  cheirank_score: number;
  tipr_rank: number;
  tipr_score: number;
  classification: string;
  inbound_count: number;
  outbound_count: number;
  click_depth: number;
  cluster: string;
}

interface TiprRecommendation {
  type: string;
  priority: string;
  group: string;
  source_url: string;
  target_url: string;
  reason: string;
  expected_impact: string;
  source_pr_score: number;
  target_pr_score: number;
  source_outlinks: number;
  source_classification: string;
  target_classification: string;
  content_relevance: number;
}

interface TiprSummary {
  total_pages: number;
  stars: number;
  hoarders: number;
  wasters: number;
  dead_weight: number;
  avg_pagerank: number;
  max_pagerank_url: string;
  max_cheirank_url: string;
  top_hoarders: TiprPage[];
  top_wasters: TiprPage[];
  orphan_count: number;
  deep_pages_count: number;
}

interface TiprAnalysis {
  version: string;
  signal_count: number;
  pages: TiprPage[];
  summary: TiprSummary;
  recommendations: TiprRecommendation[];
}

/* ─── Constants ─── */
const QUADRANT_COLORS: Record<string, string> = {
  star: '#22C55E',
  hoarder: '#F59E0B',
  waster: '#EF4444',
  dead_weight: '#6B7280',
};

const QUADRANT_BG: Record<string, string> = {
  star: 'bg-green-500/10',
  hoarder: 'bg-amber-500/10',
  waster: 'bg-red-500/10',
  dead_weight: 'bg-gray-500/10',
};

const QUADRANT_TEXT: Record<string, string> = {
  star: 'text-green-400',
  hoarder: 'text-amber-400',
  waster: 'text-red-400',
  dead_weight: 'text-text-muted',
};

const QUADRANT_BORDER: Record<string, string> = {
  star: 'border-green-500/30',
  hoarder: 'border-amber-500/30',
  waster: 'border-red-500/30',
  dead_weight: 'border-gray-500/30',
};

const QUADRANT_LABELS: Record<string, string> = {
  star: 'Star',
  hoarder: 'Hoarder',
  waster: 'Waster',
  dead_weight: 'Dead Weight',
};

const QUADRANT_ICONS: Record<string, React.ElementType> = {
  star: Star,
  hoarder: Layers,
  waster: AlertTriangle,
  dead_weight: Target,
};

const QUADRANT_DESCRIPTIONS: Record<string, string> = {
  star: 'Healthy hub pages that receive and distribute link equity effectively.',
  hoarder: 'High-authority pages not distributing equity. Add outbound links.',
  waster: 'Pages distributing more equity than they receive. Prune outlinks.',
  dead_weight: 'Low authority, low distribution. Need more inbound links.',
};

const GROUP_COLORS: Record<string, string> = {
  quick_win: 'border-l-green-500',
  strategic: 'border-l-blue-500',
  maintenance: 'border-l-gray-500',
};

const GROUP_LABELS: Record<string, string> = {
  quick_win: 'Quick Win',
  strategic: 'Strategic',
  maintenance: 'Maintenance',
};

const PRIORITY_BADGE: Record<string, string> = {
  high: 'bg-red-500/15 text-red-400',
  medium: 'bg-amber-500/15 text-amber-400',
  low: 'bg-gray-500/15 text-text-muted',
};

const DEPTH_COLORS = ['#22C55E', '#84CC16', '#EAB308', '#F97316', '#EF4444', '#DC2626'];

/* ─── Helpers ─── */
function shortUrl(url: string): string {
  try {
    const u = new URL(url.startsWith('http') ? url : `https://example.com${url}`);
    return u.pathname === '/' ? '/' : u.pathname;
  } catch {
    return url.length > 60 ? url.slice(0, 57) + '...' : url;
  }
}

function exportRecommendationsCsv(recs: TiprRecommendation[]) {
  const header = 'Priority,Group,Type,Source URL,Target URL,Reason,Expected Impact,Source PR,Target PR,Source Outlinks,Content Relevance';
  const rows = recs.map((r) =>
    [
      r.priority,
      r.group,
      r.type,
      `"${r.source_url}"`,
      `"${r.target_url}"`,
      `"${r.reason.replace(/"/g, '""')}"`,
      `"${r.expected_impact}"`,
      r.source_pr_score,
      r.target_pr_score,
      r.source_outlinks,
      r.content_relevance,
    ].join(',')
  );
  const csv = [header, ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'tipr-recommendations.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

/* ─── Section Components ─── */

function QuadrantKpiCards({ summary }: { summary: TiprSummary }) {
  const quadrants = [
    { key: 'star', count: summary.stars },
    { key: 'hoarder', count: summary.hoarders },
    { key: 'waster', count: summary.wasters },
    { key: 'dead_weight', count: summary.dead_weight },
  ] as const;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {quadrants.map(({ key, count }) => {
        const Icon = QUADRANT_ICONS[key];
        return (
          <div
            key={key}
            className={`${QUADRANT_BG[key]} border ${QUADRANT_BORDER[key]} rounded-xl p-4`}
          >
            <div className="flex items-center gap-2 mb-2">
              <Icon size={16} className={QUADRANT_TEXT[key]} />
              <span className="text-xs font-bold uppercase tracking-widest text-text-muted">
                {QUADRANT_LABELS[key]}s
              </span>
            </div>
            <div className={`text-2xl font-bold font-heading ${QUADRANT_TEXT[key]}`}>{count}</div>
            <p className="text-xs text-text-muted mt-1 leading-relaxed">{QUADRANT_DESCRIPTIONS[key]}</p>
          </div>
        );
      })}
    </div>
  );
}

function ScatterPlot({ pages }: { pages: TiprPage[] }) {
  const data = useMemo(
    () =>
      pages.map((p) => ({
        x: p.pagerank_score,
        y: p.cheirank_score,
        url: shortUrl(p.url),
        fullUrl: p.url,
        classification: p.classification,
        fill: QUADRANT_COLORS[p.classification] ?? '#6B7280',
      })),
    [pages]
  );

  const medianPR = useMemo(() => {
    const scores = pages.map((p) => p.pagerank_score).sort((a, b) => a - b);
    return scores.length > 0 ? scores[Math.floor(scores.length / 2)] : 50;
  }, [pages]);

  const medianCR = useMemo(() => {
    const scores = pages.map((p) => p.cheirank_score).sort((a, b) => a - b);
    return scores.length > 0 ? scores[Math.floor(scores.length / 2)] : 50;
  }, [pages]);

  return (
    <div className="bg-surface-raised border border-border rounded-xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <Network size={16} className="text-accent" />
        <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
          TIPR Quadrant Map
        </h2>
      </div>
      <p className="text-xs text-text-muted mb-4">
        Each dot is a page. X-axis = PageRank (authority received), Y-axis = CheiRank (equity distributed).
        Median thresholds divide pages into four quadrants.
      </p>
      <div className="h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
            <XAxis
              type="number"
              dataKey="x"
              domain={[0, 100]}
              name="PageRank Score"
              tick={{ fill: '#94A3B8', fontSize: 11 }}
              stroke="#334155"
            >
              <Label value="PageRank Score (Authority)" position="bottom" offset={20} style={{ fill: '#64748B', fontSize: 11 }} />
            </XAxis>
            <YAxis
              type="number"
              dataKey="y"
              domain={[0, 100]}
              name="CheiRank Score"
              tick={{ fill: '#94A3B8', fontSize: 11 }}
              stroke="#334155"
            >
              <Label value="CheiRank (Distribution)" angle={-90} position="insideLeft" offset={-5} style={{ fill: '#64748B', fontSize: 11 }} />
            </YAxis>
            <ReferenceLine x={medianPR} stroke="#475569" strokeDasharray="5 5" />
            <ReferenceLine y={medianCR} stroke="#475569" strokeDasharray="5 5" />
            <Tooltip
              content={({ payload }) => {
                if (!payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-surface-overlay border border-border rounded-lg px-3 py-2 shadow-card text-xs">
                    <p className="font-semibold text-text mb-1 break-all">{d.url}</p>
                    <p className="text-text-secondary">PR: {d.x?.toFixed(1)} | CR: {d.y?.toFixed(1)}</p>
                    <p style={{ color: d.fill }} className="font-semibold capitalize mt-0.5">
                      {d.classification?.replace('_', ' ')}
                    </p>
                  </div>
                );
              }}
            />
            <Scatter data={data} isAnimationActive={false}>
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.fill} fillOpacity={0.7} r={3} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-3 justify-center">
        {Object.entries(QUADRANT_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-1.5 text-xs text-text-muted">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: QUADRANT_COLORS[key] }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}

function PageTable({
  title,
  icon: Icon,
  pages,
  colorKey,
  auditId,
}: {
  title: string;
  icon: React.ElementType;
  pages: TiprPage[];
  colorKey: string;
  auditId: string | undefined;
}) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? pages : pages.slice(0, 10);

  return (
    <div className="bg-surface-raised border border-border rounded-xl overflow-hidden">
      <div className="px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={16} className={QUADRANT_TEXT[colorKey]} />
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">{title}</h2>
          <span className="text-xs text-text-muted">({pages.length})</span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-t border-border text-text-muted">
              <th className="text-left px-4 py-2.5 font-semibold">URL</th>
              <th className="text-center px-3 py-2.5 font-semibold">PR Score</th>
              <th className="text-center px-3 py-2.5 font-semibold">CR Score</th>
              <th className="text-center px-3 py-2.5 font-semibold">Inbound</th>
              <th className="text-center px-3 py-2.5 font-semibold">Outbound</th>
              <th className="text-center px-3 py-2.5 font-semibold">Delta</th>
              <th className="text-center px-3 py-2.5 font-semibold">TIPR Rank</th>
              <th className="text-left px-3 py-2.5 font-semibold hidden lg:table-cell">Cluster</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((p, i) => {
              const delta = p.inbound_count - p.outbound_count;
              return (
                <tr key={p.url} className={`border-t border-border/50 ${i % 2 === 0 ? 'bg-surface-raised' : 'bg-surface-overlay/30'} hover:bg-surface-overlay/60 transition-colors`}>
                  <td className="px-4 py-2.5 text-text max-w-[300px] truncate font-mono text-[11px]">
                    {shortUrl(p.url)}
                  </td>
                  <td className="text-center px-3 py-2.5 font-semibold text-text">{p.pagerank_score.toFixed(0)}</td>
                  <td className="text-center px-3 py-2.5 text-text-secondary">{p.cheirank_score.toFixed(0)}</td>
                  <td className="text-center px-3 py-2.5 text-text-secondary">{p.inbound_count}</td>
                  <td className="text-center px-3 py-2.5 text-text-secondary">{p.outbound_count}</td>
                  <td className={`text-center px-3 py-2.5 font-semibold ${delta > 0 ? 'text-green-400' : delta < 0 ? 'text-red-400' : 'text-text-muted'}`}>
                    {delta > 0 ? '+' : ''}{delta}
                  </td>
                  <td className="text-center px-3 py-2.5 text-text-muted">#{p.tipr_rank}</td>
                  <td className="text-left px-3 py-2.5 text-text-muted font-mono text-[10px] hidden lg:table-cell">{p.cluster}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {pages.length > 10 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full py-2.5 text-xs text-accent hover:text-accent-hover flex items-center justify-center gap-1 border-t border-border transition-colors"
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? 'Show less' : `Show all ${pages.length}`}
        </button>
      )}
    </div>
  );
}

function OrphanSection({ pages, recommendations }: { pages: TiprPage[]; recommendations: TiprRecommendation[] }) {
  const orphans = useMemo(() => pages.filter((p) => p.inbound_count === 0), [pages]);
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? orphans : orphans.slice(0, 15);

  // Group orphans by cluster
  const clusterDist = useMemo(() => {
    const map: Record<string, number> = {};
    for (const o of orphans) {
      const c = o.cluster || '/';
      map[c] = (map[c] || 0) + 1;
    }
    return Object.entries(map)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
  }, [orphans]);

  // Find recommendations for each orphan
  const orphanRecs = useMemo(() => {
    const map: Record<string, string[]> = {};
    for (const rec of recommendations) {
      if (rec.type === 'add_link' && rec.target_url) {
        if (!map[rec.target_url]) map[rec.target_url] = [];
        map[rec.target_url].push(rec.source_url);
      }
    }
    return map;
  }, [recommendations]);

  if (orphans.length === 0) {
    return (
      <div className="bg-surface-raised border border-border rounded-xl p-6 text-center">
        <CheckCircle2 size={20} className="text-green-400 mx-auto mb-2" />
        <p className="text-sm font-semibold text-text">No Orphan Pages Found</p>
        <p className="text-xs text-text-muted mt-1">All pages have at least one inbound internal link.</p>
      </div>
    );
  }

  const pct = ((orphans.length / pages.length) * 100).toFixed(1);

  return (
    <div className="bg-surface-raised border border-border rounded-xl overflow-hidden">
      <div className="px-6 py-4 flex items-center gap-2">
        <AlertTriangle size={16} className="text-red-400" />
        <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">Orphan Pages</h2>
        <span className="text-xs text-red-400 font-semibold">{orphans.length} pages ({pct}%)</span>
      </div>
      <div className="px-6 pb-4">
        <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4 mb-4">
          <p className="text-xs text-text-secondary leading-relaxed">
            <strong className="text-text">Orphan pages have zero internal inbound links</strong> and are effectively invisible
            to search engine crawlers. Google cannot discover these pages through your site's link structure,
            meaning they won't be crawled, indexed, or ranked regardless of content quality.
          </p>
        </div>

        {/* Cluster distribution */}
        {clusterDist.length > 1 && (
          <div className="mb-4">
            <p className="text-xs text-text-muted font-semibold mb-2">Orphan distribution by directory:</p>
            <div className="flex flex-wrap gap-2">
              {clusterDist.map(([cluster, count]) => (
                <span key={cluster} className="text-[10px] font-mono bg-surface-overlay px-2 py-1 rounded text-text-secondary">
                  {cluster} <span className="text-text-muted">({count})</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Orphan list */}
        <div className="space-y-2">
          {visible.map((o) => {
            const suggested = orphanRecs[o.url]?.slice(0, 3) ?? [];
            return (
              <div key={o.url} className="border border-border/50 rounded-lg px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />
                  <span className="text-xs text-text font-mono truncate">{shortUrl(o.url)}</span>
                  {o.click_depth >= 0 && (
                    <span className="text-[10px] text-text-muted ml-auto">depth: {o.click_depth}</span>
                  )}
                </div>
                {suggested.length > 0 && (
                  <div className="mt-2 ml-3.5">
                    <p className="text-[10px] text-text-muted font-semibold mb-1">Suggested source pages:</p>
                    {suggested.map((src, i) => (
                      <p key={i} className="text-[10px] text-accent font-mono truncate">{shortUrl(src)}</p>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        {orphans.length > 15 && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="mt-3 text-xs text-accent hover:text-accent-hover flex items-center gap-1 transition-colors"
          >
            {showAll ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {showAll ? 'Show less' : `Show all ${orphans.length} orphans`}
          </button>
        )}
      </div>
    </div>
  );
}

function DepthSection({ pages }: { pages: TiprPage[] }) {
  const depthData = useMemo(() => {
    const counts: Record<number, number> = {};
    for (const p of pages) {
      const d = p.click_depth >= 0 ? Math.min(p.click_depth, 5) : -1;
      if (d >= 0) counts[d] = (counts[d] || 0) + 1;
    }
    return [0, 1, 2, 3, 4, 5].map((d) => ({
      depth: d === 5 ? '5+' : String(d),
      count: counts[d] || 0,
      fill: DEPTH_COLORS[d],
    }));
  }, [pages]);

  const deepPages = useMemo(
    () => pages.filter((p) => p.click_depth > 3).sort((a, b) => b.click_depth - a.click_depth).slice(0, 10),
    [pages]
  );

  return (
    <div className="bg-surface-raised border border-border rounded-xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <GitBranch size={16} className="text-accent" />
        <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">Link Depth Analysis</h2>
      </div>
      <p className="text-xs text-text-muted mb-4">
        Pages at click depth 4+ are hard for search engines to discover. Google recommends important content within 3 clicks of the homepage.
      </p>
      <div className="h-[200px] mb-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={depthData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
            <XAxis dataKey="depth" tick={{ fill: '#94A3B8', fontSize: 11 }} stroke="#334155" />
            <YAxis tick={{ fill: '#94A3B8', fontSize: 11 }} stroke="#334155" />
            <Tooltip
              formatter={((value: any) => [value, 'Pages']) as any}
              contentStyle={{ backgroundColor: '#1A2235', border: '1px solid #1E293B', borderRadius: 8, fontSize: 11 }}
              itemStyle={{ color: '#F1F5F9' }}
              labelStyle={{ color: '#94A3B8' }}
              labelFormatter={((label: any) => `Depth ${label}`) as any}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {depthData.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {deepPages.length > 0 && (
        <div>
          <p className="text-xs text-red-400 font-semibold mb-2">
            {deepPages.length} pages at depth 4+ need shorter paths:
          </p>
          <div className="space-y-1">
            {deepPages.map((p) => (
              <div key={p.url} className="flex items-center justify-between text-[11px]">
                <span className="text-text font-mono truncate max-w-[400px]">{shortUrl(p.url)}</span>
                <span className="text-red-400 font-semibold ml-2">depth {p.click_depth}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function HubSection({ pages }: { pages: TiprPage[] }) {
  const hubs = useMemo(
    () =>
      [...pages]
        .sort((a, b) => b.outbound_count - a.outbound_count)
        .slice(0, 15),
    [pages]
  );

  return (
    <div className="bg-surface-raised border border-border rounded-xl overflow-hidden">
      <div className="px-6 py-4 flex items-center gap-2">
        <Eye size={16} className="text-accent" />
        <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">Top Hub Pages</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-t border-border text-text-muted">
              <th className="text-left px-4 py-2.5 font-semibold">URL</th>
              <th className="text-center px-3 py-2.5 font-semibold">Out Links</th>
              <th className="text-center px-3 py-2.5 font-semibold">In Links</th>
              <th className="text-center px-3 py-2.5 font-semibold">PR Score</th>
              <th className="text-center px-3 py-2.5 font-semibold">CR Score</th>
              <th className="text-center px-3 py-2.5 font-semibold">Type</th>
            </tr>
          </thead>
          <tbody>
            {hubs.map((p, i) => (
              <tr key={p.url} className={`border-t border-border/50 ${i % 2 === 0 ? 'bg-surface-raised' : 'bg-surface-overlay/30'}`}>
                <td className="px-4 py-2.5 text-text font-mono text-[11px] max-w-[300px] truncate">{shortUrl(p.url)}</td>
                <td className="text-center px-3 py-2.5 font-semibold text-text">{p.outbound_count}</td>
                <td className="text-center px-3 py-2.5 text-text-secondary">{p.inbound_count}</td>
                <td className="text-center px-3 py-2.5 text-text-secondary">{p.pagerank_score.toFixed(0)}</td>
                <td className="text-center px-3 py-2.5 text-text-secondary">{p.cheirank_score.toFixed(0)}</td>
                <td className="text-center px-3 py-2.5">
                  <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${QUADRANT_BG[p.classification]} ${QUADRANT_TEXT[p.classification]}`}>
                    {QUADRANT_LABELS[p.classification]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RecommendationsSection({ recommendations }: { recommendations: TiprRecommendation[] }) {
  const [filterGroup, setFilterGroup] = useState<string | null>(null);

  const grouped = useMemo(() => {
    const filtered = filterGroup ? recommendations.filter((r) => r.group === filterGroup) : recommendations;
    const groups: Record<string, TiprRecommendation[]> = { quick_win: [], strategic: [], maintenance: [] };
    for (const r of filtered) {
      if (groups[r.group]) groups[r.group].push(r);
    }
    return groups;
  }, [recommendations, filterGroup]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { quick_win: 0, strategic: 0, maintenance: 0 };
    for (const r of recommendations) {
      if (c[r.group] !== undefined) c[r.group]++;
    }
    return c;
  }, [recommendations]);

  if (recommendations.length === 0) {
    return (
      <div className="bg-surface-raised border border-border rounded-xl p-6 text-center">
        <Info size={20} className="text-text-muted mx-auto mb-2" />
        <p className="text-sm font-semibold text-text">No Recommendations</p>
        <p className="text-xs text-text-muted mt-1">The internal link structure looks balanced.</p>
      </div>
    );
  }

  return (
    <div className="bg-surface-raised border border-border rounded-xl overflow-hidden">
      <div className="px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wrench size={16} className="text-accent" />
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">Link Recommendations</h2>
          <span className="text-xs text-text-muted">({recommendations.length})</span>
        </div>
        <button
          onClick={() => exportRecommendationsCsv(recommendations)}
          className="flex items-center gap-1.5 text-xs text-accent hover:text-accent-hover font-semibold transition-colors"
        >
          <Download size={12} />
          Export CSV
        </button>
      </div>

      {/* Filter tabs */}
      <div className="px-6 pb-3 flex gap-2">
        <button
          onClick={() => setFilterGroup(null)}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            filterGroup === null ? 'bg-accent text-white' : 'bg-surface-overlay text-text-muted hover:text-text'
          }`}
        >
          All ({recommendations.length})
        </button>
        {['quick_win', 'strategic', 'maintenance'].map((g) => (
          <button
            key={g}
            onClick={() => setFilterGroup(filterGroup === g ? null : g)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              filterGroup === g ? 'bg-accent text-white' : 'bg-surface-overlay text-text-muted hover:text-text'
            }`}
          >
            {GROUP_LABELS[g]} ({counts[g]})
          </button>
        ))}
      </div>

      {/* Recommendation cards */}
      <div className="px-6 pb-6 space-y-3">
        {Object.entries(grouped).map(([group, recs]) =>
          recs.map((rec, i) => (
            <div
              key={`${group}-${i}`}
              className={`border-l-4 ${GROUP_COLORS[group]} bg-surface-overlay/40 border border-border/50 rounded-r-lg p-4`}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${PRIORITY_BADGE[rec.priority]}`}>
                    {rec.priority}
                  </span>
                  <span className="text-[10px] text-text-muted font-semibold uppercase">
                    {GROUP_LABELS[rec.group]}
                  </span>
                  <span className="text-[10px] text-text-muted capitalize">
                    {rec.type.replace('_', ' ')}
                  </span>
                </div>
                <span className="text-[10px] text-green-400 font-semibold whitespace-nowrap">
                  {rec.expected_impact}
                </span>
              </div>

              {/* Source → Target */}
              {rec.type === 'add_link' && (
                <div className="flex items-center gap-2 mb-2 text-[11px]">
                  <span className="font-mono text-text truncate max-w-[280px]">{shortUrl(rec.source_url)}</span>
                  <ArrowRight size={12} className="text-accent flex-shrink-0" />
                  <span className="font-mono text-text truncate max-w-[280px]">{shortUrl(rec.target_url)}</span>
                </div>
              )}
              {rec.type === 'review_outlinks' && (
                <div className="mb-2 text-[11px]">
                  <span className="font-mono text-text truncate">{shortUrl(rec.source_url)}</span>
                </div>
              )}

              <p className="text-xs text-text-secondary leading-relaxed mb-2">{rec.reason}</p>

              <div className="flex flex-wrap gap-3 text-[10px] text-text-muted">
                <span>Source PR: <strong className="text-text">{rec.source_pr_score.toFixed(0)}</strong></span>
                {rec.target_pr_score > 0 && (
                  <span>Target PR: <strong className="text-text">{rec.target_pr_score.toFixed(0)}</strong></span>
                )}
                <span>Source outlinks: <strong className="text-text">{rec.source_outlinks}</strong></span>
                {rec.content_relevance > 0 && (
                  <span>Relevance: <strong className="text-text">{(rec.content_relevance * 100).toFixed(0)}%</strong></span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/* ─── Main Page Component ─── */
export default function DashboardLinkIntelligencePage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);
  const tipr = report?.tipr_analysis as TiprAnalysis | null;

  if (!tipr) {
    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto">
        <Link
          to={`/dashboard/${auditId}`}
          className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text transition-colors mb-4"
        >
          <ArrowLeft size={12} />
          Back to Overview
        </Link>
        <div className="bg-surface-raised border border-border rounded-xl p-8 text-center">
          <div className="w-12 h-12 mx-auto mb-4 bg-surface-overlay rounded-xl flex items-center justify-center">
            <Zap size={20} className="text-text-muted" />
          </div>
          <p className="text-sm font-semibold text-text mb-1">Link Intelligence Not Available</p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            TIPR analysis requires a DataForSEO site crawl with link data. Run a Comprehensive Audit to generate
            PageRank, CheiRank, and link equity recommendations.
          </p>
        </div>
      </div>
    );
  }

  const { pages, summary, recommendations } = tipr;
  const hoarders = useMemo(
    () => pages.filter((p) => p.classification === 'hoarder').sort((a, b) => b.pagerank_score - a.pagerank_score),
    [pages]
  );
  const wasters = useMemo(
    () => pages.filter((p) => p.classification === 'waster').sort((a, b) => b.cheirank_score - a.cheirank_score),
    [pages]
  );

  const healthRatio = summary.total_pages > 0 ? ((summary.stars / summary.total_pages) * 100).toFixed(1) : '0';

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
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
            <Zap size={20} className="text-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text font-heading">Link Intelligence</h1>
            <p className="text-sm text-text-secondary mt-0.5">
              TIPR analysis across {summary.total_pages} pages &middot; {healthRatio}% healthy hubs &middot; {recommendations.length} recommendations
            </p>
          </div>
        </div>
      </motion.div>

      {/* Section 1: KPI cards */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <QuadrantKpiCards summary={summary} />
      </motion.div>

      {/* Section 2: Scatter Plot */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <ScatterPlot pages={pages} />
      </motion.div>

      {/* Section 3: Top Hoarders */}
      {hoarders.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <PageTable title="Top Hoarders" icon={Layers} pages={hoarders} colorKey="hoarder" auditId={auditId} />
        </motion.div>
      )}

      {/* Section 4: Top Wasters */}
      {wasters.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <PageTable title="Top Wasters" icon={AlertTriangle} pages={wasters} colorKey="waster" auditId={auditId} />
        </motion.div>
      )}

      {/* Section 5: Orphan Pages */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <OrphanSection pages={pages} recommendations={recommendations} />
      </motion.div>

      {/* Section 6: Link Depth */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
        <DepthSection pages={pages} />
      </motion.div>

      {/* Section 7: Hub Pages */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
        <HubSection pages={pages} />
      </motion.div>

      {/* Section 8: Recommendations */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
        <RecommendationsSection recommendations={recommendations} />
      </motion.div>
    </div>
  );
}
