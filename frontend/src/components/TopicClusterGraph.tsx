import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { ForceGraphMethods, NodeObject, LinkObject } from 'react-force-graph-2d';
import { motion } from 'framer-motion';
import { Maximize2, Minimize2, Target, Eye, EyeOff } from 'lucide-react';

/* ─── Types ─── */

interface ClusterNode {
  id: string;
  label: string;
  cluster: number;
  clusterLabel: string;
  color: string;
  isPillar: boolean;
  wordCount: number;
  entityOverlap: number;
  x?: number;
  y?: number;
}

interface ClusterLink {
  source: string;
  target: string;
  isRecommended?: boolean; // dashed = missing recommended link
}

interface SemanticCluster {
  id: number;
  label: string;
  color: string;
  pillar: { url: string; title: string; score: number; word_count: number } | null;
  pages: {
    url: string;
    title: string;
    links_to_pillar: boolean | null;
    pillar_links_here: boolean | null;
    entity_overlap: number;
    word_count: number;
  }[];
  size: number;
  link_health: Record<string, unknown>;
}

interface TopicClusterGraphProps {
  clusters: SemanticCluster[];
  graphLinks: { source: string; target: string }[];
  linkRecommendations?: { source_url: string; target_url: string }[];
}

/* ─── Constants ─── */

const BG_COLOR = '#0F172A';
const LINK_COLOR = 'rgba(148, 163, 184, 0.12)';
const LINK_RECOMMENDED = 'rgba(239, 68, 68, 0.25)';
const PILLAR_RING = '#FBBF24';

function truncateUrl(url: string, maxLen = 35): string {
  try {
    const u = new URL(url);
    const path = u.pathname;
    if (path.length <= maxLen) return path || '/';
    return '...' + path.slice(-maxLen + 3);
  } catch {
    return url.length > maxLen ? '...' + url.slice(-maxLen + 3) : url;
  }
}

/* ─── Component ─── */

