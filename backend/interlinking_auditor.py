"""
Page-pair interlinking opportunity detector.
Sprint 4C: Find pages with high content similarity but no internal link between them.

Approach:
1. Build TF-IDF vectors for all site pages (from clean_text)
2. Compute pairwise cosine similarity
3. Cross-reference with link_graph edges
4. Emit top 50 interlinking opportunities (high similarity, no link)

Performance:
- 2,000 pages: ~2M pairs, ~30MB matrix, sub-second computation
- 5,000+ pages: use sparse_dot_topn for top-K only
"""
import logging
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class InterlinkingOpportunity:
    source_url: str
    target_url: str
    similarity: float          # cosine similarity (0.0-1.0)
    suggested_anchor: str      # most relevant shared term(s)
    source_title: str | None
    target_title: str | None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InterlinkingResult:
    total_pages: int
    total_existing_links: int
    opportunities: List[InterlinkingOpportunity]
    avg_similarity: float
    findings: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["opportunities"] = [o.to_dict() if isinstance(o, InterlinkingOpportunity) else o for o in self.opportunities]
        return d


def _tokenize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_interlinking_opportunities(
    pages: List[Dict[str, Any]],
    existing_links: Set[Tuple[str, str]],
    max_opportunities: int = 50,
    min_similarity: float = 0.15,
) -> InterlinkingResult:
    """Find page pairs with high content similarity but no internal link.

    Args:
        pages: List of dicts with 'url', 'clean_text', and optionally 'title'.
        existing_links: Set of (source_url, target_url) tuples from link graph.
        max_opportunities: Maximum opportunities to return.
        min_similarity: Minimum cosine similarity threshold.

    Returns:
        InterlinkingResult with ranked opportunities and findings.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    # Filter pages with enough content
    valid_pages = [p for p in pages if p.get("clean_text") and len(p["clean_text"].split()) > 20]
    if len(valid_pages) < 2:
        return InterlinkingResult(
            total_pages=len(pages),
            total_existing_links=len(existing_links),
            opportunities=[],
            avg_similarity=0.0,
            findings=[],
        )

    urls = [p["url"] for p in valid_pages]
    texts = [_tokenize(p["clean_text"]) for p in valid_pages]
    titles = {p["url"]: p.get("title", "") for p in valid_pages}

    # Build TF-IDF matrix
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=2,
        max_df=0.9,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    n_pages = len(valid_pages)

    # For large sites (5,000+), use sparse top-K
    if n_pages > 3000:
        opportunities = _sparse_top_k(
            tfidf_matrix, urls, titles, feature_names,
            existing_links, min_similarity, max_opportunities
        )
    else:
        # Standard pairwise cosine similarity
        sim_matrix = cosine_similarity(tfidf_matrix)
        opportunities = _extract_opportunities(
            sim_matrix, urls, titles, feature_names, tfidf_matrix,
            existing_links, min_similarity, max_opportunities
        )

    # Compute average similarity for reporting
    if opportunities:
        avg_sim = sum(o.similarity for o in opportunities) / len(opportunities)
    else:
        avg_sim = 0.0

    # Generate findings
    findings: List[Dict[str, Any]] = []
    if len(opportunities) >= 20:
        high_sim_count = sum(1 for o in opportunities if o.similarity > 0.3)
        findings.append({
            "severity": "high" if high_sim_count > 10 else "medium",
            "description": (
                f"Found {len(opportunities)} interlinking opportunities — "
                f"page pairs with similar content but no internal link between them. "
                f"{high_sim_count} pairs have similarity above 30%."
            ),
            "recommendation": (
                "Add internal links between these related pages using descriptive anchor text. "
                "Focus on the highest-similarity pairs first, as they represent the strongest "
                "topical connections."
            ),
            "reference": "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
            "why_it_matters": (
                "Strategic internal linking improves crawl efficiency and distributes link equity. "
                "Sites with strong internal linking earn 40% more organic traffic (Ahrefs, 2023)."
            ),
        })
    elif len(opportunities) > 0:
        findings.append({
            "severity": "medium",
            "description": (
                f"Found {len(opportunities)} potential interlinking opportunities."
            ),
            "recommendation": "Review the suggested page pairs and add internal links where relevant.",
            "reference": "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
        })

    return InterlinkingResult(
        total_pages=n_pages,
        total_existing_links=len(existing_links),
        opportunities=opportunities,
        avg_similarity=round(avg_sim, 4),
        findings=findings,
    )


def _extract_opportunities(
    sim_matrix: np.ndarray,
    urls: List[str],
    titles: Dict[str, str],
    feature_names: np.ndarray,
    tfidf_matrix: Any,
    existing_links: Set[Tuple[str, str]],
    min_similarity: float,
    max_opportunities: int,
) -> List[InterlinkingOpportunity]:
    """Extract top interlinking opportunities from a full similarity matrix."""
    n = len(urls)
    candidates: List[Tuple[float, int, int]] = []

    for i in range(n):
        for j in range(i + 1, n):
            sim = float(sim_matrix[i, j])
            if sim < min_similarity:
                continue
            # Skip if link already exists in either direction
            if (urls[i], urls[j]) in existing_links or (urls[j], urls[i]) in existing_links:
                continue
            candidates.append((sim, i, j))

    # Sort by similarity descending
    candidates.sort(key=lambda x: x[0], reverse=True)
    candidates = candidates[:max_opportunities]

    opportunities: List[InterlinkingOpportunity] = []
    for sim, i, j in candidates:
        anchor = _suggest_anchor(tfidf_matrix, i, j, feature_names)
        opportunities.append(InterlinkingOpportunity(
            source_url=urls[i],
            target_url=urls[j],
            similarity=round(sim, 4),
            suggested_anchor=anchor,
            source_title=titles.get(urls[i]),
            target_title=titles.get(urls[j]),
        ))

    return opportunities


def _sparse_top_k(
    tfidf_matrix: Any,
    urls: List[str],
    titles: Dict[str, str],
    feature_names: np.ndarray,
    existing_links: Set[Tuple[str, str]],
    min_similarity: float,
    max_opportunities: int,
) -> List[InterlinkingOpportunity]:
    """For large sites: use sparse_dot_topn or chunked computation."""
    from sklearn.metrics.pairwise import cosine_similarity

    n = tfidf_matrix.shape[0]
    chunk_size = 500
    candidates: List[Tuple[float, int, int]] = []

    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        chunk_sim = cosine_similarity(tfidf_matrix[start:end], tfidf_matrix)

        for local_i in range(end - start):
            global_i = start + local_i
            for j in range(global_i + 1, n):
                sim = float(chunk_sim[local_i, j])
                if sim < min_similarity:
                    continue
                if (urls[global_i], urls[j]) in existing_links or (urls[j], urls[global_i]) in existing_links:
                    continue
                candidates.append((sim, global_i, j))

        # Keep only top candidates to manage memory
        if len(candidates) > max_opportunities * 5:
            candidates.sort(key=lambda x: x[0], reverse=True)
            candidates = candidates[:max_opportunities * 2]

    candidates.sort(key=lambda x: x[0], reverse=True)
    candidates = candidates[:max_opportunities]

    opportunities: List[InterlinkingOpportunity] = []
    for sim, i, j in candidates:
        anchor = _suggest_anchor(tfidf_matrix, i, j, feature_names)
        opportunities.append(InterlinkingOpportunity(
            source_url=urls[i],
            target_url=urls[j],
            similarity=round(sim, 4),
            suggested_anchor=anchor,
            source_title=titles.get(urls[i]),
            target_title=titles.get(urls[j]),
        ))

    return opportunities


def _suggest_anchor(
    tfidf_matrix: Any,
    idx_a: int,
    idx_b: int,
    feature_names: np.ndarray,
) -> str:
    """Suggest anchor text based on shared high-TF-IDF terms."""
    vec_a = tfidf_matrix[idx_a].toarray().flatten()
    vec_b = tfidf_matrix[idx_b].toarray().flatten()

    # Find terms present in both pages
    shared_mask = (vec_a > 0) & (vec_b > 0)
    if not shared_mask.any():
        return ""

    # Score by combined TF-IDF weight
    combined = (vec_a + vec_b) * shared_mask
    top_indices = np.argsort(combined)[-3:][::-1]  # top 3 shared terms

    terms = [str(feature_names[i]) for i in top_indices if combined[i] > 0]
    return " ".join(terms) if terms else ""
