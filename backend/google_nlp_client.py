"""
Google Cloud Natural Language API client.
Sprint 3E: Content classification using v2 API (1,091 hierarchical categories).
Sprint 4D: Entity analysis using v1 API (salience scores), entity sentiment analysis.

CRITICAL: v1 vs v2 API versioning:
- v1 (language_v1): Entity analysis — ONLY v1 returns salience scores (0.0-1.0),
  Wikipedia URLs, and Knowledge Graph MIDs. v2 removed salience entirely.
- v2 (language_v2): Content classification — 1,091 categories (vs v1's ~700).

Both versions used simultaneously via REST API (httpx).
Authenticates with API key (GOOGLE_API_KEY env var).

Cost per 2,000-page audit (selective strategy):
- Classification (all pages):          $0    (within 30K free tier)
- Entity Analysis (top 500 pages):     ~$2.50
- Entity Sentiment (key 200 pages):    ~$2.00
- Total:                               ~$4.50
"""
import asyncio
import logging
import os
import re
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

NLP_V2_BASE = "https://language.googleapis.com/v2"
NLP_V1_BASE = "https://language.googleapis.com/v1"


# ── Classification Data Structures (Sprint 3E, v2 API) ─────────────


@dataclass
class NLPClassificationResult:
    category: str       # e.g., "/Business & Industrial/Advertising & Marketing"
    confidence: float   # 0.0-1.0


@dataclass
class PageClassification:
    url: str
    primary_category: str | None
    primary_confidence: float
    all_categories: List[NLPClassificationResult]


# ── Entity Analysis Data Structures (Sprint 4D, v1 API) ────────────


@dataclass
class NLPEntityResult:
    name: str
    entity_type: str          # PERSON, ORGANIZATION, CONSUMER_GOOD, WORK_OF_ART, etc.
    salience: float           # 0.0-1.0 (v1 only — how central to the document)
    wikipedia_url: str | None
    knowledge_graph_mid: str | None
    mentions_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NLPSentimentResult:
    score: float              # -1.0 to +1.0
    magnitude: float          # 0.0 to ∞


@dataclass
class NLPEntitySentiment:
    name: str
    entity_type: str
    salience: float
    sentiment_score: float    # -1.0 to +1.0
    sentiment_magnitude: float
    mentions_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PageEntityAnalysis:
    url: str
    entities: List[NLPEntityResult]
    primary_entity: str | None           # highest salience entity
    primary_entity_salience: float | None
    entity_focus_aligned: bool | None    # does primary entity match H1/title?
    sentiment: NLPSentimentResult | None
    entity_sentiments: List[NLPEntitySentiment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "entities": [e.to_dict() for e in self.entities],
            "primary_entity": self.primary_entity,
            "primary_entity_salience": self.primary_entity_salience,
            "entity_focus_aligned": self.entity_focus_aligned,
            "sentiment": asdict(self.sentiment) if self.sentiment else None,
            "entity_sentiments": [e.to_dict() for e in self.entity_sentiments],
        }


def is_configured() -> bool:
    """Check if Google API key is available for NLP calls."""
    return bool(os.environ.get("GOOGLE_API_KEY"))


