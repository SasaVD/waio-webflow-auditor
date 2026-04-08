"""
TIPR (True Internal PageRank) Scoring Engine
=============================================

Computes Internal PageRank, CheiRank, and composite TIPR scores for every
crawled page, then generates actionable internal linking recommendations.

Based on Kevin Indig's TIPR methodology:
- PageRank measures how much link equity a page *receives* (authority)
- CheiRank measures how much link equity a page *distributes* (generosity)
- TIPR composite = rank-averaged blend of both signals

Quadrant classification:
  Star       — High PR, High CR  → healthy hub page
  Hoarder    — High PR, Low CR   → receiving equity but not passing it on
  Waster     — Low PR, High CR   → distributing equity without receiving enough
  Dead Weight — Low PR, Low CR    → needs attention

Pure Python module: depends only on numpy, scipy, and standard library.
"""

import math
import logging
from collections import defaultdict

import numpy as np
from scipy import sparse
from scipy.stats import rankdata

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1A. PageRank
# ---------------------------------------------------------------------------

def compute_pagerank(
    adj_matrix: sparse.csr_matrix,
    alpha: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> np.ndarray:
    """Power-iteration PageRank on a sparse adjacency matrix.

    adj_matrix[i][j] = 1 means page *i* links to page *j*.
    Returns an array of PR values normalised to sum to 1.0.
    """
    N = adj_matrix.shape[0]
    if N == 0:
        return np.array([])

    adj = adj_matrix.copy()
    adj.setdiag(0)
    adj.eliminate_zeros()

    out_degree = np.array(adj.sum(axis=1)).flatten()
    dangling = out_degree == 0

    inv_out = np.zeros(N)
    inv_out[~dangling] = 1.0 / out_degree[~dangling]
    M = (sparse.diags(inv_out) @ adj).T  # column-stochastic transition matrix

    pr = np.ones(N) / N
    teleport = np.ones(N) / N

    for _ in range(max_iter):
        pr_old = pr.copy()
        dangling_sum = alpha * pr_old[dangling].sum()
        pr = alpha * M.dot(pr_old) + dangling_sum * teleport + (1 - alpha) * teleport

        if np.abs(pr - pr_old).sum() < tol:
            break

    return pr / pr.sum()


# ---------------------------------------------------------------------------
# 1B. CheiRank
# ---------------------------------------------------------------------------

def compute_cheirank(
    adj_matrix: sparse.csr_matrix,
    alpha: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> np.ndarray:
    """CheiRank = PageRank on the *reversed* link graph."""
    return compute_pagerank(adj_matrix.T.tocsr(), alpha, max_iter, tol)


# ---------------------------------------------------------------------------
# 1C. TIPR Composite Score
# ---------------------------------------------------------------------------

def compute_tipr_scores(
    pagerank_values: np.ndarray,
    cheirank_values: np.ndarray,
    backlink_counts: np.ndarray | None = None,
) -> np.ndarray:
    """Rank-averaged TIPR composite.  Lower value = stronger page."""
    pr_ranks = rankdata(-pagerank_values, method="min")
    cr_ranks = rankdata(-cheirank_values, method="min")

    if backlink_counts is not None and len(backlink_counts) > 0:
        bl_ranks = rankdata(-backlink_counts, method="min")
        return (pr_ranks + cr_ranks + bl_ranks) / 3.0

    return (pr_ranks + cr_ranks) / 2.0


# ---------------------------------------------------------------------------
# 1D. Quadrant Classification
# ---------------------------------------------------------------------------

QUADRANT_STAR = "star"
QUADRANT_HOARDER = "hoarder"
QUADRANT_WASTER = "waster"
QUADRANT_DEAD_WEIGHT = "dead_weight"


def classify_pages(
    pagerank_values: np.ndarray,
    cheirank_values: np.ndarray,
) -> list[str]:
    """Classify every page into a TIPR quadrant using median thresholds."""
    pr_median = float(np.median(pagerank_values))
    cr_median = float(np.median(cheirank_values))

    classifications: list[str] = []
    for pr, cr in zip(pagerank_values, cheirank_values):
        if pr >= pr_median and cr >= cr_median:
            classifications.append(QUADRANT_STAR)
        elif pr >= pr_median and cr < cr_median:
            classifications.append(QUADRANT_HOARDER)
        elif pr < pr_median and cr >= cr_median:
            classifications.append(QUADRANT_WASTER)
        else:
            classifications.append(QUADRANT_DEAD_WEIGHT)
    return classifications


# ---------------------------------------------------------------------------
# 1E. Graph Construction
# ---------------------------------------------------------------------------

def build_adjacency_matrix(
    nodes: list[dict],
    links: list[dict],
) -> tuple[sparse.csr_matrix, dict[str, int], dict[int, str]]:
    """Build a sparse adjacency matrix from graph node/link lists.

    Returns (adj_matrix, url_to_idx, idx_to_url).
    """
    valid_urls = [n["id"] for n in nodes]
    url_to_idx = {url: i for i, url in enumerate(valid_urls)}
    N = len(valid_urls)

    rows: list[int] = []
    cols: list[int] = []
    for link in links:
        src_raw = link.get("source")
        tgt_raw = link.get("target")
        src_url = src_raw if isinstance(src_raw, str) else (src_raw or {}).get("id", "")
        tgt_url = tgt_raw if isinstance(tgt_raw, str) else (tgt_raw or {}).get("id", "")

        src = url_to_idx.get(src_url)
        tgt = url_to_idx.get(tgt_url)
        if src is not None and tgt is not None and src != tgt:
            rows.append(src)
            cols.append(tgt)

    if N == 0:
        return sparse.csr_matrix((0, 0)), url_to_idx, {}

    A = sparse.csr_matrix(
        (np.ones(len(rows), dtype=np.float64), (rows, cols)),
        shape=(N, N),
    )
    idx_to_url = {i: url for url, i in url_to_idx.items()}
    return A, url_to_idx, idx_to_url


# ---------------------------------------------------------------------------
# Helper: normalise raw PR values to 0-100 (log-scale like Screaming Frog)
# ---------------------------------------------------------------------------

def _normalise_scores(values: np.ndarray) -> np.ndarray:
    """Map raw PageRank/CheiRank floats to a 0–100 log-scale."""
    if len(values) == 0:
        return np.array([])
    # Clamp to positive
    safe = np.maximum(values, 1e-15)
    log_vals = np.log(safe)
    lo, hi = log_vals.min(), log_vals.max()
    if hi - lo < 1e-12:
        return np.full_like(values, 50.0)
    normalised = (log_vals - lo) / (hi - lo) * 100.0
    return np.clip(normalised, 0, 100)


# ---------------------------------------------------------------------------
# Helper: URL cluster prefix
# ---------------------------------------------------------------------------

def _url_cluster(url: str) -> str:
    """Extract the first directory segment as a cluster label."""
    from urllib.parse import urlparse

    path = urlparse(url).path.rstrip("/")
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 1:
        return "/" + parts[0] + "/"
    return "/"


# ---------------------------------------------------------------------------
# 1F. Recommendation Engine
# ---------------------------------------------------------------------------

def generate_link_recommendations(
    nodes: list[dict],
    links: list[dict],
    tipr_pages: list[dict],
    max_recommendations: int = 50,
    nlp_analysis: dict | None = None,
) -> list[dict]:
    """Generate actionable 'add link from A → B' recommendations.

    Three recommendation types:
      1. Hoarder redistribution  – high-PR pages not distributing equity
      2. Weak page boosting      – low-PR pages that need inbound links
      3. Waster pruning          – pages with too many outlinks diluting equity
    """
    if not tipr_pages:
        return []

    # Build lookup structures
    url_data: dict[str, dict] = {p["url"]: p for p in tipr_pages}
    max_pr = max(((p["pagerank_score"] or 0) for p in tipr_pages), default=1) or 1

    # Existing edges set (for quick duplicate check)
    existing_edges: set[tuple[str, str]] = set()
    for link in links:
        src = link.get("source") if isinstance(link.get("source"), str) else (link.get("source") or {}).get("id", "")
        tgt = link.get("target") if isinstance(link.get("target"), str) else (link.get("target") or {}).get("id", "")
        existing_edges.add((src, tgt))

    # Entity data for content relevance (if available)
    page_entities: dict[str, set[str]] = {}
    if nlp_analysis and nlp_analysis.get("entities"):
        # Build a site-wide entity set from report-level data
        pass
    # Try per-node NLP entities from the nodes list
    for node in nodes:
        entities = node.get("nlp_entities") or []
        if isinstance(entities, list):
            page_entities[node["id"]] = {
                (e.get("name") or "").lower() for e in entities if isinstance(e, dict)
            }

    def _content_relevance(src_url: str, tgt_url: str) -> float:
        """0.0-1.0 relevance score: 60 % cluster match + 40 % entity overlap."""
        cluster_score = 1.0 if _url_cluster(src_url) == _url_cluster(tgt_url) else 0.0
        entity_score = 0.0
        src_ents = page_entities.get(src_url, set())
        tgt_ents = page_entities.get(tgt_url, set())
        if src_ents and tgt_ents:
            union = src_ents | tgt_ents
            if union:
                entity_score = len(src_ents & tgt_ents) / len(union)
        return 0.6 * cluster_score + 0.4 * entity_score

    # Identify hoarder sources and weak targets
    hoarders = [p for p in tipr_pages if p["classification"] == QUADRANT_HOARDER]
    hoarders.sort(key=lambda p: p["pagerank_score"] or 0, reverse=True)

    weak_pages = [p for p in tipr_pages if (p["pagerank_score"] or 0) < 30 and (p["inbound_count"] or 0) < 5]
    weak_pages.sort(key=lambda p: p["pagerank_score"] or 0)

    orphans = [p for p in tipr_pages if (p["inbound_count"] or 0) == 0]

    # Stars can also donate links
    stars = [p for p in tipr_pages if p["classification"] == QUADRANT_STAR]
    stars.sort(key=lambda p: p["pagerank_score"] or 0, reverse=True)

    recommendations: list[dict] = []
    source_rec_count: dict[str, int] = defaultdict(int)
    target_rec_count: dict[str, int] = defaultdict(int)

    def _add_rec(
        rec_type: str,
        priority: str,
        group: str,
        source_url: str,
        target_url: str,
        reason: str,
        relevance: float,
    ) -> bool:
        if source_rec_count[source_url] >= 5:
            return False
        if target_rec_count[target_url] >= 10:
            return False
        if (source_url, target_url) in existing_edges:
            return False
        if len(recommendations) >= max_recommendations:
            return False

        src = url_data.get(source_url, {})
        tgt = url_data.get(target_url, {})
        src_pr = src.get("pagerank_score") or 0
        tgt_pr = tgt.get("pagerank_score") or 0
        src_out = src.get("outbound_count") or 0
        delta = max(1, int(src_pr * 0.15))

        recommendations.append({
            "type": rec_type,
            "priority": priority,
            "group": group,
            "source_url": source_url,
            "target_url": target_url,
            "reason": reason,
            "expected_impact": f"+{delta} PR points for target",
            "source_pr_score": round(src_pr, 1),
            "target_pr_score": round(tgt_pr, 1),
            "source_outlinks": src_out,
            "source_classification": src.get("classification", ""),
            "target_classification": tgt.get("classification", ""),
            "content_relevance": round(relevance, 2),
        })
        source_rec_count[source_url] += 1
        target_rec_count[target_url] += 1
        existing_edges.add((source_url, target_url))
        return True

    # --- Strategy 1: Hoarder redistribution → Quick Wins ---
    for hoarder in hoarders[:30]:
        if len(recommendations) >= max_recommendations:
            break
        src_url = hoarder["url"]
        candidates = []
        for weak in weak_pages[:100]:
            if weak["url"] == src_url:
                continue
            rel = _content_relevance(src_url, weak["url"])
            # Priority score
            pr_norm = (hoarder["pagerank_score"] or 0) / max_pr
            deficit = 1 - ((weak["pagerank_score"] or 0) / max_pr)
            dimret = 1 / (1 + (hoarder["outbound_count"] or 0) / 50)
            score = 0.40 * pr_norm + 0.25 * deficit + 0.20 * rel + 0.15 * dimret
            candidates.append((weak, rel, score))

        candidates.sort(key=lambda x: x[2], reverse=True)
        for weak, rel, score in candidates[:5]:
            if len(recommendations) >= max_recommendations:
                break
            pr_label = f"PR: {hoarder['pagerank_score'] or 0:.0f}/100"
            out_label = f"{hoarder['outbound_count'] or 0} outbound links"
            _add_rec(
                "add_link",
                "high" if score > 0.5 else "medium",
                "quick_win",
                src_url,
                weak["url"],
                f"This high-authority page ({pr_label}) has only {out_label}. "
                f"Adding a link to this underlinked page would distribute equity "
                f"to content that currently has low internal authority.",
                rel,
            )

    # --- Strategy 2: Boost orphans from stars/hoarders → Strategic ---
    source_pool = (stars + hoarders)[:40]
    for orphan in orphans[:30]:
        if len(recommendations) >= max_recommendations:
            break
        best_src = None
        best_rel = -1.0
        for src in source_pool:
            if src["url"] == orphan["url"]:
                continue
            rel = _content_relevance(src["url"], orphan["url"])
            if rel > best_rel:
                best_rel = rel
                best_src = src
        if best_src:
            _add_rec(
                "add_link",
                "high",
                "strategic",
                best_src["url"],
                orphan["url"],
                f"This page is orphaned (0 internal inbound links) and invisible "
                f"to search crawlers. Adding a link from a high-authority page "
                f"would bring it into the site's link graph.",
                best_rel,
            )

    # --- Strategy 3: Waster review → Maintenance ---
    wasters = [p for p in tipr_pages if p["classification"] == QUADRANT_WASTER]
    wasters.sort(key=lambda p: p["outbound_count"] or 0, reverse=True)
    for waster in wasters[:15]:
        if len(recommendations) >= max_recommendations:
            break
        if (waster["outbound_count"] or 0) > 30:
            _add_rec(
                "review_outlinks",
                "medium",
                "maintenance",
                waster["url"],
                "",
                f"This page has {waster['outbound_count'] or 0} outbound links but a low "
                f"PageRank score of {waster['pagerank_score'] or 0:.0f}/100. Audit and "
                f"remove low-value outlinks to concentrate link equity on the most "
                f"important targets.",
                0.0,
            )

    return recommendations


# ---------------------------------------------------------------------------
# 1G. Main entry point — run full TIPR analysis
# ---------------------------------------------------------------------------

def run_tipr_analysis(
    graph_data: dict,
    nlp_analysis: dict | None = None,
    backlink_counts: dict[str, int] | None = None,
    max_recommendations: int = 50,
) -> dict | None:
    """Run the full TIPR analysis pipeline on link graph data.

    Parameters
    ----------
    graph_data : dict
        Must have "nodes" and "links" keys (from build_link_graph).
    nlp_analysis : dict, optional
        NLP entity data from the report for content relevance scoring.
    backlink_counts : dict, optional
        URL → external backlink count mapping (for future 3-signal mode).
    max_recommendations : int
        Cap on total recommendations.

    Returns
    -------
    dict or None
        Full TIPR analysis dict, or None if insufficient data.
    """
    nodes = graph_data.get("nodes") or []
    links = graph_data.get("links") or []

    if len(nodes) < 3 or len(links) < 1:
        logger.info("Skipping TIPR: insufficient graph data (%d nodes, %d links)", len(nodes), len(links))
        return None

    logger.info("Running TIPR analysis on %d nodes, %d links", len(nodes), len(links))

    # Build adjacency matrix
    A, url_to_idx, idx_to_url = build_adjacency_matrix(nodes, links)
    N = A.shape[0]
    if N < 3:
        return None

    # Compute PageRank and CheiRank
    pr_values = compute_pagerank(A)
    cr_values = compute_cheirank(A)

    # Optional backlink signal
    bl_array = None
    if backlink_counts:
        bl_array = np.array([backlink_counts.get(idx_to_url[i], 0) for i in range(N)], dtype=np.float64)

    # TIPR composite ranks
    tipr_ranks = compute_tipr_scores(pr_values, cr_values, bl_array)

    # Quadrant classification
    classifications = classify_pages(pr_values, cr_values)

    # Normalise to 0-100 display scores
    pr_scores = _normalise_scores(pr_values)
    cr_scores = _normalise_scores(cr_values)

    # Build per-node lookup for inbound/outbound counts
    node_lookup: dict[str, dict] = {n["id"]: n for n in nodes}

    # Assemble per-page TIPR data
    # NOTE: node fields from DataForSEO can be None even when the key exists,
    # so dict.get(key, default) is NOT sufficient — use `or 0` to coalesce.
    tipr_pages: list[dict] = []
    for i in range(N):
        url = idx_to_url[i]
        node = node_lookup.get(url, {})
        raw_depth = node.get("depth")
        tipr_pages.append({
            "url": url,
            "pagerank": float(pr_values[i]),
            "pagerank_score": round(float(pr_scores[i]), 1),
            "cheirank": float(cr_values[i]),
            "cheirank_score": round(float(cr_scores[i]), 1),
            "tipr_rank": int(tipr_ranks[i]),
            "tipr_score": round(float(tipr_ranks[i]), 1),
            "classification": classifications[i],
            "inbound_count": node.get("inbound") or 0,
            "outbound_count": node.get("outbound") or 0,
            "click_depth": raw_depth if raw_depth is not None else -1,
            "cluster": node.get("cluster") or _url_cluster(url),
        })

    # Sort by TIPR rank (best first)
    tipr_pages.sort(key=lambda p: p["tipr_rank"])

    # Summary statistics
    class_counts = defaultdict(int)
    for c in classifications:
        class_counts[c] += 1

    orphan_count = sum(1 for p in tipr_pages if (p["inbound_count"] or 0) == 0)
    deep_count = sum(1 for p in tipr_pages if (p["click_depth"] or 0) > 3)

    max_pr_page = tipr_pages[0] if tipr_pages else {}
    max_cr_idx = int(np.argmax(cr_scores)) if len(cr_scores) > 0 else 0
    max_cr_url = idx_to_url.get(max_cr_idx, "")

    top_hoarders = [p for p in tipr_pages if p["classification"] == QUADRANT_HOARDER][:10]
    top_wasters = [p for p in tipr_pages if p["classification"] == QUADRANT_WASTER][:10]

    summary = {
        "total_pages": N,
        "stars": class_counts.get(QUADRANT_STAR, 0),
        "hoarders": class_counts.get(QUADRANT_HOARDER, 0),
        "wasters": class_counts.get(QUADRANT_WASTER, 0),
        "dead_weight": class_counts.get(QUADRANT_DEAD_WEIGHT, 0),
        "avg_pagerank": round(float(pr_values.mean()), 6),
        "max_pagerank_url": max_pr_page.get("url", ""),
        "max_cheirank_url": max_cr_url,
        "top_hoarders": top_hoarders,
        "top_wasters": top_wasters,
        "orphan_count": orphan_count,
        "deep_pages_count": deep_count,
    }

    # Generate recommendations
    recommendations = generate_link_recommendations(
        nodes, links, tipr_pages,
        max_recommendations=max_recommendations,
        nlp_analysis=nlp_analysis,
    )

    signal_count = 3 if bl_array is not None else 2

    return {
        "version": "1.0",
        "signal_count": signal_count,
        "pages": tipr_pages,
        "summary": summary,
        "recommendations": recommendations,
    }
