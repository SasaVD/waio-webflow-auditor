"""Integration tests for run_ai_visibility_analysis industry handling.

These exercise the wiring between resolve_industry() (Contract 5) and the
rest of the AI Visibility pipeline (build_prompts, blob assembly).

The two critical behaviours locked by these tests:

1. When resolve_industry returns (None, None), the engine MUST short-circuit
   before calling build_prompts (prevents the sched.com silent-fallback bug
   where prompts were generated with "business services" and then benchmarked
   against Accenture/McKinsey/Deloitte).
2. When target_industry is provided, it flows through into build_prompts
   AND the final blob carries industry.source="user_declared".
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from unittest.mock import AsyncMock, MagicMock


async def _fake_update_audit_report(audit_id, partial, *args, **kwargs):
    _fake_update_audit_report.calls.append((audit_id, partial))


_fake_update_audit_report.calls = []  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _reset_update_calls():
    _fake_update_audit_report.calls.clear()
    yield


@pytest.mark.asyncio
async def test_ai_visibility_skips_when_both_none_and_emits_needs_attention_status(monkeypatch):
    """Regression test for sched.com incident: when both target_industry and
    detected_industry are None, the engine must NOT call build_prompts and
    must emit last_computed_status='needs_industry_confirmation' with a
    null industry block."""
    import ai_visibility.engine as engine_module

    # DB adapters — stub with deterministic in-memory results
    async def fake_get_audit(audit_id):
        return {
            "url": "https://example.com",
            "report_json": {
                "nlp_analysis": {"detected_industry": None, "entities": []},
                # No ai_visibility.target_industry override either
            },
            "competitor_urls": [],
        }

    monkeypatch.setattr(
        "db_router.get_audit_by_id", fake_get_audit, raising=True
    )
    monkeypatch.setattr(
        "db_router.update_audit_report", _fake_update_audit_report, raising=True
    )

    # Hard guard: build_prompts MUST NOT be called on the (None, None) path
    def _must_not_call(*args, **kwargs):
        raise AssertionError(
            "build_prompts was called even though resolve_industry returned "
            "(None, None) — this is the sched.com regression."
        )

    monkeypatch.setattr(engine_module, "build_prompts", _must_not_call)

    # Stub resolve_brand so we get past stage 1 without needing NLP entities
    fake_brand = MagicMock(name="brand_info")
    fake_brand.name = "Example Brand"
    fake_brand.source = "auto"
    monkeypatch.setattr(engine_module, "resolve_brand", lambda *a, **kw: fake_brand)

    # Stub competitor resolution — not exercised on this path but must not crash
    fake_competitors = MagicMock()
    fake_competitors.domains = []
    fake_competitors.to_dict = lambda: {"domains": [], "source": "none"}
    monkeypatch.setattr(engine_module, "resolve_competitors", lambda *a, **kw: fake_competitors)

    await engine_module.run_ai_visibility_analysis(audit_id="abc-123")

    # The engine must have written a "needs_industry_confirmation" blob
    assert _fake_update_audit_report.calls, "expected at least one update_audit_report call"
    last_partial = _fake_update_audit_report.calls[-1][1]
    assert "ai_visibility" in last_partial
    blob = last_partial["ai_visibility"]
    assert blob["last_computed_status"] == "needs_industry_confirmation"
    assert blob["industry"] == {
        "value": None,
        "source": None,
        "user_provided": None,
    }


@pytest.mark.asyncio
async def test_ai_visibility_uses_user_declared_industry_in_prompts(monkeypatch):
    """When target_industry is set on the audit, it must flow into
    build_prompts and the resulting blob must reflect source='user_declared'."""
    import ai_visibility.engine as engine_module

    async def fake_get_audit(audit_id):
        return {
            "url": "https://example.com",
            "report_json": {
                "nlp_analysis": {"detected_industry": None, "entities": []},
                "ai_visibility": {
                    # Previously-stored user target (set at submission time)
                    "industry": {
                        "value": "/Arts & Entertainment/Events",
                        "source": "user_declared",
                        "user_provided": "/Arts & Entertainment/Events",
                    },
                },
                "target_industry": "/Arts & Entertainment/Events",
            },
            "competitor_urls": [],
        }

    monkeypatch.setattr("db_router.get_audit_by_id", fake_get_audit, raising=True)
    monkeypatch.setattr(
        "db_router.update_audit_report", _fake_update_audit_report, raising=True
    )

    build_prompts_calls = []

    def fake_build_prompts(industry, top_entity, brand_name):
        build_prompts_calls.append({"industry": industry, "brand_name": brand_name})
        from ai_visibility.schema import PromptTemplate

        return [
            PromptTemplate(id=1, category="discovery", text="best events software"),
            PromptTemplate(id=2, category="discovery", text="top events platforms"),
            PromptTemplate(id=3, category="discovery", text="events for small business"),
            PromptTemplate(id=4, category="reputation", text=f"{brand_name} reviews"),
        ]

    monkeypatch.setattr(engine_module, "build_prompts", fake_build_prompts)

    fake_brand = MagicMock(name="brand_info")
    fake_brand.name = "Example Events"
    fake_brand.source = "auto"
    monkeypatch.setattr(engine_module, "resolve_brand", lambda *a, **kw: fake_brand)

    fake_competitors = MagicMock()
    fake_competitors.domains = []
    fake_competitors.to_dict = lambda: {"domains": [], "source": "none"}
    monkeypatch.setattr(
        engine_module, "resolve_competitors", lambda *a, **kw: fake_competitors
    )

    # Stub DFS client + fetchers so we can run end-to-end without credentials
    fake_mentions = MagicMock()
    fake_mentions.to_dict = lambda: {"total": 0}

    async def fake_fetch_mentions(*a, **kw):
        return fake_mentions

    fake_engines = {
        "chatgpt": MagicMock(
            status="ok",
            to_dict=lambda: {"status": "ok"},
        )
    }
    fake_responses = MagicMock()
    fake_responses.engines = fake_engines
    fake_responses.to_dict = lambda: {"engines": {"chatgpt": {"status": "ok"}}}

    async def fake_fetch_responses(*a, **kw):
        return fake_responses

    monkeypatch.setattr(engine_module, "fetch_mentions", fake_fetch_mentions)
    monkeypatch.setattr(engine_module, "fetch_responses", fake_fetch_responses)

    class FakeDFSClient:
        async def close(self):
            pass

    monkeypatch.setattr(engine_module, "DataForSEOClient", FakeDFSClient)

    await engine_module.run_ai_visibility_analysis(audit_id="abc-456")

    # build_prompts was called with the user-declared industry
    assert build_prompts_calls, "build_prompts should have been called"
    assert build_prompts_calls[0]["industry"] == "/Arts & Entertainment/Events"

    # The final blob reflects the user_declared source + value
    assert _fake_update_audit_report.calls, "expected at least one update"
    # The final update is the full blob (possibly after the exec-summary
    # regeneration write); find the one containing ai_visibility with industry
    relevant = [
        c for c in _fake_update_audit_report.calls if "ai_visibility" in c[1] and isinstance(c[1]["ai_visibility"], dict) and "industry" in c[1]["ai_visibility"]
    ]
    assert relevant, "expected at least one blob update with an industry key"
    blob = relevant[-1][1]["ai_visibility"]
    assert blob["industry"]["value"] == "/Arts & Entertainment/Events"
    assert blob["industry"]["source"] == "user_declared"
    assert blob["industry"]["user_provided"] == "/Arts & Entertainment/Events"


@pytest.mark.asyncio
async def test_ai_visibility_uses_nlp_detected_when_no_user_override(monkeypatch):
    """When only NLP detected an industry (no user override), the blob should
    reflect source='nlp_detected' and build_prompts should get that value."""
    import ai_visibility.engine as engine_module

    async def fake_get_audit(audit_id):
        return {
            "url": "https://example.com",
            "report_json": {
                "nlp_analysis": {
                    "detected_industry": "/Business & Industrial/Advertising & Marketing",
                    "entities": [],
                },
            },
            "competitor_urls": [],
        }

    monkeypatch.setattr("db_router.get_audit_by_id", fake_get_audit, raising=True)
    monkeypatch.setattr(
        "db_router.update_audit_report", _fake_update_audit_report, raising=True
    )

    build_prompts_calls = []

    def fake_build_prompts(industry, top_entity, brand_name):
        build_prompts_calls.append({"industry": industry})
        from ai_visibility.schema import PromptTemplate

        return [PromptTemplate(id=i, category="discovery", text=f"p{i}") for i in (1, 2, 3, 4)]

    monkeypatch.setattr(engine_module, "build_prompts", fake_build_prompts)

    fake_brand = MagicMock(name="brand_info")
    fake_brand.name = "Acme Agency"
    fake_brand.source = "auto"
    monkeypatch.setattr(engine_module, "resolve_brand", lambda *a, **kw: fake_brand)

    fake_competitors = MagicMock()
    fake_competitors.domains = []
    fake_competitors.to_dict = lambda: {"domains": [], "source": "none"}
    monkeypatch.setattr(
        engine_module, "resolve_competitors", lambda *a, **kw: fake_competitors
    )

    async def fake_fetch_mentions(*a, **kw):
        m = MagicMock()
        m.to_dict = lambda: {"total": 0}
        return m

    async def fake_fetch_responses(*a, **kw):
        r = MagicMock()
        r.engines = {"chatgpt": MagicMock(status="ok", to_dict=lambda: {})}
        r.to_dict = lambda: {"engines": {}}
        return r

    monkeypatch.setattr(engine_module, "fetch_mentions", fake_fetch_mentions)
    monkeypatch.setattr(engine_module, "fetch_responses", fake_fetch_responses)

    class FakeDFSClient:
        async def close(self):
            pass

    monkeypatch.setattr(engine_module, "DataForSEOClient", FakeDFSClient)

    await engine_module.run_ai_visibility_analysis(audit_id="abc-789")

    assert build_prompts_calls[0]["industry"] == (
        "/Business & Industrial/Advertising & Marketing"
    )

    relevant = [
        c
        for c in _fake_update_audit_report.calls
        if "ai_visibility" in c[1]
        and isinstance(c[1]["ai_visibility"], dict)
        and "industry" in c[1]["ai_visibility"]
    ]
    assert relevant
    blob = relevant[-1][1]["ai_visibility"]
    assert blob["industry"]["value"] == (
        "/Business & Industrial/Advertising & Marketing"
    )
    assert blob["industry"]["source"] == "nlp_detected"
    assert blob["industry"]["user_provided"] is None
