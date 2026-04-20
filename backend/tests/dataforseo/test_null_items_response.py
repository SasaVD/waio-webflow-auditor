"""Regression: DataForSEO returns `items: null` (not `[]`) when a crawl
completes with 0 pages — typically because the target site blocked the
crawler (Cloudflare / Akamai). The client must treat null the same as an
empty list; otherwise the outer enrichment task crashes with
`TypeError: 'NoneType' object is not iterable` (see loungelizard.com audit
on 2026-04-20, task 04201715-1562-0216-0000-d87b5f4851c3).
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DATAFORSEO_LOGIN", "test-login")
os.environ.setdefault("DATAFORSEO_PASSWORD", "test-password")

import dataforseo_client  # noqa: E402


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeHTTPXClient:
    """Captures POSTs and returns a pre-canned JSON payload."""

    def __init__(self, payload):
        self._payload = payload
        self.is_closed = False
        self.calls = []

    async def post(self, url, json=None):
        self.calls.append((url, json))
        return _FakeResponse(self._payload)

    async def aclose(self):
        self.is_closed = True


def _zero_page_payload():
    """Real shape observed from DataForSEO when crawl fetches 0 pages:
    result exists but `items` and `items_count` are null rather than empty."""
    return {
        "status_code": 20000,
        "status_message": "Ok.",
        "tasks": [
            {
                "status_code": 20000,
                "result": [
                    {
                        "crawl_progress": "finished",
                        "crawl_status": {"status": "finished", "max_crawl_pages": 100},
                        "total_items_count": 0,
                        "items_count": None,
                        "items": None,
                    }
                ],
            }
        ],
    }


@pytest.fixture
def null_items_client(monkeypatch):
    fake = _FakeHTTPXClient(_zero_page_payload())
    client = dataforseo_client.DataForSEOClient()

    async def _fake_get_client():
        return fake

    monkeypatch.setattr(client, "_get_client", _fake_get_client)
    return client, fake


def test_get_pages_treats_null_items_as_empty_list(null_items_client):
    client, _ = null_items_client
    result = _run(client.get_pages("task-abc"))
    assert result == {"items": [], "total_count": 0}


def test_get_links_treats_null_items_as_empty_list(null_items_client):
    client, _ = null_items_client
    result = _run(client.get_links("task-abc"))
    assert result == {"items": [], "total_count": 0}


def test_get_resources_treats_null_items_as_empty_list(null_items_client):
    client, _ = null_items_client
    result = _run(client.get_resources("task-abc"))
    assert result == {"items": [], "total_count": 0}


def test_get_all_links_does_not_crash_on_null_items(null_items_client):
    """The exact crash point: `all_items.extend(items)` used to throw
    TypeError when `items` was None. Must now return an empty list cleanly."""
    client, _ = null_items_client
    result = _run(client.get_all_links("task-abc"))
    assert result == []


def test_get_all_pages_does_not_crash_on_null_items(null_items_client):
    client, _ = null_items_client
    result = _run(client.get_all_pages("task-abc"))
    assert result == []
