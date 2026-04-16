"""Integration tests for AI Visibility engine (mocked DataForSEO)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from ai_visibility.schema import PromptTemplate
from ai_visibility.mentions_fetcher import fetch_mentions
from ai_visibility.responses_fetcher import fetch_responses
from ai_visibility.cost_tracker import CostTracker


# --- Mentions fetcher integration ---

@pytest.mark.asyncio
async def test_fetch_mentions_happy_path():
    mock_client = AsyncMock()
    mock_client.llm_mentions_aggregated.return_value = {
        "result": {
            "total_count": 103,
            "ai_search_volume": 156000,
            "impressions": 42300,
            "engines": {
                "google_ai_overview": {"count": 69},
                "chatgpt": {"count": 34},
            },
        },
        "money_spent": 0.05,
    }
    mock_client.llm_mentions_search.return_value = {
        "items": [
            {"keyword": "best agencies 2026", "count": 8, "engine": "chatgpt"},
        ],
        "money_spent": 0.03,
    }
    mock_client.llm_mentions_top_pages.return_value = {
        "items": [
            {"url": "https://example.com/page1", "count": 12},
        ],
        "money_spent": 0.02,
    }

    tracker = CostTracker()
    result = await fetch_mentions(mock_client, "Belt Creative", tracker)

    assert result.total == 103
    assert result.ai_search_volume == 156000
    assert result.by_platform["google_ai_overview"] == 69
    assert len(result.triggering_prompts) == 1
    assert len(result.top_pages) == 1
    assert abs(tracker.total - 0.10) < 0.001


@pytest.mark.asyncio
async def test_fetch_mentions_aggregated_fails_gracefully():
    mock_client = AsyncMock()
    mock_client.llm_mentions_aggregated.side_effect = Exception("API down")
    mock_client.llm_mentions_search.return_value = {"items": [], "money_spent": 0}
    mock_client.llm_mentions_top_pages.return_value = {"items": [], "money_spent": 0}

    tracker = CostTracker()
    result = await fetch_mentions(mock_client, "Belt Creative", tracker)

    # Should still return a result with zeros, not raise
    assert result.total == 0


# --- Responses fetcher integration ---

@pytest.mark.asyncio
async def test_fetch_responses_all_succeed():
    mock_client = AsyncMock()
    mock_client.llm_response.return_value = {
        "result": {"response_text": "Belt Creative is a great agency."},
        "money_spent": 0.10,
    }

    prompts = [
        PromptTemplate(id=1, category="discovery", text="best agencies"),
        PromptTemplate(id=2, category="discovery", text="top agencies"),
        PromptTemplate(id=3, category="discovery", text="agency services"),
        PromptTemplate(id=4, category="reputation", text="Belt Creative reviews"),
    ]
    tracker = CostTracker()
    result = await fetch_responses(mock_client, prompts, "Belt Creative", tracker)

    assert len(result.engines) == 4
    for engine_name, engine_result in result.engines.items():
        assert engine_result.status == "ok"
        assert engine_result.brand_mentioned_in == 4  # brand in every response


@pytest.mark.asyncio
async def test_fetch_responses_partial_failure():
    call_count = 0

    async def mock_llm_response(prompt, engine, timeout=120.0):
        nonlocal call_count
        call_count += 1
        if engine == "perplexity":
            import httpx
            raise httpx.TimeoutException("timeout")
        return {
            "result": {"response_text": "Belt Creative is great."},
            "money_spent": 0.10,
        }

    mock_client = AsyncMock()
    mock_client.llm_response = mock_llm_response

    prompts = [PromptTemplate(id=1, category="discovery", text="best agencies")]
    tracker = CostTracker()
    result = await fetch_responses(mock_client, prompts, "Belt Creative", tracker)

    assert result.engines["chatgpt"].status == "ok"
    assert result.engines["perplexity"].status == "failed"
    assert "timeout" in result.engines["perplexity"].error


@pytest.mark.asyncio
async def test_fetch_responses_all_fail():
    async def mock_llm_response(prompt, engine, timeout=120.0):
        raise Exception("everything is broken")

    mock_client = AsyncMock()
    mock_client.llm_response = mock_llm_response

    prompts = [PromptTemplate(id=1, category="discovery", text="test")]
    tracker = CostTracker()
    result = await fetch_responses(mock_client, prompts, "X", tracker)

    for engine_result in result.engines.values():
        assert engine_result.status == "failed"


@pytest.mark.asyncio
async def test_fetch_responses_brand_mention_counting():
    async def mock_llm_response(prompt, engine, timeout=120.0):
        if prompt == "Acme reviews":
            return {"result": {"response_text": "Acme Corp has great reviews."}, "money_spent": 0.1}
        return {"result": {"response_text": "Here are some agencies."}, "money_spent": 0.1}

    mock_client = AsyncMock()
    mock_client.llm_response = mock_llm_response

    prompts = [
        PromptTemplate(id=1, category="discovery", text="best agencies"),
        PromptTemplate(id=2, category="reputation", text="Acme reviews"),
    ]
    tracker = CostTracker()
    result = await fetch_responses(mock_client, prompts, "Acme", tracker)

    # Only the reputation prompt mentions "Acme"
    for engine_result in result.engines.values():
        if engine_result.status == "ok":
            assert engine_result.brand_mentioned_in == 1
