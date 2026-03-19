# Master Prompt: WAIO Webflow Audit Tool (v1.1)

---

## 1. Persona

You are a **senior full-stack software engineer and senior Python developer with at least 15 years of experience** building production-grade web applications, developer tools, and automated analysis engines. You have deep expertise in Python (FastAPI, Playwright, lxml, BeautifulSoup4), TypeScript (React, Vite, TailwindCSS), W3C web standards, Schema.org vocabulary, WCAG 2.1 accessibility guidelines, and Google Search Central documentation. You write clean, modular, well-tested code and you never rely on AI/LLM services for core application logic.

---

## 2. Project Context

### 2.1 Business Goal

The WAIO (Web AI Optimization) framework is a system of HTML attributes and structured data practices designed to help AI systems understand web content more efficiently. The framework is built on a layered approach:

| Layer | Technology | Purpose |
| --- | --- | --- |
| Layer 1 | Semantic HTML5 Elements | Native browser and crawler understanding |
| Layer 2 | JSON-LD & Microdata (Schema.org) | Machine-readable entity and relationship declarations |
| Layer 3 | WAIO `data-ai-*` Attributes | AI-specific optimization layer (experimental, under testing) |

This tool focuses exclusively on **Layers 1 and 2**, which are scientifically proven and backed by W3C standards and Google's official documentation. In addition, the tool performs comprehensive audits for **CSS/JS Code Quality** and **WCAG Accessibility**, as these are foundational to a high-performing, user-friendly website and directly relevant to the consulting services offered by Veza Digital.

Layer 3 (`data-ai-*` attributes) is deliberately excluded from this tool's scope because it is currently undergoing a Single Variable Test to validate its effectiveness. The tool must never reference, check for, or recommend `data-ai-*` attributes.

The tool will serve as a **lead-generation instrument** on the Veza Digital website. Potential clients can enter their Webflow site URL, receive a professional audit report, and see exactly where their site falls short on foundational web standards. This creates a natural entry point for WAIO consulting services.

### 2.2 Reference Application

An existing tool, the **WAIO Crawler Tracker** (deployed at `https://waio-crawler-tracker-production.up.railway.app/` ), serves as the **architectural** reference. The new audit tool must use the same tech stack. However, the UI design will follow the branding of the **Veza Digital** agency website (`https://www.vezadigital.com/` ), not the dark glassmorphic theme of the reference app.

| Component | Technology | Notes |
| --- | --- | --- |
| Backend Framework | FastAPI (Python 3.10+) | Single `main.py` entry point with modular auditors |
| HTML Parsing | BeautifulSoup4, lxml | For DOM traversal and element analysis |
| HTTP Client | `requests` | For fetching target URLs |
| JS Rendering & A11y | Playwright (Chromium) + axe-core | For JS-rendered pages and deep accessibility checks |
| Structured Data | `extruct` library (by Zyte) | For extracting JSON-LD, Microdata, OpenGraph, etc. |
| Frontend Framework | React 19 + Vite + TypeScript | Single-page application |
| Styling | TailwindCSS | Based on Veza Digital design tokens |
| Deployment | Docker (multi-stage build) on Railway | Single container serving both frontend and backend |

---

## 3. Core Objective

Build a web application called the **WAIO Webflow Audit Tool** that accepts a URL and performs a comprehensive programmatic audit across five pillars:

1. **Semantic HTML**

1. **Structured Data (JSON-LD & Microdata)**

1. **CSS Quality**

1. **JavaScript Bloat**

1. **WCAG Accessibility**

The tool must present the results in a professional, client-ready report that is branded according to the Veza Digital design system. The entire analysis engine must be deterministic and code-based, with zero reliance on LLM API calls.

---

## 4. Guiding Principles

**Programmatic and Deterministic.** Every check in the audit engine must be implemented as a Python function that produces the same output for the same input. The results must be repeatable, verifiable, and traceable to a specific rule in the codebase.

**Scientifically Grounded.** Every audit check must be directly traceable to one of the following authoritative sources: the W3C HTML5 Specification, the Schema.org vocabulary definition, Google Search Central's structured data documentation, or the WCAG 2.1/2.2 guidelines. The tool must never make claims or recommendations that cannot be backed by these sources.

**No AI Token Consumption.** The backend must not call any LLM API (OpenAI, Anthropic, Google AI, etc.) for its core analysis. This is a hard constraint driven by cost control and the need to eliminate hallucinations from the audit output.

**Webflow-Aware.** While the tool must work on any URL, the analysis engine should be aware of common Webflow-generated HTML patterns. Webflow sites frequently exhibit "div soup" (excessive `<div>` nesting instead of semantic elements), broken heading hierarchies, missing structured data, and specific JavaScript bloat patterns from features like Lottie, Rive, and User Accounts. The recommendations should be phrased in a way that a Webflow developer can act on them within the Webflow Designer.

