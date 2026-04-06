import { PILLAR_LABELS } from '../constants/pillarLabels';

/** Safely convert a positive finding to a string (handles string | object). */
function positiveText(p: unknown): string {
  if (typeof p === 'string') return p;
  if (p && typeof p === 'object') {
    const obj = p as Record<string, unknown>;
    return String(obj.text || obj.message || obj.description || JSON.stringify(p));
  }
  return String(p);
}

export function generateMarkdown(report: Record<string, any>): string {
  const lines: string[] = [];

  lines.push(`# WAIO Intelligence Report`);
  lines.push('');
  lines.push(`**URL:** ${report.url}`);
  lines.push(
    `**Date:** ${new Date(report.audit_timestamp).toLocaleString()}`
  );
  lines.push(`**Overall Score:** ${report.overall_score}/100 (${report.overall_label})`);
  lines.push(`**Tier:** ${report.tier || 'free'}`);
  if (report.cms_detection?.platform && report.cms_detection.platform !== 'unknown') {
    lines.push(`**CMS Detected:** ${report.cms_detection.platform} (${Math.round(report.cms_detection.confidence * 100)}% confidence)`);
  }
  lines.push('');

  // Executive Summary (premium)
  if (report.executive_summary) {
    lines.push('## Executive Summary');
    lines.push('');
    lines.push(report.executive_summary);
    lines.push('');
  }

  // Summary
  lines.push('## Summary');
  lines.push('');
  lines.push(`| Metric | Count |`);
  lines.push(`|--------|-------|`);
  lines.push(`| Total Findings | ${report.summary?.total_findings ?? 0} |`);
  lines.push(`| Critical | ${report.summary?.critical ?? 0} |`);
  lines.push(`| High | ${report.summary?.high ?? 0} |`);
  lines.push(`| Medium | ${report.summary?.medium ?? 0} |`);
  lines.push('');

  // Crawl Statistics (premium)
  if (report.crawl_stats) {
    const cs = report.crawl_stats;
    lines.push('## Crawl Statistics');
    lines.push('');
    lines.push(`| Metric | Value |`);
    lines.push(`|--------|-------|`);
    lines.push(`| Pages Crawled | ${cs.pages_crawled ?? 0} |`);
    lines.push(`| Pages Discovered | ${cs.pages_discovered ?? 0} |`);
    lines.push(`| Internal Links | ${cs.internal_links ?? 0} |`);
    lines.push(`| External Links | ${cs.external_links ?? 0} |`);
    lines.push(`| Broken Links | ${cs.broken_links ?? 0} |`);
    lines.push('');
  }

  // Pillar Scores
  if (report.categories) {
    lines.push('## Pillar Scores');
    lines.push('');
    lines.push('| Pillar | Score | Rating |');
    lines.push('|--------|-------|--------|');
    for (const [key, cat] of Object.entries(report.categories)) {
      const catObj = cat as Record<string, any>;
      lines.push(
        `| ${PILLAR_LABELS[key] || key} | ${catObj.score ?? '-'} | ${catObj.label ?? '-'} |`
      );
    }
    lines.push('');
  }

  // Findings by pillar
  if (report.categories) {
    lines.push('## Findings');
    lines.push('');
    for (const [key, cat] of Object.entries(report.categories)) {
      const catObj = cat as Record<string, any>;
      const checks = catObj.checks || {};
      const findings: any[] = [];
      for (const check of Object.values(checks)) {
        const checkObj = check as Record<string, any>;
        if (checkObj.findings) findings.push(...checkObj.findings);
      }
      if (findings.length === 0) continue;

      lines.push(`### ${PILLAR_LABELS[key] || key}`);
      lines.push('');
      for (const f of findings) {
        const icon =
          f.severity === 'critical'
            ? '🔴'
            : f.severity === 'high'
              ? '🟠'
              : '🟡';
        lines.push(`${icon} **[${f.severity.toUpperCase()}]** ${f.description}`);
        lines.push('');
        lines.push(`> **Recommendation:** ${f.recommendation}`);
        if (f.reference) lines.push(`> **Reference:** ${f.reference}`);
        lines.push('');
      }
    }
  }

  // Positive findings
  const positives = report.positive_findings || [];
  if (positives.length > 0) {
    lines.push('## Positive Findings');
    lines.push('');
    for (const p of positives) {
      lines.push(`- ✅ ${positiveText(p)}`);
    }
    lines.push('');
  }

  // Webflow Fix Instructions (premium)
  if (report.webflow_fixes && Object.keys(report.webflow_fixes).length > 0) {
    lines.push('## Webflow Fix Instructions');
    lines.push('');
    for (const [, fix] of Object.entries(report.webflow_fixes)) {
      const f = fix as Record<string, any>;
      lines.push(`### ${f.title || f.finding_pattern}`);
      lines.push(`**Difficulty:** ${f.difficulty || 'N/A'} | **Time:** ${f.estimated_time || 'N/A'}`);
      lines.push('');
      lines.push(f.steps_markdown || '');
      lines.push('');
    }
  }

  // Competitor Benchmarks (premium)
  if (report.competitive_data?.rankings?.length) {
    lines.push('## Competitor Benchmark');
    lines.push('');
    lines.push('| Rank | URL | Score |');
    lines.push('|------|-----|-------|');
    for (const [idx, r] of report.competitive_data.rankings.entries()) {
      const marker = r.url === report.url ? ' (You)' : '';
      lines.push(`| ${idx + 1} | ${r.url}${marker} | ${r.overall_score} |`);
    }
    lines.push('');
  }

  // NLP Analysis (premium)
  if (report.nlp_analysis) {
    lines.push('## Content Intelligence (NLP)');
    lines.push('');
    lines.push(`**Detected Industry:** ${report.nlp_analysis.detected_industry}`);
    lines.push(`**Confidence:** ${Math.round((report.nlp_analysis.industry_confidence ?? 0) * 100)}%`);
    lines.push('');
  }

  // Topic Clusters (from DataForSEO link analysis)
  const clusters = report.link_analysis?.clusters || report.topic_clusters;
  if (clusters?.length) {
    lines.push('## Topic Clusters');
    lines.push('');
    lines.push('| Cluster | Pages | Coherence |');
    lines.push('|---------|-------|-----------|');
    for (const cluster of clusters) {
      const name = cluster.prefix || cluster.name || 'Unknown';
      const count = cluster.page_count ?? 0;
      const coherence = cluster.coherence_score != null
        ? `${Math.round(cluster.coherence_score * 100)}%`
        : 'N/A';
      lines.push(`| ${name} | ${count} | ${coherence} |`);
    }
    lines.push('');
  }

  lines.push('---');
  lines.push('*Generated by WAIO Intelligence — Veza Digital*');
  lines.push('');

  return lines.join('\n');
}

export function downloadMarkdown(report: Record<string, any>): void {
  const md = generateMarkdown(report);
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const domain = report.url
    ?.replace(/https?:\/\//, '')
    .replace(/\//g, '_')
    .replace(/_$/, '');
  const date = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = `WAIO-Intelligence-Report-${domain}-${date}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
