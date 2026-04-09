"""
Semantic Topic Clustering Engine
================================

Groups pages by what they're actually about (not URL directory prefix).
Uses a hybrid feature matrix from multiple signals:
  - Google NLP entities with salience scores (strongest signal)
  - Page title TF-IDF
  - Page content TF-IDF (from Trafilatura or DataForSEO meta)
  - URL path tokens (weak structural signal)
  - NLP category classifications

Cluster count is driven by the website's actual services/products/topics,
not by arbitrary formulas like sqrt(N/2).

Pure Python module: depends on scikit-learn, scipy, numpy (all installed).
"""

import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import urlparse

import numpy as np
from scipy import sparse
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signal weights for the hybrid feature matrix
# ---------------------------------------------------------------------------

SIGNAL_WEIGHTS = {
    "entities": 0.40,
    "title_tfidf": 0.30,
    "content_tfidf": 0.15,
    "url_tokens": 0.10,
    "nlp_categories": 0.05,
}

MIN_PAGES_FOR_CLUSTERING = 20
MIN_CLUSTERS = 3
MAX_CLUSTERS = 30
SVD_COMPONENTS = 100

CLUSTER_COLORS = [
    "#6366F1", "#22D3EE", "#F472B6", "#34D399", "#FBBF24",
    "#A78BFA", "#FB923C", "#60A5FA", "#4ADE80", "#F87171",
    "#818CF8", "#2DD4BF",
]


# ---------------------------------------------------------------------------
# 1A. Feature Matrix Construction
# ---------------------------------------------------------------------------


