import { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { motion } from 'framer-motion';
import { Network, Maximize2, Minimize2, AlertCircle, Eye, EyeOff } from 'lucide-react';

/* ─── Types ─── */

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  cluster: number;
  inbound: number;
  outbound: number;
  depth: number | null;
  is_orphan: boolean;
  nlp_category?: string | null;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
  anchor?: string;
}

interface LinkGraphData {
  graph: {
    nodes: GraphNode[];
    links: GraphLink[];
  };
  stats: {
    total_pages: number;
    total_internal_links: number;
    total_edges: number;
    avg_inbound_links: number;
    max_depth: number;
    homepage_inbound: number;
  };
  orphans: {
    orphan_count: number;
    total_known_urls: number;
    crawled_count: number;
  };
  hubs: Array<{
    url: string;
    inbound_links: number;
    outbound_links: number;
    hub_score: number;
  }>;
  clusters: Array<{
    prefix: string;
    page_count: number;
    dominant_category?: string;
    coherence_score?: number;
  }>;
}

interface LinkGraphProps {
  auditId: string;
  data?: LinkGraphData | null;
}

/* ─── Cluster Color Palette ─── */

const CLUSTER_COLORS = [
  '#6366F1', // indigo
  '#22D3EE', // cyan
  '#F472B6', // pink
  '#34D399', // emerald
  '#FBBF24', // amber
  '#A78BFA', // violet
  '#FB923C', // orange
  '#60A5FA', // blue
  '#4ADE80', // green
  '#F87171', // red
  '#818CF8', // periwinkle
  '#2DD4BF', // teal
];

const ORPHAN_COLOR = '#EF4444';
const LINK_COLOR = 'rgba(0,0,0,0.08)';
const LINK_HIGHLIGHT_COLOR = 'rgba(40,32,255,0.5)';

/* ─── Component ─── */

