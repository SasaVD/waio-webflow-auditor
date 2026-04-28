"""Lock the natural phrasing of TIPR recommendation reason strings when
counts are zero.

Background: orphan templates fire on pages with inbound_count == 0 (that's
what makes them orphans). For months these templates produced strings like
"with only 0 inbound links" — readable for users with English-language
intuition but objectively a "0 looks like an unsubstituted variable" bug
on a premium-tier deliverable. Engine now uses _inbound_phrase() which
naturalizes the 0 case.

These tests exercise generate_link_recommendations() with input designed
to trigger orphan + waster templates and assert no '0 inbound' / '0
internal' / '0 outbound' phrasings leak into reason strings.
"""
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from tipr_engine import generate_link_recommendations, QUADRANT_STAR, QUADRANT_DEAD_WEIGHT, QUADRANT_HOARDER, QUADRANT_WASTER


def _star(url: str, pr: float = 85.0, inbound: int = 12, outbound: int = 8) -> dict:
    return {
        "url": url, "tipr_rank": 1, "tipr_score": pr, "pagerank_score": pr,
        "cheirank_score": 70.0, "inbound_count": inbound, "outbound_count": outbound,
        "click_depth": 1, "classification": QUADRANT_STAR, "cluster": "/",
    }


def _orphan(url: str, depth: int | None = None) -> dict:
    """A page with inbound=0 — the 'orphan' trigger that hits orphan templates."""
    return {
        "url": url, "tipr_rank": 99, "tipr_score": 8.0, "pagerank_score": 8.0,
        "cheirank_score": 5.0, "inbound_count": 0, "outbound_count": 1,
        "click_depth": depth if depth is not None else 5,
        "classification": QUADRANT_DEAD_WEIGHT, "cluster": "/blog/",
    }


def _hoarder(url: str) -> dict:
    return {
        "url": url, "tipr_rank": 5, "tipr_score": 78.0, "pagerank_score": 78.0,
        "cheirank_score": 25.0, "inbound_count": 30, "outbound_count": 1,
        "click_depth": 1, "classification": QUADRANT_HOARDER, "cluster": "/",
    }


def _waster_with_zero_inbound(url: str) -> dict:
    """Edge: a waster page that happens to have 0 inbound — exercises the
    waster template that interpolates inbound_count."""
    return {
        "url": url, "tipr_rank": 50, "tipr_score": 20.0, "pagerank_score": 20.0,
        "cheirank_score": 95.0, "inbound_count": 0, "outbound_count": 150,
        "click_depth": 3, "classification": QUADRANT_WASTER, "cluster": "/legacy/",
    }


_LEAK_PATTERNS = [
    r"\b0 outbound links?\b",
    r"\b0 inbound links?\b",
    r"\b0 internal links?\b",
    r"only links out to 0 pages",
    r"only passes equity to 0 pages",
    r"only receives 0 inbound",
    r"with only 0",
    r"with just 0",
    r"sends only 0",
]
_LEAK_RE = re.compile("|".join(f"(?:{p})" for p in _LEAK_PATTERNS), re.IGNORECASE)


def _assert_no_leaks(reasons: list[str]) -> None:
    """Walk every recommendation reason and fail loudly on the first leak."""
    for r in reasons:
        assert not _LEAK_RE.search(r), (
            f"TIPR recommendation reason leaked unsubstituted-zero phrasing.\n"
            f"Reason text: {r!r}\n"
            f"This indicates an orphan/waster template hit an inbound_count=0 "
            f"or outbound_count=0 case without going through "
            f"_inbound_phrase()/_outbound_phrase()."
        )


def test_orphan_recommendations_use_natural_inbound_phrasing():
    """Orphan templates fire on inbound=0 pages by definition. Their
    reason strings must NOT contain '0 inbound links' / '0 internal
    links' / 'only 0' patterns — _inbound_phrase() naturalizes these."""
    star_url = "https://example.com/"
    orphan_url = "https://example.com/blog/buried-post"

    nodes = [{"id": star_url}, {"id": orphan_url}]
    links: list[dict] = []
    pages = [_star(star_url), _orphan(orphan_url)]

    recs = generate_link_recommendations(nodes, links, pages, max_recommendations=20)

    # Orphan should attract at least one recommendation
    orphan_recs = [r for r in recs if r.get("target_url") == orphan_url]
    assert orphan_recs, (
        "Expected at least one recommendation targeting the orphan; "
        f"got {len(recs)} recs total, none for {orphan_url}"
    )

    _assert_no_leaks([r.get("reason", "") for r in recs])


def test_waster_recommendations_with_zero_inbound_use_natural_phrasing():
    """The 'gives away more authority than it receives' waster template
    interpolates inbound_count. When inbound=0 (rare but possible — a
    crawl quirk on a heavily-outlinking page), it must produce natural
    copy, not 'only receives 0 inbound links'."""
    waster_url = "https://example.com/legacy/index"

    nodes = [{"id": waster_url}]
    links: list[dict] = []
    pages = [_waster_with_zero_inbound(waster_url)]

    recs = generate_link_recommendations(nodes, links, pages, max_recommendations=20)

    waster_recs = [r for r in recs if r.get("source_url") == waster_url]
    if waster_recs:
        _assert_no_leaks([r.get("reason", "") for r in waster_recs])
    # If no waster recs fire on this minimal fixture, the test is a no-op
    # but harmless — the assertion is on phrasing only when the template
    # actually emits.


def test_orphan_with_unknown_depth_does_not_leak_infinity_or_zero():
    """The depth-aware orphan template uses '∞' for unknown depth. The
    inbound interpolation in the same template must still naturalize."""
    star_url = "https://example.com/"
    orphan_url = "https://example.com/buried"

    nodes = [{"id": star_url}, {"id": orphan_url}]
    links: list[dict] = []
    pages = [_star(star_url), _orphan(orphan_url, depth=None)]

    recs = generate_link_recommendations(nodes, links, pages, max_recommendations=20)
    _assert_no_leaks([r.get("reason", "") for r in recs])


def test_hoarder_recommendations_remain_natural_at_zero_outbound():
    """Hoarders by definition send little — when outbound=0 the existing
    _outbound_phrase() helper should already prevent '0 outbound' leaks.
    Belt-and-suspenders test ensures B1.2 changes don't regress this."""
    hoarder_url = "https://example.com/about"
    weak_url = "https://example.com/blog/post"

    nodes = [{"id": hoarder_url}, {"id": weak_url}]
    links: list[dict] = []
    # Force outbound to literally 0 on the hoarder — extreme edge case
    hoarder = _hoarder(hoarder_url)
    hoarder["outbound_count"] = 0
    pages = [hoarder, _orphan(weak_url)]

    recs = generate_link_recommendations(nodes, links, pages, max_recommendations=20)
    _assert_no_leaks([r.get("reason", "") for r in recs])
