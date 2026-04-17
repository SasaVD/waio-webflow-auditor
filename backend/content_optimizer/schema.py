"""Data types for Content Optimizer WDF*IDF analysis."""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class TermClassification(str, Enum):
    CORE = "core"
    SEMANTIC = "semantic"
    AUXILIARY = "auxiliary"
    FILLER = "filler"


class RecommendationType(str, Enum):
    INCREASE = "increase"
    ADD = "add"
    REDUCE = "reduce"
    REMOVE = "remove"


@dataclass
class TermAnalysis:
    term: str
    ngram_size: int
    target_wdf_idf: float
    target_frequency: int
    competitor_max_wdf_idf: float
    competitor_avg_wdf_idf: float
    competitor_min_wdf_idf: float
    competitor_max_frequency: int
    competitor_avg_frequency: float
    docs_containing: int
    idf: float
    classification: Optional[TermClassification] = None
    filler_category: Optional[str] = None
    recommendation: Optional["Recommendation"] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.classification:
            d["classification"] = self.classification.value
        if self.recommendation:
            d["recommendation"] = self.recommendation.to_dict()
        return d


@dataclass
class Recommendation:
    type: RecommendationType
    term: str
    classification: TermClassification
    reason: str
    target_frequency: int
    suggested_frequency: int
    priority: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        d["classification"] = self.classification.value
        return d


@dataclass
class ContentOptimizationResult:
    keyword: str
    target_url: str
    target_word_count: int
    competitors_analyzed: int
    competitors_failed: int
    terms: list  # list of TermAnalysis dicts
    recommendations: list  # list of Recommendation dicts
    chart_data: list  # sorted list of {term, target, comp_max, comp_avg}
    summary: dict
    serp_results: list  # original SERP data
    duration_seconds: float
    cost_usd: float

    def to_dict(self) -> dict:
        return asdict(self)
