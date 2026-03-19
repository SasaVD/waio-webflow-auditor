"""
Pillar 8: Agentic Protocol Check (MCP/A2A Readiness)
=====================================================
Analyzes whether the site exposes the necessary files and endpoints
for AI agents to discover, understand, and interact with it.

Checks for:
- llms.txt / llms-full.txt (LLM-specific site description)
- robots.txt AI crawler permissions
- sitemap.xml presence and quality
- OpenAPI / API documentation discoverability
- MCP / A2A endpoint hints

All checks are deterministic and code-based. Zero LLM dependency.

References:
- llms.txt specification: https://llmstxt.org/
- robots.txt standard: https://www.robotstxt.org/
- Model Context Protocol: https://modelcontextprotocol.io/
- Google A2A Protocol: https://google.github.io/A2A/
"""

import requests
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from urllib.parse import urljoin, urlparse


def run_agentic_protocol_audit(soup: BeautifulSoup, html_content: str, url: str) -> Dict[str, Any]:
    """Main entry point for Pillar 8 audit."""
    checks = {}
    positive_findings = []
    category_findings = []

    base_url = _get_base_url(url)

    # Check 8.1: llms.txt Presence
    checks["llms_txt"] = check_llms_txt(base_url)

    # Check 8.2: robots.txt AI Crawler Permissions
    checks["robots_ai_access"] = check_robots_ai_access(base_url)

    # Check 8.3: Sitemap.xml Quality
    checks["sitemap_quality"] = check_sitemap(base_url)

    # Check 8.4: API Documentation Discoverability
    checks["api_discoverability"] = check_api_discoverability(soup, html_content, base_url)

    # Check 8.5: Meta Agent Hints
    checks["meta_agent_hints"] = check_meta_agent_hints(soup, html_content)

    for check_key, check_val in checks.items():
        if check_val.get("status") in ["pass", "info"]:
            if "positive_message" in check_val:
                positive_findings.append(check_val["positive_message"])
                del check_val["positive_message"]
        if "findings" in check_val:
            category_findings.extend(check_val["findings"])

    return {
        "checks": checks,
        "positive_findings": positive_findings,
        "findings": category_findings
    }


def create_finding(severity: str, description: str, recommendation: str, reference: str, why_it_matters: str = "") -> Dict[str, str]:
    finding = {
        "severity": severity,
        "description": description,
        "recommendation": recommendation,
        "reference": reference
    }
    if why_it_matters:
        finding["why_it_matters"] = why_it_matters
    return finding


