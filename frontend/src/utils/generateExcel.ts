import * as XLSX from 'xlsx';
import { PILLAR_LABELS } from '../constants/pillarLabels';

interface Finding {
  severity: string;
  description: string;
  recommendation: string;
  reference?: string;
  pillar?: string;
}

interface PillarScore {
  key: string;
  label: string;
  score: number;
  scoreLabel: string;
}

function extractFindings(report: Record<string, any>): Finding[] {
  const findings: Finding[] = [];
  if (!report.categories) return findings;
  for (const [pillarKey, cat] of Object.entries(report.categories)) {
    const catObj = cat as Record<string, any>;
    const checks = catObj.checks || {};
    for (const check of Object.values(checks)) {
      const checkObj = check as Record<string, any>;
      if (checkObj.findings) {
        for (const f of checkObj.findings) {
          findings.push({ ...f, pillar: PILLAR_LABELS[pillarKey] || pillarKey });
        }
      }
    }
  }
  return findings.sort(
    (a, b) =>
      ({ critical: 0, high: 1, medium: 2 }[a.severity] ?? 3) -
      ({ critical: 0, high: 1, medium: 2 }[b.severity] ?? 3)
  );
}

function extractPillarScores(report: Record<string, any>): PillarScore[] {
  if (!report.categories) return [];
  return Object.entries(report.categories).map(([key, cat]) => {
    const catObj = cat as Record<string, any>;
    return {
      key,
      label: PILLAR_LABELS[key] || key,
      score: catObj.score ?? 0,
      scoreLabel: catObj.label ?? '',
    };
  });
}

/** Safely convert a positive finding to a string (handles string | object). */
function positiveText(p: unknown): string {
  if (typeof p === 'string') return p;
  if (p && typeof p === 'object') {
    const obj = p as Record<string, unknown>;
    return String(obj.text || obj.message || obj.description || JSON.stringify(p));
  }
  return String(p);
}

