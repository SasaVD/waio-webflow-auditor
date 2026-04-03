"""
Knowledge Base Generator — Sprint 5A
Transforms audit + crawl + NLP data into RAG-ready documents
for the future WAIO Agent (Phase 2).

Export format: JSON Lines (.jsonl) — one JSON object per line,
ready for vector DB ingestion (Pinecone, Weaviate, Qdrant, etc.).

Document types generated:
1. Page documents — title, clean_text, NLP entities/category, topics, links
2. Finding documents — problem, fix instruction, evidence
3. Fix instruction documents — steps, difficulty, context
4. CMS migration assessment — platform comparison + NLP content mapping
5. Site summary — overall scores, industry, entity map
"""
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class KBDocument:
    """A single RAG-ready document for vector DB ingestion."""
    doc_id: str           # unique document identifier
    doc_type: str         # "page", "finding", "fix", "migration", "site_summary"
    audit_id: str         # parent audit UUID
    url: str              # associated URL
    title: str            # document title for display
    content: str          # main text content for embedding
    metadata: Dict[str, Any]  # structured metadata for filtering

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict(), default=str)


def generate_page_documents(
    audit_id: str,
    site_url: str,
    pages: List[Dict[str, Any]],
) -> List[KBDocument]:
    """Generate one document per crawled page with content + NLP data.

    Args:
        audit_id: Audit UUID string.
        site_url: The root site URL.
        pages: Page content records from get_page_content_for_audit().

    Returns:
        List of KBDocument objects.
    """
    docs: List[KBDocument] = []

    for i, page in enumerate(pages):
        url = page.get("url", "")
        clean_text = page.get("clean_text") or ""
        title = page.get("title") or url.split("/")[-1] or "Untitled"

        # Build content string (what gets embedded)
        content_parts = []
        if title:
            content_parts.append(f"Title: {title}")
        h1 = page.get("h1_text")
        if h1:
            content_parts.append(f"H1: {h1}")
        meta_desc = page.get("meta_description")
        if meta_desc:
            content_parts.append(f"Description: {meta_desc}")
        if clean_text:
            # Truncate to ~4000 chars for embedding (most models use 512-8192 tokens)
            content_parts.append(clean_text[:4000])

        content = "\n".join(content_parts)
        if len(content.strip()) < 20:
            continue  # skip pages with no meaningful content

        metadata: Dict[str, Any] = {
            "site_url": site_url,
            "page_url": url,
            "word_count": page.get("word_count"),
            "language": page.get("language"),
            "click_depth": page.get("click_depth"),
            "is_orphan": page.get("is_orphan", False),
            "nlp_category": page.get("nlp_category"),
            "nlp_category_confidence": page.get("nlp_category_confidence"),
            "nlp_primary_entity": page.get("nlp_primary_entity"),
            "nlp_primary_entity_salience": page.get("nlp_primary_entity_salience"),
            "nlp_entity_focus_aligned": page.get("nlp_entity_focus_aligned"),
            "nlp_sentiment_score": page.get("nlp_sentiment_score"),
        }

        docs.append(KBDocument(
            doc_id=f"{audit_id}_page_{i}",
            doc_type="page",
            audit_id=audit_id,
            url=url,
            title=title,
            content=content,
            metadata=metadata,
        ))

    logger.info(f"Generated {len(docs)} page documents for audit {audit_id}")
    return docs


def generate_finding_documents(
    audit_id: str,
    site_url: str,
    report: Dict[str, Any],
) -> List[KBDocument]:
    """Generate one document per finding with problem + fix + evidence.

    Args:
        audit_id: Audit UUID string.
        site_url: The audited site URL.
        report: Full audit report dict (from report_generator).

    Returns:
        List of KBDocument objects.
    """
    docs: List[KBDocument] = []
    finding_idx = 0

    categories = report.get("categories", {})
    for pillar_key, pillar_data in categories.items():
        pillar_score = pillar_data.get("score", 0)
        pillar_label = pillar_data.get("label", "N/A")

        checks = pillar_data.get("checks") or {}
        for check_name, check_data in checks.items():
            findings = check_data.get("findings") or []
            for finding in findings:
                severity = finding.get("severity", "medium")
                description = finding.get("description", "")
                recommendation = finding.get("recommendation", "")
                reference = finding.get("reference", "")
                why = finding.get("why_it_matters") or finding.get("credibility_anchor", "")

                content_parts = [
                    f"Issue ({severity}): {description}",
                    f"Fix: {recommendation}",
                ]
                if why:
                    content_parts.append(f"Evidence: {why}")
                if reference:
                    content_parts.append(f"Reference: {reference}")

                docs.append(KBDocument(
                    doc_id=f"{audit_id}_finding_{finding_idx}",
                    doc_type="finding",
                    audit_id=audit_id,
                    url=site_url,
                    title=f"{pillar_key}/{check_name}: {description[:80]}",
                    content="\n".join(content_parts),
                    metadata={
                        "site_url": site_url,
                        "pillar_key": pillar_key,
                        "check_name": check_name,
                        "severity": severity,
                        "pillar_score": pillar_score,
                        "pillar_label": pillar_label,
                    },
                ))
                finding_idx += 1

    logger.info(f"Generated {len(docs)} finding documents for audit {audit_id}")
    return docs