**Actionable Output.** The report must not just list errors. Every finding must include a clear description of the problem, a specific recommendation for fixing it, a severity level, and a reference to the relevant standard. The goal is to give the client a document they can hand directly to their developer.

**Acknowledge Correct Implementations.** The audit must not only flag problems. When an element is correctly implemented (e.g., a proper `<h1>`, a valid JSON-LD `Organization` block, good color contrast), the report must acknowledge it as a positive finding. This builds trust and credibility with the client.

---

## 5. Backend Architecture (Python & FastAPI)

### 5.1 API Design

The backend exposes the following endpoints:

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/health` | GET | Returns `{"status": "ok"}` for health checks |
| `/api/audit` | POST | Accepts `{"url": "https://..."}` and returns the full audit report JSON |
| `/` | GET | Serves the static frontend build |

The `/api/audit` endpoint is the core of the application. It must validate the input URL, fetch the page, run all five audit modules, compile the results, and return a structured JSON response.

### 5.2 Python Dependencies

```
fastapi
uvicorn
requests
beautifulsoup4
lxml
extruct
w3lib
playwright
axe-playwright-python
cssutils
```

The `extruct` library (by Scrapinghub/Zyte, 950+ GitHub stars ) is the critical dependency for structured data extraction. It supports W3C Microdata, embedded JSON-LD, Microformat, OpenGraph, RDFa, and Dublin Core in a single `extruct.extract()` call. This eliminates the need to write custom parsers for each format.

The `axe-playwright-python` library integrates the industry-standard `axe-core` accessibility engine (by Deque Systems) with Playwright. It enables running dozens of WCAG checks programmatically in a real browser context, which is essential for detecting issues like color contrast failures that cannot be found by parsing HTML alone.

The `cssutils` library provides a CSS parser that can be used to analyze stylesheet content programmatically.

### 5.3 Module Breakdown

The backend code should be organized into the following modules:

**`main.py`** serves as the FastAPI application entry point. It defines the `/api/audit` endpoint, validates the incoming URL, orchestrates calls to the `crawler` and auditor modules, handles errors, and returns the final JSON response. It also serves the static frontend files from the `./static` directory.

**`crawler.py`** is responsible for fetching and preparing the HTML content. Its primary function, `fetch_page(url)`, takes a URL string, performs an HTTP GET request with a standard browser User-Agent, and returns both the raw HTML string and a `BeautifulSoup` object parsed with the `lxml` parser. It must handle common errors: connection timeouts (set a 15-second timeout), HTTP error codes (4xx, 5xx), SSL certificate errors, and redirect chains. If the initial `requests` fetch returns minimal content (indicating a JS-rendered page), it should fall back to Playwright with headless Chromium to render the page. The Playwright browser instance should be shared with the accessibility auditor to avoid launching multiple browser sessions.

**`html_auditor.py`** contains all logic for Pillar 1: Semantic HTML analysis.

**`structured_data_auditor.py`** contains all logic for Pillar 2: JSON-LD and Microdata. It uses `extruct` for extraction and then applies validation rules.

**`css_js_auditor.py`** contains all logic for Pillar 3 (CSS Quality) and Pillar 4 (JavaScript Bloat).

**`accessibility_auditor.py`** contains all logic for Pillar 5: WCAG Accessibility. It uses `axe-playwright-python` for the core scan and augments it with custom checks.

**`scoring.py`** contains the scoring model that compiles individual check results into category scores and an overall score.

**`report_generator.py`** formats the compiled audit data into the final JSON response structure.

---

### 5.4 Pillar 1: Semantic HTML Audit (html_auditor.py)

This module performs the following checks, each implemented as a separate function:

**Check 1.1: Document Foundation.**Verify that the HTML document has a `<!DOCTYPE html>` declaration, that the `<html>` element has a `lang` attribute, that a `<meta charset="utf-8">` tag is present, and that a `<meta name="viewport">` tag is present. These are foundational requirements per the W3C HTML5 specification. Each missing element is a finding.

**Check 1.2: Single H1 Tag.**Count all `<h1>` elements on the page. Per SEO best practices and Google's documentation, each page should have exactly one `<h1>` tag. Zero `<h1>` tags is a `critical` severity finding. More than one `<h1>` is a `high` severity finding.

**Check 1.3: Heading Hierarchy.**Extract all heading elements (`<h1>` through `<h6>`) in document order. Validate that heading levels are sequential and do not skip levels (e.g., an `<h1>` followed directly by an `<h3>` without an intervening `<h2>` is a violation). Each skip is a `high` severity finding. The check should output the full heading tree for the report.

**Check 1.4: Landmark Elements.**Check for the presence of the five core HTML5 landmark elements: `<header>`, `<nav>`, `<main>`, `<footer>`, and `<aside>`. A page should have at least `<header>`, `<nav>`, `<main>`, and `<footer>`. A missing `<main>` element is `critical` (it is the primary landmark for accessibility and crawlers). Other missing landmarks are `high` severity.

**Check 1.5: Semantic Richness (Div-to-Semantic Ratio).**Count the total number of generic container elements (`<div>` and `<span>`) and the total number of semantic elements from the following list: `<header>`, `<nav>`, `<main>`, `<footer>`, `<article>`, `<section>`, `<aside>`, `<figure>`, `<figcaption>`, `<blockquote>`, `<time>`, `<address>`, `<details>`, `<summary>`, `<mark>`, `<dl>`, `<dt>`, `<dd>`. Calculate the **Semantic Ratio** as: `semantic_count / (semantic_count + div_span_count)`. A ratio below 0.15 (less than 15% semantic elements) is a `high` severity finding indicating "div soup." A ratio between 0.15 and 0.30 is `medium`. Above 0.30 is considered healthy.

**Check 1.6: Image Alt Text Coverage.**Count all `<img>` elements and check how many have a non-empty `alt` attribute. Calculate the coverage percentage. Missing `alt` text is a `high` severity finding per WCAG 2.1 (1.1.1 Non-text Content) and Google's image SEO guidelines. Report the total count, the count with alt text, and the coverage percentage.

**Check 1.7: Form Accessibility.**For every `<input>`, `<textarea>`, and `<select>` element, check if it has an associated `<label>` (via the `for` attribute matching the input's `id`) or an `aria-label` attribute. Missing labels are a `high` severity finding per WCAG 2.1 (1.3.1 Info and Relationships).

**Check 1.8: Link Quality.**Check all `<a>` elements. Flag any links with empty `href` attributes, `href="#"`, or `href="javascript:void(0)"` as `medium` severity findings. Also check for links with generic anchor text like "click here," "read more," or "learn more" without additional context (these are `medium` severity per Google's link best practices).

**Check 1.9: Meta Tags.**Check for the presence and quality of essential meta tags: `<title>` (should be 45-60 characters), `<meta name="description">` (should be 135-160 characters), and Open Graph tags (`og:title`, `og:description`, `og:image`). Missing or out-of-range tags are findings.

---

### 5.5 Pillar 2: Structured Data Audit (structured_data_auditor.py)

This module uses `extruct.extract(html_string, base_url=url, syntaxes=['json-ld', 'microdata'])` to extract all JSON-LD blocks and Microdata from the page.

#### JSON-LD Checks

**Check 2.1: JSON-LD Presence.**If no JSON-LD is found on the page, this is a `critical` severity finding. JSON-LD is Google's recommended format for structured data.

**Check 2.2: Valid @context.**Every JSON-LD block must have a `@context` property set to `"https://schema.org"` or `"http://schema.org"`. A missing or invalid context is a `critical` finding.

**Check 2.3: Valid @type.**Every JSON-LD block must have a `@type` property that corresponds to a valid Schema.org type. The tool should maintain a list of the most common and Google-supported types for validation.

**Check 2.4: Required Properties Validation.**For each detected `@type`, the tool must validate that all of Google's **required** properties are present. The validation rules are defined in the following table, derived from Google Search Central documentation:

| Schema Type | Required Properties | Recommended Properties |
| --- | --- | --- |
| `Organization` | `name`, `url` | `logo`, `description`, `sameAs`, `contactPoint`, `address` |
| `LocalBusiness` | `name`, `url`, `address` | `telephone`, `openingHours`, `geo`, `priceRange`, `image` |
| `Article` / `BlogPosting` | `headline`, `author`, `datePublished` | `image`, `dateModified`, `publisher`, `description`, `mainEntityOfPage` |
| `FAQPage` | `mainEntity` (array of `Question` ) | N/A |
| `Question` (within FAQPage) | `name`, `acceptedAnswer` | N/A |
| `Answer` (within Question) | `text` | N/A |
| `Product` | `name` | `image`, `description`, `offers`, `aggregateRating`, `brand` |
| `Offer` (within Product) | `price`, `priceCurrency` | `availability`, `url`, `priceValidUntil` |
| `BreadcrumbList` | `itemListElement` (array of `ListItem`) | N/A |
| `ListItem` (within BreadcrumbList) | `position`, `name` | `item` (URL) |
| `WebSite` | `name`, `url` | `potentialAction` (SearchAction) |
| `Review` | `author`, `reviewRating` | `itemReviewed`, `datePublished`, `reviewBody` |
| `AggregateRating` | `ratingValue`, `reviewCount` or `ratingCount` | `bestRating`, `worstRating` |

A missing required property is a `critical` finding. A missing recommended property is a `medium` finding.

**Check 2.5: Nesting and Relationship Validation.**Verify that nested objects are correctly structured. For example, an `Article` should have an `author` property that is either a `Person` or `Organization` object (not just a plain string), and a `publisher` that is an `Organization` with a `name` and `logo`. A `FAQPage` must contain `mainEntity` as an array of `Question` objects, each with an `acceptedAnswer` of type `Answer`.

**Check 2.6: Recommended Types for Common Pages.**Based on the page content, suggest JSON-LD types that are typically expected but missing. For example, if the page appears to be a homepage (URL path is `/`), recommend `Organization` and `WebSite` schemas. If the page has FAQ-like content (detected by heading patterns like "FAQ," "Frequently Asked Questions"), recommend `FAQPage`. This check should be conservative and only flag `medium` severity suggestions.

#### Microdata Checks

**Check 2.7: Microdata Presence.**Report whether any Microdata is found. Unlike JSON-LD, the absence of Microdata is not necessarily a problem (since JSON-LD can cover the same ground). However, if Microdata is present, it must be valid. If neither JSON-LD nor Microdata is found for key types (FAQ, Review/Testimonial, Article), this is a `high` finding.

**Check 2.8: Scope Integrity.**Using BeautifulSoup, find all elements with `itemprop` attributes and verify that each one is nested within an element that has a corresponding `itemscope` attribute. An orphaned `itemprop` (one that exists outside any `itemscope`) is a `critical` finding because crawlers will ignore it.

**Check 2.9: Valid itemtype URLs.**For every element with `itemscope` and `itemtype`, verify that the `itemtype` URL follows the `https://schema.org/[Type]` pattern and that the type is a valid Schema.org type. An invalid or malformed `itemtype` is a `high` finding.

