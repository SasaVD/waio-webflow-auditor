"""Pure dataclass types for the AI Visibility pipeline."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrandInfo:
    name: str
    # Source discriminator (Workstream D2 — Contract B):
    #   "kg_mid"              — override validated via Knowledge Graph MID /
    #                           Wikipedia URL (HIGHEST confidence).
    #   "curated_list"        — override matched against curated brand whitelist
    #                           (MEDIUM confidence).
    #   "override_unverified" — override used but NLP unavailable / no KG hit /
    #                           not in curated list (LOWEST confidence; UI shows
    #                           an advisory).
    #   "nlp"                 — NO override; brand extracted from page NLP
    #                           entities (existing behavior, unchanged).
    # The pre-D2 ``"override"`` value has been removed — every override path
    # now picks one of the three discriminators above.
    source: str
    salience: float | None = None
    kg_mid: str | None = None
    wikipedia_url: str | None = None
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name, "source": self.source}
        if self.salience is not None:
            d["salience"] = round(self.salience, 4)
        if self.kg_mid:
            d["kg_mid"] = self.kg_mid
        if self.wikipedia_url:
            d["wikipedia_url"] = self.wikipedia_url
        if self.warning:
            d["warning"] = self.warning
        return d


@dataclass
class CompetitorSet:
    domains: list[str]
    source: str  # "user_provided" | "competitive_auditor" | "co_mentions" | "none"

    def to_dict(self) -> dict[str, Any]:
        return {"domains": self.domains, "source": self.source}


@dataclass
class PromptTemplate:
    id: int
    category: str  # "discovery" | "reputation"
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "category": self.category, "text": self.text}


@dataclass
class EngineResult:
    status: str  # "ok" | "failed"
    engine: str
    responses_by_prompt: dict[int, dict[str, Any]] = field(default_factory=dict)
    cost_usd: float = 0.0
    brand_mentioned_in: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "status": self.status,
            "cost_usd": round(self.cost_usd, 4),
            "brand_mentioned_in": self.brand_mentioned_in,
        }
        if self.status == "ok":
            d["responses_by_prompt"] = self.responses_by_prompt
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class MentionsResult:
    total: int = 0
    by_platform: dict[str, int] = field(default_factory=dict)
    ai_search_volume: int = 0
    impressions: int = 0
    top_pages: list[dict[str, Any]] = field(default_factory=list)
    triggering_prompts: list[dict[str, Any]] = field(default_factory=list)
    cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "by_platform": self.by_platform,
            "ai_search_volume": self.ai_search_volume,
            "impressions": self.impressions,
            "top_pages": self.top_pages,
            "triggering_prompts": self.triggering_prompts,
        }


@dataclass
class ResponsesResult:
    engines: dict[str, EngineResult] = field(default_factory=dict)
    cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "engines": {k: v.to_dict() for k, v in self.engines.items()},
        }


@dataclass
class SOVResult:
    brand_sov: float
    competitor_sov: dict[str, float]
    total_mentions_analyzed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": "mentions_database.cross_aggregated",
            "brand_sov": round(self.brand_sov, 4),
            "competitor_sov": {k: round(v, 4) for k, v in self.competitor_sov.items()},
            "total_mentions_analyzed": self.total_mentions_analyzed,
        }


class BrandExtractionError(Exception):
    """Raised when no brand name can be auto-extracted."""
    pass