def _extract_url_text(url: str) -> str:
    """Convert URL path into space-separated tokens."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    tokens = re.split(r"[/\-_.]", path)
    return " ".join(t.lower() for t in tokens if len(t) > 1 and not t.isdigit())


def _build_entity_matrix(
    pages: List[Dict[str, Any]],
) -> sparse.csr_matrix:
    """Build sparse matrix from entity name -> salience dicts."""
    entity_dicts = []
    for page in pages:
        entities = page.get("entities") or []
        d: Dict[str, float] = {}
        for ent in entities[:50]:
            name = ent.get("name", "").lower().strip()
            sal = ent.get("salience", 0.0)
            if name and sal >= 0.01:
                d[name] = sal
        entity_dicts.append(d)

    if not any(entity_dicts):
        return sparse.csr_matrix((len(pages), 0))

    vec = DictVectorizer(sparse=True)
    mat = vec.fit_transform(entity_dicts)
    return normalize(mat, norm="l2")


def _build_title_tfidf(pages: List[Dict[str, Any]]) -> sparse.csr_matrix:
    """TF-IDF on page titles (repeated twice for emphasis)."""
    titles = []
    for page in pages:
        title = page.get("title", "") or ""
        titles.append(f"{title} {title}")  # double emphasis

    vec = TfidfVectorizer(
        max_features=500,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
    )
    try:
        mat = vec.fit_transform(titles)
    except ValueError:
        return sparse.csr_matrix((len(pages), 0))
    return normalize(mat, norm="l2")


def _build_content_tfidf(pages: List[Dict[str, Any]]) -> sparse.csr_matrix:
    """TF-IDF on first 2000 words of extracted content."""
    texts = []
    for page in pages:
        text = page.get("content", "") or page.get("meta_description", "") or ""
        words = text.split()[:2000]
        texts.append(" ".join(words))

    vec = TfidfVectorizer(
        max_features=1000,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
    )
    try:
        mat = vec.fit_transform(texts)
    except ValueError:
        return sparse.csr_matrix((len(pages), 0))
    return normalize(mat, norm="l2")


def _build_url_tfidf(pages: List[Dict[str, Any]]) -> sparse.csr_matrix:
    """TF-IDF on URL path tokens."""
    url_texts = [_extract_url_text(p.get("url", "")) for p in pages]

    vec = TfidfVectorizer(
        max_features=200,
        ngram_range=(1, 1),
        stop_words="english",
    )
    try:
        mat = vec.fit_transform(url_texts)
    except ValueError:
        return sparse.csr_matrix((len(pages), 0))
    return normalize(mat, norm="l2")


def _build_category_matrix(pages: List[Dict[str, Any]]) -> sparse.csr_matrix:
    """Build matrix from NLP category path tokens."""
    cat_dicts = []
    for page in pages:
        cat = page.get("nlp_category", "") or ""
        tokens = [t.lower().strip() for t in cat.split("/") if t.strip()]
        d = {t: 1.0 for t in tokens}
        cat_dicts.append(d)

    if not any(cat_dicts):
        return sparse.csr_matrix((len(pages), 0))

    vec = DictVectorizer(sparse=True)
    mat = vec.fit_transform(cat_dicts)
    return normalize(mat, norm="l2")


def build_feature_matrix(pages: List[Dict[str, Any]]) -> sparse.csr_matrix:
    """Build the combined hybrid feature matrix from all signals."""
    n_pages = len(pages)
    matrices = []

    # Entity vectors
    ent_mat = _build_entity_matrix(pages)
    if ent_mat.shape[1] > 0:
        matrices.append(ent_mat * SIGNAL_WEIGHTS["entities"])
    else:
        logger.info("No entity data available for clustering")

    # Title TF-IDF
    title_mat = _build_title_tfidf(pages)
    if title_mat.shape[1] > 0:
        matrices.append(title_mat * SIGNAL_WEIGHTS["title_tfidf"])

    # Content TF-IDF
    content_mat = _build_content_tfidf(pages)
    if content_mat.shape[1] > 0:
        matrices.append(content_mat * SIGNAL_WEIGHTS["content_tfidf"])

    # URL tokens
    url_mat = _build_url_tfidf(pages)
    if url_mat.shape[1] > 0:
        matrices.append(url_mat * SIGNAL_WEIGHTS["url_tokens"])

    # NLP categories
    cat_mat = _build_category_matrix(pages)
    if cat_mat.shape[1] > 0:
        matrices.append(cat_mat * SIGNAL_WEIGHTS["nlp_categories"])

    if not matrices:
        return sparse.csr_matrix((n_pages, 0))

    combined = sparse.hstack(matrices, format="csr")
    combined = normalize(combined, norm="l2")

    # Dimensionality reduction if too many features
    if combined.shape[1] > SVD_COMPONENTS * 2:
        n_components = min(SVD_COMPONENTS, combined.shape[0] - 1, combined.shape[1] - 1)
        if n_components >= 2:
            svd = TruncatedSVD(n_components=n_components, random_state=42)
            reduced = svd.fit_transform(combined)
            combined = sparse.csr_matrix(normalize(reduced, norm="l2"))

    return combined


# ---------------------------------------------------------------------------
# 1B. Service/Product-Driven Cluster Detection
# ---------------------------------------------------------------------------


def _extract_anchor_entities(
    pages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Find entities that appear on 3+ pages with meaningful salience.
    These represent the site's core topics."""
    entity_pages: Dict[str, List[float]] = defaultdict(list)
    entity_types: Dict[str, str] = {}

    for page in pages:
        entities = page.get("entities") or []
        seen_on_page: Set[str] = set()
        for ent in entities[:50]:
            name = ent.get("name", "").lower().strip()
            sal = ent.get("salience", 0.0)
            etype = ent.get("entity_type", "OTHER")
            if name and sal >= 0.01 and name not in seen_on_page:
                entity_pages[name].append(sal)
                entity_types[name] = etype
                seen_on_page.add(name)

    anchors = []
    for name, saliences in entity_pages.items():
        if len(saliences) >= 3 and np.mean(saliences) > 0.05:
            anchors.append({
                "name": name,
                "page_count": len(saliences),
                "avg_salience": float(np.mean(saliences)),
                "max_salience": float(max(saliences)),
                "entity_type": entity_types[name],
            })

    anchors.sort(key=lambda x: x["page_count"] * x["avg_salience"], reverse=True)
    return anchors


def _merge_cooccurring_entities(
    anchors: List[Dict[str, Any]],
    pages: List[Dict[str, Any]],
    cooccurrence_threshold: float = 0.6,
) -> List[List[Dict[str, Any]]]:
    """Merge anchor entities that co-occur on >60% of their pages into topic seeds."""
    if not anchors:
        return []

    # Build page sets for each anchor entity
    entity_page_sets: Dict[str, Set[int]] = defaultdict(set)
    for page_idx, page in enumerate(pages):
        entities = page.get("entities") or []
        page_entity_names = {
            e.get("name", "").lower().strip()
            for e in entities[:50]
            if e.get("salience", 0) >= 0.01
        }
        for anchor in anchors:
            if anchor["name"] in page_entity_names:
                entity_page_sets[anchor["name"]].add(page_idx)

    # Build co-occurrence groups using union-find
    anchor_names = [a["name"] for a in anchors]
    parent = {name: name for name in anchor_names}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i, a in enumerate(anchor_names):
        for b in anchor_names[i + 1:]:
            pages_a = entity_page_sets.get(a, set())
            pages_b = entity_page_sets.get(b, set())
            if not pages_a or not pages_b:
                continue
            overlap = len(pages_a & pages_b)
            min_size = min(len(pages_a), len(pages_b))
            if min_size > 0 and overlap / min_size > cooccurrence_threshold:
                union(a, b)

    # Group by root
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    anchor_map = {a["name"]: a for a in anchors}
    for name in anchor_names:
        root = find(name)
        groups[root].append(anchor_map[name])

    # Sort groups by total signal strength
    result = sorted(
        groups.values(),
        key=lambda g: sum(a["page_count"] * a["avg_salience"] for a in g),
        reverse=True,
    )
    return result


