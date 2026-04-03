# Sprint 6: Frontend UI/UX Redesign

## Overview

Complete UI/UX overhaul of the WAIO Webflow Auditor. Three audit types (Single Page, Full Site, Competitive) with a tab selector. Free report gets Sitebulb-style hint cards with blurred premium sections. Premium gets a separate enterprise dashboard at `/dashboard/:auditId` with left sidebar navigation. All styled with WAIO brand DNA (dark-first, indigo accent, glow effects).

**Critical rule: Do NOT break existing backend API contracts.** The frontend consumes the same JSON response from `/api/audit` and `/api/premium-audit`. All changes are frontend-only unless noted.

**Design direction:** Dark-first enterprise aesthetic. NOT generic AI slop. The brand uses #0D121C surfaces, #2820FF vivid indigo accent, gaussian blur glow effects, subtle grid patterns, and rounded corners at 8/12/16px. See `.claude/rules/frontend-research.md` for the full design system spec and evidence-based patterns.

**Font choice:** Use "Plus Jakarta Sans" (Google Fonts) for headings/UI and "Inter" for body text. These pair well with the dark enterprise aesthetic and are available via Google Fonts CDN.

---

## Sprint 6A: TailwindCSS 4 Theme + Design System Foundation

### What to build
Replace the current Tailwind config with TailwindCSS 4's CSS-first `@theme` directive. All WAIO brand tokens defined in one CSS file.

### Files to create/modify
- `frontend/src/styles/theme.css` — New file. All `@theme` tokens:
  ```css
  @import "tailwindcss";
  @custom-variant dark (&:is(.dark *));

  @theme {
    --color-surface: #0D121C;
    --color-surface-raised: #151B28;
    --color-surface-overlay: #1A2235;
    --color-accent: #2820FF;
    --color-accent-hover: #3D35FF;
    --color-accent-muted: #2820FF20;
    --color-secondary-blue: #0194FE;
    --color-secondary-cyan: #30DAFF;
    --color-success: #47CD89;
    --color-success-glow: #E3FBDE;
    --color-warning: #F59E0B;
    --color-error: #EF4444;
    --color-critical: #DC2626;
    --color-text: #F1F5F9;
    --color-text-secondary: #94A3B8;
    --color-text-muted: #64748B;
    --color-border: #1E293B;
    --color-border-subtle: #1E293B80;
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 24px;
    --shadow-glow-accent: 0 0 20px 0 #2820FF40, 0 0 60px 0 #2820FF20;
    --shadow-glow-blue: 0 0 20px 0 #0194FE30, 0 0 50px 0 #0194FE15;
    --shadow-glow-success: 0 0 15px 0 #47CD8930;
    --shadow-card: 0 1px 3px 0 #0D121C80, 0 4px 16px 0 #0D121C40;
    --shadow-card-hover: 0 4px 12px 0 #0D121C90, 0 8px 24px 0 #0D121C60;
    --font-heading: "Plus Jakarta Sans", ui-sans-serif, system-ui, sans-serif;
    --font-body: "Inter", ui-sans-serif, system-ui, sans-serif;
    --font-mono: "JetBrains Mono", ui-monospace, monospace;
  }
  ```
- Add custom utilities for glow effects and grid pattern backgrounds
- Update `frontend/src/main.tsx` or `index.css` to import `theme.css`
- Remove old `tailwind.config.js` / `tailwind.config.ts` if present (v4 uses CSS-first config)
- Add Google Fonts link for Plus Jakarta Sans + Inter to `index.html`

### Acceptance criteria
- All existing components render correctly with new theme tokens
- `bg-surface`, `text-accent`, `border-border`, `rounded-md`, `shadow-card` etc. all work
- Dark-first by default (no `.dark` class needed for dark mode)
- No visual regressions on existing free audit report

---

## Sprint 6B: React Router Restructure + Layout Routes

### What to build
Add proper routing with separate paths for landing, free report, and premium dashboard. The premium dashboard uses a layout route with sidebar.

