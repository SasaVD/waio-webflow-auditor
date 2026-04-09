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
    const nlp = report.nlp_analysis;
    lines.push('## Content Intelligence (NLP)');
    lines.push('');
    if (nlp.detected_industry) {
      lines.push(`**Detected Industry:** ${nlp.detected_industry}`);
      lines.push(`**Confidence:** ${Math.round((nlp.industry_confidence ?? 0) * 100)}%`);
      lines.push('');
    }

    // Sentiment
    if (nlp.sentiment) {
      lines.push(`**Content Tone:** ${nlp.sentiment.tone}`);
      lines.push(`**Sentiment Score:** ${nlp.sentiment.score} (magnitude: ${nlp.sentiment.magnitude})`);
      lines.push('');
    }

    // Top entities table
    if (nlp.entities?.length) {
      lines.push('### Top Entities');
      lines.push('');
      lines.push('| Entity | Type | Salience | Mentions | Wikipedia |');
      lines.push('|--------|------|----------|----------|-----------|');
      for (const ent of nlp.entities.slice(0, 15)) {
        const sal = `${(ent.salience * 100).toFixed(1)}%`;
        const wiki = ent.wikipedia_url ? `[Link](${ent.wikipedia_url})` : '—';
        lines.push(`| ${ent.name} | ${ent.type} | ${sal} | ${ent.mentions_count ?? '—'} | ${wiki} |`);
      }
      lines.push('');
    }

    // SEO insights
    if (nlp.insights) {
      lines.push('### SEO Insights');
      lines.push('');
      if (nlp.insights.seo_alignment) {
        lines.push(`- **SEO Alignment:** ${nlp.insights.seo_alignment}`);
      }
      if (nlp.insights.entity_diversity_score != null) {
        lines.push(`- **Entity Diversity:** ${Math.round(nlp.insights.entity_diversity_score * 100)}%`);
      }
      if (nlp.insights.top_keyword_entities?.length) {
        lines.push(`- **Key Entities:** ${nlp.insights.top_keyword_entities.join(', ')}`);
      }
      if (nlp.entity_focus_aligned === true) {
        lines.push(`- **Entity-Title Alignment:** ✅ Primary entity matches page title/H1`);
      } else if (nlp.entity_focus_aligned === false) {
        lines.push(`- **Entity-Title Alignment:** ⚠️ Primary entity "${nlp.primary_entity}" does not match H1/title`);
      }
      lines.push('');
    }
  }

  // Topic Clusters — semantic (preferred) or directory (fallback)
  const semantic = report.semantic_clusters;
  if (semantic?.clusters?.length) {
    lines.push('## Topic Clusters (Semantic)');
    lines.push('');
    lines.push(`*Detection method: ${semantic.detection_method} · Quality: ${semantic.quality} (silhouette ${semantic.silhouette_score}) · Entity data: ${semantic.entity_data_coverage} pages*`);
    lines.push('');
    lines.push('| Cluster | Pages | Link Health | Pillar | Content Gaps |');
    lines.push('|---------|-------|:-----------:|--------|:------------:|');
    for (const c of semantic.clusters) {
      const hp = c.link_health?.health_pct != null ? `${c.link_health.health_pct}%` : 'N/A';
      const pillar = c.pillar?.url ? c.pillar.url : '—';
      lines.push(`| ${c.label} | ${c.size} | ${hp} | ${pillar} | ${c.content_gaps?.length ?? 0} |`);
    }
    lines.push('');
    // Top recommendations
    if (semantic.link_recommendations?.length) {
      lines.push('### Cluster Link Recommendations');
      lines.push('');
      for (const rec of semantic.link_recommendations.slice(0, 20)) {
        const tag = rec.type === 'missing_pillar_link' ? '→ Pillar' : 'Pillar →';
        lines.push(`- **[${tag}]** ${rec.reason}`);
      }
      if (semantic.link_recommendations.length > 20) {
        lines.push(`- *...and ${semantic.link_recommendations.length - 20} more recommendations*`);
      }
      lines.push('');
    }
  } else {
    const clusters = report.link_analysis?.clusters || report.topic_clusters;
    if (clusters?.length) {
      lines.push('## Topic Clusters (Directory)');
      lines.push('');
      lines.push('| Directory | Pages | Coherence |');
      lines.push('|-----------|-------|-----------|');
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
  }

  // Link Intelligence (TIPR Analysis)
  if (report.tipr_analysis) {
    const tipr = report.tipr_analysis;
    const s = tipr.summary;
    lines.push('## Link Intelligence (TIPR Analysis)');
    lines.push('');
    lines.push(`| Metric | Value |`);
    lines.push(`|--------|-------|`);
    lines.push(`| Total Pages | ${s?.total_pages ?? 0} |`);
    lines.push(`| Stars (healthy hubs) | ${s?.stars ?? 0} |`);
    lines.push(`| Hoarders | ${s?.hoarders ?? 0} |`);
    lines.push(`| Wasters | ${s?.wasters ?? 0} |`);
    lines.push(`| Dead Weight | ${s?.dead_weight ?? 0} |`);
    lines.push(`| Orphan Pages | ${s?.orphan_count ?? 0} |`);
    lines.push('');

    // Top Hoarders
    if (s?.top_hoarders?.length) {
      lines.push('### Top Hoarders');
      lines.push('');
      lines.push('| URL | PR Score | Outbound Links | TIPR Rank |');
      lines.push('|-----|----------|----------------|-----------|');
      for (const h of s.top_hoarders.slice(0, 10)) {
        lines.push(`| ${h.url} | ${Math.round(h.pagerank_score)} | ${h.outbound_count} | #${h.tipr_rank} |`);
      }
      lines.push('');
    }

    // Top Wasters
    if (s?.top_wasters?.length) {
      lines.push('### Top Wasters');
      lines.push('');
      lines.push('| URL | CheiRank Score | Outbound Links | TIPR Rank |');
      lines.push('|-----|----------------|----------------|-----------|');
      for (const w of s.top_wasters.slice(0, 10)) {
        lines.push(`| ${w.url} | ${Math.round(w.cheirank_score)} | ${w.outbound_count} | #${w.tipr_rank} |`);
      }
      lines.push('');
    }

    // Top Recommendations
    if (tipr.recommendations?.length) {
      lines.push('### Top Link Recommendations');
      lines.push('');
      for (const rec of tipr.recommendations.slice(0, 10)) {
        const icon = rec.priority === 'high' ? '🔴' : rec.priority === 'medium' ? '🟠' : '🟡';
        lines.push(`${icon} **[${rec.priority.toUpperCase()}]** ${rec.type === 'add_link' ? `Add link: ${rec.source_url} → ${rec.target_url}` : `Review outlinks: ${rec.source_url}`}`);
        lines.push('');
        lines.push(`> ${rec.reason}`);
        lines.push(`> **Expected Impact:** ${rec.expected_impact}`);
        lines.push('');
      }
    }
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