def generate_fix_documents(
    audit_id: str,
    site_url: str,
    webflow_fixes: List[Dict[str, Any]] | None = None,
) -> List[KBDocument]:
    """Generate one document per Webflow fix instruction.

    Args:
        audit_id: Audit UUID string.
        site_url: The audited site URL.
        webflow_fixes: Matched fix instructions from match_fixes_to_findings().

    Returns:
        List of KBDocument objects.
    """
    if not webflow_fixes:
        return []

    docs: List[KBDocument] = []
    for i, fix in enumerate(webflow_fixes):
        title = fix.get("title", "Webflow Fix")
        steps = fix.get("steps_markdown", "")
        pillar = fix.get("pillar_key", "unknown")
        difficulty = fix.get("difficulty", "medium")
        est_time = fix.get("estimated_time", "unknown")

        content = f"Fix: {title}\nDifficulty: {difficulty}\nTime: {est_time}\n\n{steps}"

        docs.append(KBDocument(
            doc_id=f"{audit_id}_fix_{i}",
            doc_type="fix",
            audit_id=audit_id,
            url=site_url,
            title=title,
            content=content,
            metadata={
                "site_url": site_url,
                "pillar_key": pillar,
                "difficulty": difficulty,
                "estimated_time": est_time,
                "finding_pattern": fix.get("finding_pattern", ""),
            },
        ))

    logger.info(f"Generated {len(docs)} fix documents for audit {audit_id}")
    return docs


def generate_migration_document(
    audit_id: str,
    site_url: str,
    migration: Dict[str, Any] | None = None,
) -> List[KBDocument]:
    """Generate a document for CMS migration assessment.

    Args:
        audit_id: Audit UUID string.
        site_url: The audited site URL.
        migration: Migration assessment dict.

    Returns:
        List with 0 or 1 KBDocument.
    """
    if not migration:
        return []

    source_cms = migration.get("source_cms", "unknown")
    target_cms = migration.get("target_cms", "webflow")

    content_parts = [
        f"CMS Migration Assessment: {source_cms} → {target_cms}",
        f"Timeline: {migration.get('migration_timeline', 'N/A')}",
        f"Redirect estimate: {migration.get('redirect_count_estimate', 0)}",
    ]

    # Platform issues
    issues = migration.get("platform_issues", [])
    if issues:
        content_parts.append(f"\n{len(issues)} platform-specific issues:")
        for iss in issues:
            sev = iss.get("severity", "medium")
            content_parts.append(f"- [{sev}] {iss.get('title', '')}: {iss.get('description', '')}")

    # TCO comparison
    tco = migration.get("tco_comparison")
    if tco:
        savings = tco.get("annual_savings", 0)
        content_parts.append(f"\nAnnual savings: ${savings:,}")
        content_parts.append(f"5-year savings: ${tco.get('five_year_savings', 0):,}")

    # NLP content mapping
    nlp_map = migration.get("nlp_content_mapping")
    if nlp_map:
        sections = nlp_map.get("sections", [])
        content_parts.append(f"\nContent mapping: {nlp_map.get('total_categories', 0)} categories")
        for sec in sections[:10]:
            content_parts.append(
                f"- {sec.get('category', 'N/A')}: {sec.get('page_count', 0)} pages "
                f"(priority: {sec.get('migration_priority', 'medium')})"
            )

    return [KBDocument(
        doc_id=f"{audit_id}_migration",
        doc_type="migration",
        audit_id=audit_id,
        url=site_url,
        title=f"Migration: {source_cms} → {target_cms}",
        content="\n".join(content_parts),
        metadata={
            "site_url": site_url,
            "source_cms": source_cms,
            "target_cms": target_cms,
            "redirect_count": migration.get("redirect_count_estimate", 0),
            "issue_count": len(issues),
        },
    )]


