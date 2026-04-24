"""Bot-challenge / verification-wall detection.

Returns a BotChallengeResult indicating whether the fetched HTML is a
vendor-served challenge page rather than the real site. When detected,
the caller MUST skip the 10-pillar homepage audit — running auditors
on a challenge page produces confidently wrong scores (see sched.com
incident 2026-04-23: 100/100 overall, 0.00% semantic ratio, NLP entities
"security verification" / "bots" / "performance").

Detection is layered:
  Approach 1 (signatures) — vendor-specific selectors, element IDs,
  script patterns, and cookies. High confidence (0.95).
  Approach 2 (content heuristic) — fallback for unknown vendors based
  on body word count, script count, semantic landmark ratio, and a
  keyword list. Medium confidence (0.75).

Dual-source retry (Approach 3) was evaluated and deferred to Workstream E —
the trust fix here is suppression, not workaround.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from bs4 import BeautifulSoup


@dataclass
class BotChallengeResult:
    detected: bool
    vendor: Optional[str] = None   # "cloudflare" | "akamai" | "datadome" | "perimeterx" | "unknown" | None
    signals: list[str] = field(default_factory=list)
    confidence: float = 0.0        # 0.0-1.0; telemetry only, not a gating threshold
    reason: Optional[str] = None   # short human-readable for logs/UI


# ---------------------------------------------------------------------------
# Vendor signature tables
# ---------------------------------------------------------------------------

_CLOUDFLARE_SELECTORS: list[tuple[str, str]] = [
    (".cf-turnstile", "cf-turnstile"),
    (".cf-browser-verification", "cf-browser-verification"),
    ("#challenge-success-text", "challenge-success-text"),
    ("#challenge-form", "challenge-form"),
    ("#cf-error-details", "cf-error-details"),
]
_CLOUDFLARE_COOKIES: set[str] = {"__cf_bm", "cf_chl_opt", "cf_clearance", "__cfduid"}
_CLOUDFLARE_SCRIPT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"challenges\.cloudflare\.com", re.I),
    re.compile(r"/cdn-cgi/challenge-platform/", re.I),
]

_AKAMAI_SELECTORS: list[tuple[str, str]] = [("#bm-verify", "bm-verify")]
_AKAMAI_COOKIES: set[str] = {"_abck", "bm_sz", "bm_sv", "ak_bmsc"}

_DATADOME_SELECTORS: list[tuple[str, str]] = [
    ("#datadome-captcha", "datadome-captcha"),
    ("[data-datadome]", "data-datadome"),
]
_DATADOME_COOKIES: set[str] = {"datadome", "dd_cookie_test", "dd_async_process"}

_PERIMETERX_SELECTORS: list[tuple[str, str]] = [("#px-captcha", "px-captcha")]
_PERIMETERX_COOKIES: set[str] = {"_px", "_pxhd", "_pxvid", "_pxde"}


# ---------------------------------------------------------------------------
# Content heuristic constants
# ---------------------------------------------------------------------------

_CHALLENGE_KEYWORDS = re.compile(
    r"(verifying you are human|checking your browser|please enable javascript and cookies"
    r"|security verification|access denied|request blocked|one more step"
    r"|prove you are a human|bot protection|attention required)",
    re.IGNORECASE,
)

_HEURISTIC_MIN_WORDS = 100
_HEURISTIC_MIN_SCRIPTS = 5
_HEURISTIC_NEAR_ZERO_SEMANTIC_RATIO = 0.05


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_bot_challenge(
    *,
    soup: BeautifulSoup,
    html: str,
    headers: Optional[dict[str, Any]] = None,
    cookies: Optional[dict[str, Any]] = None,
) -> BotChallengeResult:
    """Detect bot-challenge / verification-wall pages.

    Args:
        soup: Parsed HTML (BeautifulSoup).
        html: Raw HTML string (used for script-src regex scans).
        headers: HTTP response headers (case-insensitive dict ideally).
        cookies: Cookie jar {name: value} from the fetch.

    Returns:
        BotChallengeResult. .detected=True means the caller should skip the
        homepage 10-pillar audit. The site-wide DFS crawl is independent
        and should continue (link graph / TIPR / clusters consume DFS data,
        not this homepage fetch).
    """
    headers = headers or {}
    cookies = cookies or {}
    signals: list[str] = []

    # Approach 1: vendor signatures (high confidence)
    vendor = _check_cloudflare(soup, html, cookies, signals)
    if vendor is None:
        vendor = _check_akamai(soup, cookies, signals)
    if vendor is None:
        vendor = _check_datadome(soup, cookies, signals)
    if vendor is None:
        vendor = _check_perimeterx(soup, cookies, signals)

    if vendor is not None:
        return BotChallengeResult(
            detected=True,
            vendor=vendor,
            signals=signals,
            confidence=0.95,
            reason=f"Detected {vendor} bot protection via {signals[0]}",
        )

    # Approach 2: content heuristic (medium confidence)
    body = soup.find("body")
    if body is None:
        return BotChallengeResult(detected=False)
    body_text = body.get_text(separator=" ", strip=True)
    word_count = len(body_text.split()) if body_text else 0
    script_count = len(soup.find_all("script"))
    has_keyword = bool(_CHALLENGE_KEYWORDS.search(body_text))

    # Semantic landmark ratio — how much of the body text lives inside
    # real structural landmarks vs raw divs / scripts.
    landmarks = soup.find_all(["header", "nav", "main", "footer", "article", "section", "aside"])
    semantic_text = " ".join(el.get_text(separator=" ", strip=True) for el in landmarks)
    semantic_ratio = (len(semantic_text) / len(body_text)) if body_text else 0.0

    heuristic_signals: list[str] = []
    if word_count < _HEURISTIC_MIN_WORDS:
        heuristic_signals.append(f"low_word_count={word_count}")
    if script_count >= _HEURISTIC_MIN_SCRIPTS:
        heuristic_signals.append(f"high_script_count={script_count}")
    if has_keyword:
        heuristic_signals.append("challenge_keyword_present")
    if semantic_ratio < _HEURISTIC_NEAR_ZERO_SEMANTIC_RATIO and word_count < _HEURISTIC_MIN_WORDS:
        heuristic_signals.append(f"near_zero_semantic_ratio={semantic_ratio:.3f}")

    # Trigger: low words AND many scripts AND (keyword OR near-zero semantic
    # ratio). The conjunction is what distinguishes a challenge page from a
    # legit splash page (low words but normal scripts + real landmarks) or a
    # heavy SPA (many scripts but plenty of real content).
    triggered = (
        word_count < _HEURISTIC_MIN_WORDS
        and script_count >= _HEURISTIC_MIN_SCRIPTS
        and (has_keyword or semantic_ratio < _HEURISTIC_NEAR_ZERO_SEMANTIC_RATIO)
    )

    if triggered:
        return BotChallengeResult(
            detected=True,
            vendor="unknown",
            signals=["content_heuristic", *heuristic_signals],
            confidence=0.75,
            reason=(
                f"Content heuristic: {word_count} words, {script_count} scripts, "
                f"keyword={has_keyword}, semantic_ratio={semantic_ratio:.3f}"
            ),
        )

    return BotChallengeResult(detected=False)


# ---------------------------------------------------------------------------
# Vendor-specific helpers
# ---------------------------------------------------------------------------


def _check_cloudflare(
    soup: BeautifulSoup, html: str, cookies: dict[str, Any], signals: list[str]
) -> Optional[str]:
    for selector, signal_name in _CLOUDFLARE_SELECTORS:
        if soup.select_one(selector):
            signals.append(signal_name)
            return "cloudflare"
    for pattern in _CLOUDFLARE_SCRIPT_PATTERNS:
        if pattern.search(html):
            signals.append(f"cloudflare_script:{pattern.pattern}")
            return "cloudflare"
    matched_cookie = next((c for c in _CLOUDFLARE_COOKIES if c in cookies), None)
    if matched_cookie:
        signals.append(f"cloudflare_cookie:{matched_cookie}")
        return "cloudflare"
    return None


def _check_akamai(
    soup: BeautifulSoup, cookies: dict[str, Any], signals: list[str]
) -> Optional[str]:
    for selector, signal_name in _AKAMAI_SELECTORS:
        if soup.select_one(selector):
            signals.append(signal_name)
            return "akamai"
    matched_cookie = next((c for c in _AKAMAI_COOKIES if c in cookies), None)
    if matched_cookie:
        signals.append(f"akamai_cookie:{matched_cookie}")
        return "akamai"
    return None


def _check_datadome(
    soup: BeautifulSoup, cookies: dict[str, Any], signals: list[str]
) -> Optional[str]:
    for selector, signal_name in _DATADOME_SELECTORS:
        if soup.select_one(selector):
            signals.append(signal_name)
            return "datadome"
    matched_cookie = next((c for c in _DATADOME_COOKIES if c in cookies), None)
    if matched_cookie:
        signals.append(f"datadome_cookie:{matched_cookie}")
        return "datadome"
    return None


def _check_perimeterx(
    soup: BeautifulSoup, cookies: dict[str, Any], signals: list[str]
) -> Optional[str]:
    for selector, signal_name in _PERIMETERX_SELECTORS:
        if soup.select_one(selector):
            signals.append(signal_name)
            return "perimeterx"
    matched_cookie = next((c for c in _PERIMETERX_COOKIES if c in cookies), None)
    if matched_cookie:
        signals.append(f"perimeterx_cookie:{matched_cookie}")
        return "perimeterx"
    return None
