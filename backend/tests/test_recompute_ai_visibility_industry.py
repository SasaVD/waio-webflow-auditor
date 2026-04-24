"""Integration test: POST /api/audit/{audit_id}/recompute-ai-visibility must
accept a target_industry body field, persist it on the audit's report, and
invoke run_ai_visibility_analysis with the override threaded through.

This locks Contract 4 of Workstream D3.
"""
import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import main  # noqa: E402


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_recompute_accepts_target_industry_and_threads_to_engine(monkeypatch):
    """POST body ``{"target_industry": "..."}`` → engine receives the same
    value via ``target_industry=`` kwarg, and the report_json is updated
    with ``audit_config.target_industry`` for round-trip persistence."""

    audit_id = "00000000-0000-0000-0000-000000000001"

    async def fake_get_audit(aid):
        assert str(aid) == audit_id
        return {
            "id": audit_id,
            "url": "https://example.com",
            "report_json": {
                "ai_visibility": {
                    "last_computed_status": "ok",
                    "cumulative_cost_usd": 0.0,
                },
            },
        }

    partial_updates = []

    async def fake_update_audit_report(aid, partial, *args, **kwargs):
        partial_updates.append((str(aid), partial))

    monkeypatch.setattr(main, "get_audit_by_id", fake_get_audit, raising=True)
    monkeypatch.setattr(
        main, "update_audit_report", fake_update_audit_report, raising=True
    )

    # DataForSEO must appear configured so the endpoint doesn't 503
    monkeypatch.setattr(main, "is_dataforseo_configured", lambda: True)

    # Budget cap check — avoid real DB call
    class _FakeRow(dict):
        def __getitem__(self, key):
            return super().__getitem__(key)

    class _FakeConn:
        async def fetchrow(self, *_a, **_kw):
            return _FakeRow({"total": 0})

        async def execute(self, *_a, **_kw):
            return None

    class _AcquireCtx:
        async def __aenter__(self):
            return _FakeConn()

        async def __aexit__(self, *exc):
            return False

    class _FakePool:
        def acquire(self):
            return _AcquireCtx()

    async def fake_get_pool():
        return _FakePool()

    # db_postgres is imported lazily inside the endpoint, so patch both just
    # in case (module-level and callable-level).
    import db_postgres
    monkeypatch.setattr(db_postgres, "get_pool", fake_get_pool, raising=True)

    # Capture invocation args for run_ai_visibility_analysis. The endpoint
    # wraps it in asyncio.create_task() — for deterministic inspection we
    # replace create_task with an eager runner that pulls kwargs out of the
    # coroutine frame before closing it. No coroutine warnings, no pending
    # task lifecycle, just a snapshot of the call args.
    engine_calls: list[dict] = []

    def capturing_create_task(coro, *args, **kwargs):
        try:
            frame_locals = dict(coro.cr_frame.f_locals) if coro.cr_frame else {}
        except Exception:
            frame_locals = {}
        engine_calls.append(frame_locals)
        coro.close()

        async def _noop():
            return None

        # Return a real Task so the endpoint's caller can treat it as one if
        # it ever inspects the return value. Uses the currently-running loop.
        loop = asyncio.get_event_loop()
        return loop.create_task(_noop())

    async def fake_engine(audit_id, brand_override=None, target_industry=None):
        # Unused — capturing_create_task reads args out of the coroutine frame
        # before it would ever execute. This stub is here so create_task has
        # a real coroutine to wrap.
        return None

    monkeypatch.setattr(main, "run_ai_visibility_analysis", fake_engine)
    monkeypatch.setattr(main.asyncio, "create_task", capturing_create_task)

    # Run the endpoint
    body = {"target_industry": "/Arts & Entertainment/Events"}
    _run(main.recompute_ai_visibility(audit_id=audit_id, body=body))

    # The engine was called once with the target_industry kwarg
    assert len(engine_calls) == 1, f"expected 1 engine call, got {len(engine_calls)}"
    frame_locals = engine_calls[0]
    # The endpoint passes audit_id as a positional or kwarg; normalize:
    passed_industry = frame_locals.get("target_industry")
    assert passed_industry == "/Arts & Entertainment/Events", (
        f"target_industry was not threaded through: {frame_locals!r}"
    )

    # Contract 4: report_json carries audit_config.target_industry after the
    # endpoint persists the override. At least one of the partial updates
    # must carry the target_industry reference so the user's choice survives
    # page reloads.
    any_reference = any(
        "/Arts & Entertainment/Events" in json.dumps(p)
        for _aid, p in partial_updates
    )
    assert any_reference, (
        "expected at least one DB update to carry the user's target_industry "
        f"but got: {partial_updates!r}"
    )
