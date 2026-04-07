import { useMemo } from 'react';
import { useParams, Link } from 'react-router';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Brain,
  Sparkles,
  Info,
  ExternalLink,
  Target,
  TrendingUp,
  MessageSquare,
  Lightbulb,
  ChevronRight,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from 'recharts';
import { useAuditStore } from '../stores/auditStore';

/* ─── Helpers ─── */

const ENTITY_TYPE_COLORS: Record<string, { bg: string; text: string; fill: string }> = {
  ORGANIZATION: { bg: 'bg-blue-500/15', text: 'text-blue-400', fill: '#60A5FA' },
  PERSON: { bg: 'bg-purple-500/15', text: 'text-purple-400', fill: '#A78BFA' },
  CONSUMER_GOOD: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', fill: '#34D399' },
  WORK_OF_ART: { bg: 'bg-orange-500/15', text: 'text-orange-400', fill: '#FB923C' },
  EVENT: { bg: 'bg-pink-500/15', text: 'text-pink-400', fill: '#F472B6' },
  LOCATION: { bg: 'bg-teal-500/15', text: 'text-teal-400', fill: '#2DD4BF' },
  OTHER: { bg: 'bg-gray-500/15', text: 'text-gray-400', fill: '#94A3B8' },
  PHONE_NUMBER: { bg: 'bg-gray-500/15', text: 'text-gray-400', fill: '#94A3B8' },
  ADDRESS: { bg: 'bg-teal-500/15', text: 'text-teal-400', fill: '#2DD4BF' },
  NUMBER: { bg: 'bg-gray-500/15', text: 'text-gray-400', fill: '#94A3B8' },
  PRICE: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', fill: '#34D399' },
  DATE: { bg: 'bg-gray-500/15', text: 'text-gray-400', fill: '#94A3B8' },
  UNKNOWN: { bg: 'bg-gray-500/15', text: 'text-gray-400', fill: '#94A3B8' },
};

const getEntityColor = (type: string) =>
  ENTITY_TYPE_COLORS[type] ?? ENTITY_TYPE_COLORS.OTHER;

const PIE_COLORS = [
  '#60A5FA', '#A78BFA', '#34D399', '#FB923C', '#F472B6',
  '#2DD4BF', '#94A3B8', '#FBBF24',
];

interface NLPEntity {
  name: string;
  type: string;
  salience: number;
  wikipedia_url?: string | null;
  mentions_count?: number;
}

interface NLPCategory {
  category: string;
  confidence: number;
}

interface NLPSentiment {
  score: number;
  magnitude: number;
  tone: string;
}

interface NLPInsights {
  primary_topic?: string;
  topic_confidence?: number;
  entity_focus?: string;
  content_tone?: string;
  seo_alignment?: string;
  entity_diversity_score?: number;
  top_keyword_entities?: string[];
}

interface NLPAnalysis {
  detected_industry?: string;
  industry_confidence?: number;
  all_categories?: NLPCategory[];
  entities?: NLPEntity[];
  primary_entity?: string;
  primary_entity_salience?: number;
  entity_type_distribution?: Record<string, number>;
  entity_focus_aligned?: boolean;
  sentiment?: NLPSentiment;
  content_stats?: {
    word_count?: number;
    language?: string;
    extracted_via?: string;
  };
  insights?: NLPInsights;
}

/* ─── Sentiment gauge component ─── */
function SentimentGauge({ score, magnitude, tone }: NLPSentiment) {
  // Map score (-1 to 1) to percentage (0 to 100)
  const pct = ((score + 1) / 2) * 100;
  const gaugeColor =
    score <= -0.5 ? '#EF4444' :
    score <= -0.1 ? '#F97316' :
    score <= 0.1 ? '#94A3B8' :
    score <= 0.5 ? '#84CC16' :
    '#22C55E';

  let magDesc: string;
  if (magnitude < 1.0) {
    magDesc = 'Your content is relatively objective and fact-based.';
  } else if (magnitude < 3.0) {
    magDesc = 'Your content has moderate emotional language — good for engagement.';
  } else {
    magDesc = 'Your content is highly emotive — strong for marketing, but verify it matches your brand voice.';
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-xs text-text-muted font-semibold">
        <span>Negative</span>
        <span>Neutral</span>
        <span>Positive</span>
      </div>
      <div className="relative h-3 bg-surface-overlay rounded-full overflow-hidden">
        {/* Gradient track */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: 'linear-gradient(to right, #EF4444, #F97316, #94A3B8, #84CC16, #22C55E)',
            opacity: 0.25,
          }}
        />
        {/* Indicator */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 border-surface shadow-lg transition-all duration-700"
          style={{
            left: `calc(${pct}% - 8px)`,
            backgroundColor: gaugeColor,
          }}
        />
      </div>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-bold font-heading" style={{ color: gaugeColor }}>
            {tone}
          </div>
          <div className="text-xs text-text-muted mt-0.5">
            Score: {score.toFixed(2)} / Magnitude: {magnitude.toFixed(2)}
          </div>
        </div>
      </div>
      <p className="text-xs text-text-secondary leading-relaxed">{magDesc}</p>
    </div>
  );
}

