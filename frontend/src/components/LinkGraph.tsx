import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { ForceGraphMethods, NodeObject, LinkObject } from 'react-force-graph-2d';
import { motion } from 'framer-motion';
import {
  Network, Maximize2, Minimize2, AlertCircle, Eye, EyeOff,
  Search, X, Download, GitBranch, Workflow,
  ExternalLink, Focus, ArrowDownToLine, ArrowUpFromLine,
} from 'lucide-react';

/* ─── Types ─── */

interface GraphNode {
  id: string;
  label: string;
  cluster: number;
  inbound: number;
  outbound: number;
  depth: number | null;
  is_orphan: boolean;
  nlp_category?: string | null;
  // Added at runtime by force-graph
  x?: number;
  y?: number;
}

interface GraphLink {
  source: string;
  target: string;
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

interface TiprPageData {
  url: string;
  pagerank_score: number;
  cheirank_score: number;
  classification: string;
}

interface LinkGraphProps {
  auditId: string;
  data?: LinkGraphData | null;
  tiprPages?: TiprPageData[] | null;
}

/* ─── Cluster Color Palette ─── */

const CLUSTER_COLORS = [
  '#6366F1', '#22D3EE', '#F472B6', '#34D399', '#FBBF24',
  '#A78BFA', '#FB923C', '#60A5FA', '#4ADE80', '#F87171',
  '#818CF8', '#2DD4BF',
];

const ORPHAN_COLOR = '#EF4444';
const LINK_DEFAULT = 'rgba(148, 163, 184, 0.15)';
const LINK_HIGHLIGHT = 'rgba(99, 102, 241, 0.6)';
const BG_COLOR = '#0F172A';

/* ─── Helpers ─── */

function getClusterColor(cluster: number): string {
  if (cluster < 0) return '#64748B';
  return CLUSTER_COLORS[cluster % CLUSTER_COLORS.length];
}

function getNodeSize(
  node: GraphNode,
  homepageId: string | null,
  inDegree?: Map<string, number>,
): number {
  if (node.id === homepageId) return 14;
  // Use computed inDegree if node.inbound is 0 (backend data may have stale counts)
  const inbound = (inDegree?.get(node.id) ?? 0) || node.inbound || 0;
  if (inbound === 0) return 2.5; // Orphans / zero-inbound: tiny
  // Logarithmic scale: 3 to 12
  return Math.max(3, Math.min(12, 3 + Math.log2(inbound + 1) * 2));
}

function truncateUrl(url: string, maxLen = 30): string {
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

const TIPR_COLORS: Record<string, string> = {
  star: '#22C55E',
  hoarder: '#F59E0B',
  waster: '#EF4444',
  dead_weight: '#6B7280',
};

export const LinkGraph: React.FC<LinkGraphProps> = ({ auditId, data, tiprPages }) => {
  const graphRef = useRef<ForceGraphMethods<NodeObject<GraphNode>, LinkObject<GraphNode, GraphLink>>>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [showOrphans, setShowOrphans] = useState(true);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(!data);
  const [graphData, setGraphData] = useState<LinkGraphData | null>(data || null);
  const [error, setError] = useState<string | null>(null);
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set());
  const [containerWidth, setContainerWidth] = useState(800);

  // Search
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMatches, setSearchMatches] = useState<Set<string>>(new Set());

  // Layout mode
  const [layoutMode, setLayoutMode] = useState<'force' | 'tree'>('force');

  // Filters
  const [filterMode, setFilterMode] = useState<'all' | 'orphans' | 'hubs' | 'depth'>('all');

  // Color-by mode
  const [colorBy, setColorBy] = useState<'cluster' | 'tipr' | 'pagerank' | 'depth'>('cluster');

