/**
 * Single source of truth for all 10 pillar display names.
 * Backend keys → client-facing labels (outcome-focused).
 *
 * Every component that shows a pillar name imports from here.
 * Do NOT hardcode pillar labels elsewhere.
 */

export const PILLAR_LABELS: Record<string, string> = {
  semantic_html: 'Search Engine Clarity',
  structured_data: 'Rich Search Presence',
  aeo_content: 'AI Answer Readiness',
  css_quality: 'Visual Consistency',
  js_bloat: 'Page Speed & Load Time',
  accessibility: 'Inclusive Reach',
  rag_readiness: 'AI Retrieval Readiness',
  agentic_protocols: 'AI Agent Compatibility',
  data_integrity: 'Tracking & Analytics Accuracy',
  internal_linking: 'Content Architecture',
};

/** Short names for compact UI (radar chart axes, mobile labels) */
export const PILLAR_SHORT_LABELS: Record<string, string> = {
  semantic_html: 'Search Clarity',
  structured_data: 'Rich Search',
  aeo_content: 'AI Answers',
  css_quality: 'Visual',
  js_bloat: 'Speed',
  accessibility: 'Inclusive',
  rag_readiness: 'AI Retrieval',
  agentic_protocols: 'AI Agents',
  data_integrity: 'Tracking',
  internal_linking: 'Architecture',
};
