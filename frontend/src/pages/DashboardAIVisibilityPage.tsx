import { useEffect, useState } from 'react';
import { useParams } from 'react-router';
import { motion } from 'framer-motion';
import {
  Eye,
  RefreshCw,
  Clock,
  ExternalLink,
  BarChart3,
  Database,
  Loader2,
} from 'lucide-react';
import { useAIVisibilityStore } from '../stores/aiVisibilityStore';
import { EngineCard } from '../components/ai-visibility/EngineCard';
import { ZeroMentionsCard } from '../components/ai-visibility/ZeroMentionsCard';
import { AIVisibilityModal } from '../components/ai-visibility/AIVisibilityModal';

export default function DashboardAIVisibilityPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { data, status, fetchStatus } = useAIVisibilityStore();
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    if (auditId) fetchStatus(auditId);
    return () => {
      useAIVisibilityStore.getState().stopPolling();
    };
  }, [auditId, fetchStatus]);

  // Loading state
  if (status === 'loading' || status === 'idle') {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <Loader2 size={24} className="text-accent animate-spin" />
      </div>
    );
  }

  // Not computed state
  if (status === 'not_computed') {
    return (
      <div className="p-6 lg:p-8 max-w-4xl mx-auto">
        <div className="text-center py-16">
          <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Eye size={24} className="text-accent" />
          </div>
          <h1 className="text-xl font-bold text-text font-heading mb-2">
            AI Visibility Analysis
          </h1>
          <p className="text-sm text-text-muted max-w-md mx-auto mb-6">
            Test how your brand appears across ChatGPT, Claude, Gemini, and Perplexity.
            Discover if AI engines mention you in category searches and reputation queries.
          </p>
          <button
            onClick={() => setModalOpen(true)}
            className="px-6 py-2.5 text-sm font-bold text-white bg-accent hover:bg-accent-hover rounded-xl shadow-glow-accent/20 hover:shadow-glow-accent transition-all"
          >
            Run Analysis
          </button>
        </div>
        {auditId && (
          <AIVisibilityModal
            auditId={auditId}
            open={modalOpen}
            onClose={() => setModalOpen(false)}
          />
        )}
      </div>
    );
  }

  // Running state
  if (status === 'running') {
    return (
      <div className="p-6 lg:p-8 max-w-4xl mx-auto">
        <div className="text-center py-16">
          <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Loader2 size={24} className="text-accent animate-spin" />
          </div>
          <h1 className="text-xl font-bold text-text font-heading mb-2">
            Analysis Running
          </h1>
          <p className="text-sm text-text-muted max-w-md mx-auto">
            Querying 4 AI engines with 4 prompts each. This typically takes 30–60 seconds.
          </p>
        </div>
      </div>
    );
  }

  // Failed without data
  if (!data) {
    return (
      <div className="p-6 lg:p-8 max-w-4xl mx-auto">
        <div className="text-center py-16">
          <h1 className="text-xl font-bold text-text font-heading mb-2">
            Analysis Failed
          </h1>
          <p className="text-sm text-text-muted mb-4">
            Something went wrong. Try running the analysis again.
          </p>
          <button
            onClick={() => setModalOpen(true)}
            className="px-6 py-2.5 text-sm font-bold text-white bg-accent hover:bg-accent-hover rounded-xl transition-all"
          >
            Retry
          </button>
          {auditId && (
            <AIVisibilityModal
              auditId={auditId}
              open={modalOpen}
              onClose={() => setModalOpen(false)}
            />
          )}
        </div>
      </div>
    );
  }

  // ───── Has data ─────
  const { mentions_database: mentions, live_test: liveTest } = data;
  const hasMentions = mentions.total > 0;
  const hasSov = !!data.share_of_voice;
  const industryLeaf = data.detected_industry?.split('/').filter(Boolean).pop();
  const engines = liveTest.engines;
  const prompts = liveTest.prompts_used;
  const totalPrompts = prompts.length;

  // Compute competitive intelligence from discovery responses
  const competitorMentions = extractCompetitorMentions(engines, prompts, data.brand_name);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* ── Section 1: Header + metadata ── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-start justify-between gap-4"
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-text-muted uppercase tracking-widest">
              AI Visibility
            </span>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                data.last_computed_status === 'ok'
                  ? 'text-success bg-success/10'
                  : data.last_computed_status === 'partial'
                    ? 'text-amber-400 bg-amber-500/10'
                    : 'text-red-400 bg-red-500/10'
              }`}
            >
              {data.last_computed_status}
            </span>
          </div>
          <h1 className="text-xl font-bold text-text font-heading">
            {data.brand_name}
          </h1>
          <div className="flex items-center gap-3 mt-1 text-xs text-text-muted">
            {data.brand_name_source === 'override' && (
              <span className="bg-accent/10 text-accent px-1.5 py-0.5 rounded text-[10px] font-semibold">
                Manually set
              </span>
            )}
            {industryLeaf && (
              <span>{industryLeaf}</span>
            )}
            <span className="flex items-center gap-1">
              <Clock size={10} />
              {new Date(data.last_computed_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
            <span>{data.duration_seconds}s</span>
            <span>Run #{data.run_count}</span>
          </div>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-accent bg-accent/10 hover:bg-accent/20 rounded-xl transition-all"
        >
          <RefreshCw size={14} />
          Recompute
        </button>
      </motion.div>

      {/* ── Section 2: Share of Voice (if competitors available) ── */}
      {hasSov && data.share_of_voice && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="bg-surface-raised border border-border rounded-xl p-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 size={16} className="text-accent" />
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
              Share of Voice
            </h2>
          </div>
          <p className="text-xs text-text-muted mb-4">
            Measured across {data.share_of_voice.total_mentions_analyzed.toLocaleString()} AI
            responses from Google AI Overview + ChatGPT.
          </p>
          <div className="space-y-3">
            {/* Brand row */}
            <SovBar
              label={data.brand_name}
              value={data.share_of_voice.brand_sov}
              isAccent
            />
            {/* Competitor rows */}
            {Object.entries(data.share_of_voice.competitor_sov)
              .sort(([, a], [, b]) => b - a)
              .map(([domain, sov]) => (
                <SovBar key={domain} label={domain} value={sov} />
              ))}
          </div>
        </motion.div>
      )}

      {/* ── Section 3: Platform Breakdown (Database) ── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Database size={16} className="text-text-muted" />
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
            Pre-Indexed Mentions
          </h2>
        </div>

        {hasMentions ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {Object.entries(mentions.by_platform).map(([platform, count]) => (
              <div
                key={platform}
                className="bg-surface-raised border border-border rounded-xl p-5"
              >
                <div className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                  {platform.replace(/_/g, ' ')}
                </div>
                <div className="text-2xl font-extrabold text-text font-heading">
                  {count}
                </div>
                <div className="text-xs text-text-muted mt-1">mentions</div>
              </div>
            ))}
            {mentions.ai_search_volume > 0 && (
              <div className="bg-surface-raised border border-border rounded-xl p-5">
                <div className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                  AI Search Volume
                </div>
                <div className="text-2xl font-extrabold text-text font-heading">
                  {mentions.ai_search_volume.toLocaleString()}
                </div>
                <div className="text-xs text-text-muted mt-1">monthly queries</div>
              </div>
            )}
          </div>
        ) : (
          <ZeroMentionsCard
            brandName={data.brand_name}
            industryLeaf={industryLeaf}
          />
        )}

        {/* Triggering prompts */}
        {mentions.triggering_prompts.length > 0 && (
          <div className="mt-4 bg-surface-raised border border-border rounded-xl p-5">
            <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-3">
              Triggering Prompts
            </h3>
            <div className="space-y-2">
              {mentions.triggering_prompts.map((tp, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-2 border-b border-border last:border-0"
                >
                  <span className="text-sm text-text">{tp.prompt}</span>
                  <div className="flex items-center gap-3 text-xs text-text-muted">
                    <span>{tp.platform.replace(/_/g, ' ')}</span>
                    {tp.ai_search_volume > 0 && (
                      <span>{tp.ai_search_volume.toLocaleString()} vol</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.div>

      {/* ── Section 4: Live Engine Tests ── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
      >
        <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
          Live Engine Tests
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(engines).map(([engineKey, engine]) => (
            <EngineCard
              key={engineKey}
              engineKey={engineKey}
              engine={engine}
              prompts={prompts}
              totalPrompts={totalPrompts}
            />
          ))}
        </div>
      </motion.div>

      {/* ── Section 4.5: Competitive Intelligence (brands mentioned in discovery) ── */}
      {(competitorMentions.brand || competitorMentions.competitors.length > 0) && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.18 }}
          className="bg-surface-raised border border-border rounded-xl p-5"
        >
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
            Brands Mentioned in Discovery Prompts
          </h2>
          <p className="text-xs text-text-muted mb-4">
            {competitorMentions.brand ? (
              <>
                <strong className="text-text">{data.brand_name}</strong> appeared{' '}
                {competitorMentions.brand.count}× in AI responses to your industry's discovery prompts
                {normalizeBrand(competitorMentions.brand.name) !== normalizeBrand(data.brand_name) && (
                  <> (spelled as <em>"{competitorMentions.brand.name}"</em>)</>
                )}
                .
                {competitorMentions.competitors.length > 0
                  ? ' These competitors appeared alongside you.'
                  : ' No other brands were called out in the responses.'}
              </>
            ) : (
              <>
                These brands appeared in AI responses to your industry's discovery prompts — even though{' '}
                <strong className="text-text">{data.brand_name}</strong> was not mentioned.
                These are your AI visibility competitors.
              </>
            )}
          </p>
          <div className="flex flex-wrap gap-2">
            {competitorMentions.brand && (
              <span
                className="text-xs font-semibold text-accent bg-accent/10 border border-accent/30 px-2.5 py-1 rounded-lg"
              >
                {competitorMentions.brand.name}
                <span className="text-accent/70 ml-1">×{competitorMentions.brand.count}</span>
              </span>
            )}
            {competitorMentions.competitors.slice(0, 20).map((brand) => (
              <span
                key={brand.name}
                className="text-xs font-semibold text-text-secondary bg-surface-overlay px-2.5 py-1 rounded-lg"
              >
                {brand.name}
                <span className="text-text-muted ml-1">×{brand.count}</span>
              </span>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Section 5: Top Cited Pages ── */}
      {mentions.top_pages.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-surface-raised border border-border rounded-xl p-5"
        >
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
            Top Cited Pages
          </h2>
          <div className="space-y-2">
            {mentions.top_pages.map((page, i) => (
              <div
                key={i}
                className="flex items-center justify-between py-2 border-b border-border last:border-0"
              >
                <a
                  href={page.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-accent hover:text-accent-hover transition-colors inline-flex items-center gap-1 truncate max-w-[80%]"
                >
                  {page.url.replace(/^https?:\/\//, '')}
                  <ExternalLink size={10} />
                </a>
                <span className="text-sm font-bold text-text">{page.mention_count}</span>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Section 6: Cost & Methodology Footer ── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="bg-surface-raised border border-border rounded-xl p-5"
      >
        <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-3">
          Cost & Methodology
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          <div>
            <div className="text-xs text-text-muted">This Run</div>
            <div className="text-sm font-bold text-text">${data.cost_usd.toFixed(4)}</div>
          </div>
          <div>
            <div className="text-xs text-text-muted">Cumulative</div>
            <div className="text-sm font-bold text-text">${data.cumulative_cost_usd.toFixed(4)}</div>
          </div>
          <div>
            <div className="text-xs text-text-muted">Duration</div>
            <div className="text-sm font-bold text-text">{data.duration_seconds}s</div>
          </div>
          <div>
            <div className="text-xs text-text-muted">Total Runs</div>
            <div className="text-sm font-bold text-text">{data.run_count}</div>
          </div>
        </div>

        <div className="space-y-2 text-xs text-text-muted">
          <p>
            <strong className="text-text-secondary">Pre-Indexed Mentions</strong> — aggregated
            from DataForSEO's database of pre-scanned AI responses. Covers Google AI Overview
            and ChatGPT only. Updated periodically by DataForSEO.
          </p>
          <p>
            <strong className="text-text-secondary">Live Engine Tests</strong> — fresh queries
            sent to each AI engine at the time of analysis. Results are sampled from 4 canonical
            prompts (3 discovery + 1 reputation). Different engines may produce different results
            on repeat queries.
          </p>
          {hasSov && (
            <p>
              <strong className="text-text-secondary">Share of Voice</strong> — computed from
              cross-aggregated mention counts across the pre-indexed database. Not derived from
              live test responses.
            </p>
          )}
        </div>

        {/* Prompts used */}
        <div className="mt-4 pt-4 border-t border-border">
          <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-2">
            Prompts Used
          </h3>
          <div className="space-y-1">
            {prompts.map((p) => (
              <div key={p.id} className="flex items-center gap-2 text-xs">
                <span
                  className={`font-bold uppercase tracking-wider ${
                    p.category === 'reputation' ? 'text-accent' : 'text-text-muted'
                  }`}
                >
                  {p.category}
                </span>
                <span className="text-text-secondary">"{p.text}"</span>
              </div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Modal */}
      {auditId && (
        <AIVisibilityModal
          auditId={auditId}
          open={modalOpen}
          onClose={() => setModalOpen(false)}
        />
      )}
    </div>
  );
}

/* ── SOV Bar helper ── */
function SovBar({ label, value, isAccent }: { label: string; value: number; isAccent?: boolean }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-text-secondary w-36 truncate font-semibold">{label}</span>
      <div className="flex-1 h-6 bg-surface-overlay rounded-lg overflow-hidden">
        <div
          className={`h-full rounded-lg transition-all duration-500 ${
            isAccent ? 'bg-accent' : 'bg-text-muted/30'
          }`}
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
      <span className={`text-sm font-bold w-12 text-right ${isAccent ? 'text-accent' : 'text-text-secondary'}`}>
        {pct}%
      </span>
    </div>
  );
}

/* ── Competitive intelligence extraction ── */
interface BrandMention {
  name: string;
  count: number;
}

interface DiscoveryMentions {
  brand: BrandMention | null;   // target brand, fuzzy-matched across spelling variants
  competitors: BrandMention[];  // all other brands
}

function normalizeBrand(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function levenshtein(a: string, b: string): number {
  if (a === b) return 0;
  if (!a.length) return b.length;
  if (!b.length) return a.length;
  const dp: number[] = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let prev = dp[0];
    dp[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const tmp = dp[j];
      dp[j] = a[i - 1] === b[j - 1]
        ? prev
        : Math.min(prev, dp[j], dp[j - 1]) + 1;
      prev = tmp;
    }
  }
  return dp[b.length];
}

function isBrandMatch(extracted: string, brandName: string): boolean {
  const a = normalizeBrand(extracted);
  const b = normalizeBrand(brandName);
  if (!a || !b) return false;
  if (a === b) return true;
  // Substring handles "Lounge Lizard Inc" vs "Lounge Lizard"
  if (a.includes(b) || b.includes(a)) return true;
  // Typo tolerance: distance up to ~20% of the longer string, min 1
  const longer = Math.max(a.length, b.length);
  const tolerance = Math.max(1, Math.floor(longer * 0.2));
  return levenshtein(a, b) <= tolerance;
}

function extractCompetitorMentions(
  engines: Record<string, { status: string; responses_by_prompt: Record<string, { text: string; mentioned: boolean }> }>,
  prompts: Array<{ id: number; text: string; category: string }>,
  brandName: string,
): DiscoveryMentions {
  // Only analyze discovery prompts (not reputation)
  const discoveryIds = new Set(
    prompts.filter((p) => p.category === 'discovery').map((p) => String(p.id))
  );

  const competitorCounts: Record<string, number> = {};
  let selfCount = 0;
  let selfDisplayName: string | null = null;

  for (const engine of Object.values(engines)) {
    if (engine.status !== 'ok') continue;
    for (const [promptId, response] of Object.entries(engine.responses_by_prompt)) {
      if (!discoveryIds.has(promptId)) continue;

      // Extract bold text patterns like **Name** or **1. Name**
      const boldMatches = response.text.matchAll(/\*\*(?:\d+\.\s*)?([A-Z][A-Za-z\s&.'-]+?)(?:\s*[-—:]|\*\*)/g);
      for (const match of boldMatches) {
        const name = match[1].trim();
        // Skip short tokens, runaway phrases, and generic intros
        if (
          name.length < 3 ||
          name.split(' ').length > 4 ||
          /^(here|the|key|top|core|what|how|why|additional|notable|other|factors)/i.test(name)
        ) continue;
        // Target brand (fuzzy-matched across spelling variants) — aggregate separately
        if (isBrandMatch(name, brandName)) {
          selfCount++;
          // Prefer the first spelling the engines actually used (e.g. "Lounge Lizard"
          // surfaces even if user typed "Longe Lizard")
          if (!selfDisplayName) selfDisplayName = name;
          continue;
        }
        competitorCounts[name] = (competitorCounts[name] || 0) + 1;
      }
    }
  }

  const competitors = Object.entries(competitorCounts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  const brand = selfCount > 0 && selfDisplayName
    ? { name: selfDisplayName, count: selfCount }
    : null;

  return { brand, competitors };
}
