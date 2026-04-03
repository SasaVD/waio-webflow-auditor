"""
Google OAuth 2.0 + Search Console + Analytics 4 Data API client.
Sprint 3B: OAuth flow with encrypted token storage,
GSC search analytics / sitemaps / URL inspection,
GA4 traffic-per-URL for orphan prioritization.

Scopes:
  - https://www.googleapis.com/auth/webmasters.readonly  (GSC)
  - https://www.googleapis.com/auth/analytics.readonly    (GA4)

Credentials: GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET env vars.
Tokens encrypted at rest with Fernet (GOOGLE_TOKEN_KEY env var, auto-generated if missing).
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
]

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GSC_BASE = "https://www.googleapis.com/webmasters/v3"
GA4_BASE = "https://analyticsdata.googleapis.com/v1beta"
URL_INSPECTION_BASE = "https://searchconsole.googleapis.com/v1"

# ── Encryption helpers ────────────────────────────────────────────


def _get_fernet() -> Fernet:
    key = os.environ.get("GOOGLE_TOKEN_KEY")
    if not key:
        key = Fernet.generate_key().decode()
        os.environ["GOOGLE_TOKEN_KEY"] = key
        logger.warning(
            "GOOGLE_TOKEN_KEY not set — generated ephemeral key. "
            "Set this env var in Railway for persistent token encryption."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(data: dict) -> str:
    return _get_fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_token(encrypted: str) -> dict:
    return json.loads(_get_fernet().decrypt(encrypted.encode()).decode())


# ── OAuth flow ────────────────────────────────────────────────────


def is_configured() -> bool:
    return bool(
        os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")
    )


def get_auth_url(redirect_uri: str, state: str | None = None) -> str:
    """Build the Google OAuth consent URL."""
    params = {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str, redirect_uri: str) -> Dict[str, Any]:
    """Exchange authorization code for access + refresh tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        raise ValueError(f"Google token error: {data['error_description']}")

    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in", 3600),
        "token_type": data.get("token_type", "Bearer"),
        "scope": data.get("scope", ""),
        "obtained_at": datetime.now(timezone.utc).isoformat(),
    }


async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Use a refresh token to get a new access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        raise ValueError(f"Google refresh error: {data['error_description']}")

    return {
        "access_token": data["access_token"],
        "expires_in": data.get("expires_in", 3600),
        "token_type": data.get("token_type", "Bearer"),
        "obtained_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Authenticated request helper ──────────────────────────────────


async def _authed_request(
    method: str,
    url: str,
    token_data: dict,
    json_body: dict | None = None,
) -> dict:
    """Make an authenticated request, refreshing the token if expired."""
    obtained = datetime.fromisoformat(token_data["obtained_at"])
    expires_in = token_data.get("expires_in", 3600)
    age = (datetime.now(timezone.utc) - obtained).total_seconds()

    access_token = token_data["access_token"]
    if age > expires_in - 60:
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise ValueError("Access token expired and no refresh token available")
        refreshed = await refresh_access_token(refresh_token)
        access_token = refreshed["access_token"]
        token_data["access_token"] = access_token
        token_data["expires_in"] = refreshed["expires_in"]
        token_data["obtained_at"] = refreshed["obtained_at"]

    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            resp = await client.get(url, headers=headers)
        else:
            resp = await client.post(url, headers=headers, json=json_body)
        resp.raise_for_status()
        return resp.json()


# ── Google Search Console ─────────────────────────────────────────


async def gsc_list_sites(token_data: dict) -> List[Dict[str, str]]:
    """List all GSC properties the user has access to."""
    data = await _authed_request("GET", f"{GSC_BASE}/sites", token_data)
    return [
        {"site_url": s["siteUrl"], "permission_level": s["permissionLevel"]}
        for s in data.get("siteEntry", [])
    ]


async def gsc_search_analytics(
    token_data: dict,
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: List[str] | None = None,
    row_limit: int = 25000,
    start_row: int = 0,
) -> List[Dict[str, Any]]:
    """Query GSC Search Analytics. Returns rows with impressions, clicks, position per page."""
    body: Dict[str, Any] = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions or ["page"],
        "rowLimit": min(row_limit, 25000),
        "startRow": start_row,
    }
    url = f"{GSC_BASE}/sites/{_encode_site(site_url)}/searchAnalytics/query"
    data = await _authed_request("POST", url, token_data, json_body=body)
    return data.get("rows", [])


