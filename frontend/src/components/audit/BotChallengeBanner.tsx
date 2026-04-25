import { motion } from 'framer-motion';
import { ShieldAlert } from 'lucide-react';

/**
 * Workstream D5 — Bot Challenge Banner
 *
 * Surfaces server-side bot-challenge detection (D1) on the dashboard.
 * Two states based on whether the DataForSEO full-site crawl produced graph
 * data:
 *   - State A (partial success): homepage was bot-challenged but DFS crawl
 *     produced a link graph — link intelligence is still available
 *   - State B (full failure):    homepage AND full-site crawl were both
 *     blocked — no findings or intelligence layers are available
 *
 * Discriminator: report.link_analysis?.graph?.nodes?.length (the actual key
 * shape on the backend is `link_analysis.graph.nodes`, not `graph_data.nodes`
 * as the plan spec drafted).
 */

interface BotChallenge {
  detected: boolean;
  vendor: 'cloudflare' | 'akamai' | 'datadome' | 'perimeterx' | 'unknown' | null;
  signals?: string[];
  reason?: string | null;
  confidence?: number;
}

interface BotChallengeBannerProps {
  report: Record<string, any> | null;
}

const VENDOR_DISPLAY: Record<string, string> = {
  cloudflare: 'Cloudflare',
  akamai: 'Akamai',
  datadome: 'DataDome',
  perimeterx: 'PerimeterX',
  unknown: 'an unidentified bot protection service',
};

export function BotChallengeBanner({ report }: BotChallengeBannerProps) {
  const botChallenge = report?.bot_challenge as BotChallenge | null | undefined;
  if (!botChallenge?.detected) return null;

  const vendorKey = botChallenge.vendor ?? 'unknown';
  const vendorDisplay =
    VENDOR_DISPLAY[vendorKey] ?? 'an unidentified bot protection service';

  // State A vs B discriminator: did the full-site crawl produce a link graph?
  const hasGraphNodes = !!report?.link_analysis?.graph?.nodes?.length;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-3 p-4 rounded-lg border border-amber-500/30"
      style={{ backgroundColor: '#F59E0B15' }}
      role="alert"
    >
      <ShieldAlert size={20} className="text-amber-500 flex-shrink-0 mt-0.5" />
      <div className="flex-1 text-sm space-y-2 leading-relaxed">
        <p>
          <span className="font-semibold text-amber-400">
            This site is protected by {vendorDisplay} bot protection.
          </span>
        </p>
        {hasGraphNodes ? (
          <>
            <p className="text-text-secondary">
              The homepage audit could not access the real page — the site
              returned a verification challenge instead of content, so the
              10-pillar analysis, AI Visibility, and on-page intelligence did
              not run.{' '}
              <strong className="text-text">
                Full-site crawl completed successfully — link intelligence
                (TIPR), topic clustering, and the link graph are still
                available on this dashboard.
              </strong>
            </p>
            <p className="text-text-secondary">
              <strong className="text-text-secondary">What you can do:</strong>{' '}
              Re-run the homepage audit on a non-challenged entry point (a
              subdomain, a specific blog post URL, or a gated page where the
              bot check is only applied on <code className="text-xs px-1 py-0.5 bg-surface-overlay rounded">/</code>).
              If the challenge is site-wide, contact Veza Digital support —
              we&rsquo;re tracking workarounds for protected sites.
            </p>
          </>
        ) : (
          <>
            <p className="text-text-secondary">
              The audit could not access the site — both the homepage fetch
              and the full-site crawl were blocked by the verification
              challenge. No findings, scores, or intelligence layers are
              available for this scan.
            </p>
            <p className="text-text-secondary">
              <strong className="text-text-secondary">What you can do:</strong>{' '}
              Re-run the audit on a non-challenged entry point (a subdomain,
              a specific blog post URL, or a gated page where the bot check
              is only applied on <code className="text-xs px-1 py-0.5 bg-surface-overlay rounded">/</code>).
              If the challenge is site-wide, contact Veza Digital support —
              we&rsquo;re tracking workarounds for protected sites.
            </p>
          </>
        )}
      </div>
    </motion.div>
  );
}
