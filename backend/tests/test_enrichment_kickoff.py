"""Regression tests for AI Visibility kickoff during DFS enrichment.

Workstream D production fix (2026-04-27): the AI Visibility kickoff used
to live AFTER `_enrich_report_from_crawl`'s trivial-crawl early return
(main.py:1893). When DFS returned ≤1 page or 0 links — the bot-protected-
site signal — the function returned early and AI Visibility was never
scheduled, even though AI Visibility's data path is independent of the
DFS On-Page crawl. The smoking gun was Ticketmaster audit
9a954c09-768e-4f76-a776-56ffde7b138a where AI Visibility's blob was
literally absent from the report.

Fix lifted the kickoff into a small helper `_kickoff_ai_visibility_if_opted_in`
that runs at the top of `_enrich_report_from_crawl`, before any DFS data
is fetched. These tests lock that behavior.
"""
import asyncio
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Helper-level tests — fast, deterministic, exercise the lifted kickoff
# ---------------------------------------------------------------------------


def _make_kwarg_capturing_aiv_stub(captured: dict):
    """Build a stub for run_ai_visibility_analysis that records kwargs
    synchronously (at coroutine-construction time) then returns a no-op
    awaitable that asyncio.create_task can safely close. Avoids the
    nested-event-loop problem of trying to drive the real coroutine
    inside an already-running pytest loop."""

    def fake_run_aiv(**kwargs):
        captured.update(kwargs)

        async def _noop():
            return None

        return _noop()

    return fake_run_aiv


def _make_no_op_create_task():
    """asyncio.create_task replacement that consumes the no-op coroutine
    returned by _make_kwarg_capturing_aiv_stub without leaving a never-
    awaited warning."""

    def fake_create_task(coro):
        coro.close()
        return MagicMock()

    return fake_create_task


def test_kickoff_helper_schedules_task_when_opted_in(monkeypatch):
    """Happy path: ai_visibility_opt_in=True, brand + industry present →
    asyncio.create_task is called with run_ai_visibility_analysis and the
    expected kwargs."""
    import main

    audit_record = {
        "report_json": {
            "ai_visibility_opt_in": True,
            "ai_visibility_brand_name": "Ticketmaster",
            "target_industry": "Event ticketing",
        },
    }

    captured_kwargs: dict = {}
    monkeypatch.setattr(
        main, "run_ai_visibility_analysis", _make_kwarg_capturing_aiv_stub(captured_kwargs)
    )
    monkeypatch.setattr(main.asyncio, "create_task", _make_no_op_create_task())

    result = _run(
        main._kickoff_ai_visibility_if_opted_in(
            audit_id="abc-123", audit_record=audit_record
        )
    )

    assert result is True, "Expected True when a task was scheduled"
    assert captured_kwargs["audit_id"] == "abc-123"
    assert captured_kwargs["brand_override"] == "Ticketmaster"
    assert captured_kwargs["target_industry"] == "Event ticketing"


def test_kickoff_helper_skips_when_not_opted_in(monkeypatch):
    """ai_visibility_opt_in absent or False → no task scheduled."""
    import main

    audit_record = {
        "report_json": {
            "ai_visibility_opt_in": False,
            "ai_visibility_brand_name": "Acme",
        },
    }

    create_task_calls: list = []
    monkeypatch.setattr(
        main.asyncio,
        "create_task",
        lambda coro: (create_task_calls.append(coro), coro.close(), MagicMock())[2],
    )

    result = _run(
        main._kickoff_ai_visibility_if_opted_in(
            audit_id="abc-123", audit_record=audit_record
        )
    )

    assert result is False
    assert create_task_calls == []


