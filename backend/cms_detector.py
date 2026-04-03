"""
CMS detection module.
Sprint 3F: Auto-detect the CMS/framework powering a website.
Three-tier detection: custom regex patterns → python-Wappalyzer → DNS CNAME.
Runs on homepage HTML + HTTP headers. Zero API cost.

Supported platforms: WordPress, Shopify, Webflow, Framer, Wix,
Squarespace, Next.js, Gatsby, Nuxt, and generic fallback.
"""
import logging
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class CMSDetectionResult:
    platform: str           # "wordpress", "shopify", "webflow", "unknown", etc.
    version: str | None     # e.g., "6.4.3" for WordPress
    confidence: float       # 0.0-1.0
    detection_method: str   # "regex", "wappalyzer", "dns", "combined"
    technologies: List[str] # additional detected tech: ["React", "Cloudflare", ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Tier 1: Regex Pattern Detection ──────────────────────────────

CMS_SIGNATURES: Dict[str, Dict[str, Any]] = {
    # ── Existing platforms ──────────────────────────────────────
    "wordpress": {
        "html": [
            r'/wp-content/',
            r'/wp-includes/',
            r'<meta\s+name=["\']generator["\']\s+content=["\']WordPress\s*([\d.]*)',
            r'wp-json',
        ],
        "headers": [
            r'X-Powered-By:\s*PHP',
            r'Link:.*wp-json',
        ],
        "version_pattern": r'<meta\s+name=["\']generator["\']\s+content=["\']WordPress\s+([\d.]+)',
    },
    "shopify": {
        "html": [
            r'cdn\.shopify\.com',
            r'Shopify\.theme',
            r'shopify-section',
        ],
        "headers": [
            r'X-Shopify-Stage',
            r'X-ShopId',
        ],
    },
    "webflow": {
        "html": [
            r'data-wf-page',
            r'data-wf-site',
            r'<meta\s+name=["\']generator["\']\s+content=["\']Webflow',
            r'website-files\.com',
        ],
    },
    "framer": {
        "html": [
            r'framer-body',
            r'data-framer-hydrate-v2',
            r'framerusercontent\.com',
        ],
    },
    "wix": {
        "html": [
            r'static\.parastorage\.com',
            r'wixstatic\.com',
            r'_wix_browser_sess',
        ],
        "headers": [
            r'X-Wix-Request-Id',
        ],
    },
    "squarespace": {
        "html": [
            r'static\.squarespace\.com',
            r'sqsp-',
            r'<meta\s+name=["\']generator["\']\s+content=["\']Squarespace',
        ],
    },
    "nextjs": {
        "html": [
            r'__NEXT_DATA__',
            r'/_next/static/',
        ],
        "headers": [
            r'X-Powered-By:\s*Next\.js',
        ],
    },
    "gatsby": {
        "html": [
            r'<div\s+id=["\']___gatsby["\']',
            r'<meta\s+name=["\']generator["\']\s+content=["\']Gatsby',
        ],
    },
    "nuxt": {
        "html": [
            r'__NUXT__',
            r'/_nuxt/',
        ],
    },
    # ── Tier 1 new platforms ────────────────────────────────────
    "joomla": {
        "html": [
            r'/components/com_',
            r'/modules/mod_',
            r'<meta\s+name=["\']generator["\']\s+content=["\']Joomla',
            r'/media/system/js/',
        ],
        "headers": [
            r'X-Powered-By:\s*PHP',
        ],
        "version_pattern": r'<meta\s+name=["\']generator["\']\s+content=["\']Joomla!\s*([\d.]+)',
    },
    "hubspot": {
        "html": [
            r'js\.hs-scripts\.com',
            r'js\.hubspot\.com',
            r'_hcms',
            r'hs-sites\.com',
            r'<!--\s*HubSpot',
        ],
        "headers": [
            r'X-HubSpot-',
        ],
    },
    "weebly": {
        "html": [
            r'cdn\d*\.editmysite\.com',
            r'weebly\.com/uploads/',
            r'class=["\'][^"\']*wsite-',
            r'weeblycloud\.com',
        ],
    },
    # ── Tier 2 platforms ────────────────────────────────────────
    "drupal": {
        "html": [
            r'/sites/all/',
            r'/sites/default/files/',
            r'Drupal\.settings',
            r'<meta\s+name=["\']generator["\']\s+content=["\']Drupal',
        ],
        "headers": [
            r'X-Drupal-Cache',
            r'X-Generator:\s*Drupal',
        ],
        "version_pattern": r'<meta\s+name=["\']generator["\']\s+content=["\']Drupal\s+([\d.]+)',
    },
    "duda": {
        "html": [
            r'cdn\.duda\.co',
            r'dm-layouts',
            r'class=["\'][^"\']*dmBody',
            r'duda\.co/templates',
        ],
    },
    "craft": {
        "html": [
            r'/cpresources/',
            r'<meta\s+name=["\']generator["\']\s+content=["\']Craft\s*CMS',
            r'craft-cms',
        ],
        "headers": [
            r'X-Powered-By:\s*Craft\s*CMS',
        ],
    },
    "ghost": {
        "html": [
            r'ghost-(?:url|api)',
            r'class=["\'][^"\']*gh-',
            r'ghost\.io',
            r'<meta\s+name=["\']generator["\']\s+content=["\']Ghost',
        ],
    },
    "bigcommerce": {
        "html": [
            r'cdn\d*\.bigcommerce\.com',
            r'/product_images/',
            r'data-stencil-',
            r'BigCommerce',
        ],
        "headers": [
            r'X-BC-',
        ],
    },
    # ── Tier 3 platforms (detection-only) ───────────────────────
    "hugo": {
        "html": [
            r'<meta\s+name=["\']generator["\']\s+content=["\']Hugo',
        ],
    },
    "jekyll": {
        "html": [
            r'<meta\s+name=["\']generator["\']\s+content=["\']Jekyll',
            r'/assets/css/style\.css\?v=',
        ],
    },
    "astro": {
        "html": [
            r'astro-island',
            r'astro-slot',
            r'<meta\s+name=["\']generator["\']\s+content=["\']Astro',
        ],
    },
    "sveltekit": {
        "html": [
            r'__sveltekit/',
            r'data-sveltekit-',
            r'svelte-',
        ],
    },
    "typo3": {
        "html": [
            r'<meta\s+name=["\']generator["\']\s+content=["\']TYPO3',
            r'/typo3conf/',
            r'/typo3temp/',
        ],
    },
    "aem": {
        "html": [
            r'/content/dam/',
            r'/etc\.clientlibs/',
            r'cq-authoring',
        ],
        "headers": [
            r'X-Powered-By:\s*Adobe',
        ],
    },
    "magento": {
        "html": [
            r'mage/cookies',
            r'Magento_',
            r'/static/version',
            r'<meta\s+name=["\']generator["\']\s+content=["\']Magento',
        ],
    },
    "prestashop": {
        "html": [
            r'prestashop',
            r'/modules/ps_',
            r'<meta\s+name=["\']generator["\']\s+content=["\']PrestaShop',
        ],
    },
    "cargo": {
        "html": [
            r'cargo\.site',
            r'cargocollective\.com',
        ],
    },
    "readymag": {
        "html": [
            r'readymag\.com',
            r'class=["\'][^"\']*rm-',
        ],
    },
    "contentful": {
        "html": [
            r'contentful\.com',
            r'ctfassets\.net',
        ],
    },
    "strapi": {
        "html": [
            r'strapi',
        ],
        "headers": [
            r'X-Powered-By:\s*Strapi',
        ],
    },
    "sanity": {
        "html": [
            r'sanity\.io',
            r'cdn\.sanity\.io',
        ],
    },
}