**Check 2.10: Required Properties for Microdata Types.**Apply the same required/recommended property validation as in Check 2.4, but using the `itemprop` attributes found within each `itemscope`. The same table of required properties applies.

**Check 2.11: JSON-LD and Microdata Alignment.**If both JSON-LD and Microdata are present on the page for the same schema type (e.g., both declare an `Organization` ), check for consistency. Conflicting information (e.g., different `name` values) is a `medium` finding.

---

### 5.6 Pillar 3: CSS Quality Audit (css_js_auditor.py)

This module analyzes the CSS class naming conventions and detects common Webflow-specific bloat patterns.

**Check 3.1: Webflow CSS Framework Detection.**Collect a sample of 50-100 class names from the page's HTML. Analyze the naming patterns to classify the site's CSS framework:

| Framework | Detection Pattern | Typical Class Length |
| --- | --- | --- |
| **Client-First** (Finsweet) | Long, descriptive, full-word names with underscores. E.g., `home-header_background-image`, `section-hero_heading-text`. | 25-40+ chars |
| **MAST** (NoCodeSupplyCo) | Concise, grid/layout-focused. E.g., `grid-col-6`, `flex-center`, `text-large`. | 10-20 chars |
| **Lumos** (Wizardry) | Utility-based, class stacking. E.g., `flex gap-md`, `text-bold text-color-primary`. | Utility stacking |
| **No Framework / Custom** | Inconsistent, abbreviated, numbered. E.g., `btn-p`, `hero-section-1`, `new-button`. | Varies |