async def classify_text(
    text: str,
    api_key: str | None = None,
) -> List[NLPClassificationResult]:
    """Classify text into Google's 1,091 content categories (v2 API).

    Args:
        text: Plain text content (minimum 20 tokens). Feed Trafilatura clean_text.
        api_key: Google API key. Falls back to GOOGLE_API_KEY env var.

    Returns:
        List of categories with confidence scores, sorted by confidence desc.
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY env var required for NLP classification")

    # Classification requires minimum 20 tokens
    if len(text.split()) < 20:
        return []

    # Truncate to ~990KB to stay under 1MB limit (leave room for JSON wrapper)
    if len(text.encode("utf-8")) > 990_000:
        text = text[:250_000]

    body = {
        "document": {
            "type": "PLAIN_TEXT",
            "content": text,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{NLP_V2_BASE}/documents:classifyText?key={key}",
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    categories = data.get("categories", [])
    results = [
        NLPClassificationResult(
            category=c.get("name", ""),
            confidence=c.get("confidence", 0.0),
        )
        for c in categories
    ]
    return sorted(results, key=lambda r: r.confidence, reverse=True)


async def classify_pages_batch(
    pages: List[Dict[str, str]],
    api_key: str | None = None,
    concurrency: int = 20,
    cache_reset_interval: int = 500,
) -> List[PageClassification]:
    """Classify multiple pages concurrently.

    Args:
        pages: List of dicts with 'url' and 'text' keys.
        api_key: Google API key.
        concurrency: Max concurrent API calls (stay under 600/min limit).
        cache_reset_interval: Not used here but kept for interface consistency.

    Returns:
        List of PageClassification results.
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY env var required for NLP classification")

    semaphore = asyncio.Semaphore(concurrency)
    results: List[PageClassification] = []

    async def classify_one(page: Dict[str, str]) -> PageClassification:
        url = page["url"]
        text = page.get("text", "")
        async with semaphore:
            try:
                cats = await classify_text(text, api_key=key)
                primary = cats[0] if cats else None
                return PageClassification(
                    url=url,
                    primary_category=primary.category if primary else None,
                    primary_confidence=primary.confidence if primary else 0.0,
                    all_categories=cats,
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning(f"NLP rate limit hit, waiting 5s (at {url})")
                    await asyncio.sleep(5)
                    try:
                        cats = await classify_text(text, api_key=key)
                        primary = cats[0] if cats else None
                        return PageClassification(
                            url=url,
                            primary_category=primary.category if primary else None,
                            primary_confidence=primary.confidence if primary else 0.0,
                            all_categories=cats,
                        )
                    except Exception:
                        pass
                logger.warning(f"NLP classification failed for {url}: {e}")
                return PageClassification(url=url, primary_category=None, primary_confidence=0.0, all_categories=[])
            except Exception as e:
                logger.warning(f"NLP classification error for {url}: {e}")
                return PageClassification(url=url, primary_category=None, primary_confidence=0.0, all_categories=[])

    tasks = [classify_one(page) for page in pages]
    results = await asyncio.gather(*tasks)

    classified = sum(1 for r in results if r.primary_category)
    logger.info(f"NLP classification complete: {classified}/{len(pages)} pages classified")
    return list(results)


# ── Entity Analysis (Sprint 4D, v1 API) ──────────────────────────


_TERMINAL = re.compile(r"[.!?:;]\s*$")


def _prepare_text(text: str) -> str:
    """Normalize and truncate text for the NLP API (max ~990KB).

    BUG-2 fix: Trafilatura preserves heading/paragraph structure via
    newlines but leaves headings (and some list items) unpunctuated.
    Google NLP's PLAIN_TEXT tokenizer doesn't treat a bare \\n as a
    sentence boundary when the preceding line ends without terminal
    punctuation. On shadowdigital.cc this caused the homepage's
    heading "About Webflow" to merge with the next paragraph
    ("Webflow is a no-code development tool...") and emit the
    stuttering entity "Webflow Webflow" at 0.368 salience, which then
    surfaced as "webflow services for webflow" in AI Visibility
    prompts, as a SEMANTIC term classification for the Content
    Optimizer, and as "Double down on Webflow Webflow" copy in the
    executive summary.

    Fixing at the boundary: append a period to any non-blank line
    that doesn't already end in terminal punctuation. Block
    boundaries become sentence boundaries without changing meaning.
    nlp_sanitizer.py stays in place as defense in depth for any
    other upstream quirks.
    """
    lines = []
    for line in text.splitlines():
        stripped = line.rstrip()
        if stripped and not _TERMINAL.search(stripped):
            stripped += "."
        lines.append(stripped)
    text = "\n".join(lines)
    if len(text.encode("utf-8")) > 990_000:
        text = text[:250_000]
    return text


async def analyze_entities(
    text: str,
    api_key: str | None = None,
) -> List[NLPEntityResult]:
    """Analyze entities in text using v1 API (returns salience scores).

    Args:
        text: Plain text content.
        api_key: Google API key. Falls back to GOOGLE_API_KEY env var.

    Returns:
        List of entities sorted by salience (descending).
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY env var required for entity analysis")

    if len(text.split()) < 5:
        return []

    body = {
        "document": {
            "type": "PLAIN_TEXT",
            "content": _prepare_text(text),
        },
        "encodingType": "UTF8",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{NLP_V1_BASE}/documents:analyzeEntities?key={key}",
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    entities = []
    for e in data.get("entities", []):
        metadata = e.get("metadata", {})
        entities.append(NLPEntityResult(
            name=e.get("name", ""),
            entity_type=e.get("type", "UNKNOWN"),
            salience=e.get("salience", 0.0),
            wikipedia_url=metadata.get("wikipedia_url"),
            knowledge_graph_mid=metadata.get("mid"),
            mentions_count=len(e.get("mentions", [])),
        ))

    return sorted(entities, key=lambda e: e.salience, reverse=True)


async def analyze_sentiment(
    text: str,
    api_key: str | None = None,
) -> NLPSentimentResult:
    """Analyze document-level sentiment using v1 API.

    Args:
        text: Plain text content.
        api_key: Google API key.

    Returns:
        NLPSentimentResult with score (-1.0 to +1.0) and magnitude.
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY env var required for sentiment analysis")

    body = {
        "document": {
            "type": "PLAIN_TEXT",
            "content": _prepare_text(text),
        },
        "encodingType": "UTF8",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{NLP_V1_BASE}/documents:analyzeSentiment?key={key}",
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    doc_sentiment = data.get("documentSentiment", {})
    return NLPSentimentResult(
        score=doc_sentiment.get("score", 0.0),
        magnitude=doc_sentiment.get("magnitude", 0.0),
    )


async def analyze_entity_sentiment(
    text: str,
    api_key: str | None = None,
) -> List[NLPEntitySentiment]:
    """Combined entity + sentiment analysis in one call (v1 API).

    More cost-efficient than separate calls. Returns entities with
    per-entity and per-mention sentiment scores.

    Args:
        text: Plain text content.
        api_key: Google API key.

    Returns:
        List of entities with sentiment, sorted by salience.
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY env var required for entity sentiment analysis")

    if len(text.split()) < 5:
        return []

    body = {
        "document": {
            "type": "PLAIN_TEXT",
            "content": _prepare_text(text),
        },
        "encodingType": "UTF8",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{NLP_V1_BASE}/documents:analyzeEntitySentiment?key={key}",
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for e in data.get("entities", []):
        sentiment = e.get("sentiment", {})
        results.append(NLPEntitySentiment(
            name=e.get("name", ""),
            entity_type=e.get("type", "UNKNOWN"),
            salience=e.get("salience", 0.0),
            sentiment_score=sentiment.get("score", 0.0),
            sentiment_magnitude=sentiment.get("magnitude", 0.0),
            mentions_count=len(e.get("mentions", [])),
        ))

    return sorted(results, key=lambda e: e.salience, reverse=True)


# ── Batch Entity Analysis ─────────────────────────────────────────


async def analyze_entities_batch(
    pages: List[Dict[str, str]],
    api_key: str | None = None,
    concurrency: int = 20,
    h1_titles: Dict[str, str] | None = None,
) -> List[PageEntityAnalysis]:
    """Run entity analysis on multiple pages with concurrency control.

    Args:
        pages: List of dicts with 'url' and 'text' keys.
        api_key: Google API key.
        concurrency: Max concurrent API calls.
        h1_titles: Optional url -> h1/title text for entity focus alignment check.

    Returns:
        List of PageEntityAnalysis results.
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY env var required")

    semaphore = asyncio.Semaphore(concurrency)

    async def analyze_one(page: Dict[str, str]) -> PageEntityAnalysis:
        url = page["url"]
        text = page.get("text", "")
        async with semaphore:
            try:
                entities = await analyze_entities(text, api_key=key)
                primary = entities[0] if entities else None

                # Entity focus alignment: check if primary entity matches H1/title
                aligned = None
                if primary and h1_titles and url in h1_titles:
                    title_text = h1_titles[url].lower()
                    aligned = primary.name.lower() in title_text or \
                              any(word in title_text for word in primary.name.lower().split())

                return PageEntityAnalysis(
                    url=url,
                    entities=entities[:10],  # top 10 by salience
                    primary_entity=primary.name if primary else None,
                    primary_entity_salience=primary.salience if primary else None,
                    entity_focus_aligned=aligned,
                    sentiment=None,
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning(f"NLP rate limit hit, waiting 5s (at {url})")
                    await asyncio.sleep(5)
                    try:
                        entities = await analyze_entities(text, api_key=key)
                        primary = entities[0] if entities else None
                        return PageEntityAnalysis(
                            url=url,
                            entities=entities[:10],
                            primary_entity=primary.name if primary else None,
                            primary_entity_salience=primary.salience if primary else None,
                            entity_focus_aligned=None,
                            sentiment=None,
                        )
                    except Exception:
                        pass
                logger.warning(f"Entity analysis failed for {url}: {e}")
                return PageEntityAnalysis(url=url, entities=[], primary_entity=None,
                                         primary_entity_salience=None, entity_focus_aligned=None,
                                         sentiment=None)
            except Exception as e:
                logger.warning(f"Entity analysis error for {url}: {e}")
                return PageEntityAnalysis(url=url, entities=[], primary_entity=None,
                                         primary_entity_salience=None, entity_focus_aligned=None,
                                         sentiment=None)

    tasks = [analyze_one(page) for page in pages]
    results = list(await asyncio.gather(*tasks))

    analyzed = sum(1 for r in results if r.primary_entity)
    logger.info(f"NLP entity analysis complete: {analyzed}/{len(pages)} pages analyzed")
    return results


async def analyze_entity_sentiment_batch(
    pages: List[Dict[str, str]],
    api_key: str | None = None,
    concurrency: int = 10,
) -> List[PageEntityAnalysis]:
    """Run entity sentiment analysis on key pages (selective, higher cost).

    Args:
        pages: List of dicts with 'url' and 'text' keys.
        api_key: Google API key.
        concurrency: Max concurrent API calls.

    Returns:
        List of PageEntityAnalysis with sentiment data.
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY env var required")

    semaphore = asyncio.Semaphore(concurrency)

    async def analyze_one(page: Dict[str, str]) -> PageEntityAnalysis:
        url = page["url"]
        text = page.get("text", "")
        async with semaphore:
            try:
                entity_sentiments = await analyze_entity_sentiment(text, api_key=key)
                sentiment = await analyze_sentiment(text, api_key=key)

                primary = entity_sentiments[0] if entity_sentiments else None

                # Convert entity sentiments to entity results for consistency
                entities = [
                    NLPEntityResult(
                        name=es.name,
                        entity_type=es.entity_type,
                        salience=es.salience,
                        wikipedia_url=None,
                        knowledge_graph_mid=None,
                        mentions_count=es.mentions_count,
                    )
                    for es in entity_sentiments[:10]
                ]

                return PageEntityAnalysis(
                    url=url,
                    entities=entities,
                    primary_entity=primary.name if primary else None,
                    primary_entity_salience=primary.salience if primary else None,
                    entity_focus_aligned=None,
                    sentiment=sentiment,
                    entity_sentiments=entity_sentiments[:10],
                )
            except Exception as e:
                logger.warning(f"Entity sentiment analysis failed for {url}: {e}")
                return PageEntityAnalysis(url=url, entities=[], primary_entity=None,
                                         primary_entity_salience=None, entity_focus_aligned=None,
                                         sentiment=None)

    tasks = [analyze_one(page) for page in pages]
    results = list(await asyncio.gather(*tasks))

    analyzed = sum(1 for r in results if r.sentiment)
    logger.info(f"NLP entity sentiment complete: {analyzed}/{len(pages)} pages analyzed")
    return results


# ── Site-Wide Entity Aggregation ──────────────────────────────────


def build_site_entity_map(
    page_analyses: List[PageEntityAnalysis],
) -> List[Dict[str, Any]]:
    """Aggregate entities across all pages into a site-wide entity map.

    Ranks entities by frequency * average_salience.

    Returns:
        Sorted list of entities with page_count, avg_salience, total_mentions.
    """
    from collections import defaultdict

    entity_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "salience_values": [],
        "total_mentions": 0,
        "entity_type": "UNKNOWN",
        "pages": set(),
    })

    for analysis in page_analyses:
        for entity in analysis.entities:
            key = entity.name.lower()
            stats = entity_stats[key]
            stats["salience_values"].append(entity.salience)
            stats["total_mentions"] += entity.mentions_count
            stats["entity_type"] = entity.entity_type
            stats["pages"].add(analysis.url)

    site_map: List[Dict[str, Any]] = []
    for name, stats in entity_stats.items():
        avg_salience = sum(stats["salience_values"]) / len(stats["salience_values"])
        page_count = len(stats["pages"])
        # Rank by page_count * avg_salience
        rank_score = page_count * avg_salience
        site_map.append({
            "entity": name,
            "entity_type": stats["entity_type"],
            "page_count": page_count,
            "avg_salience": round(avg_salience, 4),
            "total_mentions": stats["total_mentions"],
            "rank_score": round(rank_score, 4),
        })

    site_map.sort(key=lambda e: e["rank_score"], reverse=True)
    return site_map[:50]  # top 50 entities


def detect_brand_sentiment(
    page_analyses: List[PageEntityAnalysis],
    brand_names: List[str] | None = None,
) -> Dict[str, Any]:
    """Detect brand and competitor sentiment across all analyzed pages.

    Args:
        page_analyses: Results from entity sentiment batch analysis.
        brand_names: Optional list of brand names to track. If None, detects
                     ORGANIZATION entities automatically.

    Returns:
        Dict mapping entity names to average sentiment scores and mention counts.
    """
    from collections import defaultdict

    brand_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "sentiment_scores": [],
        "total_mentions": 0,
        "entity_type": "UNKNOWN",
    })

    for analysis in page_analyses:
        for es in analysis.entity_sentiments:
            # Track organizations by default, or match against brand_names
            if brand_names:
                if not any(bn.lower() in es.name.lower() for bn in brand_names):
                    continue
            elif es.entity_type != "ORGANIZATION":
                continue

            key = es.name.lower()
            brand_stats[key]["sentiment_scores"].append(es.sentiment_score)
            brand_stats[key]["total_mentions"] += es.mentions_count
            brand_stats[key]["entity_type"] = es.entity_type

    result: Dict[str, Any] = {}
    for name, stats in brand_stats.items():
        if stats["total_mentions"] < 3:  # skip entities with very few mentions
            continue
        avg_sentiment = sum(stats["sentiment_scores"]) / len(stats["sentiment_scores"])
        result[name] = {
            "avg_sentiment": round(avg_sentiment, 3),
            "total_mentions": stats["total_mentions"],
            "pages_analyzed": len(stats["sentiment_scores"]),
            "entity_type": stats["entity_type"],
        }

    return result