# Additional technology fingerprints (not full CMS, but useful to report)
TECH_SIGNATURES: Dict[str, List[str]] = {
    "React": [r'react\.production\.min\.js', r'__REACT_DEVTOOLS', r'data-reactroot'],
    "Vue.js": [r'vue\.runtime', r'__VUE__', r'data-v-[a-f0-9]'],
    "Angular": [r'ng-version', r'angular\.min\.js'],
    "jQuery": [r'jquery[\.-][\d]+', r'jQuery\.fn\.jquery'],
    "Tailwind CSS": [r'tailwindcss', r'tw-'],
    "Bootstrap": [r'bootstrap\.min\.(css|js)', r'class=["\'][^"\']*\bcontainer-fluid\b'],
    "Google Analytics": [r'googletagmanager\.com', r'google-analytics\.com', r'gtag/js'],
    "Google Tag Manager": [r'googletagmanager\.com/gtm\.js'],
    "Cloudflare": [r'cdnjs\.cloudflare\.com', r'cf-ray'],
    "Hotjar": [r'static\.hotjar\.com', r'hotjar\.com/c/hotjar'],
    "HubSpot": [r'js\.hs-scripts\.com', r'js\.hubspot\.com'],
    "Intercom": [r'widget\.intercom\.io', r'intercomSettings'],
}


