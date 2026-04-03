"""
CMS-specific migration intelligence module.
Sprint 4E: Platform-specific analysis for non-Webflow sites with
migration recommendations and NLP-powered content mapping.

Only runs when detected CMS != Webflow.
Provides: platform-specific issues, Webflow advantages,
redirect mapping estimate, migration timeline, TCO comparison.
"""
import logging
import re
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class PlatformIssue:
    category: str         # "security", "performance", "seo", "url_structure", "content"
    title: str
    description: str
    severity: str         # "critical", "high", "medium"
    evidence: str | None  # specific evidence found in audit

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WebflowAdvantage:
    category: str
    title: str
    description: str
    impact: str           # "high", "medium", "low"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MigrationAssessment:
    source_cms: str
    target_cms: str
    platform_issues: List[PlatformIssue]
    webflow_advantages: List[WebflowAdvantage]
    redirect_count_estimate: int
    migration_timeline: str
    tco_comparison: Dict[str, Any] | None
    nlp_content_mapping: Dict[str, Any] | None
    findings: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# ── Platform-Specific Issue Databases ─────────────────────────────


WORDPRESS_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="security",
        title="Plugin Vulnerability Surface",
        description=(
            "WordPress plugins account for 97% of all WP security vulnerabilities. "
            "The average WP site runs 20+ plugins, each an attack vector."
        ),
        severity="critical",
        evidence=None,
    ),
    PlatformIssue(
        category="security",
        title="Database Injection Risk",
        description=(
            "WordPress's MySQL/MariaDB layer is a persistent target for SQL injection. "
            "WPScan reports 150,000+ known vulnerabilities in the WP ecosystem."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="performance",
        title="Plugin Bloat & Render Blocking",
        description=(
            "Plugin-heavy WordPress sites average 3.5s LCP vs 1.8s for static sites. "
            "Each plugin adds JS/CSS that blocks rendering."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="performance",
        title="Database Query Overhead",
        description=(
            "WordPress generates 50-200 database queries per page load. "
            "Dynamic rendering adds latency that static/JAMstack eliminates."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="seo",
        title="Duplicate Content from Taxonomies",
        description=(
            "WordPress auto-generates archive pages for categories, tags, authors, "
            "and dates — creating thin duplicate content that dilutes crawl budget."
        ),
        severity="medium",
        evidence=None,
    ),
]

SHOPIFY_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="url_structure",
        title="Forced /collections/ and /products/ URL Prefixes",
        description=(
            "Shopify forces /collections/ and /products/ URL patterns that cannot be customized. "
            "This creates unnecessary URL depth and limits SEO URL optimization."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="seo",
        title="Duplicate Content from Product Variants",
        description=(
            "Shopify generates separate URLs for product variants and collections, "
            "creating canonical issues. Pagination also creates duplicate faceted URLs."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="url_structure",
        title="301 Redirect Limitations",
        description=(
            "Shopify has a 100K redirect limit and lacks regex-based redirect rules. "
            "Complex migration scenarios may exceed this limit."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="performance",
        title="Liquid Template Rendering Overhead",
        description=(
            "Shopify's Liquid templating adds server-side rendering time. "
            "Average TTFB is 300-800ms vs 50-100ms for edge-deployed static sites."
        ),
        severity="medium",
        evidence=None,
    ),
]

WIX_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="performance",
        title="Heavy JavaScript Bundle",
        description=(
            "Wix sites ship 2-5MB of JavaScript by default, causing significant "
            "First Input Delay. Average LCP: 4.2s (HTTPArchive, 2024)."
        ),
        severity="critical",
        evidence=None,
    ),
    PlatformIssue(
        category="seo",
        title="Limited HTML Control",
        description=(
            "Wix generates non-semantic HTML with deeply nested divs. "
            "Heading hierarchy is often broken and cannot be manually corrected."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="No Content Export",
        description=(
            "Wix does not provide a native content export mechanism. "
            "Migration requires scraping all pages to extract content."
        ),
        severity="high",
        evidence=None,
    ),
]

SQUARESPACE_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="performance",
        title="Above-Average Page Weight",
        description=(
            "Squarespace sites average 3-4MB page weight with aggressive "
            "JavaScript loading. Core Web Vitals pass rate: 33% (HTTPArchive, 2024)."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="seo",
        title="Heading Hierarchy Limitations",
        description=(
            "Squarespace templates often hard-code heading levels. "
            "Users frequently end up with H3 before H2 or multiple H1s."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="seo",
        title="Limited Structured Data Control",
        description=(
            "Squarespace auto-generates basic schema but does not allow "
            "custom JSON-LD injection without developer mode."
        ),
        severity="medium",
        evidence=None,
    ),
]

FRAMER_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="seo",
        title="Limited SEO Customization",
        description=(
            "Framer provides basic SEO fields but lacks advanced features like "
            "custom structured data, hreflang tags, and granular canonical control."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="No Native CMS for Complex Content",
        description=(
            "Framer's CMS is limited compared to Webflow's. Complex content models "
            "with references, multi-image fields, and conditional visibility are unsupported."
        ),
        severity="medium",
        evidence=None,
    ),
]

NEXTJS_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="performance",
        title="Hydration Overhead",
        description=(
            "Next.js client-side hydration can cause significant FID/INP issues. "
            "TTI is often 2-4x higher than TTFB for content-heavy pages."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="seo",
        title="SSR/SSG Configuration Complexity",
        description=(
            "Misconfigured SSR can serve client-rendered content to bots. "
            "ISR revalidation timing affects crawl freshness."
        ),
        severity="medium",
        evidence=None,
    ),
]