export const LinkGraph: React.FC<LinkGraphProps> = ({ auditId, data }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [showOrphans, setShowOrphans] = useState(true);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(!data);
  const [graphData, setGraphData] = useState<LinkGraphData | null>(data || null);
  const [error, setError] = useState<string | null>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null);

  const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

  // Fetch graph data if not provided as prop
  useEffect(() => {
    if (data) {
      setGraphData(data);
      setLoading(false);
      return;
    }
    const fetchData = async () => {
      try {
        const res = await fetch(`${apiBase}/api/audit/link-graph/${auditId}`);
        if (!res.ok) {
          if (res.status === 404) {
            setError('Link graph data not available yet. It will appear after the site crawl completes.');
          } else {
            setError('Failed to load link graph data.');
          }
          return;
        }
        const result = await res.json();
        setGraphData(result);
      } catch {
        setError('Failed to fetch link graph data.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [auditId, data, apiBase]);

  const getNodeColor = useCallback((node: GraphNode): string => {
    if (node.is_orphan) return ORPHAN_COLOR;
    if (node.cluster >= 0 && node.cluster < CLUSTER_COLORS.length) {
      return CLUSTER_COLORS[node.cluster];
    }
    return CLUSTER_COLORS[Math.abs(node.cluster) % CLUSTER_COLORS.length];
  }, []);

  const getNodeRadius = useCallback((node: GraphNode): number => {
    const base = 3;
    const inbound = node.inbound || 0;
    return Math.min(base + Math.sqrt(inbound) * 1.5, 20);
  }, []);

  // D3 force simulation
  useEffect(() => {
    if (!graphData || !svgRef.current || !containerRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = expanded ? 700 : 450;

    svg.attr('width', width).attr('height', height);

    // Level of detail: for large graphs, show top nodes by inbound + all orphans
    let displayNodes = graphData.graph.nodes;
    let displayLinks = graphData.graph.links;
    const MAX_DISPLAY_NODES = 300;

    if (displayNodes.length > MAX_DISPLAY_NODES) {
      const orphanNodes = displayNodes.filter(n => n.is_orphan && showOrphans);
      const nonOrphanNodes = displayNodes
        .filter(n => !n.is_orphan)
        .sort((a, b) => (b.inbound || 0) - (a.inbound || 0))
        .slice(0, MAX_DISPLAY_NODES - orphanNodes.length);
      displayNodes = [...nonOrphanNodes, ...orphanNodes];
      const nodeIds = new Set(displayNodes.map(n => n.id));
      displayLinks = displayLinks.filter(l => {
        const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
        const targetId = typeof l.target === 'string' ? l.target : l.target.id;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
    }

    if (!showOrphans) {
      displayNodes = displayNodes.filter(n => !n.is_orphan);
      const nodeIds = new Set(displayNodes.map(n => n.id));
      displayLinks = displayLinks.filter(l => {
        const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
        const targetId = typeof l.target === 'string' ? l.target : l.target.id;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
    }

    // Clone data for D3 mutation
    const nodes: GraphNode[] = displayNodes.map(d => ({ ...d }));
    const links: GraphLink[] = displayLinks.map(d => ({ ...d }));

    // Zoom behavior
    const g = svg.append('g');
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 8])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });
    svg.call(zoom);

    // Links
    const linkSelection = g.append('g')
      .selectAll<SVGLineElement, GraphLink>('line')
      .data(links)
      .join('line')
      .attr('stroke', LINK_COLOR)
      .attr('stroke-width', 0.5);

    // Nodes
    const nodeSelection = g.append('g')
      .selectAll<SVGCircleElement, GraphNode>('circle')
      .data(nodes)
      .join('circle')
      .attr('r', d => getNodeRadius(d))
      .attr('fill', d => getNodeColor(d))
      .attr('stroke', d => d.is_orphan ? ORPHAN_COLOR : 'rgba(0,0,0,0.12)')
      .attr('stroke-width', d => d.is_orphan ? 2 : 0.5)
      .attr('opacity', 0.85)
      .style('cursor', 'pointer');

    // Hover interactions
    nodeSelection
      .on('mouseenter', (_event, d) => {
        setHoveredNode(d);
        // Highlight connected links
        linkSelection
          .attr('stroke', l => {
            const sId = typeof l.source === 'object' ? l.source.id : l.source;
            const tId = typeof l.target === 'object' ? l.target.id : l.target;
            return sId === d.id || tId === d.id ? LINK_HIGHLIGHT_COLOR : LINK_COLOR;
          })
          .attr('stroke-width', l => {
            const sId = typeof l.source === 'object' ? l.source.id : l.source;
            const tId = typeof l.target === 'object' ? l.target.id : l.target;
            return sId === d.id || tId === d.id ? 1.5 : 0.5;
          });
        nodeSelection.attr('opacity', n =>
          n.id === d.id ? 1 : 0.3
        );
        // Re-highlight connected nodes
        const connectedIds = new Set<string>();
        links.forEach(l => {
          const sId = typeof l.source === 'object' ? l.source.id : l.source;
          const tId = typeof l.target === 'object' ? l.target.id : l.target;
          if (sId === d.id) connectedIds.add(tId as string);
          if (tId === d.id) connectedIds.add(sId as string);
        });
        nodeSelection.attr('opacity', n =>
          n.id === d.id || connectedIds.has(n.id) ? 1 : 0.2
        );
      })
      .on('mouseleave', () => {
        setHoveredNode(null);
        linkSelection.attr('stroke', LINK_COLOR).attr('stroke-width', 0.5);
        nodeSelection.attr('opacity', 0.85);
      });

    // Drag behavior
    const drag = d3.drag<SVGCircleElement, GraphNode>()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });
    nodeSelection.call(drag);

    // Force simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink<GraphNode, GraphLink>(links)
        .id(d => d.id)
        .distance(40)
        .strength(0.3))
      .force('charge', d3.forceManyBody().strength(-30).distanceMax(200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide<GraphNode>().radius(d => getNodeRadius(d) + 2))
      .on('tick', () => {
        linkSelection
          .attr('x1', d => (d.source as GraphNode).x!)
          .attr('y1', d => (d.source as GraphNode).y!)
          .attr('x2', d => (d.target as GraphNode).x!)
          .attr('y2', d => (d.target as GraphNode).y!);
        nodeSelection
          .attr('cx', d => d.x!)
          .attr('cy', d => d.y!);
      });

    simulationRef.current = simulation;

    // Initial zoom to fit
    setTimeout(() => {
      const bounds = g.node()?.getBBox();
      if (bounds && bounds.width > 0 && bounds.height > 0) {
        const padding = 40;
        const scale = Math.min(
          (width - padding * 2) / bounds.width,
          (height - padding * 2) / bounds.height,
          1.5
        );
        const tx = width / 2 - (bounds.x + bounds.width / 2) * scale;
        const ty = height / 2 - (bounds.y + bounds.height / 2) * scale;
        svg.transition().duration(500).call(
          zoom.transform,
          d3.zoomIdentity.translate(tx, ty).scale(scale)
        );
      }
    }, 2000);

    return () => {
      simulation.stop();
    };
  }, [graphData, expanded, showOrphans, getNodeColor, getNodeRadius]);

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-raised border border-border rounded-2xl p-8 text-center"
      >
        <div className="animate-pulse text-text-muted text-sm">Loading link graph...</div>
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-raised border border-border rounded-2xl p-6"
      >
        <div className="flex items-center gap-2 text-text-muted text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      </motion.div>
    );
  }

  if (!graphData || graphData.graph.nodes.length === 0) return null;

  const stats = graphData.stats;
  const orphanCount = graphData.orphans.orphan_count;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.13 }}
      className="rounded-2xl overflow-hidden mb-4"
    >
      {/* Header */}
      <div className="bg-surface-raised border-b border-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-muted flex items-center justify-center">
            <Network size={16} className="text-accent" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-text">Site Link Graph</h3>
            <p className="text-xs text-text-muted">
              {stats.total_pages} pages &middot; {stats.total_internal_links} internal links
              {orphanCount > 0 && (
                <span className="text-severity-critical ml-2">&middot; {orphanCount} orphan pages</span>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowOrphans(!showOrphans)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-overlay hover:bg-border text-xs text-text-secondary transition-colors"
            title={showOrphans ? 'Hide orphan pages' : 'Show orphan pages'}
          >
            {showOrphans ? <EyeOff size={12} /> : <Eye size={12} />}
            Orphans
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-overlay hover:bg-border text-xs text-text-secondary transition-colors"
          >
            {expanded ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
            {expanded ? 'Collapse' : 'Expand'}
          </button>
        </div>
      </div>

      {/* Graph Canvas — intentionally dark for data visualization contrast */}
      <div
        ref={containerRef}
        className="relative bg-[#0F172A]"
        style={{ height: expanded ? 700 : 450 }}
      >
        <svg ref={svgRef} className="w-full h-full" />

        {/* Tooltip */}
        {hoveredNode && (
          <div className="absolute top-4 right-4 bg-white/95 backdrop-blur border border-border rounded-xl p-4 max-w-xs pointer-events-none z-10 shadow-card-hover">
            <div className="text-xs font-bold text-text truncate mb-2">{hoveredNode.label}</div>
            <div className="text-[10px] text-text-muted truncate mb-3">{hoveredNode.id}</div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
              <span className="text-text-muted">Inbound:</span>
              <span className="text-text font-medium">{hoveredNode.inbound}</span>
              <span className="text-text-muted">Outbound:</span>
              <span className="text-text font-medium">{hoveredNode.outbound}</span>
              <span className="text-text-muted">Click depth:</span>
              <span className="text-text font-medium">{hoveredNode.depth ?? 'N/A'}</span>
              {hoveredNode.is_orphan && (
                <>
                  <span className="text-severity-critical">Status:</span>
                  <span className="text-severity-critical font-medium">Orphan page</span>
                </>
              )}
              {hoveredNode.nlp_category && (
                <>
                  <span className="text-text-muted">Category:</span>
                  <span className="text-text font-medium truncate">{hoveredNode.nlp_category}</span>
                </>
              )}
            </div>
          </div>
        )}

        {/* Cluster Legend */}
        {graphData.clusters.length > 0 && (
          <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur border border-border rounded-xl p-3 max-w-xs max-h-40 overflow-y-auto z-10 shadow-card">
            <div className="text-[10px] text-text-muted font-semibold uppercase tracking-wider mb-2">Clusters</div>
            <div className="space-y-1">
              {graphData.clusters.slice(0, 8).map((cluster, i) => (
                <div key={cluster.prefix} className="flex items-center gap-2 text-[11px]">
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }}
                  />
                  <span className="text-text-secondary truncate">{cluster.prefix}</span>
                  <span className="text-text-muted ml-auto">{cluster.page_count}</span>
                </div>
              ))}
              {orphanCount > 0 && (
                <div className="flex items-center gap-2 text-[11px]">
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0 border border-red-500" style={{ backgroundColor: 'transparent' }} />
                  <span className="text-severity-critical">Orphan pages</span>
                  <span className="text-text-muted ml-auto">{orphanCount}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      <div className="bg-surface-raised px-6 py-3 grid grid-cols-2 md:grid-cols-5 gap-4 text-center border-t border-border">
        <div>
          <div className="text-lg font-bold text-text">{stats.total_pages}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Pages</div>
        </div>
        <div>
          <div className="text-lg font-bold text-text">{stats.avg_inbound_links}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Avg Links</div>
        </div>
        <div>
          <div className="text-lg font-bold text-text">{stats.max_depth}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Max Depth</div>
        </div>
        <div>
          <div className={`text-lg font-bold ${orphanCount > 0 ? 'text-severity-critical' : 'text-text'}`}>{orphanCount}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Orphans</div>
        </div>
        <div>
          <div className="text-lg font-bold text-text">{graphData.hubs.length}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Hub Pages</div>
        </div>
      </div>
    </motion.div>
  );
};