def test_kickoff_helper_uses_audit_config_target_industry_when_top_level_missing(monkeypatch):
    """Compatibility path: older submissions persisted target_industry on
    audit_config rather than at the top level of the report. The kickoff
    falls back to that location."""
    import main

    audit_record = {
        "report_json": {
            "ai_visibility_opt_in": True,
            "ai_visibility_brand_name": "Cvent",
            # NOT at top level — only inside audit_config
            "audit_config": {"target_industry": "Event Management Software"},
        },
    }

    captured_kwargs: dict = {}
    monkeypatch.setattr(
        main, "run_ai_visibility_analysis", _make_kwarg_capturing_aiv_stub(captured_kwargs)
    )
    monkeypatch.setattr(main.asyncio, "create_task", _make_no_op_create_task())

    _run(
        main._kickoff_ai_visibility_if_opted_in(
            audit_id="cvent-1", audit_record=audit_record
        )
    )

    assert captured_kwargs.get("target_industry") == "Event Management Software"


# ---------------------------------------------------------------------------
# End-to-end regression: trivial-crawl path must still kick off AI Visibility
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trivial_crawl_still_kicks_off_ai_visibility(monkeypatch):
    """The exact production regression from Ticketmaster audit 9a954c09:
    DFS returns 1 page + 0 links → trivial-crawl early-return at main.py:~1893.
    Pre-fix, AI Visibility kickoff lived AFTER this return and was never
    reached. Post-fix, the kickoff fires before DFS data is even fetched.

    This test drives `_enrich_report_from_crawl` end-to-end with a stubbed
    DFS client that returns trivial data. AI Visibility kickoff MUST fire."""
    import main

    audit_id = "ticketmaster-regression-test"
    task_id = "dfs-task-001"

    async def fake_get_dataforseo_task(_task_id):
        return {"audit_id": audit_id}

    async def fake_get_audit_by_id(_audit_id):
        return {
            "url": "https://www.ticketmaster.com/",
            "report_json": {
                "ai_visibility_opt_in": True,
                "ai_visibility_brand_name": "Ticketmaster",
                "target_industry": "Event ticketing",
            },
        }

    update_calls: list = []

    async def fake_update_audit_report(audit_id, partial, *args, **kwargs):
        update_calls.append((audit_id, partial))

    monkeypatch.setattr(main, "get_dataforseo_task", fake_get_dataforseo_task)
    monkeypatch.setattr(main, "get_audit_by_id", fake_get_audit_by_id)
    monkeypatch.setattr(main, "update_audit_report", fake_update_audit_report)

    # Track AI Visibility kickoff via create_task interception
    aiv_kickoff_count = 0

    def fake_create_task(coro):
        nonlocal aiv_kickoff_count
        # Inspect the coroutine's qualname to decide what was scheduled.
        # We're agnostic about other create_task usages — only count
        # run_ai_visibility_analysis.
        qual = getattr(coro, "__qualname__", "") or getattr(getattr(coro, "cr_code", None), "co_qualname", "")
        if "run_ai_visibility_analysis" in qual:
            aiv_kickoff_count += 1
        coro.close()
        return MagicMock()

    monkeypatch.setattr(main.asyncio, "create_task", fake_create_task)

    # DFS client returns trivial data — the bot-protected-site signal
    class TrivialDFSClient:
        async def get_all_pages(self, _task_id):
            return [{"url": "https://www.ticketmaster.com/"}]  # 1 page

        async def get_all_links(self, _task_id):
            return []  # 0 links

        async def close(self):
            pass

    summary = {"pages_crawled": 1, "pages_count": 1, "internal_links_count": 0}

    await main._enrich_report_from_crawl(task_id, TrivialDFSClient(), summary)

    # The trivial-crawl early-return path persists crawl_status="no_data"
    no_data_writes = [u for u in update_calls if u[1].get("crawl_status") == "no_data"]
    assert no_data_writes, (
        "Expected the trivial-crawl branch to write crawl_status='no_data' "
        "— if missing, the fixture didn't reach the early-return path."
    )

    # The fix: AI Visibility kickoff must have fired despite the early return
    assert aiv_kickoff_count == 1, (
        f"Expected exactly 1 AI Visibility kickoff on the trivial-crawl path, "
        f"got {aiv_kickoff_count}. Pre-fix this was 0 because the kickoff "
        f"lived AFTER the early return. If this regresses, every bot-protected "
        f"audit will silently skip AI Visibility (production audit 9a954c09 "
        f"on 2026-04-27 was the smoking gun)."
    )