# ── Tier 1 New Platforms ────────────────────────────────────────

JOOMLA_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="security",
        title="Outdated Extension Ecosystem",
        description=(
            "Joomla's extension ecosystem has contracted by ~80% over the past decade. "
            "Many extensions are unmaintained, creating unpatched security vulnerabilities."
        ),
        severity="critical",
        evidence=None,
    ),
    PlatformIssue(
        category="security",
        title="Unmaintained Extension Vulnerabilities",
        description=(
            "Joomla extensions without active maintenance accumulate CVEs. "
            "Unlike WordPress, Joomla lacks a centralized security review pipeline for extensions."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="performance",
        title="Poor Mobile Responsive Defaults",
        description=(
            "Many Joomla templates were designed pre-mobile-first era. "
            "Responsive behavior often requires manual template overrides or third-party templates."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Complex Admin UI",
        description=(
            "Joomla's administration panel has a steep learning curve. "
            "Content editors frequently require developer assistance for routine tasks."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Declining Developer Community",
        description=(
            "Joomla's market share has declined from ~9% to ~1.9%. "
            "Finding qualified Joomla developers is increasingly difficult and expensive."
        ),
        severity="medium",
        evidence=None,
    ),
]

HUBSPOT_CMS_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="content",
        title="Expensive CMS Hub Pricing",
        description=(
            "HubSpot CMS Hub Professional starts at $360+/month ($4,320/year). "
            "Enterprise features require $1,200+/month. Far exceeds Webflow's pricing."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="performance",
        title="Slow Page Speed",
        description=(
            "HubSpot-hosted pages consistently score lower on Core Web Vitals than "
            "static-site alternatives. Average LCP is 3-5s due to HubSpot's tracking scripts."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Developer Dependency for Design Changes",
        description=(
            "HubSpot's drag-and-drop editor is limited for custom layouts. "
            "Non-trivial design changes require HubL template code and a developer."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="seo",
        title="Limited Design Flexibility",
        description=(
            "HubSpot templates are rigid compared to Webflow's visual builder. "
            "Custom interactions, animations, and layout patterns require HubL + JS development."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Vendor Lock-In with HubSpot Ecosystem",
        description=(
            "HubSpot CMS is tightly coupled with HubSpot's CRM, marketing, and sales tools. "
            "Migrating away means losing CMS + marketing automation integration."
        ),
        severity="medium",
        evidence=None,
    ),
]

GATSBY_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="performance",
        title="Excessive Build Times",
        description=(
            "Gatsby build times regularly exceed 30 minutes for sites with 1,000+ pages. "
            "Incremental builds (DSG) are unreliable and poorly maintained."
        ),
        severity="critical",
        evidence=None,
    ),
    PlatformIssue(
        category="security",
        title="Plugin Rot and Dependency Conflicts",
        description=(
            "Gatsby's plugin ecosystem is decaying. Many key plugins have unresolved "
            "dependency conflicts and have not been updated in 12+ months."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Core Team Departed After Netlify Acquisition",
        description=(
            "Gatsby's core team was disbanded after the Netlify acquisition. "
            "Near-zero maintenance activity on the core repository since mid-2024."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Developer Dependency for Content Updates",
        description=(
            "Content changes require a developer to trigger builds and deploys. "
            "No built-in visual editing — relies on external headless CMS integrations."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Near-Zero Maintenance Activity",
        description=(
            "The Gatsby GitHub repository shows minimal commit activity. "
            "Critical bugs and security issues go unaddressed for months."
        ),
        severity="high",
        evidence=None,
    ),
]

WEEBLY_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="content",
        title="Platform Discontinuation Imminent",
        description=(
            "Weebly is being actively sunsetted by Square. Support ends July 2026. "
            "No new features are being developed. Migration is mandatory, not optional."
        ),
        severity="critical",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Mobile App Discontinued",
        description=(
            "Weebly's mobile app was discontinued in December 2025. "
            "Mobile content management is no longer possible."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="seo",
        title="Limited SEO Controls",
        description=(
            "Weebly provides only basic title and description fields. "
            "No custom canonical URLs, limited redirect management, no hreflang support."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="seo",
        title="No Structured Data Support",
        description=(
            "Weebly does not support custom JSON-LD or any structured data injection "
            "without third-party embed code workarounds."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="No New Features",
        description=(
            "Weebly has been in maintenance-only mode since Square's acquisition. "
            "No meaningful feature updates since 2023."
        ),
        severity="medium",
        evidence=None,
    ),
]

# ── Tier 2 Platforms (shorter issue lists) ──────────────────────

DRUPAL_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="content",
        title="High Developer Dependency",
        description=(
            "Drupal requires PHP developers for most site changes. "
            "Content editors cannot modify layouts or add new page types without developer help."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="security",
        title="Complex Update Process",
        description=(
            "Drupal major version upgrades (e.g., 9→10) are complex migrations, not updates. "
            "Custom modules often break during upgrades, requiring significant developer time."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Declining Community",
        description=(
            "Drupal's market share has declined from ~2.3% to ~1.1%. "
            "The pool of available Drupal developers continues to shrink."
        ),
        severity="medium",
        evidence=None,
    ),
]

DUDA_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="content",
        title="White-Label Limitations",
        description=(
            "Duda is primarily an agency white-label platform. "
            "Client-facing features and direct access are limited compared to Webflow."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="seo",
        title="Design Ceiling",
        description=(
            "Duda's template system limits custom design possibilities. "
            "Advanced interactions and animations require custom code injection."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Limited CMS Flexibility",
        description=(
            "Duda's content management is basic compared to Webflow's CMS. "
            "No reference fields, limited collection structure, no conditional visibility."
        ),
        severity="medium",
        evidence=None,
    ),
]

NUXT_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="content",
        title="Developer Dependency",
        description=(
            "Nuxt.js requires Vue.js developers for all content and design changes. "
            "No visual editing capability — purely code-driven."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="performance",
        title="Hydration Issues",
        description=(
            "Nuxt SSR hydration mismatches cause layout shifts and interactivity delays. "
            "Debugging hydration errors requires deep Vue.js expertise."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="performance",
        title="Build Complexity",
        description=(
            "Nuxt's build pipeline involves Nitro, Vite/Webpack, and Vue compiler. "
            "Build failures are common and difficult to diagnose without framework expertise."
        ),
        severity="medium",
        evidence=None,
    ),
]

CRAFT_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="content",
        title="Small Plugin Ecosystem",
        description=(
            "Craft CMS has a fraction of the plugins available on WordPress or Webflow. "
            "Many features require custom development."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Hosting Complexity",
        description=(
            "Craft CMS requires self-managed PHP hosting with database administration. "
            "No managed hosting option like Webflow's built-in CDN deployment."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Developer Required for Templates",
        description=(
            "Craft uses Twig templates that require PHP/Twig developer expertise. "
            "Design changes cannot be made visually."
        ),
        severity="medium",
        evidence=None,
    ),
]

GHOST_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="content",
        title="Limited Design Flexibility",
        description=(
            "Ghost themes are primarily blog-focused. Building complex marketing sites "
            "or multi-section landing pages requires extensive custom theme development."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="Newsletter-Focused Platform",
        description=(
            "Ghost has pivoted toward newsletter/membership publishing. "
            "Website building features receive less development attention."
        ),
        severity="medium",
        evidence=None,
    ),
    PlatformIssue(
        category="seo",
        title="Basic SEO Controls",
        description=(
            "Ghost provides basic meta title/description but lacks custom structured data, "
            "advanced canonical control, and granular redirect management."
        ),
        severity="medium",
        evidence=None,
    ),
]

BIGCOMMERCE_ISSUES: List[PlatformIssue] = [
    PlatformIssue(
        category="seo",
        title="Blog on Subdomain by Default",
        description=(
            "BigCommerce hosts the blog on a subdomain (/blog/) by default, "
            "splitting domain authority. This is devastating for content-driven SEO strategies."
        ),
        severity="critical",
        evidence=None,
    ),
    PlatformIssue(
        category="content",
        title="No Staging Environment",
        description=(
            "BigCommerce lacks a built-in staging or preview environment. "
            "Theme changes go live immediately with no safe testing workflow."
        ),
        severity="high",
        evidence=None,
    ),
    PlatformIssue(
        category="url_structure",
        title="Rigid URL Structures",
        description=(
            "BigCommerce enforces specific URL patterns for products, categories, and brands. "
            "URL customization is limited, and changing structures risks broken links."
        ),
        severity="medium",
        evidence=None,
    ),
]

CMS_ISSUES: Dict[str, List[PlatformIssue]] = {
    # Tier 1 — full migration intelligence
    "wordpress": WORDPRESS_ISSUES,
    "shopify": SHOPIFY_ISSUES,
    "wix": WIX_ISSUES,
    "squarespace": SQUARESPACE_ISSUES,
    "framer": FRAMER_ISSUES,
    "nextjs": NEXTJS_ISSUES,
    "joomla": JOOMLA_ISSUES,
    "hubspot": HUBSPOT_CMS_ISSUES,
    "gatsby": GATSBY_ISSUES,
    "weebly": WEEBLY_ISSUES,
    # Tier 2 — basic migration assessment
    "drupal": DRUPAL_ISSUES,
    "duda": DUDA_ISSUES,
    "nuxt": NUXT_ISSUES,
    "craft": CRAFT_ISSUES,
    "ghost": GHOST_ISSUES,
    "bigcommerce": BIGCOMMERCE_ISSUES,
}


# ── CMS Tier Classification ────────────────────────────────────

CMS_TIER: Dict[str, int] = {
    # Tier 1: Full migration intelligence
    "wordpress": 1, "shopify": 1, "wix": 1, "squarespace": 1,
    "framer": 1, "nextjs": 1, "joomla": 1, "hubspot": 1,
    "gatsby": 1, "weebly": 1,
    # Tier 2: Basic migration assessment
    "drupal": 2, "duda": 2, "nuxt": 2, "craft": 2,
    "ghost": 2, "bigcommerce": 2,
    # Tier 3: Detection only
    "hugo": 3, "jekyll": 3, "astro": 3, "sveltekit": 3,
    "typo3": 3, "aem": 3, "magento": 3, "prestashop": 3,
    "cargo": 3, "readymag": 3, "contentful": 3, "strapi": 3,
    "sanity": 3,
}

# Human-readable platform names for Tier 3 detection-only results
CMS_DISPLAY_NAMES: Dict[str, str] = {
    "wordpress": "WordPress", "shopify": "Shopify", "wix": "Wix",
    "squarespace": "Squarespace", "framer": "Framer", "nextjs": "Next.js",
    "joomla": "Joomla", "hubspot": "HubSpot CMS", "gatsby": "Gatsby",
    "weebly": "Weebly", "drupal": "Drupal", "duda": "Duda",
    "nuxt": "Nuxt.js", "craft": "Craft CMS", "ghost": "Ghost",
    "bigcommerce": "BigCommerce", "hugo": "Hugo", "jekyll": "Jekyll",
    "astro": "Astro", "sveltekit": "SvelteKit", "typo3": "TYPO3",
    "aem": "Adobe Experience Manager", "magento": "Magento",
    "prestashop": "PrestaShop", "cargo": "Cargo", "readymag": "Readymag",
    "contentful": "Contentful", "strapi": "Strapi", "sanity": "Sanity",
    "webflow": "Webflow", "unknown": "Unknown",
}


# ── Webflow Honest Limitations ─────────────────────────────────

WEBFLOW_LIMITATIONS: List[Dict[str, Any]] = [
    {
        "limitation": "10,000 CMS items max (20,000 with add-ons)",
        "threshold_field": "cms_items",
        "threshold_value": 10000,
        "description": (
            "Webflow CMS is limited to 10,000 items per collection (20,000 with Localization or "
            "Enterprise add-ons). Sites with larger content volumes may need a headless CMS hybrid."
        ),
    },
    {
        "limitation": "5 reference fields per collection (hard cap)",
        "threshold_field": None,
        "threshold_value": None,
        "description": (
            "Each Webflow CMS collection supports a maximum of 5 reference/multi-reference fields. "
            "Complex relational data models may require restructuring during migration."
        ),
    },
    {
        "limitation": "100 items per collection list",
        "threshold_field": None,
        "threshold_value": None,
        "description": (
            "Collection lists on a page display a maximum of 100 items. "
            "Pagination or filtering is required for larger collections."
        ),
    },
    {
        "limitation": "15,000 products max (Ecommerce)",
        "threshold_field": "product_count",
        "threshold_value": 15000,
        "description": (
            "Webflow Ecommerce supports up to 15,000 products. "
            "Large e-commerce catalogs may exceed this limit."
        ),
    },
    {
        "limitation": "4 payment gateways (Stripe, PayPal, Apple Pay, Google Pay)",
        "threshold_field": None,
        "threshold_value": None,
        "description": (
            "Webflow Ecommerce supports only 4 payment gateways. "
            "Sites requiring other gateways need third-party integrations."
        ),
    },
]


# ── Webflow Advantages ───────────────────────────────────────────


WEBFLOW_ADVANTAGES: List[WebflowAdvantage] = [
    WebflowAdvantage(
        category="performance",
        title="Edge-Deployed Static Output",
        description=(
            "Webflow generates static HTML/CSS/JS deployed to a global CDN. "
            "Average TTFB: 50-150ms. No server-side rendering overhead."
        ),
        impact="high",
    ),
    WebflowAdvantage(
        category="security",
        title="Zero Server-Side Attack Surface",
        description=(
            "No database, no plugins, no server-side code. "
            "Webflow's static output eliminates SQL injection, XSS, and RCE vectors."
        ),
        impact="high",
    ),
    WebflowAdvantage(
        category="seo",
        title="Full Semantic HTML Control",
        description=(
            "Webflow gives designers full control over HTML element types, "
            "heading hierarchy, ARIA attributes, and structured data."
        ),
        impact="high",
    ),
    WebflowAdvantage(
        category="seo",
        title="Clean URL Architecture",
        description=(
            "Fully customizable URL slugs with automatic 301 redirect management. "
            "No forced prefixes like /collections/ or /wp-content/."
        ),
        impact="high",
    ),
    WebflowAdvantage(
        category="seo",
        title="Native Structured Data Support",
        description=(
            "Custom JSON-LD injection per page with CMS-driven dynamic values. "
            "No plugins required."
        ),
        impact="medium",
    ),
    WebflowAdvantage(
        category="content",
        title="Visual CMS with Reference Fields",
        description=(
            "Webflow CMS supports complex content models with multi-reference fields, "
            "rich text, image galleries, and conditional visibility — all visual."
        ),
        impact="medium",
    ),
    WebflowAdvantage(
        category="performance",
        title="Automatic Image Optimization",
        description=(
            "Webflow auto-generates responsive srcset with WebP conversion, "
            "lazy loading, and CDN delivery without any configuration."
        ),
        impact="medium",
    ),
]


# ── Migration Assessment Engine ──────────────────────────────────


def estimate_redirect_count(
    total_pages: int,
    source_cms: str,
) -> int:
    """Estimate number of redirects needed based on CMS and page count."""
    multipliers = {
        "wordpress": 1.5,     # categories, tags, author, date archives
        "shopify": 1.8,       # collections, variants, paginated
        "squarespace": 1.1,
        "wix": 1.0,           # no extra URL patterns
        "framer": 1.0,
        "nextjs": 1.2,        # API routes, dynamic segments
        "joomla": 1.4,        # component views, menu items, aliases
        "hubspot": 1.2,       # landing pages, blog pagination
        "gatsby": 1.0,        # static routes
        "weebly": 1.0,        # flat URL structure
        "drupal": 1.5,        # taxonomy terms, views, aliases
        "duda": 1.0,
        "nuxt": 1.2,          # dynamic routes
        "craft": 1.2,         # section/entry types
        "ghost": 1.1,         # tag and author pages
        "bigcommerce": 1.6,   # category/brand/product URLs
    }
    multiplier = multipliers.get(source_cms, 1.2)
    return int(total_pages * multiplier)


def estimate_migration_timeline(
    total_pages: int,
    source_cms: str,
) -> str:
    """Estimate migration timeline based on complexity."""
    if total_pages <= 20:
        base = "1-2 weeks"
    elif total_pages <= 100:
        base = "2-4 weeks"
    elif total_pages <= 500:
        base = "4-8 weeks"
    elif total_pages <= 2000:
        base = "8-12 weeks"
    else:
        base = "12-16 weeks"

    complexity_notes = {
        "wordpress": "Plugin functionality may need custom Webflow solutions.",
        "shopify": "E-commerce migration requires Webflow Ecommerce or Foxy/Snipcart integration.",
        "wix": "No content export — full manual content migration required.",
        "squarespace": "Squarespace offers limited XML export for blog posts only.",
        "joomla": "Joomla extension functionality will need replacement in Webflow.",
        "hubspot": "HubSpot CRM/marketing automation integration will need re-architecture.",
        "gatsby": "Static site content needs CMS migration; developer workflows change entirely.",
        "weebly": "Platform shutting down — migrate before July 2026 support end.",
        "drupal": "Complex content types and views need careful mapping to Webflow CMS.",
        "bigcommerce": "E-commerce migration requires Webflow Ecommerce or headless checkout.",
    }
    note = complexity_notes.get(source_cms, "")
    return f"{base}{' — ' + note if note else ''}"


def estimate_tco_comparison(
    source_cms: str,
    total_pages: int,
) -> Dict[str, Any]:
    """Estimate Total Cost of Ownership comparison (annual)."""
    source_costs: Dict[str, Dict[str, Any]] = {
        "wordpress": {
            "hosting": 300, "plugins": 500, "maintenance": 2400,
            "security": 600, "total_annual": 3800,
        },
        "shopify": {
            "hosting": 948, "apps": 1200, "maintenance": 1200,
            "transaction_fees": "2.9% + $0.30/transaction", "total_annual": 3348,
        },
        "wix": {
            "hosting": 396, "apps": 300, "maintenance": 600, "total_annual": 1296,
        },
        "squarespace": {
            "hosting": 396, "extensions": 200, "maintenance": 600, "total_annual": 1196,
        },
        "joomla": {
            "hosting": 300, "extensions": 300, "maintenance": 3600,
            "security": 600, "total_annual": 4800,
        },
        "hubspot": {
            "hosting": 4320, "maintenance": 1200, "total_annual": 5520,
            "note": "CMS Hub Professional at $360/mo",
        },
        "gatsby": {
            "hosting": 228, "maintenance": 6000, "total_annual": 6228,
            "note": "Developer costs dominate due to build/deploy pipeline",
        },
        "weebly": {
            "hosting": 312, "maintenance": 300, "total_annual": 612,
            "note": "Low cost but platform is being discontinued",
        },
        "drupal": {
            "hosting": 360, "maintenance": 4800, "security": 600,
            "total_annual": 5760,
        },
        "bigcommerce": {
            "hosting": 948, "apps": 600, "maintenance": 1200,
            "total_annual": 2748,
        },
    }

    webflow_cost = {
        "hosting": 276 if total_pages <= 100 else 516,
        "maintenance": 600,
        "security": 0,
        "total_annual": 876 if total_pages <= 100 else 1116,
    }

    source = source_costs.get(source_cms, {"total_annual": 2000})
    annual_savings = source.get("total_annual", 2000) - webflow_cost["total_annual"]

    return {
        "source_cms": source_cms,
        "source_annual": source,
        "webflow_annual": webflow_cost,
        "annual_savings": annual_savings,
        "five_year_savings": annual_savings * 5,
    }


def _check_webflow_limitations(
    total_pages: int,
    source_cms: str,
) -> List[Dict[str, Any]]:
    """Check if the source site may exceed Webflow's known limits.

    Returns a list of limitation warnings to include in the assessment.
    """
    warnings: List[Dict[str, Any]] = []

    # E-commerce platforms likely have large product catalogues
    ecommerce_platforms = {"shopify", "bigcommerce", "magento", "prestashop"}

    # Always include the reference-field and collection-list limits (informational)
    for lim in WEBFLOW_LIMITATIONS:
        threshold = lim.get("threshold_value")
        field = lim.get("threshold_field")

        if field == "cms_items" and total_pages > (threshold or 10000):
            warnings.append({
                "severity": "high",
                "limitation": lim["limitation"],
                "description": (
                    f"Your site has ~{total_pages:,} pages. {lim['description']} "
                    "Webflow migration may not be suitable for your content volume."
                ),
            })
        elif field == "product_count" and source_cms in ecommerce_platforms and total_pages > 5000:
            warnings.append({
                "severity": "high",
                "limitation": lim["limitation"],
                "description": (
                    f"As a {CMS_DISPLAY_NAMES.get(source_cms, source_cms)} site, you may have a "
                    f"large product catalogue. {lim['description']}"
                ),
            })

    return warnings


def run_migration_assessment(
    source_cms: str,
    total_pages: int = 0,
    audit_findings: List[Dict[str, Any]] | None = None,
    nlp_categories: Dict[str, str] | None = None,
    nlp_confidences: Dict[str, float] | None = None,
) -> MigrationAssessment:
    """Generate CMS migration assessment for a non-Webflow site.

    Behaviour varies by platform tier:
    - Tier 1: Full migration intelligence with issues, Webflow advantages,
              redirect/timeline/TCO estimates, NLP content mapping.
    - Tier 2: Shorter assessment with issues and basic estimates, no
              step-by-step guidance.
    - Tier 3: Detection result only with generic consulting CTA.

    Args:
        source_cms: Detected CMS platform key.
        total_pages: Total pages on the site.
        audit_findings: Existing audit findings to cross-reference with CMS issues.
        nlp_categories: URL -> NLP category mapping for content mapping.
        nlp_confidences: URL -> NLP confidence mapping.

    Returns:
        MigrationAssessment with platform issues, Webflow advantages, and estimates.
    """
    display_name = CMS_DISPLAY_NAMES.get(source_cms, source_cms.title())
    tier = CMS_TIER.get(source_cms, 3)

    if source_cms == "webflow":
        return MigrationAssessment(
            source_cms="webflow",
            target_cms="webflow",
            platform_issues=[],
            webflow_advantages=[],
            redirect_count_estimate=0,
            migration_timeline="N/A — already on Webflow",
            tco_comparison=None,
            nlp_content_mapping=None,
            findings=[],
        )

    # ── Tier 3: Detection-only ──────────────────────────────────
    if tier == 3:
        return MigrationAssessment(
            source_cms=source_cms,
            target_cms="webflow",
            platform_issues=[],
            webflow_advantages=[],
            redirect_count_estimate=0,
            migration_timeline="Contact us for a platform-specific estimate",
            tco_comparison=None,
            nlp_content_mapping=None,
            findings=[{
                "severity": "medium",
                "description": (
                    f"Detected {display_name}. Contact us for a platform-specific "
                    f"migration assessment."
                ),
                "recommendation": (
                    f"We detected your site is built on {display_name}. "
                    f"Our team can provide a detailed migration assessment with "
                    f"platform-specific recommendations for moving to Webflow."
                ),
                "reference": "https://webflow.com/made-in-webflow",
            }],
        )

    # ── Tier 1 & 2: Full / basic assessment ─────────────────────

    # Get platform-specific issues
    platform_issues = list(CMS_ISSUES.get(source_cms, []))

    # Cross-reference audit findings with known CMS issues (Tier 1 only)
    if audit_findings and tier == 1:
        _enrich_issues_with_evidence(platform_issues, audit_findings, source_cms)

    # Migration estimates
    redirect_count = estimate_redirect_count(total_pages, source_cms)
    timeline = estimate_migration_timeline(total_pages, source_cms)

    # TCO comparison (Tier 1 only — Tier 2 gets None)
    tco = estimate_tco_comparison(source_cms, total_pages) if tier == 1 else None

    # NLP content mapping (Tier 1 only)
    nlp_mapping = None
    if nlp_categories and tier == 1:
        nlp_mapping = _build_content_mapping(nlp_categories, nlp_confidences)

    # Generate findings
    findings: List[Dict[str, Any]] = []
    critical_count = sum(1 for i in platform_issues if i.severity == "critical")
    high_count = sum(1 for i in platform_issues if i.severity == "high")

    if critical_count > 0:
        savings_note = ""
        if tco:
            savings_note = (
                f" Migration ROI is typically positive within 12-18 months "
                f"(estimated annual savings: ${tco.get('annual_savings', 0):,})."
            )
        findings.append({
            "severity": "critical",
            "description": (
                f"Your {display_name} site has {critical_count} critical platform-level issues "
                f"that cannot be fixed without migration."
            ),
            "recommendation": (
                f"Migrating to Webflow would eliminate these {display_name}-specific "
                f"vulnerabilities while improving performance and SEO control."
            ),
            "reference": "https://webflow.com/vs/wordpress",
            "why_it_matters": (
                f"Platform-level issues affect every page on your site.{savings_note}"
            ),
        })

    if high_count > 0:
        findings.append({
            "severity": "high",
            "description": (
                f"Found {high_count} high-severity {display_name}-specific issues "
                f"that Webflow resolves architecturally."
            ),
            "recommendation": (
                "Review the platform-specific issues in the migration assessment section."
            ),
            "reference": "https://webflow.com/vs/wordpress",
        })

    # Tier 2: add a note that full assessment is available
    if tier == 2:
        findings.append({
            "severity": "medium",
            "description": (
                f"This is a basic migration assessment for {display_name}. "
                f"Contact us for a full platform-specific migration plan with "
                f"step-by-step guidance and TCO analysis."
            ),
            "recommendation": (
                "A full Tier 1 migration assessment includes detailed redirect mapping, "
                "TCO comparison, NLP content mapping, and step-by-step migration guidance."
            ),
            "reference": "https://webflow.com/made-in-webflow",
        })

    # Check Webflow limitations (both tiers)
    webflow_warnings = _check_webflow_limitations(total_pages, source_cms)
    for warning in webflow_warnings:
        findings.append({
            "severity": warning["severity"],
            "description": warning["description"],
            "recommendation": (
                "Review Webflow's CMS limits before committing to migration. "
                "A headless CMS hybrid (Webflow frontend + external CMS) may be needed."
            ),
            "reference": "https://university.webflow.com/lesson/cms-limits",
        })

    return MigrationAssessment(
        source_cms=source_cms,
        target_cms="webflow",
        platform_issues=platform_issues,
        webflow_advantages=WEBFLOW_ADVANTAGES if tier == 1 else [],
        redirect_count_estimate=redirect_count,
        migration_timeline=timeline,
        tco_comparison=tco,
        nlp_content_mapping=nlp_mapping,
        findings=findings,
    )


def _enrich_issues_with_evidence(
    issues: List[PlatformIssue],
    audit_findings: List[Dict[str, Any]],
    source_cms: str,
):
    """Add evidence from audit findings to platform issues."""
    for issue in issues:
        if issue.category == "performance":
            perf_findings = [
                f for f in audit_findings
                if "performance" in f.get("description", "").lower()
                or "lcp" in f.get("description", "").lower()
                or "blocking" in f.get("description", "").lower()
            ]
            if perf_findings:
                issue.evidence = f"Confirmed in audit: {perf_findings[0].get('description', '')[:120]}"

        elif issue.category == "seo":
            seo_findings = [
                f for f in audit_findings
                if "heading" in f.get("description", "").lower()
                or "duplicate" in f.get("description", "").lower()
                or "structured data" in f.get("description", "").lower()
            ]
            if seo_findings:
                issue.evidence = f"Confirmed in audit: {seo_findings[0].get('description', '')[:120]}"


def _build_content_mapping(
    nlp_categories: Dict[str, str],
    nlp_confidences: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    """Build NLP-powered content mapping for migration planning.

    Groups pages by NLP category and provides migration priority.
    """
    from collections import defaultdict

    category_pages: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for url, category in nlp_categories.items():
        conf = (nlp_confidences or {}).get(url, 0.5)
        category_pages[category].append({"url": url, "confidence": conf})

    sections: List[Dict[str, Any]] = []
    for category, pages in sorted(category_pages.items(), key=lambda x: -len(x[1])):
        avg_conf = sum(p["confidence"] for p in pages) / len(pages)
        sections.append({
            "category": category,
            "page_count": len(pages),
            "avg_confidence": round(avg_conf, 3),
            "migration_priority": "high" if len(pages) >= 10 else "medium" if len(pages) >= 3 else "low",
            "sample_urls": [p["url"] for p in pages[:5]],
        })

    return {
        "total_categories": len(sections),
        "sections": sections,
        "recommendation": (
            "Migrate content by category cluster. Start with the highest page-count "
            "categories to preserve the most topical authority during transition."
        ),
    }
