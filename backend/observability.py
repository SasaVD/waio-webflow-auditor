"""In-memory counter store for bot-protection observability.

Surfaces aggregates via GET /api/admin/bot-protection-stats so we can
measure pre-vs-post-deploy rates of:
  - bot_challenge.detected (Workstream D1 outcome on the homepage path)
  - crawl_status.no_data (DataForSEO trivial-crawl path)
  - accessibility.scan_failed (Workstream E target metric)

Multi-worker partitioning is acceptable: counters are per-process. For a
one-week SEO-review observation window with 2-4 audits/day on a small
worker fleet, the per-worker partition is directionally correct.
Postgres-backed aggregation is filed for a follow-up if the signal needs
more precision later.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock
from typing import Any


_lock = Lock()
_counters: dict[str, dict[str, Any]] = defaultdict(
    lambda: {"total": 0, "by_vendor": defaultdict(int), "last_seen_at": None}
)


def record_event(event: str, **dims: Any) -> None:
    """Increment the counter for the given event name.

    Optional dims:
      - vendor: bucketed under by_vendor[vendor] (e.g. cloudflare, akamai).
        Other dims are accepted but currently ignored — kept on the
        signature so future dimensions don't require call-site updates.
    """
    with _lock:
        bucket = _counters[event]
        bucket["total"] += 1
        vendor = dims.get("vendor")
        if vendor:
            bucket["by_vendor"][vendor] += 1
        bucket["last_seen_at"] = datetime.now(timezone.utc).isoformat()


def get_event_aggregates() -> dict[str, dict[str, Any]]:
    """Return a deep copy of the current counter state.

    Defensive copy: callers can mutate the returned dict without affecting
    internal state. The admin endpoint serializes this to JSON.
    """
    with _lock:
        return {
            event: {
                "total": data["total"],
                "by_vendor": dict(data["by_vendor"]),
                "last_seen_at": data["last_seen_at"],
            }
            for event, data in _counters.items()
        }


def reset_for_test() -> None:
    """Clear all counters. Tests only — not exposed via any endpoint."""
    with _lock:
        _counters.clear()
