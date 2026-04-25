/**
 * Workstream D5 — Scan Stats Strip
 *
 * One-line summary rendered below the KPI cards on the overview page.
 * Format:
 *   📊 Scanned {pages_crawled} of {pages_discovered} pages · {finding_summary}
 *      [· {bot_challenge_summary} when detected]
 *
 * - When bot_challenge is detected, the finding count reads
 *   "0 findings (scan blocked)" and the strip uses amber styling.
 * - When clean, the strip is neutral text-text-muted.
 * - When crawl_stats is absent (free-tier audit, no DataForSEO crawl), we
 *   default pages to 1/1 — single-page audit.
 */

interface BotChallenge {
  detected: boolean;
  vendor: 'cloudflare' | 'akamai' | 'datadome' | 'perimeterx' | 'unknown' | null;
}

interface ScanStatsStripProps {
  report: Record<string, any> | null;
}

const VENDOR_DISPLAY: Record<string, string> = {
  cloudflare: 'Cloudflare',
  akamai: 'Akamai',
  datadome: 'DataDome',
  perimeterx: 'PerimeterX',
  unknown: 'an unidentified bot protection service',
};

export function ScanStatsStrip({ report }: ScanStatsStripProps) {
  if (!report) return null;

  const botChallenge = report.bot_challenge as BotChallenge | null | undefined;
  const isBotChallenged = !!botChallenge?.detected;

  const crawlStats = report.crawl_stats as
    | { pages_crawled?: number; pages_discovered?: number }
    | null
    | undefined;
  const pagesCrawled = crawlStats?.pages_crawled ?? 1;
  const pagesDiscovered = crawlStats?.pages_discovered ?? 1;

  // Total findings: prefer report.summary.total_findings (computed on backend),
  // fall back to summing across categories if absent.
  const totalFindings =
    (report.summary?.total_findings as number | undefined) ??
    Object.values((report.categories ?? {}) as Record<string, any>).reduce(
      (sum, cat: any) => sum + (cat?.findings?.length ?? 0),
      0,
    );

  const findingSummary = isBotChallenged
    ? '0 findings (scan blocked)'
    : `${totalFindings} ${totalFindings === 1 ? 'finding' : 'findings'}`;

  const vendorKey = botChallenge?.vendor ?? 'unknown';
  const vendorDisplay =
    VENDOR_DISPLAY[vendorKey] ?? 'an unidentified bot protection service';
  const botSegment = isBotChallenged
    ? `Bot challenge detected (${vendorDisplay})`
    : null;

  const containerClasses = isBotChallenged
    ? 'flex items-center flex-wrap gap-x-2 gap-y-1 text-xs px-3 py-2 rounded-lg border border-amber-500/30 text-amber-400'
    : 'flex items-center flex-wrap gap-x-2 gap-y-1 text-xs text-text-muted';

  const containerStyle = isBotChallenged
    ? { backgroundColor: '#F59E0B15' }
    : undefined;

  return (
    <div className={containerClasses} style={containerStyle}>
      <span aria-hidden="true">📊</span>
      <span>
        Scanned <strong className={isBotChallenged ? 'text-amber-400' : 'text-text-secondary'}>{pagesCrawled}</strong> of{' '}
        <strong className={isBotChallenged ? 'text-amber-400' : 'text-text-secondary'}>{pagesDiscovered}</strong>{' '}
        {pagesDiscovered === 1 ? 'page' : 'pages'}
      </span>
      <span aria-hidden="true">·</span>
      <span>{findingSummary}</span>
      {botSegment && (
        <>
          <span aria-hidden="true">·</span>
          <span className="font-semibold">{botSegment}</span>
        </>
      )}
    </div>
  );
}
