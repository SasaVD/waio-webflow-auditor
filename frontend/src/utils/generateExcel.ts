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

export function generateExcel(report: Record<string, any>): void {
  const wb = XLSX.utils.book_new();

  // Sheet 1: Summary
  const summaryData = [
    ['WAIO Intelligence Report'],
    [''],
    ['URL', report.url],
    ['Audit Date', report.audit_timestamp],
    ['Overall Score', report.overall_score],
    ['Overall Label', report.overall_label],
    ['Tier', report.tier || 'free'],
    [''],
    ['Summary'],
    ['Total Findings', report.summary?.total_findings ?? 0],
    ['Critical', report.summary?.critical ?? 0],
    ['High', report.summary?.high ?? 0],
    ['Medium', report.summary?.medium ?? 0],
    [''],
    ['Pillar Scores'],
    ['Pillar', 'Score', 'Label'],
    ...extractPillarScores(report).map((p) => [p.label, p.score, p.scoreLabel]),
  ];
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
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
      ...positives.map((p: string) => [p]),
    ];
    const posSheet = XLSX.utils.aoa_to_sheet(posData);
    posSheet['!cols'] = [{ wch: 80 }];
    XLSX.utils.book_append_sheet(wb, posSheet, 'Positive Findings');
  }

  // Generate file
  const domain = report.url
    ?.replace(/https?:\/\//, '')
    .replace(/\//g, '_')
    .replace(/_$/, '');
  const date = new Date().toISOString().slice(0, 10);
  XLSX.writeFile(wb, `WAIO-Intelligence-Report-${domain}-${date}.xlsx`);
}