def detect_cms_from_html(
    html_content: str,
    response_headers: Dict[str, str] | None = None,
) -> CMSDetectionResult:
    """Detect CMS from HTML content and HTTP response headers.

    Args:
        html_content: Full HTML source of the homepage.
        response_headers: HTTP response headers dict (header name → value).

    Returns:
        CMSDetectionResult with platform, version, confidence, and detected technologies.
    """
    headers_str = ""
    if response_headers:
        headers_str = "\n".join(f"{k}: {v}" for k, v in response_headers.items())

    # Score each CMS
    cms_scores: Dict[str, float] = {}
    cms_versions: Dict[str, str | None] = {}

    for cms, sigs in CMS_SIGNATURES.items():
        score = 0.0
        html_patterns = sigs.get("html", [])
        header_patterns = sigs.get("headers", [])

        for pattern in html_patterns:
            if re.search(pattern, html_content, re.IGNORECASE):
                score += 1.0

        for pattern in header_patterns:
            if headers_str and re.search(pattern, headers_str, re.IGNORECASE):
                score += 1.5  # header matches are stronger signals

        if score > 0:
            cms_scores[cms] = score

        # Try to extract version
        version_pat = sigs.get("version_pattern")
        if version_pat:
            match = re.search(version_pat, html_content, re.IGNORECASE)
            if match:
                cms_versions[cms] = match.group(1)

    # Detect additional technologies
    technologies: List[str] = []
    for tech, patterns in TECH_SIGNATURES.items():
        for pattern in patterns:
            if re.search(pattern, html_content, re.IGNORECASE):
                technologies.append(tech)
                break
        if headers_str:
            for pattern in patterns:
                if re.search(pattern, headers_str, re.IGNORECASE):
                    if tech not in technologies:
                        technologies.append(tech)
                    break

    if not cms_scores:
        return CMSDetectionResult(
            platform="unknown",
            version=None,
            confidence=0.0,
            detection_method="regex",
            technologies=technologies,
        )

    # Pick the highest-scoring CMS
    best_cms = max(cms_scores, key=cms_scores.get)  # type: ignore[arg-type]
    best_score = cms_scores[best_cms]
    max_possible = len(CMS_SIGNATURES[best_cms].get("html", [])) + \
                   len(CMS_SIGNATURES[best_cms].get("headers", [])) * 1.5
    confidence = min(best_score / max(max_possible, 1), 1.0)

    return CMSDetectionResult(
        platform=best_cms,
        version=cms_versions.get(best_cms),
        confidence=round(confidence, 3),
        detection_method="regex",
        technologies=technologies,
    )


# ── Tier 3: DNS CNAME Detection ──────────────────────────────────

DNS_CNAME_PATTERNS: Dict[str, str] = {
    "shopify": r"\.myshopify\.com|\.shopify\.com",
    "webflow": r"\.webflow\.io|proxy-ssl\.webflow\.com",
    "squarespace": r"\.squarespace\.com",
    "framer": r"\.framer\.app|\.framer\.website",
    "wix": r"\.wixsite\.com|\.wixdns\.net",
    "ghost": r"\.ghost\.io",
    "hubspot": r"\.hubspot\.com|\.hs-sites\.com",
    "weebly": r"\.weebly\.com",
    "duda": r"\.dudaone\.com|\.multiscreensite\.com",
    "bigcommerce": r"\.mybigcommerce\.com",
    "cargo": r"\.cargo\.site",
}


async def detect_cms_from_dns(domain: str) -> CMSDetectionResult | None:
    """Supplemental CMS detection via DNS CNAME records.
    Only called when Tier 1 regex returns 'unknown' or low confidence.
    """
    try:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(domain, "CNAME")
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            return None

        for rdata in answers:
            cname = str(rdata.target).lower()
            for platform, pattern in DNS_CNAME_PATTERNS.items():
                if re.search(pattern, cname):
                    return CMSDetectionResult(
                        platform=platform,
                        version=None,
                        confidence=0.7,
                        detection_method="dns",
                        technologies=[],
                    )
    except ImportError:
        logger.debug("dnspython not installed — skipping DNS CNAME detection")
    except Exception as e:
        logger.debug(f"DNS CNAME detection failed for {domain}: {e}")

    return None


# ── Combined Detection ────────────────────────────────────────────


async def detect_cms(
    html_content: str,
    response_headers: Dict[str, str] | None = None,
    domain: str | None = None,
) -> CMSDetectionResult:
    """Run full CMS detection pipeline.

    1. Regex patterns on HTML + headers (primary, fast)
    2. DNS CNAME check (supplemental, if regex confidence < 0.5)

    Args:
        html_content: Homepage HTML.
        response_headers: HTTP response headers.
        domain: Domain for DNS lookup (extracted from URL if not provided).
    """
    # Tier 1: Regex
    result = detect_cms_from_html(html_content, response_headers)

    if result.platform != "unknown" and result.confidence >= 0.5:
        return result

    # Tier 3: DNS CNAME (if regex was inconclusive)
    if domain:
        dns_result = await detect_cms_from_dns(domain)
        if dns_result:
            # Merge technologies from regex scan
            dns_result.technologies = list(set(result.technologies + dns_result.technologies))
            if result.platform != "unknown":
                # Both detected something — combine
                dns_result.detection_method = "combined"
                dns_result.confidence = min(dns_result.confidence + result.confidence * 0.3, 1.0)
            return dns_result

    return result