def _detect_title_ngrams(
    pages: List[Dict[str, Any]],
    min_count: int = 3,
) -> List[Tuple[str, int]]:
    """Extract common 2-gram and 3-gram phrases from page titles."""
    from collections import Counter

    ngram_counts: Counter = Counter()
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "this", "that", "these",
        "those", "it", "its", "from", "how", "what", "why", "when", "where",
        "who", "which", "your", "our", "my", "his", "her", "their", "all",
        "each", "every", "both", "few", "more", "most", "other", "some", "such",
        "no", "not", "only", "own", "same", "so", "than", "too", "very",
    }

    for page in pages:
        title = (page.get("title") or "").lower().strip()
        words = re.findall(r"[a-z]+", title)
        words = [w for w in words if w not in stop_words and len(w) > 2]
        for n in (2, 3):
            for i in range(len(words) - n + 1):
                gram = " ".join(words[i:i + n])
                ngram_counts[gram] += 1

    return [
        (gram, count) for gram, count in ngram_counts.most_common(50)
        if count >= min_count
    ]


def _detect_category_branches(
    pages: List[Dict[str, Any]],
) -> List[str]:
    """Find distinct top-level NLP category branches."""
    branch_counts: Dict[str, int] = defaultdict(int)
    for page in pages:
        cat = page.get("nlp_category", "") or ""
        parts = [p.strip() for p in cat.split("/") if p.strip()]
        if parts:
            branch_counts[parts[0]] += 1

    # Only count branches with 2+ pages
    return [
        branch for branch, count in branch_counts.items()
        if count >= 2
    ]


