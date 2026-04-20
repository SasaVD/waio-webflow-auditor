"""Threshold + error-message coverage for Content Optimizer engine.

Guards the policy that:
- 2 extracted competitor pages is enough (minimum = 2, not 3).
- When extraction falls below the minimum, the failure message names the hosts
  that failed and why so the user can act on it.
"""
import asyncio
import sys
import types
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _install_fake_db_router(state: dict) -> None:
    """Register a stub db_router module so engine.py's runtime `from db_router import ...`
    resolves without pulling in aiosqlite/asyncpg."""
    fake = types.ModuleType("db_router")

    async def get_audit_by_id(_audit_id):
        return {"id": _audit_id, "report_json": state["report_json"]}

    async def update_audit_report(_audit_id, patch):
        for k, v in patch.items():
            state["report_json"][k] = v
        return True

    fake.get_audit_by_id = get_audit_by_id
    fake.update_audit_report = update_audit_report
    sys.modules["db_router"] = fake


import content_optimizer.content_extractor as extractor_mod  # noqa: E402
from content_optimizer import engine as engine_mod  # noqa: E402


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def stub_db():
    state = {"report_json": {}}
    _install_fake_db_router(state)
    yield state
    sys.modules.pop("db_router", None)


@pytest.fixture
def stub_serp(monkeypatch):
    async def fake_fetch_serp_results(keyword, num_results=20):
        return [
            {"url": f"https://competitor{i}.example/page", "title": f"c{i}", "position": i}
            for i in range(1, 11)
        ]

    monkeypatch.setattr(engine_mod, "fetch_serp_results", fake_fetch_serp_results)


def test_word_count_floor_is_200_not_300():
    """Thin but legitimate service pages (~200 words) must survive extraction."""
    assert extractor_mod._MIN_WORDS_AFTER_FILTER == 200


def test_two_successful_extractions_now_pass_the_minimum(stub_db, stub_serp, monkeypatch):
    """With exactly 2 successful competitor extractions, analysis should run to completion."""
    sample_text = " ".join(["webflow"] * 220)

    async def fake_extract(urls, **kwargs):
        results = []
        for i, u in enumerate(urls):
            if i < 2:
                results.append({"url": u, "text": sample_text, "word_count": 220, "success": True, "error": None})
            else:
                results.append({"url": u, "text": "", "word_count": 0, "success": False, "error": "fetch timeout"})
        return results

    monkeypatch.setattr(engine_mod, "extract_content_from_urls", fake_extract)

    _run(engine_mod.run_content_optimization(
        audit_id="test-audit",
        target_url="https://example.com/services",
        target_text=" ".join(["webflow"] * 250),
        keyword="webflow development services",
        num_competitors=10,
    ))

    analyses = stub_db["report_json"]["content_optimizer"]["analyses"]
    entry = next(iter(analyses.values()))
    assert entry["status"] == "ok", entry.get("error")
    assert entry["result"]["competitors_analyzed"] == 2


def test_failure_message_names_failed_hosts_and_reasons(stub_db, stub_serp, monkeypatch):
    """When extraction produces <2 competitors, error lists hosts + reasons, not just a count."""
    async def fake_extract(urls, **kwargs):
        return [
            {"url": "https://webflow.com/ai", "text": "", "word_count": 0, "success": False, "error": "Bot-protection page detected ('cloudflare')"},
            {"url": "https://framer.com/features", "text": "", "word_count": 0, "success": False, "error": "Content too short after extraction (48 words, need 200)"},
            *[
                {"url": u, "text": "", "word_count": 0, "success": False, "error": "fetch timeout"}
                for u in urls[2:]
            ],
        ]

    monkeypatch.setattr(engine_mod, "extract_content_from_urls", fake_extract)

    _run(engine_mod.run_content_optimization(
        audit_id="test-audit",
        target_url="https://example.com/services",
        target_text="webflow " * 100,
        keyword="webflow",
        num_competitors=10,
    ))

    analyses = stub_db["report_json"]["content_optimizer"]["analyses"]
    entry = next(iter(analyses.values()))
    assert entry["status"] == "failed"
    err = entry["error"]
    assert "webflow.com" in err
    assert "framer.com" in err
    assert "cloudflare" in err.lower() or "bot-protection" in err.lower()
    assert "need at least 2" in err
