"""
Generic (CMS-agnostic) Fix Knowledge Base
Platform-agnostic fix instructions for common audit findings.
Used when the detected CMS is NOT Webflow.
"""
from typing import Dict, List

# Same structure as webflow_fixes.py FIXES dict:
#   finding_pattern, pillar_key, title, steps_markdown, difficulty, estimated_time

GENERIC_FIXES: Dict[str, Dict[str, str]] = {

    # ─── Semantic HTML ───

    "document_foundation": {
        "finding_pattern": "document_foundation",
        "pillar_key": "semantic_html",
        "title": "Fix Document Foundation Issues",
        "steps_markdown": """1. **DOCTYPE**: Ensure your pages start with `<!DOCTYPE html>`. Most CMS platforms add this automatically — check your theme/template header file.
2. **Lang attribute**: Add `lang="en"` (or your language code) to the `<html>` tag. In most CMS platforms, this is set in the theme's `header.php`, `_document.tsx`, or equivalent template.
3. **Viewport meta tag**: Ensure this exists in your `<head>`:
   ```html
   <meta name="viewport" content="width=device-width, initial-scale=1">
   ```
4. **Charset**: Ensure `<meta charset="UTF-8">` is present in the `<head>` before any other content.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    "heading_h1": {
        "finding_pattern": "heading_h1",
        "pillar_key": "semantic_html",
        "title": "Add or Fix H1 Heading",
        "steps_markdown": """1. Open your page template or content editor and find the main heading.
2. Ensure it uses an `<h1>` tag — not a styled `<div>` or `<span>`.
3. Each page should have exactly **one H1** that describes the page's primary topic.
4. If you have multiple H1 tags, change the extras to H2 or a styled `<div>`.
5. Use browser DevTools (F12 → Elements) to verify: search for `h1` in the DOM.

**Tip**: Run `document.querySelectorAll('h1').length` in the browser console to count H1 tags.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    "heading_hierarchy": {
        "finding_pattern": "heading_hierarchy",
        "pillar_key": "semantic_html",
        "title": "Fix Heading Hierarchy Skips",
        "steps_markdown": """1. Headings must follow a logical order: H1 → H2 → H3 → H4 (no skipping levels).
2. Open browser DevTools and run: `document.querySelectorAll('h1,h2,h3,h4,h5,h6')` to see your heading structure.
3. Common mistake: using H3 under H1 with no H2, because of the visual size.
4. Fix by changing the heading level in your CMS editor or template code.
5. If you want a smaller visual style, use CSS to restyle the correct heading level instead of using the wrong tag.

**Validation**: Use the [HeadingsMap browser extension](https://chromewebstore.google.com/detail/headingsmap) to visualize your heading tree.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    "landmark_elements": {
        "finding_pattern": "landmark_elements",
        "pillar_key": "semantic_html",
        "title": "Add Semantic Landmark Elements",
        "steps_markdown": """1. Replace generic `<div>` wrappers with semantic HTML5 elements:
   - Navigation → `<nav>`
   - Page header → `<header>`
   - Main content area → `<main>` (only one per page)
   - Footer → `<footer>`
   - Sidebars → `<aside>`
2. Edit your theme template files to change the outer wrapper tags.
3. You should have exactly **one `<main>`** element per page.

**Verification**: In browser DevTools, run `document.querySelectorAll('main, nav, header, footer, aside')` to check your landmarks.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "semantic_richness": {
        "finding_pattern": "semantic_richness",
        "pillar_key": "semantic_html",
        "title": "Improve Semantic HTML Ratio",
        "steps_markdown": """1. Audit your page for excessive `<div>` nesting — aim for 30%+ semantic elements.
2. Replace container divs with semantic tags where appropriate:
   - Content sections → `<section>`
   - Articles/blog posts → `<article>`
   - Navigation groups → `<nav>`
   - Sidebar content → `<aside>`
3. Use `<ul>` / `<ol>` for lists of items instead of stacked divs.
4. Use `<table>` for tabular data instead of CSS grid divs.
5. Use `<figure>` and `<figcaption>` for images with captions.

**Goal**: Aim for at least 30% of your elements to be semantic (not plain divs/spans).""",
        "difficulty": "medium",
        "estimated_time": "20 minutes",
    },

    "image_alt_coverage": {
        "finding_pattern": "image_alt_coverage",
        "pillar_key": "semantic_html",
        "title": "Add Alt Text to Images",
        "steps_markdown": """1. Find all images missing alt text. In DevTools console: `document.querySelectorAll('img:not([alt])')`.
2. Add descriptive alt text to each image (e.g., "Team meeting in modern office" not "image1").
3. For decorative images (backgrounds, dividers), use `alt=""` (empty alt) to indicate they're decorative.
4. In your CMS, ensure every image upload field has a corresponding alt text field.
5. Keep alt text under 125 characters and describe the image's content and purpose.

**Bulk check**: Use [Google Lighthouse](https://developer.chrome.com/docs/lighthouse/) to scan for missing alt text across pages.""",
        "difficulty": "easy",
        "estimated_time": "15 minutes",
    },

    "meta_tags": {
        "finding_pattern": "meta_tags",
        "pillar_key": "semantic_html",
        "title": "Fix Meta Tags",
        "steps_markdown": """1. Ensure every page has a unique **title tag** (under 60 characters) and **meta description** (150-160 characters).
2. In your CMS, look for SEO settings per page (or install an SEO plugin like Yoast/RankMath for WordPress).
3. Add Open Graph tags for social sharing:
   - `og:title`, `og:description`, `og:image` (1200x630px)
4. Add `<meta name="robots" content="index, follow">` for pages you want indexed.
5. Validate with [Google's Rich Results Test](https://search.google.com/test/rich-results).

**Each page needs unique meta tags** — don't use the same title/description across multiple pages.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes per page",
    },

    # ─── Structured Data ───

    "json_ld_presence": {
        "finding_pattern": "json_ld_presence",
        "pillar_key": "structured_data",
        "title": "Add JSON-LD Structured Data",
        "steps_markdown": """1. Add a JSON-LD script to your page's `<head>` or before `</body>`:
   ```html
   <script type="application/ld+json">
   {
     "@context": "https://schema.org",
     "@type": "Organization",
     "name": "Your Company",
     "url": "https://yoursite.com"
   }
   </script>
   ```
2. Choose the right schema type for each page: Organization (homepage), Article (blog), Product (shop), etc.
3. For CMS-managed pages, generate JSON-LD dynamically from your content fields.
4. Validate with [Google's Rich Results Test](https://search.google.com/test/rich-results).

**Common types**: Organization, WebSite, Article, BlogPosting, Product, FAQPage, BreadcrumbList.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes",
    },

    "recommended_types": {
        "finding_pattern": "recommended_types",
        "pillar_key": "structured_data",
        "title": "Add Recommended Schema Types",
        "steps_markdown": """1. Identify which schema types are missing from your pages.
2. Common recommendations:
   - **Homepage**: Organization + WebSite + BreadcrumbList
   - **Blog posts**: Article or BlogPosting + BreadcrumbList
   - **Product pages**: Product with offers, reviews
   - **FAQ pages**: FAQPage
   - **Contact page**: LocalBusiness or Organization with contactPoint
3. Add JSON-LD scripts for each missing type.
4. Use [Schema.org documentation](https://schema.org/docs/full.html) for required and recommended properties.

**Priority**: Start with Organization, WebSite, and BreadcrumbList — these have the broadest impact.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes",
    },

    # ─── AEO Content ───

    "readability": {
        "finding_pattern": "readability",
        "pillar_key": "aeo_content",
        "title": "Improve Content Readability",
        "steps_markdown": """1. Target a Flesch-Kincaid Grade Level of **6-8** for general audiences.
2. Break long paragraphs into 2-3 sentence chunks.
3. Use bullet points and numbered lists for multi-item information.
4. Replace jargon with plain language where possible.
5. Use short sentences (under 20 words on average).
6. Add subheadings (H2/H3) every 300 words to break up content.

**Why it matters**: Content at Grade 6-8 readability earns 15% more AI citations (SE Ranking, 2025).""",
        "difficulty": "medium",
        "estimated_time": "20 minutes per page",
    },

    "question_answer_patterns": {
        "finding_pattern": "question_answer_patterns",
        "pillar_key": "aeo_content",
        "title": "Add Question-Answer Patterns",
        "steps_markdown": """1. Identify common questions your audience asks about your topic.
2. Add explicit Q&A sections using heading tags:
   ```html
   <h2>What is [topic]?</h2>
   <p>[Direct answer in 1-2 sentences]</p>
   ```
3. Start answers with the direct response — no preamble.
4. Consider adding an FAQ section with FAQPage schema markup.
5. Use "People Also Ask" from Google Search as inspiration for questions.

**Format**: Question as H2/H3, answer as the first paragraph immediately following.""",
        "difficulty": "easy",
        "estimated_time": "15 minutes per page",
    },

    # ─── Accessibility ───

    "axe_scan": {
        "finding_pattern": "axe_scan",
        "pillar_key": "accessibility",
        "title": "Fix Accessibility Violations",
        "steps_markdown": """1. Run a [Lighthouse accessibility audit](https://developer.chrome.com/docs/lighthouse/accessibility/) in Chrome DevTools.
2. Install the [axe DevTools extension](https://www.deque.com/axe/devtools/) for detailed violation reports.
3. Common fixes:
   - Add `alt` text to images
   - Ensure sufficient color contrast (4.5:1 for normal text, 3:1 for large text)
   - Add `aria-label` to icon-only buttons and links
   - Ensure all form inputs have associated `<label>` elements
4. Fix violations in order of impact: Critical → Serious → Moderate → Minor.
5. Test with keyboard navigation (Tab, Enter, Escape) to ensure all interactive elements are reachable.

**Goal**: Score 90+ on Lighthouse Accessibility.""",
        "difficulty": "medium",
        "estimated_time": "30 minutes",
    },

    "touch_targets": {
        "finding_pattern": "touch_targets",
        "pillar_key": "accessibility",
        "title": "Fix Touch Target Sizes",
        "steps_markdown": """1. All interactive elements (buttons, links, form inputs) should be at least **44x44 CSS pixels**.
2. Check your mobile layout — small links and buttons are common offenders.
3. Add padding to increase clickable area without changing visual size:
   ```css
   .small-link { padding: 8px 12px; min-height: 44px; min-width: 44px; }
   ```
4. Ensure adequate spacing between touch targets (at least 8px gap).
5. Test on a real mobile device — not just browser responsive mode.

**Standard**: WCAG 2.5.5 requires 44x44px minimum for Level AAA compliance.""",
        "difficulty": "easy",
        "estimated_time": "15 minutes",
    },

    # ─── RAG Readiness ───

    "content_noise_ratio": {
        "finding_pattern": "content_noise_ratio",
        "pillar_key": "rag_readiness",
        "title": "Improve Content-to-Noise Ratio",
        "steps_markdown": """1. Reduce boilerplate content that repeats across pages (excessive footers, sidebars, popups).
2. Use semantic landmarks (`<main>`, `<nav>`, `<aside>`) so AI crawlers can identify primary content.
3. Remove or minimize: cookie banners that dominate the page, auto-play videos, excessive ad units.
4. Ensure your main content area contains more text than navigation/chrome elements.
5. Use `<article>` tags to clearly delineate primary content blocks.

**Goal**: Main content should be at least 60% of the visible page content.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes",
    },

    "heading_content_pairing": {
        "finding_pattern": "heading_content_pairing",
        "pillar_key": "rag_readiness",
        "title": "Pair Headings with Content",
        "steps_markdown": """1. Every heading (H2-H6) should have substantial content beneath it — not just another heading.
2. Minimum 50 words of content under each heading for AI retrieval effectiveness.
3. Don't use headings purely for visual styling — use CSS classes instead.
4. Each section (heading + content) should be self-contained and make sense in isolation.
5. Use descriptive headings that summarize the section's content.

**Why**: AI retrieval systems chunk content by headings. Empty or thin sections create poor retrieval quality.""",
        "difficulty": "easy",
        "estimated_time": "15 minutes",
    },

    # ─── Agentic Protocols ───

    "llms_txt": {
        "finding_pattern": "llms_txt",
        "pillar_key": "agentic_protocols",
        "title": "Add llms.txt File",
        "steps_markdown": """1. Create a file at `https://yoursite.com/llms.txt` — similar to `robots.txt` but for AI agents.
2. Format:
   ```
   # Your Site Name
   > Brief description of your site

   ## Key Pages
   - [Homepage](https://yoursite.com/): Main landing page
   - [About](https://yoursite.com/about): Company information
   - [Blog](https://yoursite.com/blog): Latest articles
   ```
3. Upload as a static file to your hosting or add a route that serves plain text.
4. List your most important pages and their purpose.

**Why**: AI agents increasingly check for `llms.txt` to understand site structure and preferred interaction patterns.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "sitemap_quality": {
        "finding_pattern": "sitemap_quality",
        "pillar_key": "agentic_protocols",
        "title": "Fix XML Sitemap Issues",
        "steps_markdown": """1. Ensure your site has an XML sitemap at `https://yoursite.com/sitemap.xml`.
2. Most CMS platforms generate this automatically — check your SEO plugin settings.
3. The sitemap should:
   - Include all indexable pages
   - Exclude noindex pages, redirects, and error pages
   - Use `<lastmod>` dates that reflect actual content changes
   - Be under 50MB and 50,000 URLs per file
4. Submit your sitemap to [Google Search Console](https://search.google.com/search-console).
5. For large sites, use sitemap index files to split into multiple sitemaps.

**Validation**: Use an online sitemap validator to check for errors.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    # ─── Internal Linking ───

    "outgoing_internal_links": {
        "finding_pattern": "outgoing_internal_links",
        "pillar_key": "internal_linking",
        "title": "Optimize Internal Link Count",
        "steps_markdown": """1. Check how many internal links are on your page.
2. **Too few** (under 3): Add contextual links to related pages, breadcrumbs, or a "Related Content" section.
3. **Too many** (over 150): Reduce by consolidating mega-menus, using pagination, or removing redundant footer links.
4. **Ideal range**: 10-50 internal links per page for most content pages.
5. Prioritize contextual links within your main content over navigation-only links.

**Goal**: Every page should link to at least 3 other relevant pages on your site.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "anchor_text_quality": {
        "finding_pattern": "anchor_text_quality",
        "pillar_key": "internal_linking",
        "title": "Improve Internal Link Anchor Text",
        "steps_markdown": """1. Replace vague anchor text ("Click here", "Read more", "Learn more") with descriptive text.
2. Good anchor text describes the destination page's topic in 2-5 words.
3. Examples:
   - "Read more" → "Read our complete SEO audit guide"
   - "Click here" → "View pricing plans"
4. Don't use identical anchor text for links to different pages.
5. Avoid keyword-stuffed anchor text — keep it natural and descriptive.

**Standard**: Descriptive anchor text improves both SEO link equity distribution and accessibility.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },
}


def get_generic_fix(finding_pattern: str) -> Dict[str, str] | None:
    """Look up a generic fix by finding pattern."""
    return GENERIC_FIXES.get(finding_pattern)


def get_all_generic_fixes() -> List[Dict[str, str]]:
    """Return all generic fixes as a list."""
    return list(GENERIC_FIXES.values())


def match_generic_fixes_to_findings(report: dict) -> Dict[str, Dict[str, str]]:
    """Given a report, return generic fixes matched to detected findings."""
    matched: Dict[str, Dict[str, str]] = {}
    categories = report.get("categories", {})
    for pillar_key, pillar_data in categories.items():
        checks = pillar_data.get("checks", {})
        for check_name, check_data in checks.items():
            if not isinstance(check_data, dict):
                continue
            if check_data.get("findings") and check_name in GENERIC_FIXES:
                matched[check_name] = GENERIC_FIXES[check_name]
    return matched
