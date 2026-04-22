"""Defense-in-depth boundary sanitization for Google NLP entity data before
it reaches downstream consumers (AI Visibility prompts, Content Optimizer
term classifier, Topic Clustering feature matrix, Executive Summary
opportunity lines).

The upstream NLP pipeline (google_nlp_client.py) occasionally emits
malformed entity names — adjacent-token repetitions like "Webflow Webflow",
single-token entities that duplicate the detected industry, etc. Those
artifacts have surfaced in generated LLM prompts ("webflow services for
webflow"), Semantic term classifications, the 0.40-weighted entity vector
in the topic-cluster hybrid matrix, and exec-summary opportunity copy.
Fixing the upstream emitter is BUG-2; this module is the boundary filter
every consumer runs entities through, so future upstream regressions
can't poison downstream output. Keep this sanitizer in place after BUG-2
ships — defense in depth.

Three public functions cover the shapes consumers hand us:
  * sanitize_entity_dicts — list[dict] with name/salience/type/...
  * sanitize_entity_names — list[str] (already-flattened names)
  * sanitize_entity_name  — single str (AI Visibility's top_entity)

All three apply the same rules:
  1. Collapse runs of adjacent identical tokens inside a single name
     ("Webflow Webflow" → "Webflow", "web design web design" → "web
     design"). Non-adjacent repeats ("foo bar foo") are preserved.
  2. Drop names that are PURE single-token repetitions post-collapse —
     i.e. the original was >1 token but collapsed to 1. Those are almost
     always artifacts of the stuttering-emitter bug; a legitimate
     single-token entity would have arrived as one token to begin with.
  3. Drop names equal to the detected-industry leaf (case-insensitive,
     whitespace-normalized). The industry is already reported separately;
     surfacing it again as a "top entity" double-counts.
  4. Dedupe across the list case-insensitively, preserving first-
     occurrence order (upstream sorts by descending salience, which we
     must not reshuffle).
"""
from __future__ import annotations

import re
from typing import Any, Iterable


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(name: str) -> str:
    """Lowercase, strip, collapse internal whitespace."""
    return _WHITESPACE_RE.sub(" ", name.strip().lower())


def _industry_leaf(industry: str | None) -> str | None:
    """Extract the leaf segment of a hierarchical industry path.

    "/Business & Industrial/Advertising & Marketing" → "advertising & marketing"
    """
    if not industry:
        return None
    leaf = industry.rstrip("/").rsplit("/", 1)[-1]
    normalized = _normalize(leaf)
    return normalized or None


def _collapse_adjacent_repeats(name: str) -> str:
    """Collapse runs of identical adjacent tokens (case-insensitive match)."""
    tokens = name.split()
    if len(tokens) <= 1:
        return name
    out = [tokens[0]]
    for tok in tokens[1:]:
        if tok.lower() == out[-1].lower():
            continue
        out.append(tok)
    return " ".join(out)


def _is_single_token_repetition(original: str, collapsed: str) -> bool:
    """True when the only reason the original had >1 token was the
    repetition — collapsing produced a single-token name."""
    return len(original.split()) > 1 and len(collapsed.split()) == 1


def _clean_name(name: str, industry_leaf: str | None) -> str | None:
    """Apply all sanitization rules to a single entity name.

    Returns the cleaned name, or None if the entity should be dropped.
    """
    if not name:
        return None
    stripped = _WHITESPACE_RE.sub(" ", name.strip())
    if not stripped:
        return None
    collapsed = _collapse_adjacent_repeats(stripped)
    if _is_single_token_repetition(stripped, collapsed):
        return None
    if industry_leaf and _normalize(collapsed) == industry_leaf:
        return None
    return collapsed


def sanitize_entity_dicts(
    entities: Iterable[dict[str, Any]] | None,
    detected_industry: str | None = None,
) -> list[dict[str, Any]]:
    """Sanitize a list of entity dicts (the google_nlp_client shape).

    Preserves every other key on each entity (salience, type,
    wikipedia_url, mentions_count, ...). Only the name is rewritten;
    dicts that fail sanitization are dropped entirely.
    """
    if not entities:
        return []
    leaf = _industry_leaf(detected_industry)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        raw = ent.get("name") or ""
        cleaned = _clean_name(raw, leaf)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        new_ent = dict(ent)
        new_ent["name"] = cleaned
        out.append(new_ent)
    return out


def sanitize_entity_names(
    names: Iterable[str] | None,
    detected_industry: str | None = None,
) -> list[str]:
    """Sanitize a list of plain entity-name strings."""
    if not names:
        return []
    leaf = _industry_leaf(detected_industry)
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if not isinstance(name, str):
            continue
        cleaned = _clean_name(name, leaf)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def sanitize_entity_name(
    name: str | None,
    detected_industry: str | None = None,
) -> str | None:
    """Sanitize a single entity-name string (AI Visibility's top_entity).

    Returns None when the name is pure adjacent-token repetition or
    duplicates the industry leaf — callers should treat that the same
    way they'd treat a missing top_entity.
    """
    if not name or not isinstance(name, str):
        return None
    leaf = _industry_leaf(detected_industry)
    return _clean_name(name, leaf)
