"""
Probe script for DataForSEO AI Optimization API.
Makes ONE LLM Mentions call + ONE LLM Responses call.
Cost: ~$0.10. Run this first to verify subscription is active.

Usage:
    cd backend
    python -m scripts.probe_ai_visibility
"""
import asyncio
import base64
import os
import sys
import json

import httpx

AI_OPT_BASE_URL = "https://api.dataforseo.com/v3/ai_optimization"


async def main():
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        print("ERROR: Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD env vars")
        sys.exit(1)

    creds = base64.b64encode(f"{login}:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(headers=headers, timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        # --- Probe 1: LLM Mentions Aggregated ---
        print("\n=== Probe 1: LLM Mentions Aggregated (brand='webflow') ===")
        try:
            resp = await client.post(
                f"{AI_OPT_BASE_URL}/ai_search/aggregated_search_data/live",
                json=[{"keyword": "webflow", "engines": ["google_ai_overview", "chatgpt"]}],
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status_code", 0)
            print(f"  Status: {status} ({data.get('status_message', '?')})")
            tasks = data.get("tasks", [])
            if tasks and tasks[0].get("result"):
                result = tasks[0]["result"][0]
                print(f"  Total mentions: {result.get('total_count', '?')}")
                print(f"  Money spent: ${tasks[0].get('cost', 0):.4f}")
            else:
                print(f"  No result data. Full response:")
                print(f"  {json.dumps(data, indent=2)[:1000]}")
        except Exception as e:
            print(f"  FAILED: {e}")
            print("  >>> AI Optimization subscription may not be active <<<")

        # --- Probe 2: LLM Responses (single prompt, gemini) ---
        print("\n=== Probe 2: LLM Responses (engine='gemini', 1 prompt) ===")
        try:
            resp = await client.post(
                f"{AI_OPT_BASE_URL}/llm_responses/live",
                json=[{
                    "prompt": "best website builders 2026",
                    "engine": "gemini",
                }],
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status_code", 0)
            print(f"  Status: {status} ({data.get('status_message', '?')})")
            tasks = data.get("tasks", [])
            if tasks and tasks[0].get("result"):
                result = tasks[0]["result"][0]
                text = result.get("response_text", "")
                print(f"  Response length: {len(text)} chars")
                print(f"  First 200 chars: {text[:200]}...")
                print(f"  Money spent: ${tasks[0].get('cost', 0):.4f}")
            else:
                print(f"  No result data. Full response:")
                print(f"  {json.dumps(data, indent=2)[:1000]}")
        except httpx.TimeoutException:
            print("  TIMEOUT (>30s). LLM Responses can take up to 120s in production.")
        except Exception as e:
            print(f"  FAILED: {e}")

    print("\n=== Probe complete ===")


if __name__ == "__main__":
    asyncio.run(main())
