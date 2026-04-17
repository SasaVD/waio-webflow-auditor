"""Core WDF*IDF math -- Karl Kratz variant with double-log normalization."""
import math
import re
from collections import Counter
from typing import Tuple

from .schema import TermAnalysis


def tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split on whitespace, filter stop words."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    stop = _get_stop_words()
    return [t for t in tokens if len(t) > 2 and t not in stop]


def compute_ngrams(tokens: list[str], n: int) -> list[str]:
    """Generate n-grams from token list."""
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def compute_wdf(term_freq: int, total_words: int) -> float:
    """WDF = log2(freq + 1) / log2(total_words + 1)"""
    if total_words == 0:
        return 0.0
    return math.log2(term_freq + 1) / math.log2(total_words + 1)


def compute_idf(num_docs: int, docs_containing_term: int) -> float:
    """IDF = log2(N / docs_containing_term)"""
    if docs_containing_term == 0:
        return 0.0
    return math.log2(num_docs / docs_containing_term)


def run_wdf_idf_analysis(
    target_text: str,
    competitor_texts: list[str],
    max_terms: int = 100,
    ngram_range: Tuple[int, int] = (1, 3),
) -> list[TermAnalysis]:
    """Compute WDF*IDF for all terms across target + competitor corpus.

    Returns top ``max_terms`` sorted by competitor average WDF*IDF descending.
    """
    all_texts = [target_text] + competitor_texts
    num_docs = len(all_texts)

    # Tokenize all documents
    all_tokenized = [tokenize(text) for text in all_texts]

    # Build term frequency counters (unigrams + bigrams + trigrams)
    all_term_freqs: list[Counter] = []
    all_word_counts: list[int] = []
    for tokens in all_tokenized:
        term_counter: Counter = Counter()
        for n in range(ngram_range[0], ngram_range[1] + 1):
            ngrams = compute_ngrams(tokens, n)
            term_counter.update(ngrams)
        all_term_freqs.append(term_counter)
        all_word_counts.append(len(tokens))

    # Collect all unique terms
    all_terms: set[str] = set()
    for counter in all_term_freqs:
        all_terms.update(counter.keys())

    # Compute WDF*IDF for each term in each document
    results: list[TermAnalysis] = []
    for term in all_terms:
        docs_with_term = sum(1 for counter in all_term_freqs if term in counter)

        # Skip terms in only 1 doc (noise) or ALL docs (too common)
        if docs_with_term < 2 or docs_with_term == num_docs:
            continue

        idf = compute_idf(num_docs, docs_with_term)

        # Target page
        target_freq = all_term_freqs[0].get(term, 0)
        target_wdf = compute_wdf(target_freq, all_word_counts[0])
        target_wdf_idf = target_wdf * idf

        # Competitors
        competitor_wdf_idfs: list[float] = []
        competitor_freqs: list[int] = []
        for i in range(1, num_docs):
            freq = all_term_freqs[i].get(term, 0)
            wdf = compute_wdf(freq, all_word_counts[i])
            competitor_wdf_idfs.append(wdf * idf)
            competitor_freqs.append(freq)

        comp_max = max(competitor_wdf_idfs) if competitor_wdf_idfs else 0
        comp_avg = (
            sum(competitor_wdf_idfs) / len(competitor_wdf_idfs)
            if competitor_wdf_idfs
            else 0
        )
        comp_min = min(competitor_wdf_idfs) if competitor_wdf_idfs else 0

        results.append(
            TermAnalysis(
                term=term,
                ngram_size=len(term.split()),
                target_wdf_idf=round(target_wdf_idf, 4),
                target_frequency=target_freq,
                competitor_max_wdf_idf=round(comp_max, 4),
                competitor_avg_wdf_idf=round(comp_avg, 4),
                competitor_min_wdf_idf=round(comp_min, 4),
                competitor_max_frequency=(
                    max(competitor_freqs) if competitor_freqs else 0
                ),
                competitor_avg_frequency=(
                    round(sum(competitor_freqs) / len(competitor_freqs), 1)
                    if competitor_freqs
                    else 0
                ),
                docs_containing=docs_with_term,
                idf=round(idf, 4),
            )
        )

    # Sort by competitor average WDF*IDF descending
    results.sort(key=lambda t: t.competitor_avg_wdf_idf, reverse=True)
    return results[:max_terms]


def _get_stop_words() -> set[str]:
    """Minimal English stop words -- preserves content-relevant common words."""
    return {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "can", "this", "that",
        "these", "those", "it", "its", "they", "them", "their", "we", "our",
        "you", "your", "he", "she", "his", "her", "not", "no", "nor", "so",
        "if", "then", "than", "too", "very", "just", "about", "also", "more",
        "other", "some", "such", "into", "over", "after", "before", "between",
        "under", "again", "further", "once", "here", "there", "when", "where",
        "why", "how", "all", "each", "every", "both", "few", "many", "most",
        "own", "same", "any", "only", "while", "during", "through",
    }