### Route structure
```
/                           → LandingPage (audit form)
/audit/:auditId             → FreeReport (public, shareable)
/dashboard/:auditId         → DashboardLayout > DashboardOverview
/dashboard/:auditId/links   → DashboardLayout > DashboardLinks
/dashboard/:auditId/graph   → DashboardLayout > DashboardGraph
/dashboard/:auditId/content → DashboardLayout > DashboardContent
/dashboard/:auditId/export  → DashboardLayout > DashboardExport
```

### Files to create/modify
- `frontend/src/router.tsx` — New file. Route definitions with React.lazy for dashboard pages
- `frontend/src/layouts/DashboardLayout.tsx` — New file. Sidebar + `<Outlet />` wrapper
- `frontend/src/layouts/PublicLayout.tsx` — New file. Simple layout for landing + free report
- `frontend/src/App.tsx` — Replace current single-page setup with `<RouterProvider />`
- Install `react-router` v7.x (single package, no separate `-dom` needed in v7)

### Key patterns
- Dashboard pages use `React.lazy()` for code splitting — the premium bundle doesn't load for free users
- `DashboardLayout` renders the sidebar + `<Outlet />` so sidebar persists across sub-page navigation
- After a free audit completes, navigate to `/audit/:auditId` with the report data
- After a premium audit completes, navigate to `/dashboard/:auditId`
- Store audit results in a lightweight Zustand store or pass via route loader

### Acceptance criteria
- Landing page at `/` shows the audit form
- Free audit results display at `/audit/:auditId`
- Dashboard shell renders at `/dashboard/:auditId` (can be placeholder content for now)
- Browser back/forward works correctly
- Direct URL access works (e.g., bookmarking `/audit/abc123`)

---

## Sprint 6C: Audit Form Redesign with Tab Selector

### What to build
Replace the current audit form with a tabbed interface: **Single Page** (free), **Full Site** (premium), **Competitive** (premium). Each tab shows a different form configuration.

### Component architecture
- `AuditForm.tsx` — Complete rewrite. Uses Radix `Tabs` for the three audit types
- `SinglePageForm.tsx` — URL input + "Analyze" button. Minimal, fast.
- `FullSiteForm.tsx` — URL input + scope selector (domain/subdomain/subfolder) + page limit display + competitor URL inputs (bundled competitive). Premium badge on tab.
- `CompetitiveForm.tsx` — Hidden/merged into FullSiteForm since competitive is bundled

### Tab design
- **Single Page tab**: No icon, active by default
- **Full Site tab**: Crown or sparkle icon + "Pro" badge chip (indigo). If user is not premium, clicking shows a tooltip: "Available with Premium Audit — $4,500"
- Use `@radix-ui/react-tabs` v1.1.x for accessibility (WAI-ARIA compliant, keyboard nav)
- Active tab: `bg-surface-raised` with `shadow-glow-accent` subtle glow bottom border
- Inactive tabs: `text-text-secondary` with hover `text-text`

### Form styling
- URL input: Large, prominent, with `bg-surface-raised` background, `border-border` border, `focus:ring-accent` focus ring, placeholder "Enter your website URL"
- Auto-prepend `https://` if missing
- Submit button: `bg-accent` with `hover:bg-accent-hover`, text "Analyze" for single page, "Start Full Audit" for full site
- The submit button should have the indigo glow effect on hover (`shadow-glow-accent`)

### Acceptance criteria
- Three tabs render with correct styling
- Single Page tab works identically to current audit (no regressions)
- Full Site tab shows expanded form with scope + competitor inputs
- Premium tabs show visual indicator (Pro badge)
- Form submits correctly to existing API endpoints
- URL validation works (auto-prepend https, handle www variants)

---

## Sprint 6D: Free Report Redesign — Sitebulb-Style Hint Cards

### What to build
Restructure the free audit report at `/audit/:auditId` with: health score gauge at top, pillar score cards grid, and Sitebulb-style hint cards for findings. Add blurred premium sections at the bottom.

