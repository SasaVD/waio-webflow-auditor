"""
Webflow Fix Knowledge Base — Sprint 2B
Curated fix instructions for common audit findings, specific to Webflow.
Each entry maps a finding pattern (check name) to step-by-step Webflow instructions.
"""
from typing import Dict, Any, List

# Each fix entry:
#   finding_pattern: str  — matches check key from auditors
#   pillar_key: str       — which audit pillar
#   title: str            — human-readable fix title
#   steps_markdown: str   — step-by-step Webflow instructions
#   difficulty: str       — "easy", "medium", "advanced"
#   estimated_time: str   — e.g. "2 minutes", "15 minutes"

FIXES: Dict[str, Dict[str, str]] = {

    # ─── Semantic HTML (html_auditor.py) ───

    "document_foundation": {
        "finding_pattern": "document_foundation",
        "pillar_key": "semantic_html",
        "title": "Fix Document Foundation Issues in Webflow",
        "steps_markdown": """1. **DOCTYPE & charset**: Webflow auto-generates these. If missing, check your custom code in **Project Settings > Custom Code > Head Code** for overrides that may break the default.
2. **Lang attribute**: Go to **Project Settings > General > Localization**. Set your primary language. Webflow adds `lang` automatically when localization is enabled.
3. **Viewport meta tag**: Webflow includes this by default. If missing, add to **Project Settings > Custom Code > Head Code**:
   ```html
   <meta name="viewport" content="width=device-width, initial-scale=1">
   ```""",
        "difficulty": "easy",
        "estimated_time": "2 minutes",
    },

    "heading_h1": {
        "finding_pattern": "heading_h1",
        "pillar_key": "semantic_html",
        "title": "Add or Fix H1 Heading in Webflow",
        "steps_markdown": """1. Open the **Navigator** panel (shortcut: `F`).
2. Find your main heading element. Select it.
3. In the **Settings** panel (right side), check the **Tag** dropdown under the element settings.
4. Change the tag to **H1**.
5. Ensure only **one H1** exists per page. If you have multiple, change extras to H2 or a styled div.
6. Repeat for every page — each page should have its own unique H1.

**Tip**: Use Webflow's **Audit** panel to quickly find heading issues across all pages.""",
        "difficulty": "easy",
        "estimated_time": "2 minutes",
    },

    "heading_hierarchy": {
        "finding_pattern": "heading_hierarchy",
        "pillar_key": "semantic_html",
        "title": "Fix Heading Hierarchy Skips in Webflow",
        "steps_markdown": """1. Open the **Navigator** panel and review your heading structure.
2. Headings must follow a logical order: H1 → H2 → H3 → H4 (no skipping levels).
3. Select any heading that skips a level (e.g., H1 → H3 with no H2).
4. In the **Settings** panel, change the **Tag** dropdown to the correct level.
5. If you used heading tags purely for styling, switch to a **div** or **paragraph** with a custom class instead.

**Common mistake**: Using H3 for a subtitle under H1 because you like the default size. Instead, use H2 and restyle it.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    "landmark_elements": {
        "finding_pattern": "landmark_elements",
        "pillar_key": "semantic_html",
        "title": "Add Semantic Landmarks in Webflow",
        "steps_markdown": """1. Select your top navigation wrapper in the **Navigator**.
2. In **Settings > Tag**, change it from **div** to **nav**.
3. Select your page header section → change tag to **header**.
4. Select your main content wrapper → change tag to **main**.
5. Select your footer section → change tag to **footer**.
6. For sidebars, change the tag to **aside**.

**Important**: You should have exactly **one `<main>`** element per page. The `<header>` and `<footer>` should wrap your site-wide navigation and footer, not individual sections.""",
        "difficulty": "easy",
        "estimated_time": "3 minutes",
    },

    "semantic_richness": {
        "finding_pattern": "semantic_richness",
        "pillar_key": "semantic_html",
        "title": "Improve Semantic HTML Ratio in Webflow",
        "steps_markdown": """1. Open the **Navigator** and look for excessive nesting of **div** elements.
2. Replace container divs with semantic tags where appropriate:
   - Content sections → **section** (add via Tag dropdown)
   - Articles/blog posts → **article**
   - Navigation groups → **nav**
   - Sidebar content → **aside**
3. Use **Rich Text** elements for long-form content instead of stacked div/paragraph combos.
4. For lists of items, use the **List** element (creates proper `<ul>` or `<ol>` markup).
5. For data tables, use Webflow's **Table** element or embed a custom `<table>` in an HTML Embed.

**Goal**: Aim for at least 30% of your elements to be semantic (not plain divs/spans).""",
        "difficulty": "medium",
        "estimated_time": "15 minutes",
    },

    "image_alt_coverage": {
        "finding_pattern": "image_alt_coverage",
        "pillar_key": "semantic_html",
        "title": "Add Alt Text to Images in Webflow",
        "steps_markdown": """1. Select an image element on the canvas or in the **Navigator**.
2. In the **Settings** panel (gear icon), find the **Alt Text** field.
3. Write a concise, descriptive alt text (e.g., "Team meeting in modern office" not "image1").
4. For **decorative images** (backgrounds, dividers), check the **Decorative** checkbox to output an empty alt attribute.
5. For **CMS-bound images**, bind the alt text to a CMS field. Create a "Alt Text" plain text field in your Collection.
6. Use **Webflow's Audit panel** to find all images missing alt text across your site.

**Tip**: Good alt text describes the image's content and purpose in under 125 characters.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "form_accessibility": {
        "finding_pattern": "form_accessibility",
        "pillar_key": "semantic_html",
        "title": "Fix Form Accessibility in Webflow",
        "steps_markdown": """1. Select each form input in the **Navigator**.
2. Ensure every input has a **Label** element linked to it. Webflow's Form Block includes labels by default — don't delete them.
3. If you've hidden labels for design purposes, add **aria-label** via **Settings > Custom Attributes**:
   - Name: `aria-label`
   - Value: Descriptive text (e.g., "Email address")
4. For custom form elements, add `role` and `aria-*` attributes via Custom Attributes.
5. Ensure the **Submit** button has descriptive text (not just "Submit" — use "Send Message" or "Subscribe").

**Common mistake**: Hiding form labels with `display: none` removes them from screen readers. Use a `visually-hidden` class instead.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    "link_quality": {
        "finding_pattern": "link_quality",
        "pillar_key": "semantic_html",
        "title": "Fix Link Quality Issues in Webflow",
        "steps_markdown": """1. **Empty href links**: Select the link element, go to **Settings**, and set a valid URL or page link.
2. **Generic link text**: Change text like "Click here" or "Read more" to descriptive text like "Read our pricing guide" or "View case study results".
3. **JavaScript void links**: Replace `javascript:void(0)` hrefs with proper links or buttons. If it triggers an action, use a **button** element instead.
4. For CMS-bound links, ensure the link text field contains descriptive text, not generic placeholders.
5. Add **aria-label** for icon-only links (e.g., social media icons): Settings > Custom Attributes > `aria-label` = "Visit our Twitter page".""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "meta_tags": {
        "finding_pattern": "meta_tags",
        "pillar_key": "semantic_html",
        "title": "Fix Meta Tags in Webflow",
        "steps_markdown": """1. Select the page in the **Pages** panel (left sidebar).
2. Click the **gear icon** next to the page name to open Page Settings.
3. Fill in:
   - **Title Tag**: Unique, descriptive, under 60 characters
   - **Meta Description**: Compelling summary, 150-160 characters
4. Scroll down to **Open Graph Settings**:
   - **OG Title**: Same as or similar to title tag
   - **OG Description**: Same as meta description
   - **OG Image**: Upload a 1200x630px image
5. For CMS pages, bind these fields to CMS Collection fields.
6. Repeat for **every page** — each page needs unique meta tags.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes per page",
    },

    # ─── Structured Data (structured_data_auditor.py) ───

    "json_ld_presence": {
        "finding_pattern": "json_ld_presence",
        "pillar_key": "structured_data",
        "title": "Add JSON-LD Structured Data in Webflow",
        "steps_markdown": """1. Go to the page in the Webflow Designer.
2. Open **Page Settings** (gear icon in Pages panel).
3. Scroll to **Custom Code > Before </body> tag**.
4. Add your JSON-LD script. Example for a homepage:
   ```html
   <script type="application/ld+json">
   {
     "@context": "https://schema.org",
     "@type": "Organization",
     "name": "Your Company Name",
     "url": "https://yoursite.com",
     "logo": "https://yoursite.com/logo.png",
     "sameAs": ["https://twitter.com/yourco", "https://linkedin.com/company/yourco"]
   }
   </script>
   ```
5. For **site-wide** schema (Organization, WebSite), add it in **Project Settings > Custom Code > Footer Code** so it appears on every page.
6. Use [Google's Rich Results Test](https://search.google.com/test/rich-results) to validate.

**CMS pages**: Use Webflow's Embed element with CMS-bound fields for dynamic JSON-LD.""",
        "difficulty": "medium",
        "estimated_time": "10 minutes",
    },

    "json_ld_context": {
        "finding_pattern": "json_ld_context",
        "pillar_key": "structured_data",
        "title": "Fix JSON-LD @context in Webflow",
        "steps_markdown": """1. Find your JSON-LD script in **Page Settings > Custom Code** or in an **Embed** element.
2. Ensure the `@context` field is set to `"https://schema.org"`.
3. Common mistakes:
   - Missing `@context` entirely
   - Using `http://` instead of `https://`
   - Typos like `"schema.orgs"` or `"shema.org"`
4. Save and republish.""",
        "difficulty": "easy",
        "estimated_time": "2 minutes",
    },

    "json_ld_type": {
        "finding_pattern": "json_ld_type",
        "pillar_key": "structured_data",
        "title": "Fix JSON-LD @type in Webflow",
        "steps_markdown": """1. Open your JSON-LD script in **Page Settings > Custom Code**.
2. Ensure every JSON-LD object has a valid `@type` property.
3. Common types by page:
   - Homepage: `Organization`, `WebSite`
   - About page: `Organization`, `Person`
   - Blog post: `Article`, `BlogPosting`
   - Service page: `Service`, `Product`
   - Contact page: `Organization` with `ContactPoint`
   - FAQ page: `FAQPage`
4. Check the type name at [schema.org](https://schema.org/docs/full.html) — it's case-sensitive.""",
        "difficulty": "easy",
        "estimated_time": "3 minutes",
    },

    "json_ld_properties": {
        "finding_pattern": "json_ld_properties",
        "pillar_key": "structured_data",
        "title": "Add Required Properties to JSON-LD in Webflow",
        "steps_markdown": """1. Open your JSON-LD script and check which `@type` you're using.
2. Add the required/recommended properties for that type:
   - **Organization**: name, url, logo, contactPoint, sameAs
   - **WebSite**: name, url, potentialAction (SearchAction)
   - **Article**: headline, datePublished, dateModified, author, image
   - **Product**: name, description, image, offers (with price, currency)
   - **FAQPage**: mainEntity array with Question/Answer pairs
   - **LocalBusiness**: name, address, telephone, openingHours
3. For CMS pages, use an **Embed** element and bind CMS fields to the JSON values.
4. Validate with [Google's Rich Results Test](https://search.google.com/test/rich-results).""",
        "difficulty": "medium",
        "estimated_time": "15 minutes",
    },

    "json_ld_nesting": {
        "finding_pattern": "json_ld_nesting",
        "pillar_key": "structured_data",
        "title": "Fix Nested JSON-LD Objects in Webflow",
        "steps_markdown": """1. Open your JSON-LD script.
2. Check nested objects have their own `@type`. Common nesting issues:
   - `author` should be `{"@type": "Person", "name": "..."}`
   - `publisher` should be `{"@type": "Organization", "name": "...", "logo": {...}}`
   - `address` should be `{"@type": "PostalAddress", ...}`
3. Don't use plain strings where an object is expected:
   - Wrong: `"author": "John Smith"`
   - Right: `"author": {"@type": "Person", "name": "John Smith"}`
4. Validate the full structure with Google's Rich Results Test.""",
        "difficulty": "medium",
        "estimated_time": "10 minutes",
    },

    "recommended_types": {
        "finding_pattern": "recommended_types",
        "pillar_key": "structured_data",
        "title": "Add Recommended Schema Types in Webflow",
        "steps_markdown": """1. Every homepage should have **Organization** and **WebSite** schema.
2. Add to **Project Settings > Custom Code > Footer Code** (applies site-wide):
   ```html
   <script type="application/ld+json">
   {"@context":"https://schema.org","@type":"WebSite","name":"Your Site","url":"https://yoursite.com"}
   </script>
   ```
3. Pages with Q&A content should add **FAQPage** schema.
4. Blog posts should add **Article** or **BlogPosting** schema.
5. Service/product pages should add **Service** or **Product** schema.
6. For CMS template pages, use an **Embed** element with dynamic bindings.""",
        "difficulty": "medium",
        "estimated_time": "10 minutes",
    },

    "microdata_scope_integrity": {
        "finding_pattern": "microdata_scope_integrity",
        "pillar_key": "structured_data",
        "title": "Fix Orphaned Microdata in Webflow",
        "steps_markdown": """1. If you have `itemprop` attributes on elements without a parent `itemscope`, they're orphaned.
2. In Webflow, select the parent container of the element with microdata.
3. Go to **Settings > Custom Attributes** and add:
   - `itemscope` (leave value empty)
   - `itemtype` = `https://schema.org/YourType`
4. **Recommended**: Switch to JSON-LD instead of microdata. JSON-LD is easier to manage in Webflow and doesn't require modifying element attributes.""",
        "difficulty": "medium",
        "estimated_time": "10 minutes",
    },

    # ─── AEO Content (aeo_content_auditor.py) ───

    "readability": {
        "finding_pattern": "readability",
        "pillar_key": "aeo_content",
        "title": "Improve Content Readability in Webflow",
        "steps_markdown": """1. Open your page in the Webflow Designer and select your **Rich Text** or text content blocks.
2. Simplify your writing:
   - Use shorter sentences (under 20 words)
   - Replace jargon with plain language
   - Break long paragraphs into 2-3 sentence chunks
3. Target **Flesch-Kincaid Grade Level 6-8** for maximum AI citability.
4. Use tools like [Hemingway Editor](https://hemingwayapp.com/) to check readability before pasting into Webflow.
5. For CMS content, create editorial guidelines for content authors.

**Why this matters**: AI engines preferentially cite content that's easy to parse and summarize.""",
        "difficulty": "medium",
        "estimated_time": "20 minutes per page",
    },

    "section_length": {
        "finding_pattern": "section_length",
        "pillar_key": "aeo_content",
        "title": "Optimize Section Lengths in Webflow",
        "steps_markdown": """1. Review your page sections in the **Navigator**.
2. Each section under a heading should be **100-200 words** — the ideal chunk size for AI extraction.
3. If sections are too long (>300 words):
   - Break them into sub-sections with H3/H4 headings
   - Move supporting details into expandable accordions or tabs
4. If sections are too short (<50 words):
   - Expand with supporting detail, examples, or data points
   - Merge with adjacent sections if they cover the same topic
5. Use Webflow's **Rich Text** element for long-form content to maintain clean structure.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes per page",
    },

    "citations_statistics": {
        "finding_pattern": "citations_statistics",
        "pillar_key": "aeo_content",
        "title": "Add Citations and Statistics to Content in Webflow",
        "steps_markdown": """1. Review your content for claims that need supporting data.
2. Add specific statistics with sources. Format: "X% of users... (Source, Year)."
3. In Webflow, use inline text styling for citations:
   - Wrap citation sources in a styled **span** class (e.g., `citation-source`)
   - Or use parenthetical references inline
4. For blog/CMS content, add a "Sources" section at the bottom using a Rich Text element.
5. Link to authoritative sources using external links with descriptive anchor text.

**Goal**: At least 2-3 data-backed claims per page to signal credibility to AI engines.""",
        "difficulty": "medium",
        "estimated_time": "20 minutes per page",
    },

    "question_answer_patterns": {
        "finding_pattern": "question_answer_patterns",
        "pillar_key": "aeo_content",
        "title": "Add Question-Answer Patterns in Webflow",
        "steps_markdown": """1. Identify the key questions your audience asks about the topic.
2. In Webflow, create **H2 or H3 headings phrased as questions**:
   - "What is [topic]?"
   - "How does [feature] work?"
   - "Why choose [solution]?"
3. Follow each question heading immediately with a **concise answer** (40-60 words in the first paragraph).
4. For FAQ sections, use an **Accordion** component:
   - Each item: question as the trigger, answer as the content
   - Add FAQPage JSON-LD schema to match
5. This pattern dramatically increases chances of being cited by AI answer engines.""",
        "difficulty": "easy",
        "estimated_time": "15 minutes",
    },

    "content_freshness_signals": {
        "finding_pattern": "content_freshness_signals",
        "pillar_key": "aeo_content",
        "title": "Add Content Freshness Signals in Webflow",
        "steps_markdown": """1. For **CMS blog posts**: Ensure your Collection has `datePublished` and `dateModified` fields.
2. Display the publish/update date visibly on the page using a CMS-bound text element.
3. In your Article JSON-LD schema, include:
   ```json
   "datePublished": "2025-01-15",
   "dateModified": "2025-03-20"
   ```
4. For **static pages**: Add a "Last updated" line in the footer or header area. Use **Page Settings > Custom Code** or a visible text element.
5. Update the `dateModified` in schema whenever you make content changes.

**Webflow CMS tip**: Bind `dateModified` to a "Last Updated" date field that editors manually set on content updates.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    "list_definition_patterns": {
        "finding_pattern": "list_definition_patterns",
        "pillar_key": "aeo_content",
        "title": "Add Structured Lists and Tables in Webflow",
        "steps_markdown": """1. Use Webflow's **List** element for any enumerated content (features, steps, benefits).
2. For ordered processes, set the list type to **Ordered List** in Settings.
3. For comparison data, use a **Table** element or embed a custom HTML table.
4. For definition-style content (term + explanation), use a **Description List**:
   - Add via Embed element: `<dl><dt>Term</dt><dd>Definition</dd></dl>`
5. Inside **Rich Text** elements, use the built-in list formatting tools.

**Why**: Structured content (lists, tables) is 2x more likely to be extracted by AI for featured snippets.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "conclusion_first": {
        "finding_pattern": "conclusion_first",
        "pillar_key": "aeo_content",
        "title": "Use Conclusion-First Writing in Webflow",
        "steps_markdown": """1. Review each content section on your page.
2. Ensure sections start with the **key takeaway or action** — not background context.
3. Pattern to follow:
   - **First sentence**: The answer or conclusion
   - **Following sentences**: Supporting evidence, details, examples
4. Avoid starting sections with: "This...", "In order to...", "As mentioned...", "It is important to note..."
5. Instead, start with active verbs: "Use...", "Add...", "Configure...", "Choose..."

**This is called the "inverted pyramid" style** — it helps AI engines extract your key points without reading the full section.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes per page",
    },

    # ─── CSS Quality (css_js_auditor.py) ───

    "framework_detection": {
        "finding_pattern": "framework_detection",
        "pillar_key": "css_quality",
        "title": "Adopt a CSS Naming Framework in Webflow",
        "steps_markdown": """1. Choose a Webflow-compatible naming framework:
   - **Client-First** (most popular): `section_[name]`, `[name]_component`, `padding-[size]`
   - **Lumos**: Utility-focused with semantic classes
   - **MAST**: Modular approach
2. In the Webflow Designer, rename your classes to follow the chosen convention.
3. Use the **Style Manager** panel to audit and clean up class names.
4. Create utility classes for spacing, colors, and typography.
5. Document your naming convention for team consistency.

**Tip**: Client-First has the most community support and templates. Start there if unsure.""",
        "difficulty": "medium",
        "estimated_time": "30 minutes",
    },

    "naming_consistency": {
        "finding_pattern": "naming_consistency",
        "pillar_key": "css_quality",
        "title": "Fix CSS Naming Inconsistencies in Webflow",
        "steps_markdown": """1. Open the **Style Manager** panel in Webflow.
2. Review all class names for consistency:
   - Pick one separator: hyphens (`hero-section`) or underscores (`hero_section`)
   - Use consistent prefixes for layout classes
3. Rename inconsistent classes by selecting an element, clicking the class name, and editing.
4. Use Webflow's **Clean Up** feature to find unused styles.
5. Avoid Webflow's auto-generated combo classes when possible — they create clutter.""",
        "difficulty": "easy",
        "estimated_time": "15 minutes",
    },

    "inline_styles": {
        "finding_pattern": "inline_styles",
        "pillar_key": "css_quality",
        "title": "Remove Inline Styles in Webflow",
        "steps_markdown": """1. Inline styles are created when you style elements directly without a class.
2. Select elements that have styles but no class name (shown as "No Class" in the Style panel).
3. Create a **reusable class** and apply your styles to the class instead.
4. For dynamic styles (e.g., CMS-driven colors), use **Webflow's native conditional visibility** or minimal custom CSS via an Embed.
5. Check for inline styles added via **Custom Code** embeds — move these to a `<style>` block in **Project Settings > Custom Code > Head Code**.

**Goal**: Keep inline styles under 30 across the entire page.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "external_stylesheets": {
        "finding_pattern": "external_stylesheets",
        "pillar_key": "css_quality",
        "title": "Reduce External Stylesheets in Webflow",
        "steps_markdown": """1. Check **Project Settings > Custom Code > Head Code** for external CSS `<link>` tags.
2. Common offenders: Google Fonts (multiple files), icon libraries, third-party widget CSS.
3. For **Google Fonts**: Use Webflow's built-in font loader instead of manual `<link>` tags. Go to **Project Settings > Fonts**.
4. For **icon libraries**: Switch to inline SVGs or Webflow's built-in icon component.
5. Consolidate remaining external CSS into a single file if possible.

**Target**: No more than 5 external stylesheets total.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes",
    },

    "render_blocking": {
        "finding_pattern": "render_blocking",
        "pillar_key": "css_quality",
        "title": "Fix Render-Blocking Scripts in Webflow",
        "steps_markdown": """1. Go to **Project Settings > Custom Code > Head Code**.
2. Find any `<script>` tags and add `defer` or `async`:
   - `defer`: Script runs after HTML is parsed (best for most scripts)
   - `async`: Script runs as soon as it downloads (best for analytics)
3. Move non-critical scripts from **Head Code** to **Footer Code** (before `</body>`).
4. For third-party embeds (chat widgets, analytics), check if they offer an async loading option.
5. Webflow's own scripts are already optimized — focus on scripts you've added manually.

**Example**: Change `<script src="analytics.js"></script>` to `<script src="analytics.js" defer></script>`""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    # ─── JS Bloat (css_js_auditor.py) ───

    "webflow_js_bloat": {
        "finding_pattern": "webflow_js_bloat",
        "pillar_key": "js_bloat",
        "title": "Reduce Webflow JavaScript Bloat",
        "steps_markdown": """1. **Interactions (IX2)**: Review interactions in the **Interactions** panel. Remove unused ones.
   - Prefer CSS-only animations (transitions, hover states) over JavaScript interactions where possible.
2. **Lottie animations**: Each Lottie adds ~50-150KB. Consider:
   - Replacing simple Lotties with CSS animations
   - Lazy-loading Lotties below the fold
3. **Webflow User Accounts**: Loads significant JS even if unused. If not needed, remove from Project Settings.
4. **eCommerce**: Similar to User Accounts — only enable if actively used.
5. **Rive animations**: Heavy runtime. Use sparingly and lazy-load.

**Audit tip**: Open DevTools > Network > JS tab to see the actual sizes of loaded scripts.""",
        "difficulty": "medium",
        "estimated_time": "20 minutes",
    },

    "third_party_scripts": {
        "finding_pattern": "third_party_scripts",
        "pillar_key": "js_bloat",
        "title": "Audit Third-Party Scripts in Webflow",
        "steps_markdown": """1. Go to **Project Settings > Custom Code** and review all script tags in both Head and Footer code.
2. Also check individual **Page Settings > Custom Code** for page-specific scripts.
3. For each third-party script, ask:
   - Is this still needed? Remove if not.
   - Can it load async/defer? Add the attribute.
   - Is there a lighter alternative? (e.g., Plausible instead of GA4)
4. Common heavy offenders: chat widgets, heatmap tools, multiple analytics, social embeds.
5. Use **Google Tag Manager** to consolidate scripts and control loading.

**Target**: Keep third-party scripts under 8 total.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes",
    },

    "total_scripts": {
        "finding_pattern": "total_scripts",
        "pillar_key": "js_bloat",
        "title": "Reduce Total Script Count in Webflow",
        "steps_markdown": """1. Count all `<script>` tags: check **Project Settings > Custom Code**, **Page Settings > Custom Code**, and **Embed** elements.
2. Consolidate inline scripts into a single `<script>` block in Footer Code.
3. Remove duplicate scripts (e.g., jQuery loaded twice).
4. Replace heavy libraries with lightweight alternatives:
   - jQuery → native JavaScript
   - Slick Slider → Webflow's native slider
   - Moment.js → native Date APIs
5. For scripts needed only on specific pages, move them from Project-level to Page-level custom code.

**Target**: Under 15 total script tags per page.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes",
    },

    # ─── Accessibility (accessibility_auditor.py) ───

    "axe_scan": {
        "finding_pattern": "axe_scan",
        "pillar_key": "accessibility",
        "title": "Fix WCAG Accessibility Violations in Webflow",
        "steps_markdown": """1. The most common WCAG violations in Webflow:
   - **Color contrast**: Select text elements → adjust color in Style panel to meet 4.5:1 ratio for normal text, 3:1 for large text. Use [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/).
   - **Missing alt text**: Select images → add alt text in Settings panel.
   - **Missing form labels**: Ensure every input has a visible or aria-label.
   - **Empty links/buttons**: Add text content or aria-label to interactive elements.
2. For ARIA issues, add custom attributes via **Settings > Custom Attributes**.
3. Test with keyboard navigation: every interactive element should be reachable with Tab and activatable with Enter/Space.
4. Use Webflow's **Audit** panel for a quick accessibility overview.""",
        "difficulty": "medium",
        "estimated_time": "30 minutes",
    },

    "touch_targets": {
        "finding_pattern": "touch_targets",
        "pillar_key": "accessibility",
        "title": "Fix Touch Target Sizes in Webflow",
        "steps_markdown": """1. Select buttons, links, and other interactive elements.
2. In the **Style** panel, ensure minimum dimensions:
   - Width: at least 44px
   - Height: at least 44px
   - Or add padding to achieve 44x44px touch area
3. For inline text links, add vertical padding:
   ```css
   padding-top: 8px;
   padding-bottom: 8px;
   ```
4. For icon buttons, ensure the clickable area (not just the icon) meets 44x44px.
5. Check on **mobile breakpoint** — touch targets matter most on mobile devices.

**WCAG 2.5.5**: Touch targets must be at least 44x44 CSS pixels.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "focus_styles": {
        "finding_pattern": "focus_styles",
        "pillar_key": "accessibility",
        "title": "Add Focus Styles in Webflow",
        "steps_markdown": """1. Webflow removes default focus outlines by default. You need to add them back.
2. Go to **Project Settings > Custom Code > Head Code** and add:
   ```html
   <style>
   *:focus-visible {
     outline: 2px solid #2820FF;
     outline-offset: 2px;
     border-radius: 4px;
   }
   </style>
   ```
3. Or style focus states per element: select the element, add a **Focused** state in the Style panel.
4. Test: press **Tab** through your page. Every interactive element should show a visible focus indicator.
5. Never use `outline: none` without providing an alternative focus style.

**Important**: Focus styles are required for keyboard-only users and WCAG 2.4.7 compliance.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    "keyboard_traps": {
        "finding_pattern": "keyboard_traps",
        "pillar_key": "accessibility",
        "title": "Fix Keyboard Traps in Webflow",
        "steps_markdown": """1. A keyboard trap occurs when Tab key focus gets stuck in a loop within a component.
2. Common Webflow culprits: modals, sliders, dropdown menus, lightboxes.
3. For **modals/popups**:
   - Ensure the close button is keyboard-accessible
   - Add `Escape` key handler via custom code to close the modal
   - Return focus to the trigger element on close
4. For **sliders**: Ensure Tab moves through slides then continues past the slider.
5. Test: Tab through your entire page. If focus gets stuck anywhere, fix that component.
6. For complex components, add `tabindex="-1"` to skip non-interactive wrappers.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes",
    },

    # ─── RAG Readiness (rag_readiness_auditor.py) ───

    "context_independence": {
        "finding_pattern": "context_independence",
        "pillar_key": "rag_readiness",
        "title": "Make Content Sections Context-Independent in Webflow",
        "steps_markdown": """1. Review each section's opening sentence in your content.
2. Each section should make sense **when read in isolation** — AI systems extract individual chunks.
3. Replace context-dependent openers:
   - "This feature..." → "The [Feature Name] feature..."
   - "As mentioned above..." → Restate the relevant point
   - "These benefits..." → "The key benefits of [Topic]..."
4. Include the subject noun in every section's first sentence.
5. For CMS content, add this guideline to your editorial style guide.

**Why**: RAG systems chunk content by headings. Each chunk must stand alone without requiring the reader to have seen previous sections.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes per page",
    },

    "content_noise_ratio": {
        "finding_pattern": "content_noise_ratio",
        "pillar_key": "rag_readiness",
        "title": "Improve Content-to-Noise Ratio in Webflow",
        "steps_markdown": """1. Open your page in the Designer and identify boilerplate elements that repeat across pages:
   - Navigation, footer, sidebar ads, cookie banners, newsletter popups
2. These elements are "noise" for AI extraction. While you can't remove them, you can:
   - Use **semantic tags** (nav, header, footer, aside) so AI can identify and skip them
   - Keep your main content in a **`<main>`** tag
3. Reduce promotional/decorative content within the main content area.
4. Ensure actual content (article text, product info, service descriptions) makes up **>60%** of the page.
5. Move supplementary content into separate pages rather than cluttering the main page.

**Goal**: Content signal-to-noise ratio above 60%.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes",
    },

    "heading_content_pairing": {
        "finding_pattern": "heading_content_pairing",
        "pillar_key": "rag_readiness",
        "title": "Fix Orphan Headings in Webflow",
        "steps_markdown": """1. Open the **Navigator** panel and review your heading elements.
2. Every heading (H2, H3, H4) should be followed by at least one paragraph with **5+ words** of content.
3. If a heading has no content after it (or only an image/button):
   - Add a descriptive paragraph explaining the section
   - Or merge the heading into the previous or next section
4. For sections with only a heading and CTA button, add a 1-2 sentence description.
5. Avoid using headings purely for visual styling — use a styled div/span instead.

**Why**: AI systems pair headings with following content for context. An orphan heading wastes a chunking boundary.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "structured_content": {
        "finding_pattern": "structured_content",
        "pillar_key": "rag_readiness",
        "title": "Add Structured Content Elements in Webflow",
        "steps_markdown": """1. Use **lists** for enumerations: select content and use Webflow's List element or Rich Text list formatting.
2. Use **tables** for comparison/data: add a Table element or HTML Embed with `<table>`.
3. For every table, ensure:
   - Headers use `<th>` elements (Webflow's Table element does this automatically)
   - Add a caption or preceding heading explaining what the table shows
4. For every list, add context before it: "The key features include:" followed by the list.
5. Avoid using line breaks or styled divs to simulate lists — use actual `<ul>/<ol>` elements.

**Why**: Structured content is 2x easier for AI to extract and cite accurately.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "internal_link_context": {
        "finding_pattern": "internal_link_context",
        "pillar_key": "rag_readiness",
        "title": "Fix Vague Link Text for RAG Readiness in Webflow",
        "steps_markdown": """1. Find links with generic text: "click here", "read more", "learn more", "link".
2. Replace with descriptive anchor text that indicates the destination:
   - "click here" → "view our pricing plans"
   - "read more" → "read the full case study on [Topic]"
   - "learn more" → "explore our enterprise features"
3. In Webflow, select the link element and edit the text directly on canvas.
4. For CMS-bound links, use a "Link Text" field in your Collection.
5. The link text should make sense **out of context** — someone should understand where it leads without reading surrounding text.

**Why**: AI systems use anchor text to understand page relationships and topic relevance.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    # ─── Agentic Protocols (agentic_protocol_auditor.py) ───

    "llms_txt": {
        "finding_pattern": "llms_txt",
        "pillar_key": "agentic_protocols",
        "title": "Add llms.txt File in Webflow",
        "steps_markdown": """1. Create a `llms.txt` file with your site's key information for AI agents:
   ```
   # Your Company Name
   > Brief one-line description of what your company does.

   ## About
   2-3 sentences about your company.

   ## Key Pages
   - [Homepage](https://yoursite.com): Main landing page
   - [Pricing](https://yoursite.com/pricing): Plans and pricing
   - [Docs](https://yoursite.com/docs): Documentation

   ## Contact
   Email: hello@yoursite.com
   ```
2. Host the file: In Webflow, create a new page with slug `llms-txt`.
3. Add a **Custom Code Embed** with the content as plain text, or host the file externally and redirect.
4. **Alternative**: Host `llms.txt` as a static asset using Webflow's asset CDN and add a redirect rule.
5. Optionally create `llms-full.txt` with more detailed content.

**Note**: This is an emerging standard. Having it signals AI-readiness to crawler agents.""",
        "difficulty": "medium",
        "estimated_time": "15 minutes",
    },

    "robots_ai_access": {
        "finding_pattern": "robots_ai_access",
        "pillar_key": "agentic_protocols",
        "title": "Configure robots.txt for AI Crawlers in Webflow",
        "steps_markdown": """1. Go to **Project Settings > SEO > robots.txt** (under the SEO tab).
2. Webflow lets you customize the robots.txt content directly.
3. Add explicit allow rules for AI crawlers:
   ```
   User-agent: GPTBot
   Allow: /

   User-agent: ClaudeBot
   Allow: /

   User-agent: PerplexityBot
   Allow: /

   User-agent: GoogleOther
   Allow: /
   ```
4. If you want to **block** specific AI crawlers, use `Disallow: /` instead.
5. The key is being **explicit** — having no mention of AI crawlers leaves your intent ambiguous.

**Important**: Ensure your sitemap URL is also listed in robots.txt: `Sitemap: https://yoursite.com/sitemap.xml`""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    "sitemap_quality": {
        "finding_pattern": "sitemap_quality",
        "pillar_key": "agentic_protocols",
        "title": "Improve Sitemap Quality in Webflow",
        "steps_markdown": """1. Webflow **auto-generates** a sitemap.xml. Check it at `https://yoursite.com/sitemap.xml`.
2. To configure: Go to **Project Settings > SEO**.
3. Ensure all important pages are included:
   - Check each page's Settings → make sure **"Exclude from sitemap"** is NOT checked for important pages.
   - For CMS items, ensure the Collection is not excluded from sitemap.
4. For `<lastmod>` dates: Webflow updates these when you publish. Publish regularly to keep dates current.
5. Verify sitemap in **Google Search Console** under Sitemaps.

**Common issue**: Utility pages (style guide, 404, password) should be excluded. Important landing pages should never be excluded.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    "api_discoverability": {
        "finding_pattern": "api_discoverability",
        "pillar_key": "agentic_protocols",
        "title": "Add API/Agent Discovery Endpoints in Webflow",
        "steps_markdown": """1. If your site offers an API or machine-readable data, make it discoverable.
2. Create a `.well-known` page or use redirects for:
   - `/.well-known/ai-plugin.json` (OpenAI plugin manifest)
   - `/openapi.json` or `/swagger.json` (API documentation)
3. In Webflow, set up **301 redirects** in **Project Settings > Hosting > 301 Redirects** to point to your API documentation.
4. Add a `<link>` tag in **Head Code**:
   ```html
   <link rel="api" href="https://api.yoursite.com/openapi.json" type="application/json">
   ```
5. For most Webflow marketing sites, this check is informational — focus on other agentic protocol items first.

**Note**: This is most relevant for SaaS products with public APIs.""",
        "difficulty": "advanced",
        "estimated_time": "30 minutes",
    },

    "meta_agent_hints": {
        "finding_pattern": "meta_agent_hints",
        "pillar_key": "agentic_protocols",
        "title": "Add Machine-Readable Meta Hints in Webflow",
        "steps_markdown": """1. Add meta tags in **Project Settings > Custom Code > Head Code** to signal AI-readiness:
   ```html
   <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
   ```
2. Add Schema.org **Actions** to your JSON-LD for interactive elements:
   ```json
   {
     "@type": "WebSite",
     "potentialAction": {
       "@type": "SearchAction",
       "target": "https://yoursite.com/search?q={search_term}",
       "query-input": "required name=search_term"
     }
   }
   ```
3. For pages with downloadable content, add:
   ```html
   <link rel="alternate" type="application/json" href="/api/page-data.json">
   ```
4. Use semantic HTML (covered in Semantic HTML pillar) so machine parsers can extract content reliably.""",
        "difficulty": "medium",
        "estimated_time": "10 minutes",
    },

    # ─── Data Integrity (data_integrity_auditor.py) ───

    "price_conflicts": {
        "finding_pattern": "price_conflicts",
        "pillar_key": "data_integrity",
        "title": "Fix Price Data Conflicts in Webflow",
        "steps_markdown": """1. Check all price displays on your page for consistency.
2. If using **Webflow eCommerce**: prices are managed centrally. Ensure the same product doesn't show different prices in different sections.
3. If displaying prices manually: search for all price mentions in your content and ensure they match.
4. Verify **JSON-LD schema** prices match visible prices:
   - Check your Product/Offer schema `price` and `priceCurrency` fields
   - These must exactly match what's displayed on the page
5. Use a single currency throughout the page. If showing multiple currencies, clearly label each.

**Why**: AI systems cross-reference prices between schema and visible text. Conflicts reduce trust signals.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "contact_conflicts": {
        "finding_pattern": "contact_conflicts",
        "pillar_key": "data_integrity",
        "title": "Fix Contact Information Conflicts in Webflow",
        "steps_markdown": """1. Audit all phone numbers and email addresses across your site.
2. Use Webflow **Symbols** for contact info blocks — edit once, update everywhere.
3. Check for conflicts between:
   - Header/footer contact info vs. Contact page
   - Schema.org data vs. visible text
   - Different formatting (e.g., "+1 (555) 123-4567" vs "555-123-4567")
4. In your Organization JSON-LD, ensure `telephone` and `email` match the visible values.
5. For multi-location businesses, ensure each location's contact info is in its own LocalBusiness schema.

**Tip**: Create a CMS Collection for locations/contacts and bind all display elements to it for single-source-of-truth consistency.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "brand_consistency": {
        "finding_pattern": "brand_consistency",
        "pillar_key": "data_integrity",
        "title": "Fix Brand Name Inconsistencies in Webflow",
        "steps_markdown": """1. Search your site for all variations of your brand name.
2. Common inconsistencies: "My Company" vs "MyCompany" vs "My Company, Inc." vs "my company".
3. Choose **one canonical brand name** and use it consistently in:
   - Organization JSON-LD `name` field
   - `og:site_name` meta tag (Page Settings > Open Graph)
   - Page titles
   - Footer copyright text
   - Header logo alt text
4. In Webflow, use **Find & Replace** (Cmd+Shift+H) to locate text variations.
5. For CMS content, create a Global variable or reference field for the brand name.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "schema_conflicts": {
        "finding_pattern": "schema_conflicts",
        "pillar_key": "data_integrity",
        "title": "Fix Duplicate Schema Entities in Webflow",
        "steps_markdown": """1. Check your page source for duplicate JSON-LD blocks of the same type.
2. Common cause: Organization schema in both **Project Settings > Footer Code** and individual **Page Settings**.
3. Rules for singleton entities:
   - Only **one Organization** schema per page
   - Only **one WebSite** schema per page
   - Multiple Article/Product schemas are OK (e.g., product listing pages)
4. To fix: Remove the duplicate from either the page-level or project-level custom code.
5. Combine properties into a single, comprehensive schema block.

**Tip**: Put Organization and WebSite schema in Project-level Footer Code (site-wide), and page-specific schema (Article, Product) in individual Page Settings.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    "date_conflicts": {
        "finding_pattern": "date_conflicts",
        "pillar_key": "data_integrity",
        "title": "Fix Date Conflicts in Webflow",
        "steps_markdown": """1. Check your JSON-LD for `datePublished` and `dateModified` fields.
2. Rules:
   - `datePublished` must be before or equal to `dateModified`
   - Dates must not be in the future
   - Use ISO 8601 format: `YYYY-MM-DD` or `YYYY-MM-DDTHH:mm:ssZ`
3. For **CMS blog posts**: bind these schema fields to actual CMS date fields.
4. Common mistake: hardcoding dates in JSON-LD and forgetting to update `dateModified` when content changes.
5. In Webflow CMS, use a "Last Updated" date field and bind it to the schema's `dateModified`.

**Automation tip**: Set up a Webflow workflow or reminder to update `dateModified` whenever you republish content changes.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    # ─── Internal Linking (internal_linking_auditor.py) ───

    "outgoing_internal_links": {
        "finding_pattern": "outgoing_internal_links",
        "pillar_key": "internal_linking",
        "title": "Optimize Internal Link Count in Webflow",
        "steps_markdown": """1. Check how many internal links are on your page.
2. **Too few** (under 3): You have an isolated page. Add contextual links:
   - Link to related services/products
   - Add a "Related Articles" section for blog posts
   - Include breadcrumb navigation
   - Add footer links to key pages
3. **Too many** (over 150): You may be link-stuffing. Reduce by:
   - Removing redundant navigation links
   - Consolidating footer mega-menus
   - Using pagination instead of listing all items
4. **Ideal range**: 3-150 internal links per page, with most pages having 10-50.
5. In Webflow, use **Symbols** for navigation components to maintain consistent linking across pages.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "anchor_text_quality": {
        "finding_pattern": "anchor_text_quality",
        "pillar_key": "internal_linking",
        "title": "Improve Internal Link Anchor Text in Webflow",
        "steps_markdown": """1. Review your internal links for vague anchor text:
   - "Click here", "Read more", "Learn more", "Link" — these are bad for SEO and AI.
2. Replace with descriptive text that indicates the target page's topic:
   - "Read more" → "Read our complete guide to Webflow SEO"
   - "Click here" → "View our pricing plans"
3. Avoid using the **same anchor text** for links to **different pages** — this confuses search engines.
4. In Webflow CMS, create a "Link Text" plain text field for dynamic link labels.
5. For navigation links, the menu text already serves as anchor text — make it descriptive.

**Ideal anchor text**: 2-5 words that describe the destination page's primary topic.""",
        "difficulty": "easy",
        "estimated_time": "10 minutes",
    },

    "self_referencing_links": {
        "finding_pattern": "self_referencing_links",
        "pillar_key": "internal_linking",
        "title": "Remove Self-Referencing Links in Webflow",
        "steps_markdown": """1. A self-referencing link points to the same page it's on.
2. One is acceptable (e.g., logo linking to homepage while on homepage). More than one is wasteful.
3. Common causes in Webflow:
   - Navigation highlighting the current page with an active link
   - Breadcrumb showing the current page as a link
   - CMS templates where the page links to itself
4. Fix: Use Webflow's **Current** state for nav items — style the current page differently without making it a link.
5. For breadcrumbs: make the last item plain text, not a link.
6. For CMS: add conditional visibility to hide self-links (e.g., compare the current page URL with the link URL).""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },

    "nofollow_internal_links": {
        "finding_pattern": "nofollow_internal_links",
        "pillar_key": "internal_linking",
        "title": "Remove Nofollow from Internal Links in Webflow",
        "steps_markdown": """1. Internal links should almost **never** have `rel="nofollow"`.
2. `nofollow` tells search engines not to pass link equity — this wastes your own site's authority.
3. In Webflow, select the link element → **Settings** panel → check if `rel` attribute is set.
4. Remove `nofollow` from internal links. Keep `nofollow` only on:
   - External links to untrusted/user-generated content
   - Sponsored/affiliate links (use `rel="sponsored"`)
5. Check **Custom Attributes** on link elements for any `rel="nofollow"` entries.
6. Also check global scripts that might add nofollow to links programmatically.

**Rule**: All internal links should pass full link equity to strengthen your site's authority distribution.""",
        "difficulty": "easy",
        "estimated_time": "5 minutes",
    },
}


def get_fix(finding_pattern: str) -> Dict[str, str] | None:
    """Look up a fix by finding pattern (check name)."""
    return FIXES.get(finding_pattern)


def get_all_fixes() -> List[Dict[str, str]]:
    """Return all fixes as a list."""
    return list(FIXES.values())


def get_fixes_for_pillar(pillar_key: str) -> List[Dict[str, str]]:
    """Return all fixes for a given pillar."""
    return [f for f in FIXES.values() if f["pillar_key"] == pillar_key]


def match_fixes_to_findings(report: dict) -> Dict[str, Dict[str, str]]:
    """Given a report, return a dict of finding_pattern -> fix for all matched findings."""
    matched: Dict[str, Dict[str, str]] = {}
    categories = report.get("categories", {})
    for pillar_key, pillar_data in categories.items():
        checks = pillar_data.get("checks", {})
        for check_name, check_data in checks.items():
            if not isinstance(check_data, dict):
                continue
            if check_data.get("findings") and check_name in FIXES:
                matched[check_name] = FIXES[check_name]
    return matched
