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
import random
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
    """Classify every page into a TIPR quadrant using percentile ranks.

    Raw PageRank follows a power law — the homepage may have PR=0.15 while
    95 % of pages sit below PR=0.001.  A simple median threshold on raw
    values puts almost every page "above median" on both axes (= all Stars).

    Instead, convert to percentile ranks (0-100) and split at the 50th
    percentile.  This guarantees roughly 25 % of pages in each quadrant
    (with minor variation from ties), matching Kevin Indig's TIPR model
    which is a *relative ranking* system, not an absolute-threshold one.
    """
    n = len(pagerank_values)
    if n == 0:
        return []

    # rankdata gives 1-based ranks; dividing by n converts to 0-100 percentiles
    pr_pct = (rankdata(pagerank_values, method="average") / n) * 100
    cr_pct = (rankdata(cheirank_values, method="average") / n) * 100

    classifications: list[str] = []
    for pr_p, cr_p in zip(pr_pct, cr_pct):
        if pr_p >= 50 and cr_p >= 50:
            classifications.append(QUADRANT_STAR)
        elif pr_p >= 50 and cr_p < 50:
            classifications.append(QUADRANT_HOARDER)
        elif pr_p < 50 and cr_p >= 50:
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


def _short_path(url: str) -> str:
    """Return just the URL path (e.g. /blog/seo-guide) for readable output."""
    from urllib.parse import urlparse

    try:
        return urlparse(url).path or "/"
    except Exception:
        return url


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

    # Compute site-wide averages for contextual templates
    all_inbound = [p["inbound_count"] or 0 for p in tipr_pages]
    avg_inbound = sum(all_inbound) / max(len(all_inbound), 1)

    # Percentile rank lookup for readable "top X%" labels
    all_pr_scores = sorted(((p["pagerank_score"] or 0) for p in tipr_pages), reverse=True)
    pr_rank_cache: dict[str, int] = {}
    for p in tipr_pages:
        pr_val = p["pagerank_score"] or 0
        rank_idx = sum(1 for v in all_pr_scores if v > pr_val)
        pr_rank_cache[p["url"]] = max(1, int((rank_idx / max(len(all_pr_scores), 1)) * 100))

    recommendations: list[dict] = []
    source_rec_count: dict[str, int] = defaultdict(int)
    target_rec_count: dict[str, int] = defaultdict(int)

    # --- Varied impact text templates ---
    def _impact_text(tgt: dict, delta: int) -> str:
        tgt_cls = tgt.get("classification", "")
        tgt_path = _short_path(tgt.get("url", ""))
        options = [
            f"+{delta} PR points for {tgt_path}",
            f"Could increase {tgt_path}'s internal authority by ~{max(5, delta * 3)}%",
            f"Estimated +{delta} PageRank points, improving crawl priority for {tgt_path}",
        ]
        if tgt_cls == QUADRANT_DEAD_WEIGHT:
            options.append(f"Could move {tgt_path} from Dead Weight toward Waster or Star quadrant")
        if tgt_cls == QUADRANT_WASTER:
            options.append(f"Could move {tgt_path} from Waster to Star quadrant with added authority")
        return random.choice(options)

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
            "expected_impact": _impact_text(tgt, delta) if target_url else "Concentrate equity across fewer, higher-value links",
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

    # --- Hoarder redistribution templates ---
    _HOARDER_TEMPLATES = [
        lambda s, t: (
            f"**{_short_path(s['url'])}** receives {s['inbound_count'] or 0} inbound links "
            f"but only links out to {s['outbound_count'] or 0} pages. It's accumulating "
            f"authority without sharing it. Adding a contextual link to "
            f"**{_short_path(t['url'])}** (currently underlinked with only "
            f"{t['inbound_count'] or 0} inbound links) would redistribute equity to your "
            f"{_url_cluster(t['url']).strip('/')} content."
        ),
        lambda s, t: (
            f"Your **{_url_cluster(s['url']).strip('/')}** hub page "
            f"**{_short_path(s['url'])}** is one of your strongest pages "
            f"(PR: {s['pagerank_score'] or 0:.0f}/100) but acts as an equity bottleneck "
            f"with just {s['outbound_count'] or 0} outbound links. Link it to "
            f"**{_short_path(t['url'])}** to strengthen your "
            f"{_url_cluster(t['url']).strip('/')} section."
        ),
        lambda s, t: (
            f"**{_short_path(s['url'])}** ranks in your top "
            f"{pr_rank_cache.get(s['url'], 50)}% by internal authority but only passes "
            f"equity to {s['outbound_count'] or 0} pages. Adding a link to the underserved "
            f"**{_short_path(t['url'])}** would improve its discoverability and distribute "
            f"link value more efficiently."
        ),
        lambda s, t: (
            f"High-authority page **{_short_path(s['url'])}** "
            f"(PR: {s['pagerank_score'] or 0:.0f}) is hoarding equity — it receives "
            f"{s['inbound_count'] or 0} links but sends only {s['outbound_count'] or 0}. "
            f"Connect it to **{_short_path(t['url'])}** in your "
            f"{_url_cluster(t['url']).strip('/')} cluster to balance equity flow."
        ),
        lambda s, t: (
            f"Navigation and content pages link heavily to "
            f"**{_short_path(s['url'])}**, giving it strong authority "
            f"({s['inbound_count'] or 0} inbound links). But it's a dead end with only "
            f"{s['outbound_count'] or 0} outbound links. Adding a link to "
            f"**{_short_path(t['url'])}** would pass some of that accumulated value to a "
            f"page that needs it."
        ),
    ]

    # --- Orphan / weak page boosting templates ---
    _ORPHAN_TEMPLATES = [
        lambda s, t: (
            f"**{_short_path(t['url'])}** is an orphan page with zero internal links "
            f"pointing to it. Search engines may struggle to discover it. Add a link from "
            f"**{_short_path(s['url'])}** (one of your strongest pages) to ensure it gets "
            f"crawled and indexed."
        ),
        lambda s, t: (
            f"**{_short_path(t['url'])}** in your "
            f"{_url_cluster(t['url']).strip('/')} section has only "
            f"{t['inbound_count'] or 0} inbound links — well below your site average of "
            f"{avg_inbound:.0f}. A link from the high-authority "
            f"**{_short_path(s['url'])}** would significantly boost its visibility."
        ),
        lambda s, t: (
            f"Your {_url_cluster(t['url']).strip('/')} content page "
            f"**{_short_path(t['url'])}** is essentially invisible to search engines with "
            f"just {t['inbound_count'] or 0} internal links. **{_short_path(s['url'])}** "
            f"is a natural linking candidate given its strong authority "
            f"(PR: {s['pagerank_score'] or 0:.0f}) and related content."
        ),
        lambda s, t: (
            f"**{_short_path(t['url'])}** sits at click depth "
            f"{t.get('depth') if t.get('depth') is not None else '∞'} with only "
            f"{t['inbound_count'] or 0} inbound links. Adding a link from "
            f"**{_short_path(s['url'])}** would shorten the click path and improve crawl "
            f"efficiency."
        ),
        lambda s, t: (
            f"Content at **{_short_path(t['url'])}** is stranded — "
            f"{t['inbound_count'] or 0} inbound links means minimal equity flow. "
            f"**{_short_path(s['url'])}** has authority to spare "
            f"(PR: {s['pagerank_score'] or 0:.0f}, {s['outbound_count'] or 0} current "
            f"outlinks). This is a high-impact, low-effort connection."
        ),
    ]

    # --- Waster pruning templates ---
    _WASTER_TEMPLATES = [
        lambda w: (
            f"**{_short_path(w['url'])}** has {w['outbound_count'] or 0} outbound links — "
            f"well above the recommended maximum of 100. Each link passes diminishing "
            f"equity. Review and remove links to low-priority pages to concentrate "
            f"authority on your most important content."
        ),
        lambda w: (
            f"With {w['outbound_count'] or 0} outgoing links, "
            f"**{_short_path(w['url'])}** is spreading its "
            f"PR: {w['pagerank_score'] or 0:.0f} authority extremely thin. Each link only "
            f"passes ~{max(0.1, (w['pagerank_score'] or 0) / max(w['outbound_count'] or 1, 1)):.1f} "
            f"equity. Consider consolidating to your top 50–75 most important link targets."
        ),
        lambda w: (
            f"**{_short_path(w['url'])}** links to {w['outbound_count'] or 0} pages but "
            f"only receives {w['inbound_count'] or 0} inbound links. It's giving away far "
            f"more authority than it receives. Audit its outbound links and remove "
            f"connections to non-essential pages like legal boilerplate, outdated content, "
            f"or redundant navigation."
        ),
    ]

    # Track which template index was last used per strategy to cycle through them
    hoarder_tmpl_idx = 0
    orphan_tmpl_idx = 0
    waster_tmpl_idx = 0

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
            reason = _HOARDER_TEMPLATES[hoarder_tmpl_idx % len(_HOARDER_TEMPLATES)](hoarder, weak)
            hoarder_tmpl_idx += 1
            _add_rec(
                "add_link",
                "high" if score > 0.5 else "medium",
                "quick_win",
                src_url,
                weak["url"],
                reason,
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
            reason = _ORPHAN_TEMPLATES[orphan_tmpl_idx % len(_ORPHAN_TEMPLATES)](best_src, orphan)
            orphan_tmpl_idx += 1
            _add_rec(
                "add_link",
                "high",
                "strategic",
                best_src["url"],
                orphan["url"],
                reason,
                best_rel,
            )

    # --- Strategy 3: Waster review → Maintenance ---
    wasters = [p for p in tipr_pages if p["classification"] == QUADRANT_WASTER]
    wasters.sort(key=lambda p: p["outbound_count"] or 0, reverse=True)
    for waster in wasters[:15]:
        if len(recommendations) >= max_recommendations:
            break
        if (waster["outbound_count"] or 0) > 30:
            reason = _WASTER_TEMPLATES[waster_tmpl_idx % len(_WASTER_TEMPLATES)](waster)
            waster_tmpl_idx += 1
            _add_rec(
                "review_outlinks",
                "medium",
                "maintenance",
                waster["url"],
                "",
                reason,
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

    # Derive in/out degrees directly from the adjacency matrix — this is the
    # only source guaranteed to agree with the recommendations engine. Node
    # metadata counts can drift (e.g. when a serialized graph omits per-node
    # stats) and produced a bug where every recommendation read "0 outbound".
    out_degrees = np.asarray(A.sum(axis=1)).flatten().astype(int)
    in_degrees = np.asarray(A.sum(axis=0)).flatten().astype(int)

    # Assemble per-page TIPR data
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
            "inbound_count": int(in_degrees[i]),
            "outbound_count": int(out_degrees[i]),
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