### Component architecture (all new files in `frontend/src/components/report/`)
- `HealthScoreGauge.tsx` — Circular gauge (0-100) with traffic-light coloring. Green ≥80, Yellow 50-79, Red <50. Animated on mount with Motion.
- `PillarScoreCard.tsx` — Card with pillar icon, name, score, and mini progress bar. Click navigates to filtered findings for that pillar.
- `PillarScoreGrid.tsx` — Responsive grid of PillarScoreCards. 5 columns on desktop, 3 on tablet, 2 on mobile.
- `FindingCard.tsx` — The Sitebulb-style hint card:
  - Left border color-coded by severity (Critical=#DC2626, High=#EF4444, Medium=#F59E0B, Low=#0194FE)
  - Severity badge chip (colored background + white text)
  - Issue title (semibold)
  - Two-sentence plain-English description
  - Element location (from element pinpointing — show CSS selector or HTML snippet)
  - "How to Fix in Webflow" button (only on premium, blurred on free)
  - Hover reveals action row: View Details, Copy Finding
- `FindingsPanel.tsx` — Container with:
  - Filter toolbar: severity toggle chips (Critical/High/Medium/Low), pillar dropdown, search input
  - Sort: by severity (default), by pillar, alphabetical
  - Group toggle: "By Importance" | "By Category"
  - `Object.groupBy()` for grouping, `useMemo` for filtered/sorted results
- `PositiveFindingsSection.tsx` — Collapsible section showing what's done right (green left border, checkmark icon)
- `PremiumPreviewSection.tsx` — Blurred premium sections at the bottom of free report:
  - Executive Summary (blurred, shows "Strategic Assessment" header visible)
  - Link Graph preview (blurred, shows node count visible)
  - WDF*IDF Analysis (blurred, shows "Content Gap Analysis" header visible)
  - Webflow Fix Instructions (blurred, shows count visible)
  - Each section: `filter: blur(6px)`, `pointer-events: none`, gradient fade overlay, contextual CTA button
  - CTA copy: "Unlock all {count} Webflow fix instructions" / "View full link architecture" / etc.

### Severity color mapping
```
critical: { bg: '#DC262615', border: '#DC2626', text: '#FCA5A5', badge: '#DC2626' }
high:     { bg: '#EF444415', border: '#EF4444', text: '#FCA5A5', badge: '#EF4444' }
medium:   { bg: '#F59E0B15', border: '#F59E0B', text: '#FDE68A', badge: '#F59E0B' }
low:      { bg: '#0194FE15', border: '#0194FE', text: '#93C5FD', badge: '#0194FE' }
positive: { bg: '#47CD8915', border: '#47CD89', text: '#BBF7D0', badge: '#47CD89' }
```

### Acceptance criteria
- Health score renders as animated circular gauge
- All 10 pillar scores display in responsive grid
- All findings render as hint cards with correct severity colors
- Filter/sort/group controls work
- Positive findings section works
- Blurred premium sections appear at bottom with contextual CTAs
- No regressions in audit data display
- Mobile responsive (cards stack, filters collapse to dropdown)

---

## Sprint 6E: Premium Dashboard — Sidebar + Overview

### What to build
The enterprise dashboard at `/dashboard/:auditId` with persistent left sidebar and overview page.

### Sidebar architecture (using shadcn/ui Sidebar pattern)
- Width: 256px expanded, 56px collapsed (icon-only)
- Toggle: hamburger button + Cmd/Ctrl+B keyboard shortcut
- 5 collapsible super-groups with category items:

```
📊 Overview (no group — top-level link)

🔧 Technical Health
  ├── Semantic HTML
  ├── CSS Quality
  ├── JS Performance
  └── Data Integrity

📝 Content & SEO
  ├── AEO Content
  ├── Structured Data
  └── RAG Readiness

🔗 Links & Architecture
  ├── Internal Linking
  ├── Link Graph (D3 visualization)
  └── Topic Clusters

♿ Accessibility & Protocols
  ├── Accessibility
  └── Agentic Protocols

📋 Reports & Export
  ├── Executive Summary
  ├── Webflow Fix Guide
  ├── Competitor Benchmark
  └── Export (PDF/Excel/MD)
```

- Active item: `bg-accent-muted` with `text-accent` and left border accent
- Hover: `bg-surface-overlay`
- Group headers: `text-text-muted` uppercase 11px with chevron toggle
- Bottom of sidebar: site URL being audited + audit date + health score mini badge

### Dashboard Overview page
- Top bar: Site URL + CMS detected badge + audit date + health score
- KPI row (4 cards, `col-span-3` each in 12-col grid):
  - Health Score (circular gauge, same as free report)
  - Pages Crawled (number + "of {total} discovered")
  - Critical Issues (number, red if >0)
  - Positive Findings (number, green)
- Score comparison chart: Bar chart or radar chart of all 10 pillar scores (use Recharts)
- Top 5 Critical Issues: List of the 5 highest-severity findings as compact FindingCards
- Competitor Benchmark (if available): Bar chart comparing your score vs competitors

### Files to create
- `frontend/src/components/dashboard/AppSidebar.tsx`
- `frontend/src/components/dashboard/SidebarNav.tsx`
- `frontend/src/components/dashboard/DashboardOverview.tsx`
- `frontend/src/components/dashboard/KpiCard.tsx`
- `frontend/src/components/dashboard/PillarRadarChart.tsx`
- `frontend/src/components/dashboard/CompetitorBenchmark.tsx`

### Dependencies to install
- `@radix-ui/react-collapsible` — for sidebar group collapse
- `recharts` — for charts (already may be available)
- `lucide-react` — for icons (already may be available)
- `zustand` v5.x — for cross-view audit state

### Acceptance criteria
- Sidebar renders with all category groups
- Sidebar collapses/expands with animation
- Overview page shows all KPI cards with real audit data
- Pillar score chart renders correctly
- Sidebar navigation links route to correct dashboard sub-pages
- Cmd/Ctrl+B toggles sidebar
- Mobile: sidebar becomes slide-out drawer automatically

---

## Sprint 6F: Link Graph Visualization (react-force-graph-2d)

### What to build
Interactive force-directed graph at `/dashboard/:auditId/graph` showing internal link architecture.

### Implementation
- Use `react-force-graph-2d` v1.29.x (Canvas-based, handles 2,000+ nodes)
- Nodes = pages (sized by inlink count, colored by topic cluster)
- Edges = internal links (opacity based on link weight)
- Controls: zoom, pan, drag, hover tooltip (URL, title, inlink count, outlink count, crawl depth)
- Cluster coloring: `d3.scaleOrdinal` with schemeTableau10
- Click node → navigate to that page's detail view in dashboard
- Legend: shows cluster colors + node size meaning
- Performance: `warmupTicks={100}`, `cooldownTicks={200}`, `d3AlphaDecay={0.02}`
- Level of Detail: show labels only when `globalScale > 2.5`

### Files to create
- `frontend/src/components/dashboard/LinkGraph.tsx`
- `frontend/src/components/dashboard/GraphControls.tsx` (zoom reset, cluster filter, layout toggle)
- `frontend/src/components/dashboard/GraphLegend.tsx`

### Dependencies
- `react-force-graph-2d` v1.29.x
- `d3` v7.x (for color scales and force configuration)

### Data source
- The link graph data comes from the premium audit API response under `link_analysis.graph_data`
- Expected format: `{ nodes: [{ id, url, title, cluster, inlinks, outlinks, depth }], links: [{ source, target }] }`
- If graph data is not available (API not configured), show a placeholder with sample data

### Acceptance criteria
- Graph renders with zoom, pan, drag
- Nodes colored by topic cluster
- Hover shows tooltip with page details
- Performance: smooth interaction with 500+ nodes
- Responsive: adapts to container size
- Fallback: shows placeholder message if no graph data

---

## Sprint 6G: Export System (PDF, Excel, Markdown)

### What to build
Export dropdown in the dashboard that generates PDF, XLSX, and Markdown reports.

### Implementation
- `ExportButton.tsx` — Dropdown button with three options
- PDF: Use `@react-pdf/renderer` v4.x for client-side generation
  - Cover page with WAIO branding, site URL, date, health score
  - Executive summary section
  - Pillar scores table
  - All findings grouped by severity
  - Webflow fix instructions for each finding
  - Charts rendered as base64 images (use `html2canvas` or chart library's `toBase64Image()`)
- Excel: Use `xlsx` (SheetJS) v0.20.x
  - Sheet 1: Summary (score, metadata, pillar scores)
  - Sheet 2: All Findings (severity, pillar, title, description, element, recommendation)
  - Sheet 3: Page Metrics (URL, status, crawl depth, word count, links)
  - Sheet 4: Competitor Comparison (if available)
- Markdown: Template string generation
  - Structured with headings, tables, and collapsible details blocks
  - Suitable for documentation or CMS import

### Files to create
- `frontend/src/components/export/ExportButton.tsx`
- `frontend/src/components/export/PdfReport.tsx` (react-pdf document component)
- `frontend/src/utils/generateExcel.ts`
- `frontend/src/utils/generateMarkdown.ts`

### Dependencies
- `@react-pdf/renderer` v4.x
- `xlsx` v0.20.x

### Acceptance criteria
- All three export formats generate correctly
- PDF includes branding, scores, and all findings
- Excel has proper column headers and formatting
- Markdown renders correctly in any markdown viewer
- Export works from both free report (limited) and premium dashboard (full)
- File downloads trigger with correct filename: `WAIO-Audit-{domain}-{date}.{ext}`

---

## Sprint 6H: Audit Streaming UX (SSE Progress)

### What to build
Real-time progress display during audit execution using Server-Sent Events.

### Implementation
- `useAuditStream.ts` — Custom hook wrapping `EventSource`
  - Listens for events: `progress`, `stage`, `finding`, `complete`, `error`
  - Returns: `{ progress, currentStage, findings[], isComplete, error }`
- `AuditProgress.tsx` — Multi-stage progress display:
  - Phase 1 (0-5s): Skeleton screen previewing report layout
  - Phase 2 (5s+): Step indicator showing audit stages (Fetching → Analyzing HTML → Checking Accessibility → ... → Generating Report)
  - Live counters: URLs analyzed, issues found, current stage name
  - Motion animations: pulsing dot for active stage, spring counter for numbers
- Backend: Add SSE endpoint `/api/audit/stream/{auditId}` (if not already present)
  - Must set headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`

### Files to create
- `frontend/src/hooks/useAuditStream.ts`
- `frontend/src/components/audit/AuditProgress.tsx`
- `frontend/src/components/audit/ProgressSkeleton.tsx`
- `frontend/src/components/audit/StageIndicator.tsx`

### Dependencies
- `motion` v11.x (framer-motion, import from `motion/react`)

### Acceptance criteria
- Progress displays during audit with animated stages
- Live counters update as audit progresses
- Skeleton screen shows on initial load
- Smooth transition from progress → results when complete
- Handles connection drops gracefully (SSE auto-reconnects)
- Works for both single page (fast) and full site (slow) audits

---

## Implementation Order

**Build in this exact order** — each sprint depends on the previous:

1. **6A** — Theme foundation (everything else depends on the design tokens)
2. **6B** — Router (page structure must exist before components fill them)
3. **6C** — Audit form (entry point for all audits)
4. **6D** — Free report (the most-used view, proves the design system works)
5. **6E** — Premium dashboard (builds on sidebar pattern from 6B's layout routes)
6. **6F** — Link graph (fills the dashboard's graph page)
7. **6G** — Export (works once dashboard has all data to export)
8. **6H** — Streaming UX (polish layer, can work alongside existing polling)

## General Rules

- **Do NOT remove existing components until their replacement is verified working.** Build new components alongside old ones, then swap.
- **Every component must be TypeScript** with proper type definitions for props.
- **Use Motion (framer-motion v11.x)** for animations. Import from `motion/react` for React 19 compatibility.
- **All interactive elements must be accessible**: proper ARIA attributes, keyboard navigation, focus management.
- **Mobile-first responsive**: test at 375px, 768px, 1024px, 1440px breakpoints.
- **Use CSS variables from `@theme`** — never hardcode colors. Use `bg-surface`, `text-accent`, etc.
- **Performance budget**: First paint < 1.5s, interactive < 3s. Lazy-load dashboard bundle.
- **Read `.claude/rules/frontend-research.md`** for evidence-based design decisions, library versions, and code patterns before implementing any component.