def generate_site_summary_document(
    audit_id: str,
    site_url: str,
    report: Dict[str, Any],
) -> List[KBDocument]:
    """Generate a single summary document for the entire audit.

    Args:
        audit_id: Audit UUID string.
        site_url: The audited site URL.
        report: Full audit report dict.

    Returns:
        List with 1 KBDocument.
    """
    overall_score = report.get("overall_score", 0)
    overall_label = report.get("overall_label", "N/A")
    tier = report.get("tier", "free")
    summary = report.get("summary", {})

    content_parts = [
        f"Site Audit Summary: {site_url}",
        f"Overall Score: {overall_score}/100 ({overall_label})",
        f"Tier: {tier}",
        f"Total findings: {summary.get('total_findings', 0)}",
        f"Critical: {summary.get('critical', 0)}, High: {summary.get('high', 0)}, Medium: {summary.get('medium', 0)}",
    ]

    # Pillar scores
    categories = report.get("categories", {})
    content_parts.append("\nPillar Scores:")
    for pillar_key, pillar_data in categories.items():
        content_parts.append(
            f"- {pillar_key}: {pillar_data.get('score', 0)}/100 ({pillar_data.get('label', 'N/A')})"
        )

    # CMS detection
    cms = report.get("cms_detection")
    if cms:
        content_parts.append(f"\nCMS: {cms.get('platform', 'unknown')} (confidence: {cms.get('confidence', 0)})")

    # Positive findings
    positives = report.get("positive_findings", [])
    if positives:
        content_parts.append(f"\n{len(positives)} positive findings:")
        for pos in positives[:10]:
            content_parts.append(f"- {pos}")

    # Top priorities
    priorities = summary.get("top_priorities", [])
    if priorities:
        content_parts.append("\nTop priorities:")
        for p in priorities:
            content_parts.append(f"- {p}")

    # Executive summary
    exec_summary = report.get("executive_summary")
    if exec_summary:
        content_parts.append(f"\nExecutive Summary:\n{exec_summary[:2000]}")

    metadata: Dict[str, Any] = {
        "site_url": site_url,
        "overall_score": overall_score,
        "overall_label": overall_label,
        "tier": tier,
        "total_findings": summary.get("total_findings", 0),
        "critical_count": summary.get("critical", 0),
        "high_count": summary.get("high", 0),
        "cms_platform": cms.get("platform") if cms else None,
    }

    return [KBDocument(
        doc_id=f"{audit_id}_summary",
        doc_type="site_summary",
        audit_id=audit_id,
        url=site_url,
        title=f"Audit Summary: {site_url} — {overall_score}/100",
        content="\n".join(content_parts),
        metadata=metadata,
    )]


def generate_knowledge_base(
    audit_id: str,
    site_url: str,
    report: Dict[str, Any],
    pages: List[Dict[str, Any]] | None = None,
    webflow_fixes: List[Dict[str, Any]] | None = None,
    migration: Dict[str, Any] | None = None,
) -> List[KBDocument]:
    """Generate complete RAG-ready knowledge base from an audit.

    Combines all document types into a single list.

    Args:
        audit_id: Audit UUID string.
        site_url: The audited site URL.
        report: Full audit report dict.
        pages: Page content records (from get_page_content_for_audit).
        webflow_fixes: Matched fix instructions.
        migration: Migration assessment dict.

    Returns:
        List of all KBDocument objects.
    """
    all_docs: List[KBDocument] = []

    # 1. Site summary (always)
    all_docs.extend(generate_site_summary_document(audit_id, site_url, report))

    # 2. Finding documents (always)
    all_docs.extend(generate_finding_documents(audit_id, site_url, report))

    # 3. Page documents (if crawl data available)
    if pages:
        all_docs.extend(generate_page_documents(audit_id, site_url, pages))

    # 4. Fix instructions (if available)
    if webflow_fixes:
        all_docs.extend(generate_fix_documents(audit_id, site_url, webflow_fixes))

    # 5. Migration assessment (if available)
    if migration:
        all_docs.extend(generate_migration_document(audit_id, site_url, migration))

    logger.info(
        f"Knowledge base generated for {site_url}: "
        f"{len(all_docs)} total documents "
        f"(summary=1, findings={len([d for d in all_docs if d.doc_type == 'finding'])}, "
        f"pages={len([d for d in all_docs if d.doc_type == 'page'])}, "
        f"fixes={len([d for d in all_docs if d.doc_type == 'fix'])}, "
        f"migration={len([d for d in all_docs if d.doc_type == 'migration'])})"
    )
    return all_docs


def export_jsonl(docs: List[KBDocument]) -> str:
    """Export knowledge base documents as JSON Lines string.

    Each line is a complete JSON object — ready for vector DB ingestion.
    """
    lines = [doc.to_jsonl() for doc in docs]
    return "\n".join(lines)


def export_jsonl_bytes(docs: List[KBDocument]) -> bytes:
    """Export knowledge base documents as UTF-8 bytes (for file download)."""
    return export_jsonl(docs).encode("utf-8")
