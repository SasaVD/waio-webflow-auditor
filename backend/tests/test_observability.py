"""Unit tests for the bot-protection observability counter store.

The store is a process-local in-memory counter (multi-worker partitioning
is acceptable — telemetry is directional, not exact). Three event names
are surfaced via GET /api/admin/bot-protection-stats:
  - bot_challenge.detected
  - crawl_status.no_data
  - accessibility.scan_failed

These tests lock the counter shape independent of the wiring tests.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import observability  # noqa: E402


def test_record_event_increments_total(monkeypatch):
    observability.reset_for_test()
    observability.record_event("bot_challenge.detected", vendor="cloudflare")
    observability.record_event("bot_challenge.detected", vendor="cloudflare")
    observability.record_event("bot_challenge.detected", vendor="akamai")
    agg = observability.get_event_aggregates()

    assert agg["bot_challenge.detected"]["total"] == 3
    assert agg["bot_challenge.detected"]["by_vendor"]["cloudflare"] == 2
    assert agg["bot_challenge.detected"]["by_vendor"]["akamai"] == 1


def test_record_event_without_vendor_dimension():
    """Events without a vendor dim still increment total; by_vendor stays empty."""
    observability.reset_for_test()
    observability.record_event("crawl_status.no_data")
    observability.record_event("crawl_status.no_data")
    agg = observability.get_event_aggregates()

    assert agg["crawl_status.no_data"]["total"] == 2
    assert agg["crawl_status.no_data"]["by_vendor"] == {}


def test_get_event_aggregates_returns_iso8601_last_seen():
    observability.reset_for_test()
    observability.record_event("accessibility.scan_failed")
    agg = observability.get_event_aggregates()

    last_seen = agg["accessibility.scan_failed"]["last_seen_at"]
    assert last_seen is not None
    # ISO8601 with timezone offset — the "+" or "Z" anchors it.
    assert "T" in last_seen
    assert last_seen.endswith("+00:00") or last_seen.endswith("Z")


def test_record_event_separates_by_event_name():
    """Events with the same vendor under different event names stay separate."""
    observability.reset_for_test()
    observability.record_event("bot_challenge.detected", vendor="cloudflare")
    observability.record_event("accessibility.scan_failed", vendor="cloudflare")
    agg = observability.get_event_aggregates()

    assert agg["bot_challenge.detected"]["total"] == 1
    assert agg["accessibility.scan_failed"]["total"] == 1
    assert agg["bot_challenge.detected"]["by_vendor"]["cloudflare"] == 1
    assert agg["accessibility.scan_failed"]["by_vendor"]["cloudflare"] == 1


def test_reset_for_test_clears_all_counters():
    observability.record_event("bot_challenge.detected", vendor="cloudflare")
    observability.reset_for_test()
    agg = observability.get_event_aggregates()
    assert agg == {}


def test_get_event_aggregates_returns_a_copy():
    """Mutating the returned dict must not affect internal state — guards
    against a caller accidentally corrupting the in-memory counters."""
    observability.reset_for_test()
    observability.record_event("bot_challenge.detected", vendor="cloudflare")

    agg = observability.get_event_aggregates()
    agg["bot_challenge.detected"]["total"] = 9999
    agg["bot_challenge.detected"]["by_vendor"]["cloudflare"] = 9999

    fresh = observability.get_event_aggregates()
    assert fresh["bot_challenge.detected"]["total"] == 1
    assert fresh["bot_challenge.detected"]["by_vendor"]["cloudflare"] == 1
