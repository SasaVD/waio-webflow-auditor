# WAIO Checkpoint — 2026-04-28 — Polish Sprint close-out

**Status:** Polish sprint complete. All work shipped to `origin/main`, deployed to Railway.

**Predecessor doc:** [WAIO-Checkpoint-2026-04-27.md](WAIO-Checkpoint-2026-04-27.md) — Workstream D + E close-outs.
**Plan:** [docs/superpowers/plans/2026-04-27-polish-sprint-pre-seo-review.md](docs/superpowers/plans/2026-04-27-polish-sprint-pre-seo-review.md) — sprint plan with 6-bucket structure.
**Triage report:** [docs/polish-sweep-findings-2026-04-27.md](docs/polish-sweep-findings-2026-04-27.md) — Bucket 6 sweep report covering 14 items.
**Trigger:** Pre-SEO-expert-review polish pass. Sasha's friend (15-yr SEO veteran) running the audit end-to-end this week, dashboard screen-shared and PDF as deliverable.

---

## Final commit ledger — 13 commits

Listed in shipping order. Everything on `main`, daily Railway deploys.

| # | SHA | Day | Title |
|---|---|---|---|
| 1 | `35019be` | 1 | docs(workstream-g): support email draft (Bucket 5) |
| 2 | `2d13fd5` | 1 | docs(polish-sweep): findings report pre-SEO-review (Bucket 6) |
| 3 | `9185698` | 1 | feat(observability): bot-protection counters + admin stats endpoint (Bucket 3) |
| 4 | `6966ede` | 1 | docs(backlog): subagent permission story (post-sprint) |
| 5 | `bbf1610` | 1 | docs(workstream-f): WAF coverage spike findings (Bucket 4) |
| 6 | `c8fa355` | 2 | feat(dashboard): drill-down to affected elements per finding (Workstream B Phase 2 / Bucket 2) |
| 7 | `484ab98` | 2 | docs(backlog): frontend test infra (post-sprint) |
| 8 | `b1717bf` | 3 | test(pdf): lock Content Optimizer gap-bar rendering (PDF v4 #1) |
| 9 | `e9d0ff4` | 3 | fix(tipr): no '0 inbound' template leaks in recommendations (PDF v4 #2) |
| 10 | `1bf7473` | 3 | fix(pdf): brand stopword filter handles whitespace + parenthetical variants (PDF v4 #4) |
| 11 | `ab3f7c1` | 4 | fix(content-optimizer): AI filler corpus token-match + 'comprehensive' copy nit (sweep #1+#8) |
| 12 | `aac05ee` | 4 | fix(ai-visibility): evaluate ambiguity warning against effective brand (sweep #2) |
| 13 | `f2096e0` | 4 | fix(dashboard): replace user-visible DataForSEO vendor name with neutral copy (sweep #3+#5) |
| 14 | `6bdaa96` | 4 | fix(dashboard): replace 'Report enrichment' jargon and expand TIPR/NLP abbreviations (sweep #4+#6) |
| 15 | `b7f808c` | 4 | docs(backlog): file detected_industry frontend migration + remaining DataForSEO leaks (sweep #7) |

**Test growth:** 212 backend tests pre-sprint → **253 backend tests post-sprint** (+41). Zero regressions across all 15 commits.

---

## Wave / Day structure

The sprint ran on a daily-push cadence with two waves and four days.

### Wave 1 — Day 1 (parallel batch, low-decision-density)

Five commits shipped Day 1. Originally dispatched as four parallel background subagents but all four hit a sandbox-permission wall (background agents can't get interactive Bash approval; they stall at 600s no-progress watchdogs). Ran in foreground instead. Cost: more orchestrator context. Filed as `6966ede`.

- **Bucket 3 — Telemetry observability PR** (`9185698`). New `backend/observability.py` with in-memory counter store. Counters at three existing log paths: `bot_challenge.detected` (vendor dimension), `crawl_status.no_data`, `accessibility.scan_failed`. Surfaced via `GET /api/admin/bot-protection-stats` (auth-gated via existing `require_admin`). Provides the post-deploy signal needed to measure whether Workstream E's shared-context fix actually moved the production accessibility-timeout rate. +9 tests.
- **Bucket 4 — Workstream F WAF spike** (`bbf1610`). Three POSTs to `/v3/on_page/instant_pages` against ticketmaster, cvent, sched.com. Result: 2 of 3 bypassed (cvent + sched.com returned real HTML; Ticketmaster returned 403 just like Playwright). Recommendation: F continues — dual-source fallback is empirically valuable for moderate bot protection. F + G are complementary, not redundant. Cost: $0.01275 spike total.
- **Bucket 5 — Workstream G support email draft** (`35019be`). Drafted email to DataForSEO support covering 5 questions (residential proxy, pricing, integration changes, success-rate uplift, current-config feedback) plus 3 production examples by URL. ~320 words. Sasha sends.
- **Bucket 6 — Polish sweep findings report** (`2d13fd5`). 14 items inventoried across 5 categories: confirmed bugs (3), user-visible jargon leaks (4), copy nits (1), pending features (4), low-value cleanups (2). Triaged for Day 4 vs defer.

### Wave 2 — Days 2 + 3 (sequential design-heavy)

Reversed from the plan's original PDF-first order to drill-down-first. Reason: SEO expert review is a live screen-share, dashboard is the demo surface; PDF is the deliverable artifact. Lock the demo experience first.

- **Day 2 — Drill-down UX (Bucket 2 / Workstream B Phase 2)** (`c8fa355`). Extended `Finding` interface in [DashboardPillarPage.tsx](frontend/src/pages/DashboardPillarPage.tsx) to include `elements: FindingElement[]`. New components `FindingElementsList.tsx` + `HtmlSnippetBlock.tsx`. Inline accordion (native `<details>`/`<summary>`) under each finding card, mirrors the existing Fix Suggestions disclosure pattern in the same component (no new Radix dep). Backend element data was already populated by Workstream A QW1-QW4 — this is the frontend that surfaces it. Verified clean tsc + vite build. No frontend test infra exists (filed as `484ab98`).
- **Day 3 — PDF v4 four open issues** (B1.1 through B1.4):
  - **B1.1** Content Optimizer gap bars (`b1717bf`). The bug originally reported 2026-04-20 no longer reproduces on current main — verified empirically by rendering a fixture PDF through WeasyPrint and inspecting drawn rectangles via pdfplumber across 5 gap-score values (0%, 8.1%, 45.3%, 92.7%, 100%). Likely fixed implicitly during the 04-22 BUG-1 sweep. +4 boundary regression tests lock the rendering.
  - **B1.2** TIPR template leaks (`e9d0ff4`). **Real fix.** Engine had `_outbound_phrase()` but no `_inbound_phrase()`; orphan templates BY DEFINITION fire on inbound=0 pages and leaked "with only 0 inbound links" / "with just 0 internal links" on every orphan recommendation. Test fixture caught a hoarder-template leak I missed during initial scan (target-side `{t['inbound_count']}` interpolation when target is an orphan). Added `_inbound_phrase()`, naturalized 4 orphan + 1 hoarder + 1 waster template. PDF regex defense extended for stored historical recommendations. +6 tests.
  - **B1.3** Scorecard duplication. **Already resolved on current main.** Existing test `test_scorecard_no_longer_renders_individual_pillar_cards` already locks "no `pillar-card` div in section 03." Verified rendered PDF section 03 shows 10 unique pillar rows. The `pillar_cards` builder is NOT dead code — feeds `_render_pillar_bar_chart_svg`. **No commit needed.**
  - **B1.4** "Project scope" filter (`1bf7473`). **Real fix.** Two formatting bugs in `_clean_brand_candidate`: (a) double-space `"Project  Scope"` didn't match single-space stopword, (b) parenthetical `"Project Scope (definition)"` got broken because char-strip removed `)` before the parenthetical-trim regex could match. Both fixed (parenthetical-first ordering + whitespace collapse). +2 tests covering 9 formatting variants.

### Day 4 — sweep picks (queued from Day 1's triage)

Five commits, three real fixes + two backlog files.

- **Sweep #1+#8 — AI filler corpus + 'comprehensive' copy** (`ab3f7c1`). Bundled per audit-quality theme. Real bug: `is_ai_filler()` had `phrase in term_lower OR term_lower in phrase` — the reverse direction caused 'bot' (substring of 'the bottom line is'), 'day' (substring of 'today's'), 'digital' (substring of 'today's digital') to be flagged as filler. On a Webflow agency audit, recommending removal of these legitimate brand terms is exactly the kind of bug a 15-yr SEO veteran spots in 5 minutes. Fix: drop the reverse clause. +20 tests including all of Sasha's locked test cases. Plus replaced "less comprehensive" → "thinner" in exec summary copy.
- **Sweep #2 — auto-brand ambiguity** (`aac05ee`). Two-line frontend defensive change: `effectiveBrand = brandName.trim() || brandPreview?.auto_extracted` so the warning fires immediately on first view even if the brandName-from-preview useEffect hasn't completed yet. Note: investigation showed the wiring already mostly worked due to the existing useEffect; this is a race-window defense, not a "warning never fires" fix.
- **Sweep #3+#5 — DataForSEO vendor name leaks** (`f2096e0`). Two leaks fixed in DashboardLayout.tsx + DashboardGraphPage.tsx. Grep surfaced 7 more instances across other pages — kept out of this commit per its scoped 2-file mandate, filed as backlog (`b7f808c`).
- **Sweep #4+#6 — dashboard banner copy** (`6bdaa96`). Three copy edits in DashboardLayout.tsx: "Report enrichment in progress" → "Site-wide analysis in progress"; "Report enrichment complete!" → "Site-wide analysis complete"; TIPR/NLP abbreviations expanded to "link analysis, content intelligence, AI visibility" etc. for non-technical readers.
- **Sweep #7 — verify-or-defer stale TODO** (`b7f808c`). Five-minute check confirmed frontend migration to `industry.value` is INCOMPLETE — 7+ consumers still read `detected_industry` directly. Filed as M-sized backlog item.

---

## Test growth detail

| Day | Pre-day | Post-day | Δ | Notes |
|---|---|---|---|---|
| Pre-sprint | — | 212 | — | Workstream E baseline (`a1cdc4a`) |
| Day 1 | 212 | 221 | +9 | Bucket 3 telemetry: 6 unit + 3 wiring tests |
| Day 2 | 221 | 221 | 0 | Frontend-only PR; no test infra in frontend |
| Day 3 | 221 | 233 | +12 | B1.1 +4 boundary, B1.2 +6 phrasing, B1.4 +2 brand-filter |
| Day 4 | 233 | 253 | +20 | Sweep #1 AI filler corpus +20 |
| **Total** | **212** | **253** | **+41** | Zero regressions across 15 commits |

---

## Honest scoping notes

Several items in the original plan turned out to need different treatment than planned. Documenting here for institutional memory and as a process improvement note for future sprints.

1. **Two of four PDF v4 issues were already resolved on current main.** B1.1 (Content Optimizer gap bars) and B1.3 (scorecard duplication) had been fixed implicitly by the 04-22 BUG-1 sweep but kept appearing on the "open issues" list across 04-20 → 04-21 → 04-22 → 04-23 checkpoints. Re-verifying pending items before scoping fixes is a process improvement worth carrying into future workstreams. Spending Day 3 confirming + locking with regression tests still has value (B1.1 had no rendered-geometry test before; B1.3's lock test was already in place).
2. **B1.2 was diagnosed as "0 outbound" but the real leak was "0 inbound."** Original 04-20 report framed it as outbound, but orphan templates (which dominate real audit output) leak inbound counts. Engine fix added a parallel `_inbound_phrase()` helper. The hoarder template leak (target-side inbound interpolation when target is an orphan) was caught only by the test fixture — not by manual code review.
3. **B1.4 was diagnosed as "case/punctuation normalization" but the real bugs were whitespace and parenthetical ordering.** Polish-sweep doc framed it as a stopword absence; "project scope" was already in the stopword set. Real bugs: (a) char-strip step removed `)` before the parenthetical-trim regex could match, (b) double-space variants didn't normalize.
4. **Sweep #2 was diagnosed as "warning never fires on auto-extract" but the wiring already worked.** The brandName-from-brandPreview useEffect already populates brandName from auto_extracted, so the warning DOES fire on first view in normal flow. The fix in `aac05ee` is a race-window defense, not a "warning never fires" fix. Documented this in the commit.
5. **Polish sweep was incomplete on DataForSEO leak coverage.** Doc flagged 2 leaks (#3, #5); grep during sweep #3+#5 implementation found 9 total. Kept the commit scoped to 2 files per Sasha's mandate; filed remaining 7 as backlog.

---

## Backlog filed during sprint

Three new items in [docs/BACKLOG.md](docs/BACKLOG.md):
1. **Subagent permission story** (`6966ede`) — background subagents can't get interactive Bash approval, stall at 600s watchdog. Needs settings.json allowlist + outbound-HTTPS allowlist. Deferred until after SEO review.
2. **Frontend test infrastructure** (`484ab98`) — backend has 253 pytest tests, frontend has 0. Manual smoke alone won't scale. Add vitest + testing-library post-sprint.
3. **detected_industry frontend migration** (`b7f808c`) — 7+ consumers still read the legacy field; backend can't drop it yet.
4. **Additional DataForSEO jargon leaks** (`b7f808c`) — 7 more instances across DashboardClustersPage, DashboardSummaryPage, DashboardPagesPage, DashboardLinkIntelligencePage. Some legitimate (AI Visibility methodology vendor credit), most replaceable.

---

## What the SEO expert review should focus on first

Concrete suggestions for Sasha's friend's review session, ordered by where the latest work has the highest signal:

### Highest confidence — exercise these first

1. **Drill-down UX on a real audit.** Open [shadowdigital.cc audit `5ff79646-46ea-427a-84e5-3149cd93dcc4`](https://waio.up.railway.app/dashboard/5ff79646-46ea-427a-84e5-3149cd93dcc4/pillar/search-engine-clarity) → Semantic HTML pillar → click "Show N affected elements" on findings. Real `<img>` selectors and snippets rendered inline. This is the headline new feature; expert should validate that the HTML snippets and CSS selectors are accurate enough to act on.
2. **Content Optimizer Filler tab.** After running a Content Optimizer analysis on the test site, check the Filler tab. Should NOT contain "bot", "day", "digital", "today" etc. — only genuine AI-flavored phrases. Pre-fix, these legitimate brand terms got recommended for removal.
3. **Premium PDF on a Belt Creative-tier audit.** Open the Branded PDF for `4ef284bb-9c43-4150-a82d-25a92886d9ed`. Section 03 (10-Pillar Scorecard) — single bar chart, no duplicate cards. Section 04 (TIPR) — recommendation reasons should read naturally, no "with only 0 inbound links" leaks. Section 06 (AI Visibility) — Brands Appearing in Your Category table should NOT include "Project Scope" / "Project Timeline" / "Budget Range" etc.
4. **Bot-protection telemetry endpoint.** `curl https://waio.up.railway.app/api/admin/bot-protection-stats` (with admin auth) — returns aggregate counters across the three log paths. After a few production audits, should show non-zero values for sites that hit Cloudflare etc.

### Areas with known rough edges (be candid with the expert)

1. **Frontend test infrastructure absence.** Drill-down UX, banner copy, AI Visibility modal — none of these have component tests. tsc + manual smoke is the only verification. If the expert finds a regression here, it's because we lack the test infra to catch it (filed `484ab98`).
2. **Premium homepage-only pillar ceiling.** Drill-down works, but it's bounded to homepage data — non-homepage URLs in DataForSEO crawl don't have pillar findings. If the expert clicks into a pillar finding and asks "why isn't this rendering for /blog/post-123?", that's [Workstream C](docs/BACKLOG.md) territory.
3. **Bot-protected sites still produce trivial crawls.** Workstream F shipped no implementation yet (just spike findings). Ticketmaster-class sites still hit "Site-wide crawl blocked by bot protection" banner. F + G implementations would close that gap; both deferred until after the SEO review.
4. **detected_industry / industry.value duplicate fields.** Backward-compat shim still in place. If the expert exports JSON and asks why the same value appears in two fields, that's the 7-consumer migration debt (`b7f808c`).
5. **Additional DataForSEO jargon leaks.** Sweep #3+#5 only fixed 2 of 9; 7 more remain in less-prominent locations (filed in `b7f808c`).

---

## Diagnostic audits preserved (institutional memory)

Same set as Workstream D + E close-outs. None overwritten or deleted during the polish sprint.

| Audit ID | Site | Role |
|---|---|---|
| `563145e4-4151-41cc-9505-f6a4f1bba2c8` | sched.com | Workstream D canonical incident; "Webflow Webflow" NLP stutter source for BUG-2 |
| `9a954c09-768e-4f76-a776-56ffde7b138a` | ticketmaster.com | AI Visibility blob silent-skip incident; F WAF spike target (blocked) |
| `20685624-5468-4d0f-8f89-18aa94632272` | cvent.com | Stuck-spinner banner incident; F WAF spike target (bypassed) |
| `0e2b5690-5de5-4228-90a5-b8c376991aa9` | sched.com | Accessibility-Playwright timeout case for Workstream E |
| `5ff79646-46ea-427a-84e5-3149cd93dcc4` | shadowdigital.cc | BUG-1 scan_status canonical case; QW1-4 element drill-down verification target |
| `4ef284bb-9c43-4150-a82d-25a92886d9ed` | beltcreative.com | 171-page premium audit with full TIPR + clusters + AI Visibility + 2x Content Optimizer; PDF v4 verification target |

---

## Verification matrix (live production — last checked 2026-04-28)

| Check | Live signal |
|---|---|
| Test count: 212 → 253 (+41) | ✓ verified via `pytest backend/tests/` |
| GET /api/admin/bot-protection-stats live | ✓ Railway deploy from `9185698` confirmed by Sasha |
| Drill-down UX live on shadowdigital.cc audit | ✓ Sasha smoke-verified after `c8fa355` deploy |
| Section 03 PDF: 10 pillar rows, no duplication | ✓ verified via PdfReader text extraction on fixture |
| Content Optimizer gap bars render across 0-100% | ✓ verified via pdfplumber rectangle inspection |
| Section 06 PDF: no "Project Scope" in brand table | ✓ locked by `test_extract_discovery_brands_filters_project_scope_formatting_variants` |
| AI filler corpus: "bot"/"day"/"digital" → False | ✓ locked by 20 unit tests in `test_ai_filler_corpus.py` |
| TIPR recommendations: no "0 inbound links" leaks | ✓ locked by 4 engine-side + 2 PDF-side tests |
| Frontend `tsc -b` + `vite build` clean post-sprint | ✓ verified after every Day 2 + Day 4 commit |

---

**Polish sprint is closed.** SEO-expert review can proceed against the latest deploy. Next session priorities will be driven by what the expert surfaces — which of the filed backlog items become urgent vs. stay deferred is entirely a function of their feedback.