def _get_base_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _safe_fetch(url: str, timeout: int = 8) -> dict:
    """Safely fetch a URL and return status code and content."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        return {"status": resp.status_code, "content": resp.text, "ok": resp.status_code == 200}
    except Exception:
        return {"status": 0, "content": "", "ok": False}


def check_llms_txt(base_url: str) -> Dict[str, Any]:
    """
    Check 8.1: llms.txt Presence
    The llms.txt file is an emerging standard that provides LLMs with
    a concise description of a website's purpose, content, and structure.
    """
    findings = []

    llms_url = f"{base_url}/llms.txt"
    llms_full_url = f"{base_url}/llms-full.txt"

    llms_result = _safe_fetch(llms_url)
    llms_full_result = _safe_fetch(llms_full_url)

    has_llms = llms_result["ok"] and len(llms_result["content"].strip()) > 20
    has_llms_full = llms_full_result["ok"] and len(llms_full_result["content"].strip()) > 20

    if not has_llms:
        findings.append(create_finding(
            "high",
            "No llms.txt file found at the site root.",
            "Create a /llms.txt file that describes your site's purpose, key content areas, and available services in plain text. This helps AI agents understand your site before crawling it.",
            "https://llmstxt.org/",
            "The llms.txt file is an emerging standard adopted by major platforms (Anthropic, Cloudflare, Stripe). It provides AI agents with a concise site overview, reducing hallucination and improving answer accuracy."
        ))
    else:
        # Validate llms.txt content quality
        content = llms_result["content"]
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        if len(lines) < 3:
            findings.append(create_finding(
                "medium",
                "llms.txt file exists but contains very little content (fewer than 3 lines).",
                "Expand your llms.txt to include: site name, description, key pages/sections, and links to important resources.",
                "https://llmstxt.org/"
            ))

    details = {
        "llms_txt_found": has_llms,
        "llms_full_txt_found": has_llms_full,
        "llms_txt_url": llms_url
    }

    if not findings:
        msg = "llms.txt file is present and well-structured"
        if has_llms_full:
            msg += ", with an extended llms-full.txt also available"
        msg += " — AI agents can efficiently discover your site's content."
        return {"status": "pass", "details": details, "positive_message": msg}

    return {"status": "fail", "details": details, "findings": findings}


def check_robots_ai_access(base_url: str) -> Dict[str, Any]:
    """
    Check 8.2: robots.txt AI Crawler Permissions
    Checks whether the robots.txt file allows or blocks known AI crawlers.
    """
    findings = []

    robots_url = f"{base_url}/robots.txt"
    result = _safe_fetch(robots_url)

    ai_crawlers = [
        "GPTBot", "ChatGPT-User", "Google-Extended", "Anthropic",
        "ClaudeBot", "CCBot", "PerplexityBot", "Bytespider"
    ]

    if not result["ok"]:
        findings.append(create_finding(
            "medium",
            "No robots.txt file found. AI crawlers will follow default crawling behavior.",
            "Create a robots.txt file that explicitly allows AI crawlers you want to index your content (e.g., GPTBot, Google-Extended, ClaudeBot).",
            "https://www.robotstxt.org/",
            "Without a robots.txt, you have no control over which AI systems can crawl and use your content."
        ))
        return {"status": "fail", "details": {"robots_txt_found": False}, "findings": findings}

    content = result["content"].lower()
    blocked_crawlers = []
    allowed_crawlers = []

    for crawler in ai_crawlers:
        crawler_lower = crawler.lower()
        # Check for specific user-agent blocks
        if f"user-agent: {crawler_lower}" in content:
            # Find the rules for this user-agent
            section_match = re.search(
                rf'user-agent:\s*{re.escape(crawler_lower)}[^\n]*\n((?:(?!user-agent:).*\n)*)',
                content
            )
            if section_match:
                rules = section_match.group(1)
                if 'disallow: /' in rules and 'disallow: /\n' not in rules:
                    pass  # partial disallow
                elif 'disallow: /' in rules:
                    blocked_crawlers.append(crawler)
                elif 'allow: /' in rules:
                    allowed_crawlers.append(crawler)

    # Check for blanket disallow
    blanket_block = False
    if 'user-agent: *' in content:
        wildcard_section = re.search(
            r'user-agent:\s*\*[^\n]*\n((?:(?!user-agent:).*\n)*)',
            content
        )
        if wildcard_section:
            rules = wildcard_section.group(1)
            if 'disallow: /\n' in rules or 'disallow: / \n' in rules:
                blanket_block = True

    if blanket_block and not allowed_crawlers:
        findings.append(create_finding(
            "high",
            "robots.txt contains a blanket 'Disallow: /' for all user agents, which blocks all AI crawlers.",
            "Add specific 'Allow' rules for AI crawlers you want to permit (e.g., GPTBot, Google-Extended). Blocking all crawlers prevents your content from appearing in AI-powered search results.",
            "https://www.robotstxt.org/",
            "If AI crawlers cannot access your site, your content will not appear in ChatGPT, Google AI Mode, Perplexity, or Claude responses."
        ))

    if blocked_crawlers:
        findings.append(create_finding(
            "medium",
            f"The following AI crawlers are explicitly blocked in robots.txt: {', '.join(blocked_crawlers)}.",
            f"Review whether blocking {', '.join(blocked_crawlers)} is intentional. If you want visibility in AI search results, allow these crawlers.",
            "https://www.robotstxt.org/"
        ))

    details = {
        "robots_txt_found": True,
        "blocked_ai_crawlers": blocked_crawlers,
        "allowed_ai_crawlers": allowed_crawlers,
        "blanket_block": blanket_block
    }

    if not findings:
        return {
            "status": "pass",
            "details": details,
            "positive_message": "robots.txt is configured to allow AI crawler access — your content can be indexed by AI search systems."
        }

    return {"status": "fail", "details": details, "findings": findings}


def check_sitemap(base_url: str) -> Dict[str, Any]:
    """
    Check 8.3: Sitemap.xml Quality
    A well-structured sitemap helps AI agents discover all important pages.
    """
    findings = []

    sitemap_url = f"{base_url}/sitemap.xml"
    result = _safe_fetch(sitemap_url)

    if not result["ok"]:
        findings.append(create_finding(
            "high",
            "No sitemap.xml found at the site root.",
            "Generate and publish a sitemap.xml file. In Webflow, this is auto-generated but may need to be enabled in Site Settings > SEO.",
            "https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview",
            "AI agents and crawlers use sitemaps to discover all important pages on your site. Without a sitemap, some pages may never be indexed."
        ))
        return {"status": "fail", "details": {"sitemap_found": False}, "findings": findings}

    content = result["content"]

    # Count URLs in sitemap
    url_count = content.count('<loc>')

    if url_count == 0:
        findings.append(create_finding(
            "high",
            "sitemap.xml exists but contains no URL entries.",
            "Ensure your sitemap.xml contains <url><loc> entries for all important pages.",
            "https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview"
        ))

    # Check for lastmod dates
    has_lastmod = '<lastmod>' in content
    if not has_lastmod and url_count > 0:
        findings.append(create_finding(
            "medium",
            "sitemap.xml does not include <lastmod> dates for URLs.",
            "Add <lastmod> dates to your sitemap entries. This helps AI crawlers prioritize recently updated content.",
            "https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview",
            "AI agents use lastmod dates to determine content freshness. Without them, crawlers may re-index stale content or miss updates."
        ))

    details = {
        "sitemap_found": True,
        "url_count": url_count,
        "has_lastmod": has_lastmod
    }

    if not findings:
        return {
            "status": "pass",
            "details": details,
            "positive_message": f"sitemap.xml is present with {url_count} URLs and lastmod dates — AI crawlers can efficiently discover and prioritize your content."
        }

    return {"status": "fail", "details": details, "findings": findings}


def check_api_discoverability(soup: BeautifulSoup, html_content: str, base_url: str) -> Dict[str, Any]:
    """
    Check 8.4: API Documentation Discoverability
    Checks for presence of OpenAPI/Swagger docs, API links, or
    machine-readable service descriptions that agents could use.
    """
    findings = []

    # Check for common API doc paths
    api_paths = ['/api', '/api/docs', '/api/v1', '/docs', '/swagger', '/openapi.json', '/.well-known/ai-plugin.json']
    found_apis = []

    for path in api_paths:
        result = _safe_fetch(f"{base_url}{path}", timeout=5)
        if result["ok"]:
            found_apis.append(path)

    # Check HTML for API-related links
    api_links = []
    for link in soup.find_all('a', href=True):
        href = link.get('href', '').lower()
        text = link.get_text(strip=True).lower()
        if any(kw in href or kw in text for kw in ['api', 'developer', 'documentation', 'docs', 'integrate']):
            api_links.append({"href": link.get('href'), "text": link.get_text(strip=True)})

    # Check for OpenAI plugin manifest
    has_ai_plugin = '/.well-known/ai-plugin.json' in [p for p in found_apis]

    details = {
        "api_endpoints_found": found_apis,
        "api_links_in_html": len(api_links),
        "has_ai_plugin_manifest": has_ai_plugin
    }

    # This is informational — not every site needs APIs
    # Only flag if the site appears to be a SaaS/service
    is_saas = any(kw in html_content.lower() for kw in ['pricing', 'sign up', 'free trial', 'api', 'integration', 'platform'])

    if is_saas and not found_apis and not api_links:
        findings.append(create_finding(
            "medium",
            "This appears to be a service/SaaS site but no API documentation or developer resources were found.",
            "If your product has an API, publish OpenAPI/Swagger documentation and consider creating an ai-plugin.json manifest for AI agent integration.",
            "https://platform.openai.com/docs/plugins/getting-started",
            "AI agents that can discover and call your API can become powerful distribution channels for your service."
        ))

    if not findings:
        if found_apis:
            return {
                "status": "pass",
                "details": details,
                "positive_message": f"API documentation found at {', '.join(found_apis)} — AI agents can discover and potentially interact with your services."
            }
        return {"status": "pass", "details": details}

    return {"status": "fail", "details": details, "findings": findings}


def check_meta_agent_hints(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    """
    Check 8.5: Meta Agent Hints
    Checks for emerging standards that help AI agents understand the page:
    - <meta name="robots" content="..."> with AI-specific directives
    - Structured data that declares available actions (Schema.org Action types)
    - rel="alternate" with machine-readable formats
    """
    findings = []

    # Check for machine-readable alternate formats
    alternates = soup.find_all('link', rel='alternate')
    machine_formats = []
    for alt in alternates:
        alt_type = alt.get('type', '')
        if any(fmt in alt_type for fmt in ['json', 'xml', 'rss', 'atom']):
            machine_formats.append(alt_type)

    # Check for Schema.org Action types (indicates interactable endpoints)
    has_actions = False
    if '"potentialAction"' in html_content or '"PotentialAction"' in html_content:
        has_actions = True
    if '"SearchAction"' in html_content:
        has_actions = True

    # Check for noai/noimageai meta directives
    meta_robots = soup.find_all('meta', attrs={'name': re.compile(r'robots', re.I)})
    ai_directives = []
    for meta in meta_robots:
        content = meta.get('content', '').lower()
        if any(d in content for d in ['noai', 'noimageai', 'nosnippet']):
            ai_directives.append(content)

    if ai_directives:
        findings.append(create_finding(
            "medium",
            f"Found AI-restrictive meta directives: {', '.join(ai_directives)}.",
            "Review whether these restrictions are intentional. 'noai' and 'noimageai' prevent AI systems from using your content in their responses.",
            "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
            "AI-restrictive directives reduce your visibility in AI-powered search results and prevent agents from citing your content."
        ))

    # Suggest machine-readable formats if none exist
    if not machine_formats and not has_actions:
        findings.append(create_finding(
            "medium",
            "No machine-readable alternate formats (JSON, RSS, Atom) or Schema.org Action types found.",
            "Add an RSS/Atom feed for blog content and consider adding Schema.org SearchAction to your WebSite structured data. These help AI agents discover and interact with your content programmatically.",
            "https://schema.org/SearchAction",
            "Machine-readable formats and Action schemas allow AI agents to interact with your site beyond simple content retrieval."
        ))

    details = {
        "machine_readable_formats": machine_formats,
        "has_schema_actions": has_actions,
        "ai_restrictive_directives": ai_directives
    }

    if not findings:
        msg_parts = []
        if machine_formats:
            msg_parts.append(f"machine-readable formats ({', '.join(machine_formats)})")
        if has_actions:
            msg_parts.append("Schema.org Action types")
        if msg_parts:
            return {
                "status": "pass",
                "details": details,
                "positive_message": f"Found {' and '.join(msg_parts)} — AI agents can discover and interact with your content."
            }
        return {"status": "pass", "details": details}

    return {"status": "fail", "details": details, "findings": findings}