/* ─── Custom bar chart tooltip ─── */
function EntityBarTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { name: string; type: string; salience: number; mentions: number } }> }) {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-surface-raised border border-border rounded-lg px-3 py-2 shadow-card text-xs">
      <div className="font-semibold text-text">{d.name}</div>
      <div className="text-text-muted">Type: {d.type}</div>
      <div className="text-text-muted">Salience: {(d.salience * 100).toFixed(1)}%</div>
      {d.mentions > 0 && <div className="text-text-muted">Mentions: {d.mentions}</div>}
    </div>
  );
}

/* ─── Main page component ─── */
export default function DashboardContentIntelligencePage() {
  const { auditId } = useParams();
  const report = useAuditStore((s) => s.report);
  const nlp = (report?.nlp_analysis ?? null) as NLPAnalysis | null;

  // Entity bar chart data (top 10 by salience)
  const entityBarData = useMemo(() => {
    if (!nlp?.entities) return [];
    return nlp.entities.slice(0, 10).map((e) => ({
      name: e.name.length > 20 ? e.name.slice(0, 18) + '...' : e.name,
      fullName: e.name,
      salience: e.salience,
      type: e.type,
      mentions: e.mentions_count ?? 0,
      fill: getEntityColor(e.type).fill,
    }));
  }, [nlp]);

  // Entity type pie chart data
  const typePieData = useMemo(() => {
    if (!nlp?.entity_type_distribution) return [];
    return Object.entries(nlp.entity_type_distribution)
      .map(([type, count]) => ({ name: type.replace(/_/g, ' '), value: count }))
      .sort((a, b) => b.value - a.value);
  }, [nlp]);

  // Category breadcrumb parts
  const categoryParts = useMemo(() => {
    if (!nlp?.detected_industry) return [];
    return nlp.detected_industry.split('/').filter(Boolean);
  }, [nlp]);

  // SEO recommendations based on NLP data
  const recommendations = useMemo(() => {
    if (!nlp) return [];
    const recs: { title: string; description: string; type: 'positive' | 'warning' | 'info' }[] = [];

    const conf = nlp.industry_confidence ?? 0;
    if (conf >= 0.7) {
      recs.push({
        title: 'Strong Topical Signal',
        description: `Google classifies your content as "${nlp.insights?.primary_topic}" with ${Math.round(conf * 100)}% confidence. This is a strong signal for topical authority.`,
        type: 'positive',
      });
    } else if (conf > 0 && conf < 0.6) {
      recs.push({
        title: 'Weak Topical Signal',
        description: `Google is only ${Math.round(conf * 100)}% confident about your site's topic. Strengthen topical signals by increasing relevant entity mentions and using clearer category-defining language.`,
        type: 'warning',
      });
    }

    if (nlp.entity_focus_aligned === true) {
      recs.push({
        title: 'Entity-Title Alignment',
        description: `Your primary entity "${nlp.primary_entity}" aligns with your page title/H1. This is excellent for search intent matching.`,
        type: 'positive',
      });
    } else if (nlp.entity_focus_aligned === false && nlp.primary_entity) {
      recs.push({
        title: 'Entity-Title Mismatch',
        description: `Google sees "${nlp.primary_entity}" as your primary topic (salience ${((nlp.primary_entity_salience ?? 0) * 100).toFixed(0)}%), but this doesn't match your H1/title. Consider aligning your heading with your actual content focus.`,
        type: 'warning',
      });
    }

    const diversity = nlp.insights?.entity_diversity_score ?? 0;
    if (diversity < 0.3 && nlp.entities && nlp.entities.length > 0) {
      recs.push({
        title: 'Low Entity Diversity',
        description: `Your content is heavily focused on one entity type. Consider broadening topic coverage to capture more search intent and improve topical depth.`,
        type: 'info',
      });
    }

    const hasPerson = nlp.entity_type_distribution?.PERSON ?? 0;
    if (hasPerson === 0 && nlp.entities && nlp.entities.length > 3) {
      recs.push({
        title: 'No Author/Expert Entities',
        description: 'Adding author profiles and expert mentions can improve E-E-A-T signals, which are increasingly important for search rankings and AI citations.',
        type: 'info',
      });
    }

    const sentScore = nlp.sentiment?.score ?? 0;
    if (sentScore < -0.3) {
      recs.push({
        title: 'Negative Content Tone',
        description: 'Your content has a noticeably negative tone. Service and product pages typically perform better with positive, solution-oriented language.',
        type: 'warning',
      });
    }

    if (recs.length === 0) {
      recs.push({
        title: 'Content Intelligence Active',
        description: 'Your content is being analyzed. Run a new premium audit to generate fresh NLP insights.',
        type: 'info',
      });
    }

    return recs;
  }, [nlp]);

  // No NLP data at all
  if (!nlp) {
    return (
      <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
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
              <Brain size={20} className="text-accent" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-text font-heading">Content Intelligence</h1>
              <p className="text-sm text-text-secondary mt-0.5">
                How Google's AI interprets your website's content.
              </p>
            </div>
          </div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-raised border border-border rounded-xl p-10 text-center"
        >
          <div className="w-12 h-12 mx-auto mb-4 bg-surface-overlay rounded-xl flex items-center justify-center">
            <Info size={20} className="text-text-muted" />
          </div>
          <p className="text-sm font-semibold text-text mb-1">
            Content Intelligence Not Available
          </p>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Content Intelligence requires a Premium audit with Google NLP analysis enabled.
            Run a Comprehensive Audit to generate AI-powered content insights.
          </p>
        </motion.div>
      </div>
    );
  }

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
            <Brain size={20} className="text-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text font-heading">Content Intelligence</h1>
            <p className="text-sm text-text-secondary mt-0.5">
              How Google's AI interprets your website's content
            </p>
          </div>
        </div>
      </motion.div>

      {/* Section A: Industry & Topic Classification */}
      {nlp.detected_industry && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="bg-surface-raised border border-border rounded-xl p-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <Target size={16} className="text-accent" />
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
              Industry Classification
            </h2>
          </div>

          {/* Taxonomy breadcrumb */}
          <div className="flex items-center gap-1.5 flex-wrap mb-4">
            {categoryParts.map((part, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {i > 0 && <ChevronRight size={12} className="text-text-muted" />}
                <span
                  className={`text-sm font-medium ${
                    i === categoryParts.length - 1 ? 'text-accent font-bold' : 'text-text-secondary'
                  }`}
                >
                  {part}
                </span>
              </span>
            ))}
          </div>

          {/* Confidence indicator */}
          <div className="flex items-center gap-4 mb-5">
            <div className="relative w-14 h-14">
              <svg viewBox="0 0 36 36" className="w-14 h-14 -rotate-90">
                <circle
                  cx="18" cy="18" r="15.5"
                  fill="none" stroke="currentColor"
                  className="text-surface-overlay" strokeWidth="3"
                />
                <circle
                  cx="18" cy="18" r="15.5"
                  fill="none" stroke="#2820FF" strokeWidth="3"
                  strokeDasharray={`${(nlp.industry_confidence ?? 0) * 97.4} 97.4`}
                  strokeLinecap="round"
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-accent">
                {Math.round((nlp.industry_confidence ?? 0) * 100)}%
              </span>
            </div>
            <div>
              <div className="text-sm font-semibold text-text">Classification Confidence</div>
              <div className="text-xs text-text-muted mt-0.5">
                {(nlp.industry_confidence ?? 0) >= 0.7
                  ? 'Google is confident about your content topic.'
                  : 'Google has moderate confidence — consider strengthening topical signals.'}
              </div>
            </div>
          </div>

          {/* Secondary categories */}
          {nlp.all_categories && nlp.all_categories.length > 1 && (
            <div>
              <div className="text-xs font-semibold text-text-muted mb-2">Other Detected Topics</div>
              <div className="flex flex-wrap gap-2">
                {nlp.all_categories.slice(1, 5).map((cat, i) => {
                  const shortName = cat.category.split('/').filter(Boolean).pop() ?? cat.category;
                  return (
                    <span
                      key={i}
                      className="text-xs text-text-secondary bg-surface-overlay px-2.5 py-1 rounded-lg"
                    >
                      {shortName}{' '}
                      <span className="text-text-muted">{Math.round(cat.confidence * 100)}%</span>
                    </span>
                  );
                })}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Section B: Entity Analysis */}
      {nlp.entities && nlp.entities.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-4"
        >
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-accent" />
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
              Entity Analysis
            </h2>
            <span className="text-[10px] text-text-muted bg-surface-overlay px-2 py-0.5 rounded-full">
              {nlp.entities.length} entities detected
            </span>
          </div>

          {/* Entity overview cards — top 10 */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
            {nlp.entities.slice(0, 10).map((entity, i) => {
              const colors = getEntityColor(entity.type);
              return (
                <div
                  key={i}
                  className="bg-surface-raised border border-border rounded-xl p-3.5 group hover:border-accent/20 transition-all"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}
                    >
                      {entity.type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="text-sm font-semibold text-text truncate" title={entity.name}>
                    {entity.name}
                  </div>
                  <div className="mt-2">
                    <div className="flex items-center justify-between text-[10px] text-text-muted mb-1">
                      <span>Salience</span>
                      <span className="font-semibold">{(entity.salience * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-1.5 bg-surface-overlay rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.max(3, entity.salience * 100)}%`,
                          backgroundColor: colors.fill,
                        }}
                      />
                    </div>
                  </div>
                  {entity.wikipedia_url && (
                    <a
                      href={entity.wikipedia_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 text-[10px] text-accent hover:text-accent-hover inline-flex items-center gap-0.5"
                    >
                      Wikipedia <ExternalLink size={8} />
                    </a>
                  )}
                </div>
              );
            })}
          </div>

          {/* Charts row: Entity Salience Bar Chart + Entity Type Pie */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Salience bar chart */}
            {entityBarData.length > 0 && (
              <div className="bg-surface-raised border border-border rounded-xl p-5">
                <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-4">
                  Top Entities by Salience
                </h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={entityBarData}
                    layout="vertical"
                    margin={{ top: 0, right: 12, bottom: 0, left: 0 }}
                  >
                    <XAxis
                      type="number"
                      domain={[0, 'auto']}
                      tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                      tick={{ fontSize: 10, fill: '#64748B' }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={100}
                      tick={{ fontSize: 11, fill: '#94A3B8' }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip content={<EntityBarTooltip />} cursor={{ fill: '#1E293B40' }} />
                    <Bar dataKey="salience" radius={[0, 4, 4, 0]} barSize={16}>
                      {entityBarData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Entity type distribution pie */}
            {typePieData.length > 0 && (
              <div className="bg-surface-raised border border-border rounded-xl p-5">
                <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-4">
                  Entity Type Distribution
                </h3>
                <div className="flex items-center gap-6">
                  <ResponsiveContainer width="50%" height={220}>
                    <PieChart>
                      <Pie
                        data={typePieData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        innerRadius={45}
                        paddingAngle={2}
                        stroke="none"
                      >
                        {typePieData.map((_entry, i) => (
                          <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(value: number | string | undefined, name: string | number | undefined) => [`${Number(value || 0)} entities`, String(name || '')]}
                        contentStyle={{
                          backgroundColor: '#151B28',
                          border: '1px solid #1E293B',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                        itemStyle={{ color: '#F1F5F9' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex-1 space-y-1.5">
                    {typePieData.map((item, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                        />
                        <span className="text-xs text-text-secondary flex-1 truncate">
                          {item.name}
                        </span>
                        <span className="text-xs font-semibold text-text">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Full entity table */}
          {nlp.entities.length > 10 && (
            <div className="bg-surface-raised border border-border rounded-xl p-5">
              <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-3">
                All Entities ({nlp.entities.length})
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border text-text-muted">
                      <th className="text-left py-2 pr-4 font-semibold">Entity</th>
                      <th className="text-left py-2 pr-4 font-semibold">Type</th>
                      <th className="text-right py-2 pr-4 font-semibold">Salience</th>
                      <th className="text-right py-2 pr-4 font-semibold">Mentions</th>
                      <th className="text-left py-2 font-semibold">Wikipedia</th>
                    </tr>
                  </thead>
                  <tbody>
                    {nlp.entities.map((e, i) => {
                      const colors = getEntityColor(e.type);
                      return (
                        <tr key={i} className="border-b border-border/50 hover:bg-surface-overlay/50">
                          <td className="py-2 pr-4 text-text font-medium">{e.name}</td>
                          <td className="py-2 pr-4">
                            <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                              {e.type.replace(/_/g, ' ')}
                            </span>
                          </td>
                          <td className="py-2 pr-4 text-right text-text-secondary font-mono">
                            {(e.salience * 100).toFixed(1)}%
                          </td>
                          <td className="py-2 pr-4 text-right text-text-secondary">
                            {e.mentions_count ?? '—'}
                          </td>
                          <td className="py-2">
                            {e.wikipedia_url ? (
                              <a
                                href={e.wikipedia_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-accent hover:text-accent-hover inline-flex items-center gap-0.5"
                              >
                                Link <ExternalLink size={9} />
                              </a>
                            ) : (
                              <span className="text-text-muted">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Section C: Content Tone & Sentiment */}
      {nlp.sentiment && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-surface-raised border border-border rounded-xl p-6"
        >
          <div className="flex items-center gap-2 mb-5">
            <MessageSquare size={16} className="text-accent" />
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
              Content Tone & Sentiment
            </h2>
          </div>
          <SentimentGauge
            score={nlp.sentiment.score}
            magnitude={nlp.sentiment.magnitude}
            tone={nlp.sentiment.tone}
          />
        </motion.div>
      )}

      {/* Section D: SEO Intelligence Panel */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="space-y-4"
      >
        <div className="flex items-center gap-2">
          <Lightbulb size={16} className="text-accent" />
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-widest">
            SEO Intelligence
          </h2>
        </div>

        {/* What Google Sees summary */}
        <div className="bg-surface-raised border border-border rounded-xl p-6">
          <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest mb-3 flex items-center gap-2">
            <TrendingUp size={13} />
            What Google Sees
          </h3>
          <div className="space-y-2 text-sm text-text-secondary leading-relaxed">
            {nlp.detected_industry && (
              <p>
                Google classifies your site as{' '}
                <strong className="text-text">{nlp.insights?.primary_topic ?? nlp.detected_industry}</strong>{' '}
                with{' '}
                <strong className="text-text">{Math.round((nlp.industry_confidence ?? 0) * 100)}%</strong>{' '}
                confidence.
              </p>
            )}
            {nlp.primary_entity && (
              <p>
                Your content is primarily about{' '}
                <strong className="text-text">{nlp.primary_entity}</strong>
                {nlp.insights?.top_keyword_entities && nlp.insights.top_keyword_entities.length > 1 && (
                  <>
                    , followed by{' '}
                    {nlp.insights.top_keyword_entities.slice(1, 4).map((e, i, arr) => (
                      <span key={i}>
                        <strong className="text-text">{e}</strong>
                        {i < arr.length - 1 ? ', ' : ''}
                      </span>
                    ))}
                  </>
                )}
                .
              </p>
            )}
            {nlp.sentiment && (
              <p>
                The overall tone is{' '}
                <strong className="text-text">{nlp.sentiment.tone.toLowerCase()}</strong>
                {nlp.detected_industry && (
                  <>
                    , which is{' '}
                    {nlp.sentiment.score >= -0.1 && nlp.sentiment.score <= 0.5
                      ? 'appropriate'
                      : 'notable'}{' '}
                    for the {nlp.insights?.primary_topic?.toLowerCase() ?? 'detected'} space.
                  </>
                )}
              </p>
            )}
            {nlp.insights?.seo_alignment && (
              <p>
                SEO alignment:{' '}
                <span
                  className={`font-semibold ${
                    nlp.insights.seo_alignment === 'strong'
                      ? 'text-success'
                      : nlp.insights.seo_alignment === 'moderate'
                        ? 'text-warning'
                        : 'text-severity-high'
                  }`}
                >
                  {nlp.insights.seo_alignment.charAt(0).toUpperCase() + nlp.insights.seo_alignment.slice(1)}
                </span>
              </p>
            )}
          </div>
        </div>

        {/* Recommendations */}
        <div className="space-y-2.5">
          {recommendations.map((rec, i) => (
            <div
              key={i}
              className={`bg-surface-raised border rounded-xl p-4 border-l-4 ${
                rec.type === 'positive'
                  ? 'border-l-success border-border'
                  : rec.type === 'warning'
                    ? 'border-l-severity-high border-border'
                    : 'border-l-accent border-border'
              }`}
            >
              <div className="flex items-center gap-2 mb-1.5">
                {rec.type === 'positive' ? (
                  <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-success/15 text-success">
                    Positive
                  </span>
                ) : rec.type === 'warning' ? (
                  <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-severity-high/15 text-severity-high">
                    Opportunity
                  </span>
                ) : (
                  <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-accent/15 text-accent">
                    Insight
                  </span>
                )}
                <span className="text-sm font-semibold text-text">{rec.title}</span>
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">{rec.description}</p>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Powered by badge */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="text-center pt-2 pb-6"
      >
        <span className="text-[10px] text-text-muted font-medium">
          Powered by Google Cloud Natural Language API
        </span>
      </motion.div>
    </div>
  );
}