export const TopicClusterGraph: React.FC<TopicClusterGraphProps> = ({
  clusters,
  graphLinks,
  linkRecommendations,
}) => {
  const graphRef = useRef<ForceGraphMethods<NodeObject<ClusterNode>, LinkObject<ClusterNode, ClusterLink>>>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [focusCluster, setFocusCluster] = useState<number | null>(null);
  const [showRecommended, setShowRecommended] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<ClusterNode | null>(null);

  // Build graph data from clusters
  const graphData = useMemo(() => {
    const nodes: ClusterNode[] = [];
    const nodeUrls = new Set<string>();

    for (const cluster of clusters) {
      const pillarUrl = cluster.pillar?.url ?? '';
      for (const page of cluster.pages) {
        if (nodeUrls.has(page.url)) continue;
        nodeUrls.add(page.url);
        nodes.push({
          id: page.url,
          label: page.title || truncateUrl(page.url),
          cluster: cluster.id,
          clusterLabel: cluster.label,
          color: cluster.color,
          isPillar: page.url === pillarUrl,
          wordCount: page.word_count,
          entityOverlap: page.entity_overlap,
        });
      }
    }

    // Filter actual links to only include nodes we have
    const links: ClusterLink[] = graphLinks
      .filter(l => nodeUrls.has(l.source) && nodeUrls.has(l.target))
      .map(l => ({ source: l.source, target: l.target, isRecommended: false }));

    // Add recommended links (dashed) if toggled
    if (showRecommended && linkRecommendations) {
      for (const rec of linkRecommendations) {
        if (nodeUrls.has(rec.source_url) && nodeUrls.has(rec.target_url)) {
          // Don't duplicate existing links
          const exists = links.some(
            l => l.source === rec.source_url && l.target === rec.target_url
          );
          if (!exists) {
            links.push({
              source: rec.source_url,
              target: rec.target_url,
              isRecommended: true,
            });
          }
        }
      }
    }

    return { nodes, links };
  }, [clusters, graphLinks, linkRecommendations, showRecommended]);

  // Filtered data when focusing on a specific cluster
  const filteredData = useMemo(() => {
    if (focusCluster === null) return graphData;
    const clusterUrls = new Set(
      graphData.nodes.filter(n => n.cluster === focusCluster).map(n => n.id)
    );
    return {
      nodes: graphData.nodes.filter(n => clusterUrls.has(n.id)),
      links: graphData.links.filter(
        l => clusterUrls.has(l.source as string) || clusterUrls.has(l.target as string)
      ),
    };
  }, [graphData, focusCluster]);

  // Configure forces
  useEffect(() => {
    const fg = graphRef.current;
    if (!fg) return;

    const charge = fg.d3Force('charge');
    if (charge) {
      (charge as any).strength(-80);
      (charge as any).distanceMax(350);
    }
    const link = fg.d3Force('link');
    if (link) {
      (link as any).distance((l: any) => {
        const src = typeof l.source === 'object' ? l.source : null;
        const tgt = typeof l.target === 'object' ? l.target : null;
        // Tighter within cluster, looser between
        if (src && tgt && src.cluster === tgt.cluster) return 20;
        return 60;
      });
      (link as any).strength((l: any) => {
        const src = typeof l.source === 'object' ? l.source : null;
        const tgt = typeof l.target === 'object' ? l.target : null;
        if (src && tgt && src.cluster === tgt.cluster) return 0.8;
        return 0.2;
      });
    }
    fg.d3ReheatSimulation();
  }, [filteredData]);

  // Container dimensions
  const [dims, setDims] = useState({ w: 800, h: 500 });
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setDims({ w: el.clientWidth, h: expanded ? 700 : 500 });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [expanded]);

  // Node rendering
  const nodeCanvasObject = useCallback(
    (node: NodeObject<ClusterNode>, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as ClusterNode & { x: number; y: number };
      if (!n.x || !n.y) return;

      const isPillar = n.isPillar;
      const baseSize = isPillar ? 8 : Math.max(2.5, Math.min(6, 2.5 + Math.log2((n.wordCount || 100) / 100 + 1)));
      const isHovered = hoveredNode?.id === n.id;

      // Pillar ring
      if (isPillar) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, baseSize + 3, 0, 2 * Math.PI);
        ctx.strokeStyle = PILLAR_RING;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(n.x, n.y, baseSize, 0, 2 * Math.PI);
      ctx.fillStyle = isHovered ? '#FFFFFF' : n.color;
      ctx.fill();

      // Label on zoom
      if (globalScale > 2.5 || isPillar || isHovered) {
        const label = truncateUrl(n.id, 25);
        const fontSize = isPillar ? 12 / globalScale : 10 / globalScale;
        ctx.font = `${isPillar ? 'bold ' : ''}${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = isHovered ? '#FFFFFF' : 'rgba(241, 245, 249, 0.7)';
        ctx.fillText(label, n.x, n.y + baseSize + 2);
      }
    },
    [hoveredNode],
  );

  // Link rendering
  const linkCanvasObject = useCallback(
    (link: LinkObject<ClusterNode, ClusterLink>, ctx: CanvasRenderingContext2D) => {
      const src = link.source as ClusterNode & { x: number; y: number };
      const tgt = link.target as ClusterNode & { x: number; y: number };
      if (!src?.x || !tgt?.x) return;

      ctx.beginPath();
      if ((link as any).isRecommended) {
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = LINK_RECOMMENDED;
      } else {
        ctx.setLineDash([]);
        ctx.strokeStyle = LINK_COLOR;
      }
      ctx.lineWidth = 0.5;
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.stroke();
      ctx.setLineDash([]);
    },
    [],
  );

  if (graphData.nodes.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface-raised border border-border rounded-xl overflow-hidden"
    >
      {/* Controls bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-bold text-text uppercase tracking-widest">
            Cluster Visualization
          </h3>
          <span className="text-[10px] text-text-muted">
            {filteredData.nodes.length} nodes · {filteredData.links.length} edges
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* Focus cluster selector */}
          <select
            value={focusCluster ?? ''}
            onChange={e => setFocusCluster(e.target.value === '' ? null : Number(e.target.value))}
            className="text-[10px] bg-surface-overlay border border-border rounded-lg px-2 py-1 text-text"
          >
            <option value="">All Clusters</option>
            {clusters.map(c => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>
          {/* Show recommended */}
          <button
            onClick={() => setShowRecommended(!showRecommended)}
            className={`p-1.5 rounded-lg transition-colors ${
              showRecommended ? 'bg-red-500/10 text-red-400' : 'text-text-muted hover:text-text'
            }`}
            title={showRecommended ? 'Hide recommended links' : 'Show recommended links'}
          >
            {showRecommended ? <Eye size={14} /> : <EyeOff size={14} />}
          </button>
          {/* Expand */}
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1.5 rounded-lg text-text-muted hover:text-text transition-colors"
          >
            {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      {/* Graph */}
      <div ref={containerRef} style={{ height: expanded ? 700 : 500, background: BG_COLOR }}>
        <ForceGraph2D
          ref={graphRef}
          graphData={filteredData}
          width={dims.w}
          height={dims.h}
          backgroundColor={BG_COLOR}
          nodeCanvasObject={nodeCanvasObject}
          linkCanvasObject={linkCanvasObject}
          nodeRelSize={4}
          warmupTicks={80}
          cooldownTicks={150}
          d3AlphaDecay={0.025}
          onNodeHover={(node) => setHoveredNode(node as ClusterNode | null)}
          nodeLabel={(node: any) => {
            const n = node as ClusterNode;
            return `${n.label}\nCluster: ${n.clusterLabel}${n.isPillar ? '\n⭐ Pillar Page' : ''}\nEntity overlap: ${Math.round(n.entityOverlap * 100)}%`;
          }}
        />
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 px-4 py-2 border-t border-border overflow-x-auto">
        {clusters.slice(0, 8).map(c => (
          <button
            key={c.id}
            onClick={() => setFocusCluster(focusCluster === c.id ? null : c.id)}
            className={`flex items-center gap-1.5 text-[10px] text-text-muted hover:text-text transition-colors whitespace-nowrap ${
              focusCluster === c.id ? 'font-bold text-text' : ''
            }`}
          >
            <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: c.color }} />
            {c.label.split(' · ')[0]}
          </button>
        ))}
        <span className="flex items-center gap-1 text-[10px] text-text-muted whitespace-nowrap">
          <Target size={10} className="text-amber-400" /> = Pillar
        </span>
      </div>
    </motion.div>
  );
};

export default TopicClusterGraph;
