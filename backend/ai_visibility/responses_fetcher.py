"""Fetch live LLM responses with per-engine isolation."""
import asyncio
import logging
from typing import Any

import httpx
from dataforseo_client import DataForSEOClient, DataForSEOError
from .schema import EngineResult, PromptTemplate, ResponsesResult
from .cost_tracker import CostTracker

logger = logging.getLogger(__name__)

ENGINES = ["chatgpt", "claude", "gemini", "perplexity"]
CONCURRENCY = 4  # max simultaneous live calls


async def fetch_responses(
    client: DataForSEOClient,
    prompts: list[PromptTemplate],
    brand_name: str,
    cost_tracker: CostTracker,
) -> ResponsesResult:
    """Send prompts to all 4 engines with per-engine isolation.

    Each engine runs all 4 prompts sequentially.
    Engines run in parallel with Semaphore(4).
    A failing engine does not affect other engines.
    """
    sem = asyncio.Semaphore(CONCURRENCY)

    async def _fetch_engine(engine: str) -> EngineResult:
        async with sem:
            try:
                responses_by_prompt: dict[int, dict[str, Any]] = {}
                engine_cost = 0.0
                brand_mentioned_in = 0
                brand_lower = brand_name.lower()

                for prompt in prompts:
                    resp = await client.llm_response(
                        prompt.text, engine, timeout=120.0,
                    )
                    money = resp.get("money_spent", 0) or 0
                    cost_tracker.add(money)
                    engine_cost += money

                    result_data = resp.get("result", {})
                    response_text = result_data.get("response_text", "") or ""

                    responses_by_prompt[prompt.id] = {
                        "text": response_text[:2000],  # cap stored text
                        "mentioned": brand_lower in response_text.lower(),
                    }

                    if brand_lower in response_text.lower():
                        brand_mentioned_in += 1

                return EngineResult(
                    status="ok",
                    engine=engine,
                    responses_by_prompt=responses_by_prompt,
                    cost_usd=engine_cost,
                    brand_mentioned_in=brand_mentioned_in,
                )
            except httpx.TimeoutException:
                logger.warning(f"AI Visibility: {engine} timed out")
                return EngineResult(
                    status="failed", engine=engine,
                    error="timeout after 120s",
                )
            except DataForSEOError as e:
                logger.warning(f"AI Visibility: {engine} DataForSEO error: {e}")
                return EngineResult(
                    status="failed", engine=engine,
                    error=f"{e.status_code}: {e.message}",
                )
            except Exception as e:
                logger.exception(f"AI Visibility: {engine} unexpected error")
                return EngineResult(
                    status="failed", engine=engine,
                    error=f"unexpected: {type(e).__name__}: {str(e)[:200]}",
                )

    tasks = [_fetch_engine(engine) for engine in ENGINES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    engines_map: dict[str, EngineResult] = {}
    total_cost = 0.0
    for i, r in enumerate(results):
        engine = ENGINES[i]
        if isinstance(r, Exception):
            engines_map[engine] = EngineResult(
                status="failed", engine=engine,
                error=f"gather exception: {type(r).__name__}",
            )
        else:
            engines_map[engine] = r
            total_cost += r.cost_usd

    return ResponsesResult(engines=engines_map, cost_usd=total_cost)
