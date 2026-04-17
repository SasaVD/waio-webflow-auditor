import { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart3,
  Play,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Plus,
  ArrowUp,
  ArrowDown,
  Trash2,
  X,
  ExternalLink,
  Info,
} from 'lucide-react';
import { useAuditStore } from '../stores/auditStore';
import { WdfIdfChart } from '../components/content-optimizer/WdfIdfChart';
import { TermTable } from '../components/content-optimizer/TermTable';

const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

/* ─── Types ─── */

interface Analysis {
  url: string;
  keyword: string;
  analyzed_at: string;
  status: string;
  error?: string;
  result?: {
    keyword: string;
    target_url: string;
    target_word_count: number;
    competitors_analyzed: number;
    competitors_failed: number;
    terms: any[];
    recommendations: any[];
    chart_data: any[];
    summary: {
      total_terms: number;
      core_count: number;
      semantic_count: number;
      auxiliary_count: number;
      filler_count: number;
      content_gap_score: number;
      recommendations_count: {
        increase: number;
        add: number;
        reduce: number;
        remove: number;
      };
    };
    serp_results: { url: string; title: string; position: number }[];
    duration_seconds: number;
    cost_usd: number;
  };
}

interface AnalysisPage {
  key: string;
  url: string;
  keyword: string;
  status: string;
  analyzed_at: string | null;
  content_gap_score: number | null;
}

/* ─── Helpers ─── */

const isHomepage = (url: string): boolean => {
  try {
    const path = new URL(url).pathname.replace(/\/+$/, '');
    return !path || path === '/home' || path === '/index' || path === '/index.html';
  } catch {
    return false;
  }
};

const gapColor = (score: number): string => {
  if (score > 50) return 'text-red-400';
  if (score > 20) return 'text-yellow-400';
  return 'text-green-400';
};

const gapLabel = (score: number): string => {
  if (score > 50) return 'Significant gaps';
  if (score > 20) return 'Partial coverage';
  return 'Well-optimized';
};

/* ─── Component ─── */