export function generateExcel(report: Record<string, any>): void {
  const wb = XLSX.utils.book_new();

  // Sheet 1: Summary
  const summaryRows: any[][] = [
    ['WAIO Intelligence Report'],
    [''],
    ['URL', report.url],
    ['Audit Date', report.audit_timestamp],
    ['Overall Score', report.overall_score],
    ['Overall Label', report.overall_label],
    ['Tier', report.tier || 'free'],
  ];
  if (report.cms_detection?.platform && report.cms_detection.platform !== 'unknown') {
    summaryRows.push(['CMS Detected', report.cms_detection.platform]);
  }
  summaryRows.push(
    [''],
    ['Summary'],
    ['Total Findings', report.summary?.total_findings ?? 0],
    ['Critical', report.summary?.critical ?? 0],
    ['High', report.summary?.high ?? 0],
    ['Medium', report.summary?.medium ?? 0],
  );
  if (report.crawl_stats) {
    const cs = report.crawl_stats;
    summaryRows.push(
      [''],
      ['Crawl Statistics'],
      ['Pages Crawled', cs.pages_crawled ?? 0],
      ['Pages Discovered', cs.pages_discovered ?? 0],
      ['Internal Links', cs.internal_links ?? 0],
      ['External Links', cs.external_links ?? 0],
      ['Broken Links', cs.broken_links ?? 0],
    );
  }
  summaryRows.push(
    [''],
    ['Pillar Scores'],
    ['Pillar', 'Score', 'Label'],
    ...extractPillarScores(report).map((p) => [p.label, p.score, p.scoreLabel]),
  );
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryRows);
  summarySheet['!cols'] = [{ wch: 25 }, { wch: 50 }, { wch: 20 }];
  XLSX.utils.book_append_sheet(wb, summarySheet, 'Summary');

  // Sheet 2: All Findings
  const findings = extractFindings(report);
  const findingsData = [
    ['Severity', 'Pillar', 'Description', 'Recommendation', 'Reference'],
    ...findings.map((f) => [
      f.severity,
      f.pillar || '',
      f.description,
      f.recommendation,
      f.reference || '',
    ]),
  ];
  const findingsSheet = XLSX.utils.aoa_to_sheet(findingsData);
  findingsSheet['!cols'] = [
    { wch: 10 },
    { wch: 18 },
    { wch: 60 },
    { wch: 60 },
    { wch: 40 },
  ];
  XLSX.utils.book_append_sheet(wb, findingsSheet, 'Findings');

  // Sheet 3: Positive Findings
  const positives = report.positive_findings || [];
  if (positives.length > 0) {
    const posData = [
      ['Positive Findings'],
      ...positives.map((p: unknown) => [positiveText(p)]),
    ];
    const posSheet = XLSX.utils.aoa_to_sheet(posData);
    posSheet['!cols'] = [{ wch: 80 }];
    XLSX.utils.book_append_sheet(wb, posSheet, 'Positive Findings');
  }

  // Sheet 4: Webflow Fix Instructions (premium)
  if (report.webflow_fixes && Object.keys(report.webflow_fixes).length > 0) {
    const fixData: any[][] = [
      ['Finding', 'Title', 'Difficulty', 'Time', 'Pillar'],
    ];
    for (const [pattern, fix] of Object.entries(report.webflow_fixes)) {
      const f = fix as Record<string, any>;
      fixData.push([pattern, f.title || '', f.difficulty || '', f.estimated_time || '', f.pillar_key || '']);
    }
    const fixSheet = XLSX.utils.aoa_to_sheet(fixData);
    fixSheet['!cols'] = [{ wch: 25 }, { wch: 40 }, { wch: 12 }, { wch: 15 }, { wch: 18 }];
    XLSX.utils.book_append_sheet(wb, fixSheet, 'Fix Instructions');
  }

  // Sheet 5: Competitor Data (premium)
  if (report.competitive_data?.rankings?.length) {
    const compData: any[][] = [['Rank', 'URL', 'Score', 'Label']];
    report.competitive_data.rankings.forEach((r: any, idx: number) => {
      compData.push([idx + 1, r.url, r.overall_score, r.overall_label || '']);
    });
    const compSheet = XLSX.utils.aoa_to_sheet(compData);
    compSheet['!cols'] = [{ wch: 6 }, { wch: 50 }, { wch: 8 }, { wch: 18 }];
    XLSX.utils.book_append_sheet(wb, compSheet, 'Competitors');
  }

  // Sheet 6: Content Intelligence (NLP)
  if (report.nlp_analysis) {
    const nlp = report.nlp_analysis;
    const nlpData: any[][] = [['Content Intelligence (NLP Analysis)']];
    nlpData.push(['']);
    if (nlp.detected_industry) {
      nlpData.push(['Detected Industry', nlp.detected_industry]);
      nlpData.push(['Confidence', nlp.industry_confidence != null ? `${Math.round(nlp.industry_confidence * 100)}%` : 'N/A']);
    }
    if (nlp.sentiment) {
      nlpData.push(['Content Tone', nlp.sentiment.tone]);
      nlpData.push(['Sentiment Score', nlp.sentiment.score]);
      nlpData.push(['Sentiment Magnitude', nlp.sentiment.magnitude]);
    }
    if (nlp.insights?.seo_alignment) {
      nlpData.push(['SEO Alignment', nlp.insights.seo_alignment]);
    }
    if (nlp.primary_entity) {
      nlpData.push(['Primary Entity', nlp.primary_entity]);
      nlpData.push(['Primary Entity Salience', nlp.primary_entity_salience != null ? `${(nlp.primary_entity_salience * 100).toFixed(1)}%` : 'N/A']);
    }

    // Entity table
    if (nlp.entities?.length) {
      nlpData.push(['']);
      nlpData.push(['Entity', 'Type', 'Salience', 'Mentions', 'Wikipedia']);
      for (const ent of nlp.entities) {
        nlpData.push([
          ent.name,
          ent.type,
          `${(ent.salience * 100).toFixed(1)}%`,
          ent.mentions_count ?? '',
          ent.wikipedia_url ?? '',
        ]);
      }
    }
    const nlpSheet = XLSX.utils.aoa_to_sheet(nlpData);
    nlpSheet['!cols'] = [{ wch: 30 }, { wch: 20 }, { wch: 12 }, { wch: 10 }, { wch: 50 }];
    XLSX.utils.book_append_sheet(wb, nlpSheet, 'Content Intelligence');
  }

  // Sheet 7: Topic Clusters (from DataForSEO link analysis)
  const clusters = report.link_analysis?.clusters || report.topic_clusters;
  if (clusters?.length) {
    const clusterData: any[][] = [['Cluster', 'Pages', 'Coherence Score', 'Dominant Category']];
    for (const cluster of clusters) {
      clusterData.push([
        cluster.prefix || cluster.name || '',
        cluster.page_count ?? 0,
        cluster.coherence_score != null ? Math.round(cluster.coherence_score * 100) + '%' : 'N/A',
        cluster.dominant_category || '',
      ]);
    }
    const clusterSheet = XLSX.utils.aoa_to_sheet(clusterData);
    clusterSheet['!cols'] = [{ wch: 25 }, { wch: 8 }, { wch: 15 }, { wch: 40 }];
    XLSX.utils.book_append_sheet(wb, clusterSheet, 'Topic Clusters');
  }

  // Generate file
  const domain = report.url
    ?.replace(/https?:\/\//, '')
    .replace(/\//g, '_')
    .replace(/_$/, '');
  const date = new Date().toISOString().slice(0, 10);
  XLSX.writeFile(wb, `WAIO-Intelligence-Report-${domain}-${date}.xlsx`);
}
