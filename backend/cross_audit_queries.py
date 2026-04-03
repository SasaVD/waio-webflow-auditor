"""
Cross-Audit Intelligence Queries — Sprint 5B
Aggregation queries across all audits for benchmarking, CMS-specific
insights, and industry comparisons. Works with PostgreSQL only
(requires the normalized pillar_scores and findings tables).

These functions power:
- Most common findings by CMS type
- Average scores by pillar across all sites audited
- CMS-specific benchmarks (group by detected_cms)
- Industry benchmarks by NLP category (group by detected_industry)
- Training data for the future WAIO Agent chatbot
"""
import json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _is_postgres() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


async def _get_pool():
    """Get the asyncpg connection pool (only works when PostgreSQL is configured)."""
    if not _is_postgres():
        raise RuntimeError("Cross-audit queries require PostgreSQL (DATABASE_URL not set)")
    import asyncpg
    from db_postgres import get_pool
    return await get_pool()


# ── Average Scores by Pillar ───────────────────────────────────

async def get_average_scores_by_pillar(
    tier: str | None = None,
) -> List[Dict[str, Any]]:
    """Average score per pillar across all audits.

    Args:
        tier: Optional filter — "free" or "premium". None = all audits.

    Returns:
        List of dicts with pillar_key, avg_score, audit_count.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        if tier:
            rows = await conn.fetch(
                """SELECT ps.pillar_key,
                          ROUND(AVG(ps.score)) AS avg_score,
                          COUNT(DISTINCT ps.audit_id) AS audit_count
                   FROM pillar_scores ps
                   JOIN audits a ON a.id = ps.audit_id
                   WHERE a.tier = $1
                   GROUP BY ps.pillar_key
                   ORDER BY avg_score ASC""",
                tier,
            )
        else:
            rows = await conn.fetch(
                """SELECT pillar_key,
                          ROUND(AVG(score)) AS avg_score,
                          COUNT(DISTINCT audit_id) AS audit_count
                   FROM pillar_scores
                   GROUP BY pillar_key
                   ORDER BY avg_score ASC"""
            )
    return [
        {
            "pillar_key": row["pillar_key"],
            "avg_score": int(row["avg_score"]),
            "audit_count": row["audit_count"],
        }
        for row in rows
    ]


# ── CMS-Specific Benchmarks ───────────────────────────────────

async def get_scores_by_cms() -> List[Dict[str, Any]]:
    """Average overall score and pillar breakdown grouped by detected CMS.

    Returns:
        List of dicts with cms_platform, audit_count, avg_overall_score,
        and pillar_scores breakdown.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        # Overall scores by CMS
        overall = await conn.fetch(
            """SELECT detected_cms AS cms_platform,
                      COUNT(*) AS audit_count,
                      ROUND(AVG(overall_score)) AS avg_overall_score
               FROM audits
               WHERE detected_cms IS NOT NULL AND detected_cms != 'unknown'
               GROUP BY detected_cms
               ORDER BY audit_count DESC"""
        )

        # Per-pillar scores by CMS
        pillar_by_cms = await conn.fetch(
            """SELECT a.detected_cms AS cms_platform,
                      ps.pillar_key,
                      ROUND(AVG(ps.score)) AS avg_score
               FROM pillar_scores ps
               JOIN audits a ON a.id = ps.audit_id
               WHERE a.detected_cms IS NOT NULL AND a.detected_cms != 'unknown'
               GROUP BY a.detected_cms, ps.pillar_key
               ORDER BY a.detected_cms, ps.pillar_key"""
        )

    # Build pillar breakdown per CMS
    pillar_map: Dict[str, Dict[str, int]] = {}
    for row in pillar_by_cms:
        cms = row["cms_platform"]
        if cms not in pillar_map:
            pillar_map[cms] = {}
        pillar_map[cms][row["pillar_key"]] = int(row["avg_score"])

    return [
        {
            "cms_platform": row["cms_platform"],
            "audit_count": row["audit_count"],
            "avg_overall_score": int(row["avg_overall_score"]),
            "pillar_scores": pillar_map.get(row["cms_platform"], {}),
        }
        for row in overall
    ]


# ── Industry Benchmarks (NLP Category) ────────────────────────

async def get_scores_by_industry() -> List[Dict[str, Any]]:
    """Average overall score grouped by NLP-detected industry.

    Returns:
        List of dicts with industry, audit_count, avg_overall_score.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT detected_industry AS industry,
                      COUNT(*) AS audit_count,
                      ROUND(AVG(overall_score)) AS avg_overall_score
               FROM audits
               WHERE detected_industry IS NOT NULL
               GROUP BY detected_industry
               HAVING COUNT(*) >= 2
               ORDER BY audit_count DESC"""
        )
    return [
        {
            "industry": row["industry"],
            "audit_count": row["audit_count"],
            "avg_overall_score": int(row["avg_overall_score"]),
        }
        for row in rows
    ]