export default function DashboardContentOptimizerPage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);

  const [showModal, setShowModal] = useState(false);
  const [targetUrl, setTargetUrl] = useState('');
  const [keyword, setKeyword] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const [currentAnalysis, setCurrentAnalysis] = useState<Analysis | null>(null);
  const [analyzedPages, setAnalyzedPages] = useState<AnalysisPage[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Get crawled page URLs from link graph for the URL selector
  const crawledUrls = useMemo(() => {
    const graph = report?.link_graph as Record<string, any> | null;
    const nodes = graph?.nodes as any[] | null;
    if (!nodes?.length) return [];
    return nodes
      .map((n: any) => n.id as string)
      .filter(Boolean)
      .sort();
  }, [report]);

  // Fetch analyzed pages list
  const fetchPages = useCallback(async () => {
    if (!auditId) return;
    try {
      const res = await fetch(`${apiBase}/api/audit/${auditId}/content-optimizer/pages`);
      if (res.ok) {
        const data = await res.json();
        setAnalyzedPages(data.pages || []);
      }
    } catch {
      // non-fatal
    }
  }, [auditId]);

  // Fetch latest analysis result
  const fetchLatest = useCallback(async () => {
    if (!auditId) return;
    try {
      const res = await fetch(`${apiBase}/api/audit/${auditId}/content-optimizer`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'ok' || data.status === 'failed' || data.status === 'running') {
          setCurrentAnalysis(data as Analysis);
        }
      }
    } catch {
      // non-fatal
    }
    setIsLoading(false);
  }, [auditId]);

  useEffect(() => {
    fetchPages();
    fetchLatest();
  }, [fetchPages, fetchLatest]);

  // Poll while running
  useEffect(() => {
    if (currentAnalysis?.status !== 'running') return;
    const interval = setInterval(async () => {
      const url = currentAnalysis.url;
      const kw = currentAnalysis.keyword;
      const res = await fetch(
        `${apiBase}/api/audit/${auditId}/content-optimizer?url=${encodeURIComponent(url)}&keyword=${encodeURIComponent(kw)}`
      );
      if (res.ok) {
        const data = await res.json();
        if (data.status !== 'running') {
          setCurrentAnalysis(data as Analysis);
          setIsRunning(false);
          fetchPages();
          clearInterval(interval);
        }
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [currentAnalysis?.status, currentAnalysis?.url, currentAnalysis?.keyword, auditId, fetchPages]);

  // Load a specific analysis
  const loadAnalysis = async (url: string, kw: string) => {
    const res = await fetch(
      `${apiBase}/api/audit/${auditId}/content-optimizer?url=${encodeURIComponent(url)}&keyword=${encodeURIComponent(kw)}`
    );
    if (res.ok) {
      const data = await res.json();
      setCurrentAnalysis(data as Analysis);
    }
  };

  // Run new analysis
  const handleRun = async () => {
    if (!targetUrl.trim() || !keyword.trim() || !auditId) return;
    setRunError(null);
    setIsRunning(true);
    try {
      const res = await fetch(
        `${apiBase}/api/audit/${auditId}/content-optimizer/run`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: targetUrl.trim(), keyword: keyword.trim() }),
        }
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to start analysis');
      }
      setShowModal(false);
      setCurrentAnalysis({
        url: targetUrl.trim(),
        keyword: keyword.trim(),
        analyzed_at: new Date().toISOString(),
        status: 'running',
      });
    } catch (err: unknown) {
      setRunError(err instanceof Error ? err.message : 'Unknown error');
      setIsRunning(false);
    }
  };

  const result = currentAnalysis?.result;
  const summary = result?.summary;

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <Loader2 size={24} className="animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 size={18} className="text-cyan-400" />
            <span className="text-xs font-semibold text-text-muted uppercase tracking-widest">
              Content Optimizer
            </span>
          </div>
          <h1 className="text-xl font-bold text-text font-heading">
            WDF*IDF Analysis
          </h1>
          <p className="text-xs text-text-muted mt-1">
            Compare your page's term usage against top-ranking competitors for any keyword
          </p>
        </div>
        <button
          onClick={() => { setShowModal(true); setRunError(null); }}
          className="flex items-center gap-2 px-4 py-2.5 bg-accent hover:bg-accent-hover text-white text-sm font-semibold rounded-xl transition-colors shadow-glow-accent"
        >
          <Plus size={16} />
          New Analysis
        </button>
      </motion.div>

      {/* Previous analyses list */}
      {analyzedPages.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
        >
          <div className="flex flex-wrap gap-2">
            {analyzedPages.map((page) => (
              <button
                key={page.key}
                onClick={() => loadAnalysis(page.url, page.keyword)}
                className={`text-xs px-3 py-2 rounded-lg border transition-all ${
                  currentAnalysis?.url === page.url && currentAnalysis?.keyword === page.keyword
                    ? 'border-accent bg-accent/10 text-accent'
                    : 'border-border bg-surface-raised text-text-secondary hover:border-accent/30'
                }`}
              >
                <div className="font-semibold truncate max-w-[200px]">
                  {new URL(page.url).pathname || '/'}
                </div>
                <div className="text-text-muted mt-0.5">
                  &ldquo;{page.keyword}&rdquo;
                  {page.content_gap_score != null && (
                    <span className={`ml-2 font-mono ${gapColor(page.content_gap_score)}`}>
                      {page.content_gap_score}% gap
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Running state */}
      {currentAnalysis?.status === 'running' && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-raised border border-border rounded-xl p-8 text-center"
        >
          <Loader2 size={32} className="mx-auto mb-4 text-accent animate-spin" />
          <h3 className="text-sm font-bold text-text mb-1">Analyzing content...</h3>
          <p className="text-xs text-text-muted">
            Fetching SERP competitors, extracting content, computing WDF*IDF scores.
            This typically takes 30-60 seconds.
          </p>
        </motion.div>
      )}

      {/* Error state */}
      {currentAnalysis?.status === 'failed' && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-5 flex items-start gap-3">
          <AlertTriangle size={18} className="text-red-400 mt-0.5" />
          <div>
            <h3 className="text-sm font-bold text-red-400">Analysis Failed</h3>
            <p className="text-xs text-text-secondary mt-1">{currentAnalysis.error || 'Unknown error'}</p>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!currentAnalysis && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-raised border border-border rounded-xl p-12 text-center"
        >
          <div className="w-16 h-16 mx-auto mb-4 bg-cyan-500/10 rounded-2xl flex items-center justify-center">
            <BarChart3 size={28} className="text-cyan-400" />
          </div>
          <h3 className="text-lg font-bold text-text font-heading mb-2">No analyses yet</h3>
          <p className="text-sm text-text-muted max-w-md mx-auto mb-6">
            Select a page and target keyword to see how your content compares to the
            top 10 Google results. You'll get a WDF*IDF chart, classified term table,
            and actionable recommendations.
          </p>
          <button
            onClick={() => { setShowModal(true); setRunError(null); }}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent-hover text-white text-sm font-semibold rounded-xl transition-colors"
          >
            <Play size={16} />
            Run Content Analysis
          </button>
        </motion.div>
      )}

      {/* Results */}
      {result && currentAnalysis?.status === 'ok' && (
        <>
          {/* KPI summary row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-surface-raised border border-border rounded-xl p-4">
              <div className="text-[10px] font-bold text-text-muted uppercase tracking-widest mb-1">
                Content Gap
              </div>
              <div className={`text-2xl font-extrabold font-heading ${gapColor(summary!.content_gap_score)}`}>
                {summary!.content_gap_score}%
              </div>
              <div className="text-[10px] text-text-muted mt-0.5">
                {gapLabel(summary!.content_gap_score)}
              </div>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4">
              <div className="text-[10px] font-bold text-text-muted uppercase tracking-widest mb-1">
                Terms Analyzed
              </div>
              <div className="text-2xl font-extrabold text-text font-heading">
                {summary!.total_terms}
              </div>
              <div className="text-[10px] text-text-muted mt-0.5">
                {summary!.core_count} core, {summary!.semantic_count} semantic
              </div>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4">
              <div className="text-[10px] font-bold text-text-muted uppercase tracking-widest mb-1">
                Competitors
              </div>
              <div className="text-2xl font-extrabold text-text font-heading">
                {result.competitors_analyzed}
              </div>
              <div className="text-[10px] text-text-muted mt-0.5">
                from top 10 Google SERP
              </div>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4">
              <div className="text-[10px] font-bold text-text-muted uppercase tracking-widest mb-1">
                Recommendations
              </div>
              <div className="text-2xl font-extrabold text-text font-heading">
                {result.recommendations.length}
              </div>
              <div className="text-[10px] text-text-muted mt-0.5">
                {summary!.recommendations_count.add} add, {summary!.recommendations_count.increase} increase
              </div>
            </div>
          </div>

          {/* Homepage warning */}
          {isHomepage(result.target_url) && (
            <div className="flex items-start gap-3 p-4 bg-amber-50 border-l-4 border-amber-400 rounded-xl">
              <AlertTriangle size={18} className="text-amber-500 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-amber-800 leading-relaxed">
                <span className="block font-semibold text-amber-900 mb-0.5">Homepage analysis caveat</span>
                This analysis is most accurate for service pages, blog posts, and landing pages
                optimized for specific keywords. Homepage analyses typically show inflated gap scores
                because homepages aren&rsquo;t designed to rank for single keywords.
              </p>
            </div>
          )}

          {/* Chart */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-surface-raised border border-border rounded-xl p-6"
          >
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-1">
              WDF*IDF Distribution
            </h2>
            <p className="text-xs text-text-muted mb-4">
              &ldquo;{result.keyword}&rdquo; &mdash; your page (dark line) vs competitors (red=max, yellow=avg)
            </p>
            <WdfIdfChart data={result.chart_data} />
            <div className="mt-3 p-3 bg-surface-overlay rounded-lg">
              <p className="text-xs text-text-secondary">
                {summary!.content_gap_score > 50
                  ? `Your page has significant content gaps \u2014 ${summary!.content_gap_score}% of important terms are underrepresented compared to competitors.`
                  : summary!.content_gap_score > 20
                  ? `Your page covers the topic partially \u2014 ${summary!.content_gap_score}% of important terms need strengthening.`
                  : `Your page is well-optimized \u2014 only ${summary!.content_gap_score}% of important terms are below the optimal range.`}
              </p>
            </div>
          </motion.div>

          {/* Term table */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="bg-surface-raised border border-border rounded-xl p-6"
          >
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-4">
              Term Classification
            </h2>
            <TermTable terms={result.terms} />
          </motion.div>

          {/* Recommendations */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-4"
          >
            <RecommendationCard
              type="add"
              title="Add"
              description="Important terms your competitors use that are missing from your page"
              items={result.recommendations.filter((r: any) => r.type === 'add')}
              icon={<Plus size={14} />}
              accentColor="text-red-400"
              bgColor="bg-red-500/10"
            />
            <RecommendationCard
              type="increase"
              title="Increase"
              description="Terms present but significantly below the competitor average"
              items={result.recommendations.filter((r: any) => r.type === 'increase')}
              icon={<ArrowUp size={14} />}
              accentColor="text-yellow-400"
              bgColor="bg-yellow-500/10"
            />
            <RecommendationCard
              type="reduce"
              title="Reduce"
              description="Terms used significantly more than any competitor"
              items={result.recommendations.filter((r: any) => r.type === 'reduce')}
              icon={<ArrowDown size={14} />}
              accentColor="text-orange-400"
              bgColor="bg-orange-500/10"
            />
            <RecommendationCard
              type="remove"
              title="Remove"
              description="AI-generic filler phrases that weaken content quality"
              items={result.recommendations.filter((r: any) => r.type === 'remove')}
              icon={<Trash2 size={14} />}
              accentColor="text-red-400"
              bgColor="bg-red-500/10"
            />
          </motion.div>

          {/* Methodology */}
          <motion.details
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.25 }}
            className="bg-surface-raised border border-border rounded-xl group"
          >
            <summary className="p-5 text-sm font-bold text-text-muted uppercase tracking-widest cursor-pointer flex items-center gap-2">
              <Info size={14} />
              Methodology & Competitor Data
            </summary>
            <div className="px-5 pb-5 space-y-3 text-xs text-text-secondary">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div>
                  <span className="text-text-muted block mb-0.5">Target URL</span>
                  <a
                    href={result.target_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent hover:underline truncate block"
                  >
                    {result.target_url}
                  </a>
                </div>
                <div>
                  <span className="text-text-muted block mb-0.5">Keyword</span>
                  <span className="text-text">{result.keyword}</span>
                </div>
                <div>
                  <span className="text-text-muted block mb-0.5">Target Word Count</span>
                  <span className="text-text font-mono">{result.target_word_count.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-text-muted block mb-0.5">Duration</span>
                  <span className="text-text font-mono">{result.duration_seconds}s</span>
                </div>
              </div>
              <div>
                <span className="text-text-muted block mb-1.5">SERP Competitors Used</span>
                <div className="space-y-1">
                  {result.serp_results.map((sr) => (
                    <div key={sr.url} className="flex items-center gap-2">
                      <span className="text-text-muted font-mono w-4">#{sr.position}</span>
                      <a
                        href={sr.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-accent hover:underline truncate flex items-center gap-1"
                      >
                        {sr.title || sr.url}
                        <ExternalLink size={10} />
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.details>
        </>
      )}

      {/* Modal */}
      <AnimatePresence>
        {showModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 z-40"
              onClick={() => setShowModal(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
            >
              <div className="bg-surface-raised border border-border rounded-2xl p-6 w-full max-w-lg shadow-card">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="text-lg font-bold text-text font-heading">
                    Run Content Analysis
                  </h3>
                  <button
                    onClick={() => setShowModal(false)}
                    className="p-1.5 text-text-muted hover:text-text rounded-lg hover:bg-surface-overlay transition-colors"
                  >
                    <X size={16} />
                  </button>
                </div>

                <div className="space-y-4">
                  {/* URL input */}
                  <div>
                    <label className="text-xs font-semibold text-text-secondary block mb-1.5">
                      Page URL
                    </label>
                    {crawledUrls.length > 0 ? (
                      <select
                        value={targetUrl}
                        onChange={(e) => setTargetUrl(e.target.value)}
                        className="w-full px-3 py-2.5 bg-surface-overlay border border-border rounded-xl text-sm text-text focus:outline-none focus:ring-1 focus:ring-accent"
                      >
                        <option value="">Select a crawled page...</option>
                        {crawledUrls.map((url) => (
                          <option key={url} value={url}>
                            {new URL(url).pathname || '/'}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="url"
                        value={targetUrl}
                        onChange={(e) => setTargetUrl(e.target.value)}
                        placeholder="https://example.com/page"
                        className="w-full px-3 py-2.5 bg-surface-overlay border border-border rounded-xl text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
                      />
                    )}
                    {crawledUrls.length > 0 && (
                      <div className="mt-1.5">
                        <button
                          onClick={() => {
                            const el = document.getElementById('custom-url-toggle');
                            if (el) el.classList.toggle('hidden');
                          }}
                          className="text-[10px] text-accent hover:underline"
                        >
                          Or enter a custom URL
                        </button>
                        <input
                          id="custom-url-toggle"
                          type="url"
                          value={targetUrl}
                          onChange={(e) => setTargetUrl(e.target.value)}
                          placeholder="https://example.com/custom-page"
                          className="hidden w-full mt-1.5 px-3 py-2 bg-surface-overlay border border-border rounded-xl text-xs text-text placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
                        />
                      </div>
                    )}
                  </div>

                  {/* Keyword input */}
                  <div>
                    <label className="text-xs font-semibold text-text-secondary block mb-1.5">
                      Target Keyword
                    </label>
                    <input
                      type="text"
                      value={keyword}
                      onChange={(e) => setKeyword(e.target.value)}
                      placeholder="e.g., web design agency"
                      className="w-full px-3 py-2.5 bg-surface-overlay border border-border rounded-xl text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                    <p className="text-[10px] text-text-muted mt-1">
                      We'll fetch the top 10 Google results for this keyword and compare term usage
                    </p>
                  </div>

                  {/* Error */}
                  {runError && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400 flex items-start gap-2">
                      <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
                      {runError}
                    </div>
                  )}

                  {/* Page selection guidance */}
                  <div className="p-3 bg-cyan-500/10 border border-cyan-500/15 rounded-lg flex items-start gap-2">
                    <Info size={14} className="text-cyan-400 mt-0.5 flex-shrink-0" />
                    <p className="text-[10px] text-cyan-300/80 leading-relaxed">
                      For best results, analyze service pages, blog posts, or landing pages.
                      Homepages and generic pages typically produce misleading gap scores.
                    </p>
                  </div>

                  {/* Cost note */}
                  <div className="p-3 bg-surface-overlay rounded-lg flex items-start gap-2">
                    <Info size={14} className="text-text-muted mt-0.5 flex-shrink-0" />
                    <p className="text-[10px] text-text-muted">
                      Cost: ~$0.01 (1 SerpApi search). Content extraction from competitor
                      pages is free. Analysis runs in the background and typically completes in 30-60 seconds.
                    </p>
                  </div>

                  {/* Action */}
                  <button
                    onClick={handleRun}
                    disabled={!targetUrl.trim() || !keyword.trim() || isRunning}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl transition-colors"
                  >
                    {isRunning ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <Play size={16} />
                        Run Analysis
                      </>
                    )}
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─── Recommendation Card ─── */

function RecommendationCard({
  type,
  title,
  description,
  items,
  icon,
  accentColor,
  bgColor,
}: {
  type: string;
  title: string;
  description: string;
  items: any[];
  icon: React.ReactNode;
  accentColor: string;
  bgColor: string;
}) {
  if (!items.length) {
    return (
      <div className="bg-surface-raised border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-2">
          <span className={`${accentColor}`}>{icon}</span>
          <h3 className="text-sm font-bold text-text">{title}</h3>
          <span className="text-[10px] font-mono text-text-muted ml-auto">0</span>
        </div>
        <p className="text-xs text-text-muted">{description}</p>
        <div className="mt-3 text-xs text-text-muted/60 text-center py-4">
          <CheckCircle2 size={16} className="mx-auto mb-1 text-green-500/40" />
          No {type} recommendations
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface-raised border border-border rounded-xl p-5">
      <div className="flex items-center gap-2 mb-2">
        <span className={`${accentColor}`}>{icon}</span>
        <h3 className="text-sm font-bold text-text">{title}</h3>
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${bgColor} ${accentColor}`}>
          {items.length}
        </span>
      </div>
      <p className="text-xs text-text-muted mb-3">{description}</p>
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {items.map((item: any) => {
          const cls = item.classification || 'auxiliary';
          const config: Record<string, { label: string; color: string; bg: string }> = {
            core: { label: 'Core', color: 'text-green-400', bg: 'bg-green-500/15' },
            semantic: { label: 'Semantic', color: 'text-blue-400', bg: 'bg-blue-500/15' },
            auxiliary: { label: 'Aux', color: 'text-gray-400', bg: 'bg-gray-500/15' },
            filler: { label: 'Filler', color: 'text-red-400', bg: 'bg-red-500/15' },
          };
          const c = config[cls] || config.auxiliary;
          return (
            <div
              key={item.term}
              className="p-2.5 bg-surface-overlay rounded-lg flex items-start gap-2"
            >
              <span className={`text-[10px] font-bold px-1 py-0.5 rounded mt-0.5 flex-shrink-0 ${c.bg} ${c.color}`}>
                {c.label}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold text-text">{item.term}</div>
                <div className="text-[10px] text-text-muted mt-0.5 leading-relaxed">
                  {item.reason}
                </div>
                {item.suggested_frequency > 0 && (
                  <div className="text-[10px] font-mono text-accent mt-1">
                    Suggested: {item.suggested_frequency}x
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
