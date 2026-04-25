"""Workstream D6: PDF cover-callout + per-pillar reason for bot_challenge."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from pdf_export_generator import _build_cover, _build_pillar_scorecard


def _bot_challenged_report() -> dict:
    """Mirror the report shape post-D1 + D4."""
    bot_pillar = {"score": 0, "label": "Scan incomplete", "scan_status": "bot_challenged",
                  "checks": {}, "findings": [], "positive_findings": []}
    return {
        "url": "https://example.com",
        "overall_score": None,
        "overall_label": "Scan incomplete",
        "coverage_weight": 0.0,
        "categories": {
            "semantic_html": bot_pillar,
            "structured_data": bot_pillar,
            "aeo_content": bot_pillar,
            "css_quality": bot_pillar,
            "js_bloat": bot_pillar,
            "accessibility": bot_pillar,
            "rag_readiness": bot_pillar,
            "agentic_protocols": bot_pillar,
            "data_integrity": bot_pillar,
            "internal_linking": bot_pillar,
        },
        "bot_challenge": {
            "detected": True,
            "vendor": "cloudflare",
            "signals": ["challenge-success-text"],
            "reason": "Detected cloudflare bot protection via challenge-success-text",
            "confidence": 0.95,
        },
    }


def test_cover_includes_bot_challenge_block_when_detected():
    cover = _build_cover(_bot_challenged_report())
    bc = cover.get("bot_challenge")
    assert bc is not None
    assert bc["detected"] is True
    assert "cloudflare" in bc["vendor_display"].lower() or bc["vendor_display"] == "Cloudflare"
    assert "headline" in bc and isinstance(bc["headline"], str) and bc["headline"]
    assert "body" in bc and isinstance(bc["body"], str)


def test_cover_bot_challenge_block_is_none_when_undetected():
    report = _bot_challenged_report()
    report["bot_challenge"] = None
    cover = _build_cover(report)
    assert cover.get("bot_challenge") is None


def test_cover_unknown_vendor_uses_safe_fallback_label():
    report = _bot_challenged_report()
    report["bot_challenge"]["vendor"] = "unknown"
    cover = _build_cover(report)
    assert "unidentified" in cover["bot_challenge"]["vendor_display"].lower()


def test_pillar_card_carries_bot_challenge_reason_line():
    scorecard = _build_pillar_scorecard(_bot_challenged_report())
    flat_cards = [c for group in scorecard for c in group["cards"]]
    bot_cards = [c for c in flat_cards if c["scan_status"] == "bot_challenged"]
    assert len(bot_cards) > 0
    for card in bot_cards:
        assert card.get("reason_line") == "Bot protection detected"


def test_pillar_card_has_no_reason_line_when_failed_not_bot_challenged():
    """Generic auditor failures (scan_status='failed') don't get the bot
    protection reason line — that's reserved for bot_challenged specifically."""
    report = _bot_challenged_report()
    for cat in report["categories"].values():
        cat["scan_status"] = "failed"
    report["bot_challenge"] = None
    scorecard = _build_pillar_scorecard(report)
    flat_cards = [c for group in scorecard for c in group["cards"]]
    for card in flat_cards:
        assert card.get("reason_line") is None or card["reason_line"] != "Bot protection detected"


def test_pillar_card_ok_pillar_has_no_reason_line():
    """Negative control: ok pillars don't get any reason line."""
    report = _bot_challenged_report()
    for cat in report["categories"].values():
        cat["scan_status"] = "ok"
        cat["score"] = 80
        cat["label"] = "Good"
    report["bot_challenge"] = None
    scorecard = _build_pillar_scorecard(report)
    flat_cards = [c for group in scorecard for c in group["cards"]]
    for card in flat_cards:
        assert card.get("reason_line") in (None, "")