async def gsc_get_all_pages(
    token_data: dict,
    site_url: str,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """Paginate through all GSC pages (25,000 rows per request)."""
    all_rows: List[Dict[str, Any]] = []
    start_row = 0
    while True:
        rows = await gsc_search_analytics(
            token_data, site_url, start_date, end_date,
            dimensions=["page"], row_limit=25000, start_row=start_row,
        )
        all_rows.extend(rows)
        if len(rows) < 25000:
            break
        start_row += len(rows)
        logger.info(f"GSC search analytics: fetched {len(all_rows)} rows so far")
    return all_rows


async def gsc_list_sitemaps(
    token_data: dict,
    site_url: str,
) -> List[Dict[str, Any]]:
    """List sitemaps submitted to GSC for a property."""
    url = f"{GSC_BASE}/sites/{_encode_site(site_url)}/sitemaps"
    data = await _authed_request("GET", url, token_data)
    return [
        {
            "path": s.get("path"),
            "type": s.get("type"),
            "submitted": s.get("lastSubmitted"),
            "errors": s.get("errors", 0),
            "warnings": s.get("warnings", 0),
        }
        for s in data.get("sitemap", [])
    ]


async def gsc_inspect_url(
    token_data: dict,
    inspection_url: str,
    site_url: str,
) -> Dict[str, Any]:
    """Inspect a single URL in GSC. Rate-limited to 2,000/day/property."""
    body = {
        "inspectionUrl": inspection_url,
        "siteUrl": site_url,
    }
    data = await _authed_request(
        "POST",
        f"{URL_INSPECTION_BASE}/urlInspection/index:inspect",
        token_data,
        json_body=body,
    )
    result = data.get("inspectionResult", {})
    index_status = result.get("indexStatusResult", {})
    return {
        "verdict": index_status.get("verdict"),
        "coverage_state": index_status.get("coverageState"),
        "indexing_state": index_status.get("indexingState"),
        "last_crawl_time": index_status.get("lastCrawlTime"),
        "page_fetch_state": index_status.get("pageFetchState"),
        "robots_txt_state": index_status.get("robotsTxtState"),
        "crawled_as": index_status.get("crawledAs"),
        "referring_urls": index_status.get("referringUrls", []),
        "sitemap": index_status.get("sitemap", []),
    }


async def gsc_batch_inspect(
    token_data: dict,
    urls: List[str],
    site_url: str,
    max_inspections: int = 2000,
) -> List[Dict[str, Any]]:
    """Inspect multiple URLs, respecting the 2,000/day quota.
    Returns results for as many URLs as possible within the limit."""
    results: List[Dict[str, Any]] = []
    for url in urls[:max_inspections]:
        try:
            inspection = await gsc_inspect_url(token_data, url, site_url)
            inspection["url"] = url
            results.append(inspection)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"GSC URL inspection rate limit hit after {len(results)} inspections")
                break
            logger.warning(f"GSC URL inspection failed for {url}: {e}")
        except Exception as e:
            logger.warning(f"GSC URL inspection error for {url}: {e}")
    return results


# ── Google Analytics 4 ────────────────────────────────────────────


async def ga4_list_properties(token_data: dict) -> List[Dict[str, str]]:
    """List GA4 properties via the Admin API."""
    url = "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"
    data = await _authed_request("GET", url, token_data)
    properties = []
    for account in data.get("accountSummaries", []):
        for prop in account.get("propertySummaries", []):
            properties.append({
                "property_id": prop.get("property"),
                "display_name": prop.get("displayName"),
                "account": account.get("displayName"),
            })
    return properties


async def ga4_get_traffic_by_page(
    token_data: dict,
    property_id: str,
    start_date: str = "90daysAgo",
    end_date: str = "today",
) -> List[Dict[str, Any]]:
    """Get organic traffic per landing page from GA4.
    Used for orphan detection: pages with GA4 traffic but not found by crawler."""
    body = {
        "dimensions": [{"name": "landingPage"}],
        "metrics": [
            {"name": "sessions"},
            {"name": "activeUsers"},
            {"name": "screenPageViews"},
        ],
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "sessionDefaultChannelGroup",
                "stringFilter": {
                    "matchType": "EXACT",
                    "value": "Organic Search",
                },
            }
        },
        "limit": 10000,
    }
    # property_id format: "properties/123456789"
    prop_path = property_id if property_id.startswith("properties/") else f"properties/{property_id}"
    url = f"{GA4_BASE}/{prop_path}:runReport"
    data = await _authed_request("POST", url, token_data, json_body=body)

    rows = data.get("rows", [])
    results: List[Dict[str, Any]] = []
    for row in rows:
        dims = row.get("dimensionValues", [])
        mets = row.get("metricValues", [])
        landing_page = dims[0]["value"] if dims else ""
        results.append({
            "landing_page": landing_page,
            "sessions": int(mets[0]["value"]) if len(mets) > 0 else 0,
            "active_users": int(mets[1]["value"]) if len(mets) > 1 else 0,
            "pageviews": int(mets[2]["value"]) if len(mets) > 2 else 0,
        })
    return results


# ── Helpers ───────────────────────────────────────────────────────


def _encode_site(site_url: str) -> str:
    """Encode site URL for GSC API path parameter."""
    from urllib.parse import quote
    return quote(site_url, safe="")