async def get_industry_pillar_benchmarks(
    industry: str,
) -> Dict[str, Any]:
    """Detailed pillar benchmarks for a specific industry.

    Args:
        industry: NLP category string (e.g., "/Business & Industrial/...").

    Returns:
        Dict with industry, audit_count, avg_overall_score, and per-pillar breakdown.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        overall = await conn.fetchrow(
            """SELECT COUNT(*) AS audit_count,
                      ROUND(AVG(overall_score)) AS avg_overall_score
               FROM audits
               WHERE detected_industry = $1""",
            industry,
        )
        pillars = await conn.fetch(
            """SELECT ps.pillar_key,
                      ROUND(AVG(ps.score)) AS avg_score,
                      MIN(ps.score) AS min_score,
                      MAX(ps.score) AS max_score
               FROM pillar_scores ps
               JOIN audits a ON a.id = ps.audit_id
               WHERE a.detected_industry = $1
               GROUP BY ps.pillar_key
               ORDER BY avg_score ASC""",
            industry,
        )

    return {
        "industry": industry,
        "audit_count": overall["audit_count"] if overall else 0,
        "avg_overall_score": int(overall["avg_overall_score"]) if overall and overall["avg_overall_score"] else 0,
        "pillar_benchmarks": [
            {
                "pillar_key": row["pillar_key"],
                "avg_score": int(row["avg_score"]),
                "min_score": row["min_score"],
                "max_score": row["max_score"],
            }
            for row in pillars
        ],
    }


# ── Most Common Findings ──────────────────────────────────────

async def get_common_findings(
    cms_platform: str | None = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Most frequently occurring findings, optionally filtered by CMS.

    Args:
        cms_platform: Optional CMS filter (e.g., "wordpress").
        limit: Max results.

    Returns:
        List of dicts with severity, description, occurrence_count, pillar_key.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        if cms_platform:
            rows = await conn.fetch(
                """SELECT f.severity, f.description, f.pillar_key,
                          COUNT(*) AS occurrence_count
                   FROM findings f
                   JOIN audits a ON a.id = f.audit_id
                   WHERE a.detected_cms = $1
                   GROUP BY f.severity, f.description, f.pillar_key
                   ORDER BY occurrence_count DESC
                   LIMIT $2""",
                cms_platform,
                limit,
            )
        else:
            rows = await conn.fetch(
                """SELECT severity, description, pillar_key,
                          COUNT(*) AS occurrence_count
                   FROM findings
                   GROUP BY severity, description, pillar_key
                   ORDER BY occurrence_count DESC
                   LIMIT $1""",
                limit,
            )

    return [
        {
            "severity": row["severity"],
            "description": row["description"],
            "pillar_key": row["pillar_key"],
            "occurrence_count": row["occurrence_count"],
        }
        for row in rows
    ]


# ── Severity Distribution by CMS ─────────────────────────────

async def get_severity_distribution_by_cms() -> List[Dict[str, Any]]:
    """Finding severity distribution grouped by CMS.

    Returns:
        List of dicts with cms_platform, severity, count.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT a.detected_cms AS cms_platform,
                      f.severity,
                      COUNT(*) AS finding_count
               FROM findings f
               JOIN audits a ON a.id = f.audit_id
               WHERE a.detected_cms IS NOT NULL AND a.detected_cms != 'unknown'
               GROUP BY a.detected_cms, f.severity
               ORDER BY a.detected_cms, f.severity"""
        )

    # Reshape into per-CMS dicts
    cms_map: Dict[str, Dict[str, int]] = {}
    for row in rows:
        cms = row["cms_platform"]
        if cms not in cms_map:
            cms_map[cms] = {"critical": 0, "high": 0, "medium": 0}
        cms_map[cms][row["severity"]] = row["finding_count"]

    return [
        {"cms_platform": cms, **counts}
        for cms, counts in sorted(cms_map.items())
    ]


# ── Score Trend for a URL ─────────────────────────────────────

async def get_score_trend(url: str) -> List[Dict[str, Any]]:
    """Score history for a specific URL across all audits.

    Args:
        url: The site URL.

    Returns:
        List of dicts with audit_id, overall_score, tier, created_at.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, overall_score, tier, detected_cms, created_at
               FROM audits
               WHERE url = $1
               ORDER BY created_at ASC""",
            url,
        )
    return [
        {
            "audit_id": str(row["id"]),
            "overall_score": row["overall_score"],
            "tier": row["tier"],
            "detected_cms": row["detected_cms"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


# ── Full Intelligence Summary ─────────────────────────────────

async def get_intelligence_summary() -> Dict[str, Any]:
    """Comprehensive cross-audit intelligence summary.

    Returns:
        Dict with total audits, CMS distribution, industry distribution,
        weakest pillars, and most common critical findings.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM audits")
        avg_score = await conn.fetchval("SELECT ROUND(AVG(overall_score)) FROM audits")

        cms_dist = await conn.fetch(
            """SELECT COALESCE(detected_cms, 'unknown') AS cms,
                      COUNT(*) AS count
               FROM audits
               GROUP BY detected_cms
               ORDER BY count DESC
               LIMIT 15"""
        )

        industry_dist = await conn.fetch(
            """SELECT detected_industry AS industry,
                      COUNT(*) AS count
               FROM audits
               WHERE detected_industry IS NOT NULL
               GROUP BY detected_industry
               ORDER BY count DESC
               LIMIT 10"""
        )

        weakest_pillars = await conn.fetch(
            """SELECT pillar_key,
                      ROUND(AVG(score)) AS avg_score
               FROM pillar_scores
               GROUP BY pillar_key
               ORDER BY avg_score ASC
               LIMIT 5"""
        )

        top_critical = await conn.fetch(
            """SELECT description, pillar_key, COUNT(*) AS count
               FROM findings
               WHERE severity = 'critical'
               GROUP BY description, pillar_key
               ORDER BY count DESC
               LIMIT 10"""
        )

    return {
        "total_audits": total,
        "avg_overall_score": int(avg_score) if avg_score else 0,
        "cms_distribution": [
            {"cms": row["cms"], "count": row["count"]} for row in cms_dist
        ],
        "industry_distribution": [
            {"industry": row["industry"], "count": row["count"]} for row in industry_dist
        ],
        "weakest_pillars": [
            {"pillar_key": row["pillar_key"], "avg_score": int(row["avg_score"])}
            for row in weakest_pillars
        ],
        "top_critical_findings": [
            {
                "description": row["description"],
                "pillar_key": row["pillar_key"],
                "occurrence_count": row["count"],
            }
            for row in top_critical
        ],
    }
