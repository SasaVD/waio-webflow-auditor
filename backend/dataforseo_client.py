"""
DataForSEO On-Page API async client.
Sprint 3A: Handles task creation with pingback support,
status polling, and paginated retrieval of pages/links.

Credentials: DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD env vars (Basic Auth).
Cost: ~$2.50 per 2,000-page site with JS rendering.
All GET endpoints (pages, links, summary) are FREE after task completes.
"""
import base64
import logging
import os
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

_USE_SANDBOX = os.environ.get("DATAFORSEO_USE_SANDBOX", "").lower() in ("true", "1", "yes")
BASE_URL = "https://sandbox.dataforseo.com/v3/on_page" if _USE_SANDBOX else "https://api.dataforseo.com/v3/on_page"

if _USE_SANDBOX:
    logger.info("Using DataForSEO SANDBOX mode")
else:
    logger.info("Using DataForSEO LIVE mode")


class DataForSEOError(Exception):
    """Raised when the DataForSEO API returns an error status."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"DataForSEO error {status_code}: {message}")


class DataForSEOClient:
    """Async client for the DataForSEO On-Page API.

    Usage:
        client = DataForSEOClient()
        task = await client.create_task("https://example.com", max_crawl_pages=2000)
        # ... wait for pingback or poll ...
        summary = await client.get_summary(task["task_id"])
        pages = await client.get_all_pages(task["task_id"])
        links = await client.get_all_links(task["task_id"])
        await client.close()
    """

    def __init__(self):
        login = os.environ.get("DATAFORSEO_LOGIN")
        password = os.environ.get("DATAFORSEO_PASSWORD")
        if not login or not password:
            raise ValueError("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD env vars required")

        creds = base64.b64encode(f"{login}:{password}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
        }
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self._headers,
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _check_response(self, data: dict) -> None:
        """Validate top-level API response."""
        status = data.get("status_code", 0)
        if status != 20000:
            msg = data.get("status_message", "Unknown error")
            raise DataForSEOError(status, msg)

    # ── Task Creation ──────────────────────────────────────────────

    async def create_task(
        self,
        target_url: str,
        max_crawl_pages: int = 2000,
        pingback_url: str | None = None,
        tag: str | None = None,
    ) -> Dict[str, Any]:
        """Submit an On-Page crawl task.

        Args:
            target_url: The URL/domain to crawl.
            max_crawl_pages: Max pages to crawl (capped at 5000).
            pingback_url: URL DataForSEO GETs when crawl finishes.
                          Use $id placeholder for task ID substitution.
            tag: User-defined tag (e.g. audit_id) — returned in pingback as $tag.

        Returns:
            Dict with task_id, status_code, status_message.
        """
        task_data: Dict[str, Any] = {
            "target": target_url,
            "max_crawl_pages": min(max_crawl_pages, 5000),
            "enable_javascript": True,
            "load_resources": True,
            "store_raw_html": False,
        }
        if pingback_url:
            task_data["pingback_url"] = pingback_url
        if tag:
            task_data["tag"] = tag

        client = await self._get_client()
        resp = await client.post(f"{BASE_URL}/task_post", json=[task_data])
        resp.raise_for_status()
        data = resp.json()
        self._check_response(data)

        tasks = data.get("tasks", [])
        if not tasks:
            raise DataForSEOError(0, "No tasks returned from task_post")

        task = tasks[0]
        task_status = task.get("status_code", 0)
        if task_status != 20100:
            raise DataForSEOError(
                task_status, task.get("status_message", "Task creation failed")
            )

        return {
            "task_id": task["id"],
            "status_code": task_status,
            "status_message": task.get("status_message"),
        }

    # ── Summary / Status ───────────────────────────────────────────

    async def get_summary(self, task_id: str) -> Dict[str, Any]:
        """Get crawl task summary — progress, page counts, broken links, etc."""
        client = await self._get_client()
        resp = await client.get(f"{BASE_URL}/summary/{task_id}")
        resp.raise_for_status()
        data = resp.json()
        self._check_response(data)

        tasks = data.get("tasks", [])
        if not tasks or not tasks[0].get("result"):
            return {"crawl_progress": "unknown", "pages_count": 0}

        result = tasks[0]["result"][0]
        return {
            "crawl_progress": result.get("crawl_progress", "unknown"),
            "crawl_status": result.get("crawl_status", {}),
            "pages_count": result.get("pages_count", 0),
            "pages_crawled": result.get("pages_crawled", 0),
            "internal_links_count": result.get("internal_links_count", 0),
            "external_links_count": result.get("external_links_count", 0),
            "broken_links": result.get("broken_links", 0),
            "broken_resources": result.get("broken_resources", 0),
            "duplicate_content": result.get("duplicate_content", {}),
            "checks": result.get("checks", {}),
        }

    # ── Pages ──────────────────────────────────────────────────────

    async def get_pages(
        self,
        task_id: str,
        limit: int = 1000,
        offset: int = 0,
        filters: list | None = None,
    ) -> Dict[str, Any]:
        """Get crawled pages with SEO metrics. Max 1000 per request."""
        body: Dict[str, Any] = {
            "id": task_id,
            "limit": min(limit, 1000),
            "offset": offset,
        }
        if filters:
            body["filters"] = filters

        client = await self._get_client()
        resp = await client.post(f"{BASE_URL}/pages", json=[body])
        resp.raise_for_status()
        data = resp.json()
        self._check_response(data)

        tasks = data.get("tasks", [])
        if not tasks or not tasks[0].get("result"):
            return {"items": [], "total_count": 0}

        result = tasks[0]["result"][0]
        return {
            "items": result.get("items", []),
            "total_count": result.get("items_count", 0),
        }

    async def get_all_pages(self, task_id: str) -> List[Dict[str, Any]]:
        """Fetch all pages with automatic pagination."""
        all_items: List[Dict[str, Any]] = []
        offset = 0
        while True:
            result = await self.get_pages(task_id, limit=1000, offset=offset)
            items = result["items"]
            all_items.extend(items)
            total = result["total_count"]
            offset += len(items)
            if offset >= total or not items:
                break
            logger.info(f"DataForSEO pages: fetched {offset}/{total} for task {task_id}")
        return all_items

    # ── Links ──────────────────────────────────────────────────────

    async def get_links(
        self,
        task_id: str,
        limit: int = 1000,
        offset: int = 0,
        filters: list | None = None,
    ) -> Dict[str, Any]:
        """Get link data. Max 1000 per request."""
        body: Dict[str, Any] = {
            "id": task_id,
            "limit": min(limit, 1000),
            "offset": offset,
        }
        if filters:
            body["filters"] = filters

        client = await self._get_client()
        resp = await client.post(f"{BASE_URL}/links", json=[body])
        resp.raise_for_status()
        data = resp.json()
        self._check_response(data)

        tasks = data.get("tasks", [])
        if not tasks or not tasks[0].get("result"):
            return {"items": [], "total_count": 0}

        result = tasks[0]["result"][0]
        return {
            "items": result.get("items", []),
            "total_count": result.get("items_count", 0),
        }

    async def get_all_links(self, task_id: str) -> List[Dict[str, Any]]:
        """Fetch all links with automatic pagination."""
        all_items: List[Dict[str, Any]] = []
        offset = 0
        while True:
            result = await self.get_links(task_id, limit=1000, offset=offset)
            items = result["items"]
            all_items.extend(items)
            total = result["total_count"]
            offset += len(items)
            if offset >= total or not items:
                break
            logger.info(f"DataForSEO links: fetched {offset}/{total} for task {task_id}")
        return all_items

    # ── Resources ──────────────────────────────────────────────────

    async def get_resources(
        self,
        task_id: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get page resources (JS, CSS, images). Max 1000 per request."""
        body: Dict[str, Any] = {
            "id": task_id,
            "limit": min(limit, 1000),
            "offset": offset,
        }

        client = await self._get_client()
        resp = await client.post(f"{BASE_URL}/resources", json=[body])
        resp.raise_for_status()
        data = resp.json()
        self._check_response(data)

        tasks = data.get("tasks", [])
        if not tasks or not tasks[0].get("result"):
            return {"items": [], "total_count": 0}

        result = tasks[0]["result"][0]
        return {
            "items": result.get("items", []),
            "total_count": result.get("items_count", 0),
        }


def is_configured() -> bool:
    """Check if DataForSEO credentials are available in the environment."""
    return bool(
        os.environ.get("DATAFORSEO_LOGIN") and os.environ.get("DATAFORSEO_PASSWORD")
    )