  // Context menu
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; node: GraphNode } | null>(null);

  const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';
  const graphHeight = expanded ? 700 : 480;

  // Build TIPR lookup
  const tiprLookup = useMemo(() => {
    if (!tiprPages) return new Map<string, TiprPageData>();
    return new Map(tiprPages.map((p) => [p.url, p]));
  }, [tiprPages]);

  // Find homepage node
  const homepageId = useMemo(() => {
    if (!graphData) return null;
    const nodes = graphData.graph.nodes;
    // Homepage is typically the node with the most inbound links at depth 0
    const root = nodes.find(n => {
      try {
        const u = new URL(n.id);
        return u.pathname === '/' || u.pathname === '';
      } catch { return false; }
    });
    return root?.id ?? null;
  }, [graphData]);

  // Compute real stats from graph data
  const computedStats = useMemo(() => {
    if (!graphData) return null;
    const nodes = graphData.graph.nodes;
    const links = graphData.graph.links;

    // BFS to compute depths from homepage
    const depths = new Map<string, number>();
    if (homepageId) {
      const adj = new Map<string, string[]>();
      for (const link of links) {
        const src = typeof link.source === 'object' ? (link.source as GraphNode).id : link.source;
        const tgt = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target;
        if (!adj.has(src)) adj.set(src, []);
        adj.get(src)!.push(tgt);
      }
      const queue = [homepageId];
      depths.set(homepageId, 0);
      while (queue.length > 0) {
        const current = queue.shift()!;
        const d = depths.get(current)!;
        for (const neighbor of adj.get(current) ?? []) {
          if (!depths.has(neighbor)) {
            depths.set(neighbor, d + 1);
            queue.push(neighbor);
          }
        }
      }
    }

    // Compute inDegree for orphan detection
    const inDegree = new Map<string, number>();
    for (const node of nodes) inDegree.set(node.id, 0);
    for (const link of links) {
      const tgt = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target;
      inDegree.set(tgt, (inDegree.get(tgt) ?? 0) + 1);
    }

    const orphanCount = [...inDegree.entries()].filter(
      ([id, deg]) => deg === 0 && id !== homepageId
    ).length;
    const maxDepth = depths.size > 0 ? Math.max(...depths.values()) : graphData.stats.max_depth;

    return {
      maxDepth,
      orphanCount,
      depths,
      inDegree,
    };
  }, [graphData, homepageId]);

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

  // Measure container width
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Configure forces for better clustering + zoom to fit
  useEffect(() => {
    if (!graphRef.current || !graphData) return;
    const fg = graphRef.current;

    // Stronger charge repulsion pushes unconnected nodes apart
    // Stronger link force pulls connected nodes together → tighter clusters
    if (layoutMode === 'force') {
      const charge = fg.d3Force('charge');
      if (charge) {
        charge.strength(-120);
        charge.distanceMax(400);
      }
      const link = fg.d3Force('link');
      if (link) {
        link.distance(30);
        link.strength(0.7);
      }
      const center = fg.d3Force('center');
      if (center) {
        center.strength(0.05);
      }
      fg.d3ReheatSimulation();
    }

    const timer = setTimeout(() => {
      graphRef.current?.zoomToFit(500, 60);
    }, 1500);
    return () => clearTimeout(timer);
  }, [graphData, layoutMode]);

  // Close context menu on click outside
  useEffect(() => {
    const handler = () => setContextMenu(null);
    window.addEventListener('click', handler);
    return () => window.removeEventListener('click', handler);
  }, []);

  // Search handler
  useEffect(() => {
    if (!searchQuery.trim() || !graphData) {
      setSearchMatches(new Set());
      return;
    }
    const q = searchQuery.toLowerCase();
    const matches = new Set<string>();
    for (const node of graphData.graph.nodes) {
      if (node.id.toLowerCase().includes(q) || node.label.toLowerCase().includes(q)) {
        matches.add(node.id);
      }
    }
    setSearchMatches(matches);
  }, [searchQuery, graphData]);

  // Memoize filtered graph data
  const filteredGraphData = useMemo(() => {
    if (!graphData) return { nodes: [] as GraphNode[], links: [] as GraphLink[] };

    let nodes = graphData.graph.nodes;
    let links = graphData.graph.links;

    // Apply orphan filter
    if (!showOrphans) {
      nodes = nodes.filter(n => !n.is_orphan);
    }

    // Apply filter mode
    if (filterMode === 'orphans') {
      nodes = nodes.filter(n => n.is_orphan || (computedStats?.inDegree.get(n.id) ?? 1) === 0);
    } else if (filterMode === 'hubs') {
      nodes = nodes.filter(n => n.inbound > 10);
    }

    // Filter links to match visible nodes
    const nodeIds = new Set(nodes.map(n => n.id));
    links = links.filter(l => {
      const src = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source;
      const tgt = typeof l.target === 'object' ? (l.target as GraphNode).id : l.target;
      return nodeIds.has(src) && nodeIds.has(tgt);
    });

    return { nodes, links };
  }, [graphData, showOrphans, filterMode, computedStats]);

  // Hover handling
  const handleNodeHover = useCallback((node: NodeObject<GraphNode> | null) => {
    if (!graphData) return;
    const newHighlightNodes = new Set<string>();
    const newHighlightLinks = new Set<string>();

    if (node) {
      setHoveredNode(node as GraphNode);
      newHighlightNodes.add(node.id!);
      for (const link of graphData.graph.links) {
        const src = typeof link.source === 'object' ? (link.source as GraphNode).id : link.source;
        const tgt = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target;
        if (src === node.id || tgt === node.id) {
          newHighlightLinks.add(`${src}->${tgt}`);
          newHighlightNodes.add(src);
          newHighlightNodes.add(tgt);
        }
      }
    } else {
      setHoveredNode(null);
    }
    setHighlightNodes(newHighlightNodes);
    setHighlightLinks(newHighlightLinks);
  }, [graphData]);

  // Click handler
  const handleNodeClick = useCallback((node: NodeObject<GraphNode>) => {
    setSelectedNode(prev => prev?.id === node.id ? null : node as GraphNode);
  }, []);

  // Right-click handler
  const handleNodeRightClick = useCallback((node: NodeObject<GraphNode>, event: MouseEvent) => {
    event.preventDefault();
    setContextMenu({ x: event.clientX, y: event.clientY, node: node as GraphNode });
  }, []);

  // Context menu actions
  const focusNode = useCallback((nodeId: string) => {
    if (!graphRef.current || !graphData) return;
    const node = graphData.graph.nodes.find(n => n.id === nodeId);
    if (node && node.x != null && node.y != null) {
      graphRef.current.centerAt(node.x, node.y, 500);
      graphRef.current.zoom(4, 500);
    }
    setContextMenu(null);
  }, [graphData]);

  const highlightConnected = useCallback((nodeId: string, direction: 'in' | 'out') => {
    if (!graphData) return;
    const newNodes = new Set<string>([nodeId]);
    const newLinks = new Set<string>();
    for (const link of graphData.graph.links) {
      const src = typeof link.source === 'object' ? (link.source as GraphNode).id : link.source;
      const tgt = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target;
      if (direction === 'in' && tgt === nodeId) {
        newNodes.add(src);
        newLinks.add(`${src}->${tgt}`);
      } else if (direction === 'out' && src === nodeId) {
        newNodes.add(tgt);
        newLinks.add(`${src}->${tgt}`);
      }
    }
    setHighlightNodes(newNodes);
    setHighlightLinks(newLinks);
    setContextMenu(null);
  }, [graphData]);

  // Search: navigate to matched node
  const navigateToSearchResult = useCallback(() => {
    if (!graphRef.current || searchMatches.size === 0 || !graphData) return;
    const firstMatch = graphData.graph.nodes.find(n => searchMatches.has(n.id));
    if (firstMatch && firstMatch.x != null && firstMatch.y != null) {
      graphRef.current.centerAt(firstMatch.x, firstMatch.y, 500);
      graphRef.current.zoom(3, 500);
    }
  }, [searchMatches, graphData]);

  // Export as PNG
  const exportPNG = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    const canvas = container.querySelector('canvas');
    if (!canvas) return;
    const url = canvas.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = url;
    a.download = `link-graph-${auditId}.png`;
    a.click();
  }, [auditId]);

  // Custom node rendering with zoom-aware LOD
  const nodeCanvasObject = useCallback((node: NodeObject<GraphNode>, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const n = node as GraphNode;
    const inDeg = computedStats?.inDegree;
    const inbound = (inDeg?.get(n.id) ?? 0) || n.inbound || 0;
    // Use TIPR PageRank for sizing if available (more accurate than raw inbound count)
    const tp = tiprLookup.get(n.id);
    const size = tp
      ? Math.max(3, Math.min(14, 3 + (tp.pagerank_score / 100) * 11))
      : getNodeSize(n, homepageId, inDeg);
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const isOrphan = n.is_orphan || (inbound === 0 && n.id !== homepageId);
    const isHomepage = n.id === homepageId;

    // Determine node color based on colorBy mode
    let color: string;
    if (isOrphan && colorBy !== 'tipr') {
      color = ORPHAN_COLOR;
    } else if (colorBy === 'tipr') {
      const tp = tiprLookup.get(n.id);
      color = tp ? (TIPR_COLORS[tp.classification] ?? '#6B7280') : '#6B7280';
    } else if (colorBy === 'pagerank') {
      const tp = tiprLookup.get(n.id);
      if (tp) {
        const t = Math.min(tp.pagerank_score / 100, 1);
        const r = Math.round(34 + t * 221);
        const g = Math.round(211 - t * 90);
        const b = Math.round(238 - t * 180);
        color = `rgb(${r},${g},${b})`;
      } else {
        color = '#6B7280';
      }
    } else if (colorBy === 'depth' || (filterMode === 'depth' && computedStats?.depths)) {
      const depth = computedStats?.depths?.get(n.id) ?? 0;
      const maxD = Math.max(computedStats?.maxDepth ?? 1, 1);
      const t = depth / maxD;
      const r = Math.round(99 + t * 100);
      const g = Math.round(102 + t * 100);
      const b = Math.round(241 - t * 100);
      color = `rgb(${r},${g},${b})`;
    } else {
      color = getClusterColor(n.cluster);
    }

    // Search highlighting
    const isSearchMatch = searchMatches.size > 0 && searchMatches.has(n.id);
    const isSearchDimmed = searchMatches.size > 0 && !isSearchMatch;
    const isHighlighted = highlightNodes.size > 0 && highlightNodes.has(n.id);
    const isDimmed = (highlightNodes.size > 0 && !isHighlighted) || isSearchDimmed;

    ctx.globalAlpha = isDimmed ? 0.15 : 1;

    // LOD rendering
    if (globalScale < 0.4) {
      // Extreme zoom out: just dots, sized by authority
      ctx.beginPath();
      ctx.arc(x, y, Math.max(size * 0.4, 1), 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();
    } else if (globalScale < 1.2) {
      // Medium zoom: colored circles with borders for hubs
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();
      if (inbound > 10 || isHomepage) {
        ctx.strokeStyle = 'rgba(255,255,255,0.6)';
        ctx.lineWidth = 1.5 / globalScale;
        ctx.stroke();
      }
      if (isOrphan) {
        ctx.strokeStyle = ORPHAN_COLOR;
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
      }
      // Labels for high-authority nodes even at medium zoom
      if (inbound > 5 || isHomepage) {
        const label = truncateUrl(n.id, 24);
        const fontSize = Math.max(10 / globalScale, 2);
        ctx.font = `${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = 'rgba(255,255,255,0.7)';
        ctx.fillText(label, x, y + size + 2 / globalScale);
      }
    } else {
      // Zoomed in: full detail with labels
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      if (inbound > 5 || isHomepage) {
        ctx.strokeStyle = 'rgba(255,255,255,0.7)';
        ctx.lineWidth = 1.5 / globalScale;
        ctx.stroke();
      }
      if (isOrphan) {
        ctx.strokeStyle = ORPHAN_COLOR;
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
      }

      // Label for all visible nodes at close zoom
      const label = truncateUrl(n.id);
      const fontSize = Math.max(10 / globalScale, 2);
      ctx.font = `${fontSize}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = 'rgba(255,255,255,0.85)';
      ctx.fillText(label, x, y + size + 2 / globalScale);
    }

    // Search match pulse
    if (isSearchMatch) {
      ctx.globalAlpha = 0.4;
      ctx.beginPath();
      ctx.arc(x, y, size + 4 / globalScale, 0, 2 * Math.PI);
      ctx.strokeStyle = '#FBBF24';
      ctx.lineWidth = 2 / globalScale;
      ctx.stroke();
    }

    ctx.globalAlpha = 1;
  }, [homepageId, highlightNodes, searchMatches, filterMode, computedStats, colorBy, tiprLookup]);

  // Pointer area for click detection
  const nodePointerAreaPaint = useCallback((node: NodeObject<GraphNode>, paintColor: string, ctx: CanvasRenderingContext2D) => {
    const n = node as GraphNode;
    const size = getNodeSize(n, homepageId, computedStats?.inDegree) + 3;
    ctx.beginPath();
    ctx.arc(node.x ?? 0, node.y ?? 0, size, 0, 2 * Math.PI);
    ctx.fillStyle = paintColor;
    ctx.fill();
  }, [homepageId, computedStats]);

  // Link color based on highlight state
  const linkColor = useCallback((link: LinkObject<GraphNode, GraphLink>) => {
    const src = typeof link.source === 'object' ? (link.source as GraphNode).id : link.source;
    const tgt = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target;
    const key = `${src}->${tgt}`;
    if (highlightLinks.has(key)) return LINK_HIGHLIGHT;
    return LINK_DEFAULT;
  }, [highlightLinks]);

  const linkWidth = useCallback((link: LinkObject<GraphNode, GraphLink>) => {
    const src = typeof link.source === 'object' ? (link.source as GraphNode).id : link.source;
    const tgt = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target;
    const key = `${src}->${tgt}`;
    return highlightLinks.has(key) ? 1.5 : 0.3;
  }, [highlightLinks]);

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
  const orphanCount = computedStats?.orphanCount ?? graphData.orphans.orphan_count;
  const maxDepth = computedStats?.maxDepth ?? stats.max_depth;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.13 }}
      className="rounded-2xl overflow-hidden mb-4 border border-border"
    >
      {/* Header */}
      <div className="bg-surface-raised border-b border-border px-5 py-3.5 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-muted flex items-center justify-center">
            <Network size={16} className="text-accent" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-text">Site Link Graph</h3>
            <p className="text-xs text-text-muted">
              {stats.total_pages} pages &middot; {stats.total_internal_links} internal links
              {orphanCount > 0 && (
                <span className="text-red-500 ml-2">&middot; {orphanCount} orphans</span>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Search */}
          <div className="relative">
            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && navigateToSearchResult()}
              placeholder="Search URL..."
              className="pl-7 pr-7 py-1.5 w-44 rounded-lg bg-surface-overlay border border-border text-xs text-text placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text"
              >
                <X size={12} />
              </button>
            )}
          </div>

          {/* Layout toggle */}
          <div className="flex rounded-lg overflow-hidden border border-border">
            <button
              onClick={() => setLayoutMode('force')}
              className={`flex items-center gap-1 px-2.5 py-1.5 text-xs transition-colors ${
                layoutMode === 'force'
                  ? 'bg-accent text-white'
                  : 'bg-surface-overlay text-text-secondary hover:text-text'
              }`}
              title="Force-directed layout"
            >
              <Workflow size={11} />
              Force
            </button>
            <button
              onClick={() => setLayoutMode('tree')}
              className={`flex items-center gap-1 px-2.5 py-1.5 text-xs transition-colors ${
                layoutMode === 'tree'
                  ? 'bg-accent text-white'
                  : 'bg-surface-overlay text-text-secondary hover:text-text'
              }`}
              title="Hierarchical tree layout"
            >
              <GitBranch size={11} />
              Tree
            </button>
          </div>

          {/* Filter toggles */}
          <div className="flex rounded-lg overflow-hidden border border-border">
            {(['all', 'orphans', 'hubs', 'depth'] as const).map(mode => (
              <button
                key={mode}
                onClick={() => setFilterMode(mode === filterMode ? 'all' : mode)}
                className={`px-2.5 py-1.5 text-xs capitalize transition-colors ${
                  filterMode === mode
                    ? 'bg-accent text-white'
                    : 'bg-surface-overlay text-text-secondary hover:text-text'
                }`}
              >
                {mode === 'all' ? 'All' : mode === 'orphans' ? 'Orphans' : mode === 'hubs' ? 'Hubs' : 'Depth'}
              </button>
            ))}
          </div>

          {/* Color-by selector */}
          <select
            value={colorBy}
            onChange={(e) => setColorBy(e.target.value as typeof colorBy)}
            className="px-2 py-1.5 rounded-lg bg-surface-overlay border border-border text-xs text-text-secondary focus:outline-none focus:ring-1 focus:ring-accent"
            title="Color nodes by"
          >
            <option value="cluster">Color: Cluster</option>
            <option value="tipr">Color: TIPR Quadrant</option>
            <option value="pagerank">Color: PageRank</option>
            <option value="depth">Color: Depth</option>
          </select>

          <button
            onClick={() => setShowOrphans(!showOrphans)}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-surface-overlay border border-border hover:bg-border text-xs text-text-secondary transition-colors"
            title={showOrphans ? 'Hide orphan pages' : 'Show orphan pages'}
          >
            {showOrphans ? <EyeOff size={11} /> : <Eye size={11} />}
          </button>
          <button
            onClick={exportPNG}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-surface-overlay border border-border hover:bg-border text-xs text-text-secondary transition-colors"
            title="Export as PNG"
          >
            <Download size={11} />
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-surface-overlay border border-border hover:bg-border text-xs text-text-secondary transition-colors"
          >
            {expanded ? <Minimize2 size={11} /> : <Maximize2 size={11} />}
          </button>
        </div>
      </div>

      {/* Graph Canvas */}
      <div
        ref={containerRef}
        className="relative"
        style={{ height: graphHeight, backgroundColor: BG_COLOR }}
        onContextMenu={e => e.preventDefault()}
      >
        <ForceGraph2D
          ref={graphRef}
          graphData={filteredGraphData}
          width={containerWidth}
          height={graphHeight}
          backgroundColor={BG_COLOR}
          // Performance
          warmupTicks={100}
          cooldownTicks={200}
          d3AlphaDecay={0.05}
          autoPauseRedraw={true}
          // Layout
          dagMode={layoutMode === 'tree' ? 'td' : undefined}
          dagLevelDistance={layoutMode === 'tree' ? 50 : undefined}
          // Node rendering
          nodeCanvasObject={nodeCanvasObject}
          nodeCanvasObjectMode={() => 'replace'}
          nodePointerAreaPaint={nodePointerAreaPaint}
          // Link rendering
          linkColor={linkColor}
          linkWidth={linkWidth}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          linkDirectionalArrowColor={linkColor}
          // Interaction
          onNodeHover={handleNodeHover}
          onNodeClick={handleNodeClick}
          onNodeRightClick={handleNodeRightClick}
          onBackgroundClick={() => {
            setSelectedNode(null);
            setHighlightNodes(new Set());
            setHighlightLinks(new Set());
          }}
          enableNodeDrag={true}
        />

        {/* Hover Tooltip */}
        {hoveredNode && !selectedNode && (
          <div className="absolute top-4 right-4 bg-white/95 backdrop-blur border border-gray-200 rounded-xl p-4 max-w-xs pointer-events-none z-10 shadow-lg">
            <div className="text-xs font-bold text-gray-900 truncate mb-1">{hoveredNode.label}</div>
            <div className="text-[10px] text-gray-500 truncate mb-3">{hoveredNode.id}</div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
              <span className="text-gray-500">Inbound:</span>
              <span className="text-gray-900 font-medium">{hoveredNode.inbound}</span>
              <span className="text-gray-500">Outbound:</span>
              <span className="text-gray-900 font-medium">{hoveredNode.outbound}</span>
              <span className="text-gray-500">Depth:</span>
              <span className="text-gray-900 font-medium">
                {computedStats?.depths.get(hoveredNode.id) ?? hoveredNode.depth ?? 'N/A'}
              </span>
              {hoveredNode.is_orphan && (
                <>
                  <span className="text-red-500">Status:</span>
                  <span className="text-red-500 font-medium">Orphan</span>
                </>
              )}
              {hoveredNode.nlp_category && (
                <>
                  <span className="text-gray-500">Category:</span>
                  <span className="text-gray-900 font-medium truncate">{hoveredNode.nlp_category}</span>
                </>
              )}
              <span className="text-gray-500">Cluster:</span>
              <span className="text-gray-900 font-medium">
                {graphData.clusters[hoveredNode.cluster]?.prefix ?? `#${hoveredNode.cluster}`}
              </span>
            </div>
          </div>
        )}

        {/* Selected Node Detail Panel */}
        {selectedNode && (
          <div className="absolute top-4 right-4 bg-white border border-gray-200 rounded-xl p-4 w-72 z-20 shadow-xl max-h-80 overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-gray-900 truncate flex-1 mr-2">{selectedNode.label}</span>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={14} />
              </button>
            </div>
            <a
              href={selectedNode.id}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] text-indigo-600 hover:underline flex items-center gap-1 mb-3 truncate"
            >
              {selectedNode.id} <ExternalLink size={10} />
            </a>
            <div className="grid grid-cols-3 gap-2 mb-3">
              <div className="bg-gray-50 rounded-lg p-2 text-center">
                <div className="text-sm font-bold text-gray-900">{selectedNode.inbound}</div>
                <div className="text-[9px] text-gray-500 uppercase">In</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-2 text-center">
                <div className="text-sm font-bold text-gray-900">{selectedNode.outbound}</div>
                <div className="text-[9px] text-gray-500 uppercase">Out</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-2 text-center">
                <div className="text-sm font-bold text-gray-900">
                  {computedStats?.depths.get(selectedNode.id) ?? selectedNode.depth ?? '?'}
                </div>
                <div className="text-[9px] text-gray-500 uppercase">Depth</div>
              </div>
            </div>
            {selectedNode.is_orphan && (
              <div className="bg-red-50 text-red-700 text-[10px] font-medium rounded-lg px-2.5 py-1.5 mb-3">
                Orphan page — no inbound internal links
              </div>
            )}
            {/* Inbound links */}
            <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Inbound Links ({selectedNode.inbound})
            </div>
            <div className="space-y-0.5 mb-3 max-h-24 overflow-y-auto">
              {graphData.graph.links
                .filter(l => {
                  const tgt = typeof l.target === 'object' ? (l.target as GraphNode).id : l.target;
                  return tgt === selectedNode.id;
                })
                .slice(0, 20)
                .map((l, i) => {
                  const src = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source;
                  return (
                    <div key={i} className="text-[10px] text-gray-600 truncate">{truncateUrl(src as string, 50)}</div>
                  );
                })}
            </div>
            {/* Outbound links */}
            <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Outbound Links ({selectedNode.outbound})
            </div>
            <div className="space-y-0.5 max-h-24 overflow-y-auto">
              {graphData.graph.links
                .filter(l => {
                  const src = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source;
                  return src === selectedNode.id;
                })
                .slice(0, 20)
                .map((l, i) => {
                  const tgt = typeof l.target === 'object' ? (l.target as GraphNode).id : l.target;
                  return (
                    <div key={i} className="text-[10px] text-gray-600 truncate">{truncateUrl(tgt as string, 50)}</div>
                  );
                })}
            </div>
          </div>
        )}

        {/* Cluster Legend */}
        {graphData.clusters.length > 0 && filterMode !== 'depth' && (
          <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur border border-gray-200 rounded-xl p-3 max-w-xs max-h-40 overflow-y-auto z-10 shadow-md">
            <div className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-2">Clusters</div>
            <div className="space-y-1">
              {graphData.clusters.slice(0, 8).map((cluster, i) => (
                <div key={cluster.prefix} className="flex items-center gap-2 text-[11px]">
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }}
                  />
                  <span className="text-gray-600 truncate">{cluster.prefix}</span>
                  <span className="text-gray-400 ml-auto">{cluster.page_count}</span>
                </div>
              ))}
              {orphanCount > 0 && (
                <div className="flex items-center gap-2 text-[11px]">
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0 border-2 border-red-500" />
                  <span className="text-red-500">Orphan pages</span>
                  <span className="text-gray-400 ml-auto">{orphanCount}</span>
                </div>
              )}
            </div>
          </div>
        )}
        {filterMode === 'depth' && (
          <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur border border-gray-200 rounded-xl p-3 z-10 shadow-md">
            <div className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-2">Depth</div>
            <div className="flex items-center gap-2">
              <div className="w-24 h-2 rounded-full" style={{
                background: 'linear-gradient(to right, #6366F1, #C4B5FD, #F87171)',
              }} />
              <div className="flex justify-between w-24">
                <span className="text-[9px] text-gray-500">0</span>
                <span className="text-[9px] text-gray-500">{maxDepth}</span>
              </div>
            </div>
          </div>
        )}

        {/* Search results indicator */}
        {searchQuery && searchMatches.size > 0 && (
          <div className="absolute top-4 left-4 bg-amber-100 border border-amber-300 rounded-lg px-3 py-1.5 z-10 text-[11px] text-amber-800 font-medium">
            {searchMatches.size} match{searchMatches.size !== 1 ? 'es' : ''} — press Enter to focus
          </div>
        )}

        {/* Context Menu */}
        {contextMenu && (
          <div
            className="fixed bg-white border border-gray-200 rounded-xl shadow-xl py-1 z-50 min-w-[180px]"
            style={{ left: contextMenu.x, top: contextMenu.y }}
            onClick={e => e.stopPropagation()}
          >
            <button
              onClick={() => { window.open(contextMenu.node.id, '_blank'); setContextMenu(null); }}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <ExternalLink size={12} /> Open URL
            </button>
            <button
              onClick={() => highlightConnected(contextMenu.node.id, 'in')}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <ArrowDownToLine size={12} /> Show inbound links
            </button>
            <button
              onClick={() => highlightConnected(contextMenu.node.id, 'out')}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <ArrowUpFromLine size={12} /> Show outbound links
            </button>
            <button
              onClick={() => focusNode(contextMenu.node.id)}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <Focus size={12} /> Focus here
            </button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      <div className="bg-surface-raised px-6 py-3 grid grid-cols-3 md:grid-cols-6 gap-4 text-center border-t border-border">
        <div>
          <div className="text-lg font-bold text-text">{stats.total_pages}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Pages</div>
        </div>
        <div>
          <div className="text-lg font-bold text-text">{filteredGraphData.links.length.toLocaleString()}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Links</div>
        </div>
        <div>
          <div className="text-lg font-bold text-text">{stats.avg_inbound_links}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Avg Links/Page</div>
        </div>
        <div>
          <div className="text-lg font-bold text-text">{maxDepth}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Max Depth</div>
        </div>
        <div>
          <div className={`text-lg font-bold ${orphanCount > 0 ? 'text-red-500' : 'text-text'}`}>{orphanCount}</div>
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