def detect_optimal_k(
    pages: List[Dict[str, Any]],
    feature_matrix: sparse.csr_matrix,
) -> Tuple[int, str]:
    """Detect optimal number of clusters based on site services/products.

    Returns (k, detection_method) where detection_method is either
    'service_driven' or 'fallback_silhouette'.
    """
    n_pages = len(pages)

    # Signal 1: Anchor entity groups
    anchors = _extract_anchor_entities(pages)
    entity_groups = _merge_cooccurring_entities(anchors, pages)
    n_entity_groups = len(entity_groups)

    # Signal 2: Title n-gram themes
    title_ngrams = _detect_title_ngrams(pages)
    # Deduplicate overlapping n-grams (keep longer ones)
    ngram_themes: List[str] = []
    for gram, _count in title_ngrams[:20]:
        if not any(gram in existing or existing in gram for existing in ngram_themes):
            ngram_themes.append(gram)
    n_title_themes = min(len(ngram_themes), 15)

    # Signal 3: NLP category branches
    category_branches = _detect_category_branches(pages)
    n_category_branches = len(category_branches)

    logger.info(
        f"Cluster detection signals: {n_entity_groups} entity groups, "
        f"{n_title_themes} title themes, {n_category_branches} category branches"
    )

    # Service-driven K: take the higher of entity groups and category branches
    service_k = max(n_entity_groups, n_category_branches)

    if service_k >= MIN_CLUSTERS:
        k = min(max(service_k, MIN_CLUSTERS), MAX_CLUSTERS)
        # Don't exceed ~1/3 of pages
        k = min(k, max(MIN_CLUSTERS, n_pages // 3))

        # Validate with silhouette — try K, K-1, K+1
        best_k = k
        best_score = -1.0
        for candidate_k in [k - 1, k, k + 1]:
            if candidate_k < MIN_CLUSTERS or candidate_k > MAX_CLUSTERS:
                continue
            if candidate_k >= n_pages:
                continue
            try:
                km = MiniBatchKMeans(
                    n_clusters=candidate_k,
                    random_state=42,
                    batch_size=min(1024, n_pages),
                    n_init=3,
                )
                labels = km.fit_predict(feature_matrix)
                score = silhouette_score(
                    feature_matrix, labels, sample_size=min(2000, n_pages)
                )
                if score > best_score:
                    best_score = score
                    best_k = candidate_k
            except Exception:
                continue

        logger.info(f"Service-driven K={best_k} (silhouette={best_score:.3f})")
        return best_k, "service_driven"

    # Fallback: scan a range and pick best silhouette
    logger.info("Falling back to silhouette-optimized K selection")
    max_k = min(MAX_CLUSTERS, max(MIN_CLUSTERS, int(np.sqrt(n_pages / 2)) + 5))
    max_k = min(max_k, n_pages - 1)
    best_k = MIN_CLUSTERS
    best_score = -1.0

    for candidate_k in range(MIN_CLUSTERS, max_k + 1):
        try:
            km = MiniBatchKMeans(
                n_clusters=candidate_k,
                random_state=42,
                batch_size=min(1024, n_pages),
                n_init=3,
            )
            labels = km.fit_predict(feature_matrix)
            score = silhouette_score(
                feature_matrix, labels, sample_size=min(2000, n_pages)
            )
            if score > best_score:
                best_score = score
                best_k = candidate_k
        except Exception:
            continue

    logger.info(f"Fallback K={best_k} (silhouette={best_score:.3f})")
    return best_k, "fallback_silhouette"


# ---------------------------------------------------------------------------
# 1D. Cluster Labeling with c-TF-IDF
# ---------------------------------------------------------------------------


def _generate_cluster_labels(
    pages: List[Dict[str, Any]],
    labels: np.ndarray,
    n_clusters: int,
) -> List[str]:
    """Generate human-readable cluster labels using c-TF-IDF + top entities."""
    # Build per-cluster mega-documents from titles + content snippets
    cluster_docs = [""] * n_clusters
    cluster_entities: List[Dict[str, float]] = [defaultdict(float) for _ in range(n_clusters)]

    for page, label in zip(pages, labels):
        if label < 0 or label >= n_clusters:
            continue
        title = page.get("title", "") or ""
        content = page.get("content", "") or page.get("meta_description", "") or ""
        snippet = " ".join(content.split()[:300])
        cluster_docs[label] += f" {title} {title} {snippet}"

        for ent in (page.get("entities") or [])[:30]:
            name = ent.get("name", "").strip()
            sal = ent.get("salience", 0.0)
            if name and sal >= 0.01:
                cluster_entities[label][name] += sal

    # c-TF-IDF: term frequency within cluster × inverse frequency across clusters
    vec = TfidfVectorizer(
        max_features=500,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
    )
    try:
        tfidf_matrix = vec.fit_transform(cluster_docs)
        feature_names = vec.get_feature_names_out()
    except ValueError:
        return [f"Cluster {i}" for i in range(n_clusters)]

    labels_list = []
    for cluster_idx in range(n_clusters):
        # Get top TF-IDF terms
        row = tfidf_matrix[cluster_idx].toarray().flatten()
        top_term_indices = row.argsort()[::-1][:10]
        top_terms = [
            (feature_names[i], float(row[i]))
            for i in top_term_indices
            if row[i] > 0
        ]

        # Get top entities
        ent_dict = cluster_entities[cluster_idx]
        top_ents = sorted(ent_dict.items(), key=lambda x: x[1], reverse=True)[:5]

        # Combine: prefer entity names (more semantically meaningful), fill with terms
        label_parts: List[str] = []
        seen_lower: Set[str] = set()

        for ent_name, _sal in top_ents:
            clean = ent_name.strip()
            if clean.lower() not in seen_lower and len(clean) > 1:
                label_parts.append(clean)
                seen_lower.add(clean.lower())
            if len(label_parts) >= 3:
                break

        for term, _score in top_terms:
            clean = term.strip().title()
            if clean.lower() not in seen_lower and len(clean) > 2:
                label_parts.append(clean)
                seen_lower.add(clean.lower())
            if len(label_parts) >= 4:
                break

        if label_parts:
            labels_list.append(" \u00b7 ".join(label_parts[:4]))
        else:
            labels_list.append(f"Cluster {cluster_idx}")

    return labels_list


# ---------------------------------------------------------------------------
# 1E. Pillar Page Identification
# ---------------------------------------------------------------------------


def _identify_pillar_page(
    cluster_pages: List[Dict[str, Any]],
    cluster_entity_set: Set[str],
    link_index: Dict[str, Set[str]],
) -> Dict[str, Any] | None:
    """Score every page in a cluster to find the pillar (hub) page."""
    if not cluster_pages:
        return None

    cluster_urls = {p["url"] for p in cluster_pages}
    scores = []

    # Compute normalization maxes
    max_wc = max((p.get("word_count", 0) or 0) for p in cluster_pages) or 1
    max_inlinks = 1

    for page in cluster_pages:
        url = page["url"]
        inlinks_from_cluster = sum(
            1 for src in cluster_urls
            if src != url and url in link_index.get(src, set())
        )
        max_inlinks = max(max_inlinks, inlinks_from_cluster)

    for page in cluster_pages:
        url = page["url"]
        wc = page.get("word_count", 0) or 0
        title = page.get("title", "") or ""

        # Inbound links from cluster peers
        inlinks_from_cluster = sum(
            1 for src in cluster_urls
            if src != url and url in link_index.get(src, set())
        )

        # Entity coverage breadth
        page_entities = {
            e.get("name", "").lower().strip()
            for e in (page.get("entities") or [])[:50]
            if e.get("salience", 0) >= 0.01
        }
        if cluster_entity_set:
            entity_coverage = len(page_entities & cluster_entity_set) / len(cluster_entity_set)
        else:
            entity_coverage = 0.0

        # Title generality (shorter = broader)
        title_words = len(title.split())
        title_generality = max(0, 1.0 - title_words / 15.0)

        # URL depth (fewer segments = more likely pillar)
        parsed = urlparse(url)
        segments = [s for s in parsed.path.strip("/").split("/") if s]
        url_depth_bonus = max(0, 1.0 - len(segments) / 5.0)

        # TIPR PageRank bonus
        pr_score = page.get("pagerank_score", 0) or 0
        pr_bonus = min(pr_score / 100.0, 1.0)

        # Click depth bonus (shallower = more important)
        click_depth = page.get("click_depth", 3)
        if click_depth < 0:
            click_depth = 5
        depth_bonus = max(0, 1.0 - click_depth / 5.0)

        pillar_score = (
            0.15 * (wc / max_wc) +
            0.25 * (inlinks_from_cluster / max_inlinks) +
            0.25 * entity_coverage +
            0.10 * title_generality +
            0.10 * url_depth_bonus +
            0.10 * pr_bonus +
            0.05 * depth_bonus
        )

        scores.append({
            "url": url,
            "title": title,
            "score": round(pillar_score, 3),
            "word_count": wc,
            "inlinks_from_cluster": inlinks_from_cluster,
            "entity_coverage": round(entity_coverage, 3),
        })

    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[0] if scores else None


# ---------------------------------------------------------------------------
# 1F. Internal Link Validation
# ---------------------------------------------------------------------------


def _validate_cluster_links(
    cluster_pages: List[Dict[str, Any]],
    pillar_url: str,
    link_index: Dict[str, Set[str]],
) -> Dict[str, Any]:
    """Check linking between cluster pages and the pillar page."""
    pages_linking_to_pillar = 0
    pillar_links_to_pages = 0
    bidirectional = 0
    unlinked = 0
    pillar_targets = link_index.get(pillar_url, set())

    page_details = []
    for page in cluster_pages:
        url = page["url"]
        if url == pillar_url:
            continue

        links_to_pillar = pillar_url in link_index.get(url, set())
        pillar_links_here = url in pillar_targets

        if links_to_pillar:
            pages_linking_to_pillar += 1
        if pillar_links_here:
            pillar_links_to_pages += 1
        if links_to_pillar and pillar_links_here:
            bidirectional += 1
        if not links_to_pillar and not pillar_links_here:
            unlinked += 1

        page_details.append({
            "url": url,
            "title": page.get("title", ""),
            "links_to_pillar": links_to_pillar,
            "pillar_links_here": pillar_links_here,
            "word_count": page.get("word_count", 0) or 0,
        })

    non_pillar_count = max(1, len(cluster_pages) - 1)
    return {
        "pages_linking_to_pillar": pages_linking_to_pillar,
        "pillar_links_to_pages": pillar_links_to_pages,
        "bidirectional": bidirectional,
        "unlinked": unlinked,
        "health_pct": round(pages_linking_to_pillar / non_pillar_count * 100),
        "page_details": page_details,
    }


# ---------------------------------------------------------------------------
# 1G. Content Gap Detection
# ---------------------------------------------------------------------------


def _detect_content_gaps(
    cluster_pages: List[Dict[str, Any]],
    pillar_url: str,
) -> List[Dict[str, Any]]:
    """Identify entities present in the cluster but underrepresented."""
    entity_coverage: Dict[str, List[str]] = defaultdict(list)

    for page in cluster_pages:
        url = page["url"]
        for ent in (page.get("entities") or [])[:30]:
            name = ent.get("name", "").strip()
            sal = ent.get("salience", 0.0)
            if name and sal >= 0.02:
                entity_coverage[name].append(url)

    total = len(cluster_pages)
    gaps = []
    for entity_name, covered_urls in entity_coverage.items():
        mentioned_count = len(covered_urls)
        # Entity exists in cluster but on fewer than 15% of pages
        if mentioned_count <= max(2, total * 0.15) and mentioned_count >= 1:
            gaps.append({
                "entity": entity_name,
                "mentioned_in": mentioned_count,
                "total_pages": total,
                "in_pillar": pillar_url in covered_urls,
            })

    # Sort by least-covered first
    gaps.sort(key=lambda x: x["mentioned_in"])
    return gaps[:20]


# ---------------------------------------------------------------------------
# 1H. Link Recommendations from Clusters
# ---------------------------------------------------------------------------


def _generate_link_recommendations(
    clusters: List[Dict[str, Any]],
    link_index: Dict[str, Set[str]],
) -> List[Dict[str, Any]]:
    """Generate actionable link recommendations from cluster analysis."""
    recommendations = []

    for cluster in clusters:
        pillar = cluster.get("pillar")
        if not pillar:
            continue
        pillar_url = pillar["url"]
        link_health = cluster.get("link_health", {})

        for page_detail in link_health.get("page_details", []):
            url = page_detail["url"]
            title = page_detail.get("title", "")

            if not page_detail.get("links_to_pillar"):
                recommendations.append({
                    "type": "missing_pillar_link",
                    "source_url": url,
                    "target_url": pillar_url,
                    "cluster_label": cluster["label"],
                    "reason": (
                        f'This page ("{title}") is in the "{cluster["label"]}" cluster '
                        f"but doesn't link to its pillar page. Adding a link strengthens topical authority."
                    ),
                })

            if not page_detail.get("pillar_links_here"):
                recommendations.append({
                    "type": "missing_pillar_backlink",
                    "source_url": pillar_url,
                    "target_url": url,
                    "cluster_label": cluster["label"],
                    "reason": (
                        f'The pillar page for "{cluster["label"]}" doesn\'t link to '
                        f'"{title}". Adding this link distributes authority to supporting content.'
                    ),
                })

    # Limit total recommendations
    # Prioritize missing_pillar_link (most actionable)
    recommendations.sort(
        key=lambda r: 0 if r["type"] == "missing_pillar_link" else 1
    )
    return recommendations[:100]


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


def run_topic_clustering(
    pages: List[Dict[str, Any]],
    links: List[Dict[str, Any]] | None = None,
    n_clusters: int | None = None,
) -> Dict[str, Any] | None:
    """Full semantic topic clustering pipeline.

    Args:
        pages: List of page dicts, each with:
            - url (required)
            - title, content, meta_description, word_count
            - entities: [{name, salience, entity_type}]
            - nlp_category: Google NLP classification string
            - pagerank_score, click_depth (optional, from TIPR)
        links: List of link dicts [{source, target}] for link validation.
        n_clusters: Override cluster count (auto-detect if None).

    Returns:
        Complete semantic cluster analysis dict, or None if too few pages.
    """
    n_pages = len(pages)

    if n_pages < MIN_PAGES_FOR_CLUSTERING:
        logger.info(
            f"Only {n_pages} pages — below {MIN_PAGES_FOR_CLUSTERING} minimum for clustering"
        )
        return None

    logger.info(f"Running semantic topic clustering on {n_pages} pages")

    # Check data coverage
    pages_with_entities = sum(1 for p in pages if p.get("entities"))
    pages_with_content = sum(
        1 for p in pages
        if p.get("content") or p.get("meta_description")
    )
    logger.info(
        f"Data coverage: {pages_with_entities}/{n_pages} have entities, "
        f"{pages_with_content}/{n_pages} have content/meta"
    )

    # 1. Build feature matrix
    feature_matrix = build_feature_matrix(pages)
    if feature_matrix.shape[1] == 0:
        logger.warning("Feature matrix is empty — cannot cluster")
        return None

    # 2. Detect optimal K
    if n_clusters is None:
        k, detection_method = detect_optimal_k(pages, feature_matrix)
    else:
        k = min(max(n_clusters, MIN_CLUSTERS), min(MAX_CLUSTERS, n_pages - 1))
        detection_method = "manual"

    # 3. Run clustering
    km = MiniBatchKMeans(
        n_clusters=k,
        random_state=42,
        batch_size=min(1024, n_pages),
        n_init=5,
    )
    cluster_labels = km.fit_predict(feature_matrix)

    # Compute silhouette score
    try:
        sil_score = float(silhouette_score(
            feature_matrix, cluster_labels,
            sample_size=min(2000, n_pages),
        ))
    except Exception:
        sil_score = 0.0

    # 4. Generate cluster labels
    label_names = _generate_cluster_labels(pages, cluster_labels, k)

    # 5. Build link index for validation
    link_index: Dict[str, Set[str]] = defaultdict(set)
    if links:
        for link in links:
            src = link.get("source", "")
            tgt = link.get("target", "")
            if src and tgt:
                link_index[src].add(tgt)

    # 6. Build cluster analysis
    cluster_results = []
    uncategorized_pages = []

    for cluster_idx in range(k):
        mask = cluster_labels == cluster_idx
        cluster_pages = [pages[i] for i in range(n_pages) if mask[i]]

        if not cluster_pages:
            continue

        # Collect cluster entities
        cluster_entity_set: Set[str] = set()
        cluster_top_entities: Dict[str, float] = defaultdict(float)
        for page in cluster_pages:
            for ent in (page.get("entities") or [])[:30]:
                name = ent.get("name", "").lower().strip()
                sal = ent.get("salience", 0.0)
                if name and sal >= 0.01:
                    cluster_entity_set.add(name)
                    cluster_top_entities[name] += sal

        # Top entities for this cluster
        sorted_ents = sorted(
            cluster_top_entities.items(), key=lambda x: x[1], reverse=True
        )[:10]
        top_entities = [
            [name, round(score, 3)] for name, score in sorted_ents
        ]

        # Identify pillar page
        pillar = _identify_pillar_page(cluster_pages, cluster_entity_set, link_index)

        # Link validation
        link_health = {}
        page_details_for_table = []
        if pillar and links:
            link_result = _validate_cluster_links(cluster_pages, pillar["url"], link_index)
            link_health = {
                "pages_linking_to_pillar": link_result["pages_linking_to_pillar"],
                "pillar_links_to_pages": link_result["pillar_links_to_pages"],
                "bidirectional": link_result["bidirectional"],
                "unlinked": link_result["unlinked"],
                "health_pct": link_result["health_pct"],
            }
            page_details_for_table = link_result["page_details"]

        # Content gap detection
        content_gaps = _detect_content_gaps(
            cluster_pages,
            pillar["url"] if pillar else "",
        )

        # Per-page entity overlap with cluster
        page_list = []
        for page in cluster_pages:
            url = page["url"]
            page_ents = {
                e.get("name", "").lower().strip()
                for e in (page.get("entities") or [])[:30]
                if e.get("salience", 0) >= 0.01
            }
            if cluster_entity_set:
                overlap = len(page_ents & cluster_entity_set) / len(cluster_entity_set)
            else:
                overlap = 0.0

            # Find link details for this page
            detail_match = next(
                (d for d in page_details_for_table if d["url"] == url), None
            )

            page_entry = {
                "url": url,
                "title": page.get("title", ""),
                "entity_overlap": round(overlap, 3),
                "word_count": page.get("word_count", 0) or 0,
                "entity_data": bool(page.get("entities")),
                "links_to_pillar": detail_match["links_to_pillar"] if detail_match else None,
                "pillar_links_here": detail_match["pillar_links_here"] if detail_match else None,
            }
            page_list.append(page_entry)

        # Sort pages by entity overlap descending
        page_list.sort(key=lambda x: x["entity_overlap"], reverse=True)

        # Compute per-cluster silhouette
        cluster_indices = [i for i in range(n_pages) if mask[i]]
        per_cluster_sil = 0.0
        if len(cluster_indices) >= 2:
            try:
                from sklearn.metrics import silhouette_samples
                all_sil = silhouette_samples(feature_matrix, cluster_labels)
                per_cluster_sil = float(np.mean(all_sil[mask]))
            except Exception:
                pass

        # c-TF-IDF top terms for this cluster
        # (already captured in label generation, extract here)
        cluster_result = {
            "id": cluster_idx,
            "label": label_names[cluster_idx],
            "color": CLUSTER_COLORS[cluster_idx % len(CLUSTER_COLORS)],
            "top_entities": top_entities,
            "pillar": pillar,
            "pages": page_list,
            "size": len(cluster_pages),
            "link_health": link_health,
            "content_gaps": content_gaps,
            "silhouette": round(per_cluster_sil, 3),
        }
        cluster_results.append(cluster_result)

    # Sort clusters by size descending
    cluster_results.sort(key=lambda c: c["size"], reverse=True)
    # Re-index
    for i, c in enumerate(cluster_results):
        c["id"] = i
        c["color"] = CLUSTER_COLORS[i % len(CLUSTER_COLORS)]

    # Generate link recommendations
    link_recommendations = _generate_link_recommendations(cluster_results, link_index)

    # Quality badge
    if sil_score >= 0.5:
        quality = "excellent"
    elif sil_score >= 0.25:
        quality = "good"
    elif sil_score >= 0.15:
        quality = "fair"
    else:
        quality = "low"

    result = {
        "version": "1.0",
        "method": "hybrid_entity_tfidf",
        "n_clusters": len(cluster_results),
        "silhouette_score": round(sil_score, 3),
        "quality": quality,
        "detection_method": detection_method,
        "entity_data_coverage": f"{pages_with_entities}/{n_pages}",
        "clusters": cluster_results,
        "uncategorized_pages": uncategorized_pages,
        "link_recommendations": link_recommendations,
    }

    logger.info(
        f"Semantic clustering complete: {len(cluster_results)} clusters, "
        f"silhouette={sil_score:.3f} ({quality}), "
        f"{len(link_recommendations)} link recommendations"
    )

    return result


# ---------------------------------------------------------------------------
# Helper: Prepare pages from report data
# ---------------------------------------------------------------------------


def prepare_pages_from_report(report: Dict[str, Any]) -> Tuple[
    List[Dict[str, Any]], List[Dict[str, Any]]
]:
    """Extract page and link data from a premium audit report for clustering.

    Merges data from:
      - link_analysis.graph.nodes (URL, title, cluster, inbound/outbound, depth)
      - tipr_analysis.pages (PageRank scores, classification)
      - nlp_analysis (entities, categories — homepage-only currently)
      - crawl data page meta (title, meta_description from DataForSEO)

    Returns:
        (pages, links) ready for run_topic_clustering().
    """
    graph = (report.get("link_analysis") or {}).get("graph", {})
    nodes = graph.get("nodes", [])
    graph_links = graph.get("links", [])

    if not nodes:
        return [], []

    # Build node lookup
    node_map: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        url = node.get("id", "")
        node_map[url] = node

    # Merge TIPR data
    tipr_pages = (report.get("tipr_analysis") or {}).get("pages", [])
    tipr_map = {p["url"]: p for p in tipr_pages if isinstance(p, dict)}

    # NLP data (currently homepage-only, but structured for future expansion)
    nlp = report.get("nlp_analysis") or {}
    homepage_url = report.get("url", "")
    homepage_entities = nlp.get("entities", [])

    # Build pages list
    pages = []
    for url, node in node_map.items():
        page: Dict[str, Any] = {
            "url": url,
            "title": node.get("label", "") or "",
            "word_count": node.get("word_count", 0) or 0,
            "click_depth": node.get("depth", -1),
            "content": "",
            "meta_description": "",
            "entities": [],
            "nlp_category": node.get("nlp_category", ""),
        }

        # Merge TIPR scores
        tipr = tipr_map.get(url)
        if tipr:
            page["pagerank_score"] = tipr.get("pagerank_score", 0)
            page["click_depth"] = tipr.get("click_depth", page["click_depth"])

        # Merge NLP entities (homepage only currently)
        if url == homepage_url or url.rstrip("/") == homepage_url.rstrip("/"):
            page["entities"] = homepage_entities

        pages.append(page)

    # Build links list
    links = []
    for link in graph_links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        if isinstance(src, dict):
            src = src.get("id", "")
        if isinstance(tgt, dict):
            tgt = tgt.get("id", "")
        if src and tgt:
            links.append({"source": src, "target": tgt})

    return pages, links
