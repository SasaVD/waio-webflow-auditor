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

    async with httpx.AsyncClient(headers=headers, timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        # --- Probe 1: LLM Mentions Aggregated Metrics ---
        print("\n=== Probe 1: LLM Mentions Aggregated Metrics (keyword='webflow') ===")
        try:
            resp = await client.post(
                f"{AI_OPT_BASE_URL}/llm_mentions/aggregated_metrics/live",
                json=[{
                    "target": [
                        {"keyword": "webflow", "search_filter": "include", "search_scope": ["any"]},
                    ],
                }],
            )
            print(f"  HTTP Status: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status_code", 0)
            print(f"  API Status: {status} ({data.get('status_message', '?')})")
            tasks = data.get("tasks", [])
            if tasks:
                task = tasks[0]
                print(f"  Task Status: {task.get('status_code')} ({task.get('status_message', '?')})")
                print(f"  Cost: ${task.get('cost', 0):.4f}")
                if task.get("result"):
                    result = task["result"][0]
                    total = result.get("total", {})
                    platforms = total.get("platform", [])
                    print(f"  Platform groups: {len(platforms)}")
                    for p in platforms:
                        print(f"    {p.get('key')}: mentions={p.get('mentions')}, volume={p.get('ai_search_volume')}, impressions={p.get('impressions')}")
                    # Show top-level keys for schema verification
                    print(f"  Result top-level keys: {list(result.keys())}")
                    if total:
                        print(f"  Total group keys: {list(total.keys())}")
                else:
                    print(f"  No result data.")
                    print(f"  Task keys: {list(task.keys())}")
            else:
                print(f"  No tasks returned. Full response:")
                print(f"  {json.dumps(data, indent=2)[:1000]}")
        except httpx.HTTPStatusError as e:
            print(f"  HTTP ERROR {e.response.status_code}: {e.response.text[:500]}")
            print("  >>> AI Optimization subscription may not be active <<<")
        except Exception as e:
            print(f"  FAILED: {e}")

        # --- Probe 2: LLM Responses (ChatGPT, cheapest model) ---
        print("\n=== Probe 2: LLM Responses (engine=chat_gpt, model=gpt-4o-mini) ===")
        try:
            resp = await client.post(
                f"{AI_OPT_BASE_URL}/chat_gpt/llm_responses/live",
                json=[{
                    "user_prompt": "best website builders 2026",
                    "model_name": "gpt-4o-mini",
                }],
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
            print(f"  HTTP Status: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status_code", 0)
            print(f"  API Status: {status} ({data.get('status_message', '?')})")
            tasks = data.get("tasks", [])
            if tasks:
                task = tasks[0]
                print(f"  Task Status: {task.get('status_code')} ({task.get('status_message', '?')})")
                print(f"  Task Cost: ${task.get('cost', 0):.4f}")
                if task.get("result"):
                    result = task["result"][0]
                    print(f"  Model: {result.get('model_name')}")
                    print(f"  Input tokens: {result.get('input_tokens')}")
                    print(f"  Output tokens: {result.get('output_tokens')}")
                    print(f"  money_spent: ${result.get('money_spent', 0):.4f}")
                    # Extract text from sections
                    texts = []
                    for item in result.get("items", []):
                        print(f"  Item type: {item.get('type')}")
                        if item.get("type") == "message":
                            for section in item.get("sections", []):
                                print(f"    Section type: {section.get('type')}, text length: {len(section.get('text', ''))}")
                                if section.get("text"):
                                    texts.append(section["text"])
                    full_text = "\n\n".join(texts)
                    print(f"  Full response length: {len(full_text)} chars")
                    print(f"  First 300 chars: {full_text[:300]}...")
                    print(f"  Result top-level keys: {list(result.keys())}")
                else:
                    print(f"  No result data.")
            else:
                print(f"  No tasks. Full response:")
                print(f"  {json.dumps(data, indent=2)[:1000]}")
        except httpx.TimeoutException:
            print("  TIMEOUT (>120s). LLM Responses can be slow.")
        except httpx.HTTPStatusError as e:
            print(f"  HTTP ERROR {e.response.status_code}: {e.response.text[:500]}")
        except Exception as e:
            print(f"  FAILED: {e}")

    print("\n=== Probe complete ===")


if __name__ == "__main__":
    asyncio.run(main())