The algorithm should classify if >70% of sampled classes match a known pattern. The detected framework provides context for all subsequent CSS recommendations. This check does not produce a severity finding; it produces a contextual label.

**Check 3.2: CSS Naming Convention Consistency.**If a framework is detected (e.g., Client-First), scan for classes that violate its naming rules (e.g., abbreviated names, inconsistent separators, mixing framework classes with ad-hoc custom classes). If no framework is detected, flag the lack of a consistent naming system.

| Scenario | Severity | Recommendation |
| --- | --- | --- |
| Framework detected, >90% consistent | Pass | "CSS naming is consistent with [Framework]. Well maintained." |
| Framework detected, 70-90% consistent | `medium` | "Some classes deviate from [Framework] conventions. Refactor non-compliant classes for maintainability." |
| Framework detected, <70% consistent | `high` | "Framework is partially adopted. Significant inconsistencies detected. Recommend full adoption or clear custom guidelines." |
| No framework detected | `high` | "No consistent CSS naming convention detected. Adopt a standard framework like Client-First for improved maintainability." |

**Check 3.3: Inline Style Detection.**Count all elements with inline `style` attributes. Inline styles bypass the cascade, make maintenance harder, and are a common sign of ad-hoc fixes. More than 10 inline styles is a `medium` finding. More than 30 is a `high` finding.

**Check 3.4: External Stylesheet Count.**Count the number of external CSS files loaded via `<link rel="stylesheet">`. More than 5 external stylesheets suggests fragmentation and potential for consolidation. This is a `medium` finding.

**Check 3.5: Render-Blocking Resources.**Count `<script>` tags in the `<head>` that lack `async` or `defer` attributes. Each one is a render-blocking resource that delays page rendering. More than 2 render-blocking scripts is a `medium` finding.

---

### 5.7 Pillar 4: JavaScript Bloat Audit (css_js_auditor.py)

This module detects Webflow-specific JavaScript bloat contributors.

**Check 4.1: Webflow.js Feature Detection.**Scan the page's HTML and script tags for evidence of features known to significantly bloat the `webflow.js` bundle. The following table lists the top contributors and their detection methods:

| Feature | Minified Size Added | Detection Method |
| --- | --- | --- |
| **User Accounts** | +143.5 kB | Presence of `webflow-user-account` in script src or inline scripts |
| **Lottie Animations** | +102.4 kB | Presence of `<lottie-player>` elements, `data-animation-type="lottie"`, or `lottie` in script src |
| **Interactions (IX2)** | +43 kB | Presence of `data-wf-ix` attributes or `Webflow.require('ix2')` in scripts |
| **E-Commerce** | +42.7 kB | Presence of `webflow-ecommerce` in script src or `data-commerce` attributes |
| **Rive** | +36.7 kB | Presence of `<canvas>` with `data-rive-src`, or `rive` in script src |

Each detected feature is a `medium` severity finding with a recommendation explaining the size impact and suggesting evaluation of whether the feature is critical. For User Accounts and E-Commerce, note that these are permanent once enabled and cannot be removed.

**Check 4.2: Third-Party Script Count.**Count all `<script>` tags with `src` attributes pointing to external domains (not the site's own domain or `assets.website-files.com`). A high number of third-party scripts (>5) is a `medium` finding. List the domains for the report.

**Check 4.3: Total Script Tag Count.**Count all `<script>` tags on the page (inline and external). More than 15 total scripts is a `medium` finding indicating potential script bloat.

---

### 5.8 Pillar 5: WCAG Accessibility Audit (accessibility_auditor.py)

This module uses the `axe-playwright-python` library to run a comprehensive WCAG 2.1 (Level AA) audit in a real browser context, augmented by custom checks.

**Check 5.1: Automated WCAG Scan with Axe-Core.**Initialize Playwright, navigate to the URL, and inject the axe-core library. Run `axe.run()` which executes dozens of WCAG checks simultaneously. The key checks covered by axe-core include:

| WCAG Criterion | Check | Axe Rule ID |
| --- | --- | --- |
| 1.1.1 Non-text Content | Images without alt text | `image-alt` |
| 1.3.1 Info and Relationships | Form inputs without labels | `label` |
| 1.4.3 Contrast (Minimum) | Text with insufficient color contrast | `color-contrast` |
| 2.1.1 Keyboard | Elements not keyboard accessible | `keyboard` |
| 2.4.1 Bypass Blocks | Missing skip navigation link | `bypass` |
| 2.4.4 Link Purpose | Links without discernible text | `link-name` |
| 2.4.7 Focus Visible | Focus indicator not visible | `focus-visible` (custom) |
| 3.1.1 Language of Page | Missing `lang` attribute | `html-has-lang` |
| 4.1.1 Parsing | Duplicate IDs | `duplicate-id` |
| 4.1.2 Name, Role, Value | Buttons without accessible names | `button-name` |
| 4.1.2 Name, Role, Value | ARIA attributes used incorrectly | `aria-*` rules |

Each axe-core violation maps to a severity level:

| Axe Impact | Tool Severity |
| --- | --- |
| `critical` | `critical` |
| `serious` | `high` |
| `moderate` | `medium` |
| `minor` | `medium` |

**Check 5.2: Touch Target Size (WCAG 2.5.5).**Augment the axe scan by iterating through all interactive elements (`<button>`, `<a>`, `<input>`, `[role="button"]`). Use Playwright's `element.bounding_box()` to get the rendered dimensions. Flag any element where both width and height are less than 44px as a `high` severity finding. The recommendation should be: "Increase the padding or set a min-width/min-height of 44px for this interactive element to ensure it is easily tappable on mobile devices."

**Check 5.3: Focus Style Audit.**For each interactive element, use Playwright to programmatically focus the element (via `element.focus()`) and then capture its computed styles. Check if the element has a visible focus indicator (e.g., `outline`, `box-shadow`, or `border` change). If `outline: none` is set without a visible alternative, this is a `high` severity finding per WCAG 2.4.7.

**Check 5.4: Keyboard Trap Detection.**Use Playwright to simulate Tab key navigation through the page. Track the focused element after each Tab press. If the focus returns to the same element more than twice in succession (indicating a keyboard trap), flag it as a `critical` finding per WCAG 2.1.2.

**Check 5.5: ARIA Role Validation.**For each element with an ARIA `role` attribute, verify that all required ARIA attributes for that role are present. For example, `role="button"` requires `tabIndex="0"` for keyboard accessibility. `role="checkbox"` requires `aria-checked`. Missing required attributes are `high` severity findings per WCAG 4.1.2.

---

### 5.9 Scoring Model (scoring.py)

The scoring model produces five category scores and one overall score, all on a 0-100 scale.

Each category starts at 100 points. Points are deducted for each finding based on severity:

| Severity | Point Deduction | Description |
| --- | --- | --- |
| `critical` | -15 points | Fundamental issue that breaks functionality or standards compliance |
| `high` | -8 points | Significant issue that materially impacts SEO or accessibility |
| `medium` | -3 points | Minor issue or missing recommended enhancement |

The minimum score for any category is 0. The **Overall Score** is a weighted average of the five category scores:

| Category | Weight | Rationale |
| --- | --- | --- |
| Semantic HTML | 25% | Foundation of all web content; impacts accessibility, SEO, and AI understanding |
| Structured Data (JSON-LD & Microdata) | 20% | Google's recommended structured data format; directly impacts rich results |
| CSS Quality | 10% | Affects maintainability, performance, and developer experience |
| JavaScript Bloat | 5% | Proxy for performance impact; Webflow-specific concern |
| Accessibility (WCAG) | 40% | Critical for user experience, legal compliance, and inclusive design |

The overall score should also include a qualitative label:

| Score Range | Label | Color (for UI) |
| --- | --- | --- |
| 90-100 | Excellent | `#22C55E` (Green) |
| 70-89 | Good | `#84CC16` (Light Green) |
| 50-69 | Needs Improvement | `#EAB308` (Amber) |
| 30-49 | Poor | `#F97316` (Orange) |
| 0-29 | Critical | `#EF4444` (Red) |

---

### 5.10 Report JSON Structure (report_generator.py)

The `/api/audit` endpoint must return a JSON object with the following structure:

```json
{
  "url": "https://example.com",
  "audit_timestamp": "2026-03-06T12:00:00Z",
  "overall_score": 62,
  "overall_label": "Needs Improvement",
  "categories": {
    "semantic_html": {
      "score": 65,
      "label": "Needs Improvement",
      "checks": {
        "document_foundation": {
          "status": "pass",
          "details": { "doctype": true, "lang": "en", "charset": true, "viewport": true }
        },
        "heading_h1": {
          "status": "fail",
          "details": { "h1_count": 0 },
          "findings": [
            {
              "severity": "critical",
              "description": "No H1 tag found on the page.",
              "recommendation": "Add a single H1 tag that clearly describes the page content. In Webflow, select your main heading element and change its tag to H1 in the element settings.",
              "reference": "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#use-heading-tags"
            }
          ]
        }
      }
    },
    "structured_data": {
      "score": 80,
      "label": "Good",
      "checks": {}
    },
    "css_quality": {
      "score": 55,
      "label": "Needs Improvement",
      "checks": {
        "framework_detection": {
          "status": "info",
          "details": { "detected_framework": "Client-First", "consistency": 0.78 }
        }
      }
    },
    "js_bloat": {
      "score": 70,
      "label": "Good",
      "checks": {}
    },
    "accessibility": {
      "score": 48,
      "label": "Poor",
      "checks": {
        "axe_scan": {
          "status": "fail",
          "details": { "violations_count": 14 },
          "findings": []
        }
      }
    }
  },
  "positive_findings": [
    "Valid DOCTYPE declaration found.",
    "HTML lang attribute correctly set to 'en'.",
    "Organization JSON-LD schema found with all required properties.",
    "CSS naming follows Client-First conventions (78% consistency ).",
    "No keyboard traps detected."
  ],
  "summary": {
    "total_findings": 28,
    "critical": 4,
    "high": 9,
    "medium": 15,
    "top_priorities": [
      "Add a single H1 tag to the page.",
      "Fix 6 color contrast violations identified by the accessibility scan.",
      "Add FAQPage JSON-LD schema for the FAQ section.",
      "Remove 3 render-blocking scripts from the head.",
      "Add visible focus styles to all interactive elements."
    ]
  }
}
```

---

## 6. Frontend Architecture & Design System

### 6.1 Design Language (Veza Digital Brand)

The frontend must adhere to the **Veza Digital** brand identity, extracted from `https://www.vezadigital.com/`. The design language is a clean, high-contrast, professional B2B aesthetic with minimal decoration.

#### Color Palette

| Token | Hex Value | RGB | Usage |
| --- | --- | --- | --- |
| `--color-primary` | `#2820FF` | `rgb(40, 32, 255 )` | CTA buttons, active states, accent highlights, announcement bar |
| `--color-bg-light` | `#FFFFFF` | `rgb(255, 255, 255)` | Primary page background |
| `--color-bg-dark` | `#000000` | `rgb(0, 0, 0)` | Footer, dark sections, inverted content areas |
| `--color-bg-card` | `#E3E8EF` | `rgb(227, 232, 239)` | Card backgrounds, content containers |
| `--color-text-primary` | `#000000` | `rgb(0, 0, 0)` | Headings |
| `--color-text-body` | `#333333` | `rgb(51, 51, 51)` | Body text, paragraphs |
| `--color-text-muted` | `#6B7280` | `rgb(107, 114, 128)` | Secondary text, labels, captions |
| `--color-text-on-dark` | `#FFFFFF` | `rgb(255, 255, 255)` | Text on dark backgrounds |
| `--color-score-excellent` | `#22C55E` |  | Score label: Excellent (90-100) |
| `--color-score-good` | `#84CC16` |  | Score label: Good (70-89) |
| `--color-score-needs-improvement` | `#EAB308` |  | Score label: Needs Improvement (50-69) |
| `--color-score-poor` | `#F97316` |  | Score label: Poor (30-49) |
| `--color-score-critical` | `#EF4444` |  | Score label: Critical (0-29) |

#### Typography

| Element | Font Family | Size | Weight | Letter Spacing | Line Height |
| --- | --- | --- | --- | --- | --- |
| H1 (Hero) | PPMori, Arial, sans-serif | 72-106px (responsive) | 500 | -2.24px | 1.18 |
| H2 (Section) | PPMori, Arial, sans-serif | 24-36px | 500 | -0.24px | 1.3 |
| H3 (Card Title) | PPMori, Arial, sans-serif | 18-20px | 500 | normal | 1.4 |
| Body | PPMori, Arial, sans-serif | 16px | 400 | normal | 1.6 |
| Label/Caption | PPMori, Arial, sans-serif | 14px | 400 | -0.16px | 1.4 |
| Section Label | PPMori, Arial, sans-serif | 16px | 400 | normal | uppercase |

> **Note on PPMori:** PPMori is a commercial font. If licensing is not available, use `Inter` (Google Fonts) as a close substitute. Inter is a geometric sans-serif with similar proportions and is freely available.

#### UI Components

**Buttons.** Primary CTA buttons use a pill shape (`border-radius: 500px`), solid `#2820FF` background, white uppercase text, and `padding: 16px 26px`. On hover, the background should darken slightly (e.g., `#1E18CC`).

**Cards.** Content cards use `background: #E3E8EF`, `border-radius: 8px`, `padding: 32px`, no border, and no box-shadow. This creates a clean, flat appearance.

**Score Gauge.** The overall score should be displayed as a large circular gauge (SVG-based) with the score number centered inside. The gauge ring color should correspond to the qualitative label color from the table above.

**Severity Badges.** Findings should be tagged with colored badges: `critical` (red `#EF4444`), `high` (orange `#F97316`), `medium` (amber `#EAB308`).

**Sections.** The page should alternate between white (`#FFFFFF`) and dark (`#000000`) background sections for visual rhythm, consistent with the Veza Digital homepage pattern.

### 6.2 Page Layout

The application is a single-page app with the following sections:

**Header Section.** Displays the tool name ("WAIO Webflow Audit"), a brief subtitle explaining its purpose, and the Veza Digital branding. Consider including a small announcement bar at the top in `#2820FF` linking to the main Veza Digital site.

**Input Section.** Contains a URL input field with placeholder text (e.g., `https://your-webflow-site.com` ), and a "Run Audit" button (pill-shaped, primary blue). Input validation should ensure the URL starts with `http://` or `https://`.

**Loading State.** While the backend processes the audit (which may take 10-30 seconds due to Playwright ), display a loading animation with progress indicators or status messages (e.g., "Fetching page...", "Analyzing semantic structure...", "Running accessibility scan...", "Compiling results...").

**Results Dashboard.** Once the audit is complete, display the results in a structured layout:

The **Overall Score** should be displayed prominently at the top, using a large circular gauge with the qualitative label and corresponding color.

Below the overall score, display five **Category Cards** (responsive grid: 3+2 on desktop, stacked on mobile), one for each pillar. Each card shows the category score, label, and a count of findings by severity.

Below the category cards, display a **Positive Findings** section that lists what the site is doing correctly. Use green checkmark icons.

Below the positive findings, display a **Detailed Findings** section with collapsible/expandable panels for each category. Within each category, findings should be grouped by severity (Critical first, then High, then Medium). Each finding should display its description, recommendation, and a clickable link to the reference standard.

At the bottom, display a **Top Priorities** section that lists the 3-5 most impactful actions the site owner should take.

### 6.3 Component Structure

```
App.tsx
├── Header (with optional announcement bar)
├── AuditForm (URL input + pill button)
├── LoadingState (animated progress with status messages)
├── AuditReport
│   ├── OverallScore (circular SVG gauge)
│   ├── CategoryCards (5x: Semantic, Structured Data, CSS, JS, Accessibility)
│   ├── PositiveFindings (green checkmarks list)
│   ├── DetailedFindings
│   │   ├── SemanticHTMLFindings (collapsible)
│   │   ├── StructuredDataFindings (collapsible)
│   │   ├── CSSQualityFindings (collapsible)
│   │   ├── JSBloatFindings (collapsible)
│   │   └── AccessibilityFindings (collapsible)
│   └── TopPriorities (numbered action items)
└── Footer (dark background, Veza Digital branding)
```

---

## 7. Deployment

### 7.1 Docker Configuration

Use a multi-stage Dockerfile:

Stage 1 builds the frontend using `node:18-slim`, runs `npm install` and `npm run build`, producing static files in `dist/`.

Stage 2 uses `python:3.10-slim`, installs system dependencies (Playwright's Chromium browser and its dependencies), installs Python dependencies from `requirements.txt`, runs `playwright install chromium`, copies the backend code, copies the frontend build from Stage 1 into `./static`, and starts the application with `uvicorn main:app --host 0.0.0.0 --port 8000`.

### 7.2 Railway Deployment

The application should be deployable to Railway with a single `Dockerfile`. The `PORT` environment variable should default to `8000`.

---

## 8. Authoritative References

Every audit check in this tool is grounded in one or more of the following authoritative sources. The tool's report must link findings back to these references.

| Reference ID | Source | URL |
| --- | --- | --- |
| W3C-HTML5 | W3C HTML5 Specification | `https://www.w3.org/TR/html5/` |
| W3C-ARIA | W3C WAI-ARIA Practices | `https://www.w3.org/WAI/ARIA/apg/` |
| WCAG-2.1 | Web Content Accessibility Guidelines 2.1 | `https://www.w3.org/TR/WCAG21/` |
| WCAG-2.2 | Web Content Accessibility Guidelines 2.2 | `https://www.w3.org/TR/WCAG22/` |
| SCHEMA-ORG | Schema.org Full Hierarchy | `https://schema.org/docs/full.html` |
| GOOG-SD | Google Search Central: Structured Data | `https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data` |
| GOOG-ORG | Google: Organization Markup | `https://developers.google.com/search/docs/appearance/structured-data/organization` |
| GOOG-ART | Google: Article Markup | `https://developers.google.com/search/docs/appearance/structured-data/article` |
| GOOG-FAQ | Google: FAQ Markup | `https://developers.google.com/search/docs/appearance/structured-data/faqpage` |
| GOOG-PROD | Google: Product Markup | `https://developers.google.com/search/docs/appearance/structured-data/product` |
| GOOG-LOCAL | Google: LocalBusiness Markup | `https://developers.google.com/search/docs/appearance/structured-data/local-business` |
| GOOG-BREAD | Google: Breadcrumb Markup | `https://developers.google.com/search/docs/appearance/structured-data/breadcrumb` |
| GOOG-SEO | Google SEO Starter Guide | `https://developers.google.com/search/docs/fundamentals/seo-starter-guide` |
| AXE-CORE | Axe-Core Accessibility Engine (Deque ) | `https://github.com/dequelabs/axe-core` |
| AXE-PW-PY | Axe-Playwright-Python | `https://github.com/pamelafox/axe-playwright-python` |
| EXTRUCT | Extruct Library (Zyte ) | `https://github.com/scrapinghub/extruct` |
| CLIENT-FIRST | Finsweet Client-First Documentation | `https://finsweet.com/client-first` |
| MAST | MAST Framework Documentation | `https://www.nocodesupply.co/mast` |
| LUMOS | Lumos Framework Documentation | `https://www.wizardry.design/lumos` |

---

## 9. Explicit Exclusions

The following items are explicitly **out of scope** for this tool and must not be implemented:

**`data-ai-*`**** attributes.** Do not check for, recommend, or reference any WAIO `data-ai-*` attributes. These are under active testing and have not yet been scientifically validated.

**Performance auditing (Core Web Vitals ).** Do not measure page load times, Largest Contentful Paint, Cumulative Layout Shift, or other Core Web Vitals. The JS bloat check is a proxy indicator, not a direct performance measurement.

**CMS structure.** Do not analyze Webflow CMS collections, fields, or content workflows.

**AI-powered analysis.** Do not use any LLM API calls for generating descriptions, recommendations, or analysis. All output must be deterministic and template-based.

---

## 10. Development Workflow

Follow this sequence when building the application:

**Step 1: Project Scaffolding.** Create the project directory structure with separate `backend/` and `frontend/` directories, a `Dockerfile`, and a `README.md`.

**Step 2: Backend Core - Crawler.** Implement `crawler.py` and verify it can fetch and parse HTML from a live Webflow URL. Implement the Playwright fallback for JS-rendered pages.

**Step 3: Backend - Semantic HTML Auditor.** Write and test `html_auditor.py` with all nine checks against a live Webflow site.

**Step 4: Backend - Structured Data Auditor.** Write and test `structured_data_auditor.py` with all JSON-LD and Microdata checks using `extruct`.

**Step 5: Backend - CSS/JS Auditor.** Write and test `css_js_auditor.py` with framework detection, naming consistency, and JS bloat detection.

**Step 6: Backend - Accessibility Auditor.** Write and test `accessibility_auditor.py` with `axe-playwright-python` integration and custom checks (touch targets, focus styles, keyboard traps).

**Step 7: Backend - Scoring & Report.** Implement `scoring.py` and `report_generator.py`. Wire everything together in `main.py` and test the `/api/audit` endpoint end-to-end.

**Step 8: Frontend.** Initialize the React + Vite + TypeScript + TailwindCSS project. Configure the Veza Digital design tokens. Build the input form, loading state, and results dashboard with all components.

**Step 9: Integration Testing.** Test the full application against at least 3 different Webflow sites to verify accuracy and edge case handling.

**Step 10: Deployment.** Build the Docker image, test locally, and deploy to Railway.

