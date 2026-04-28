# Workstream F — Dual-source DFS homepage analysis

**Status:** Scoping stub. Not yet ready for execution. Blocks on Workstream E (accessibility shared context) shipping first to keep changes contained.
**Date drafted:** 2026-04-27.
**Filed in:** [docs/BACKLOG.md](../../BACKLOG.md).

## Why this exists

When `fetch_page()` returns a bot-challenge page, D1 detects it and the 10 pillars are suppressed. For premium audits, the user has *already paid for DataForSEO*, and DFS often successfully crawls the same homepage that Playwright couldn't reach (its crawler architecture and IP reputation differ). Today DFS data feeds link graph / TIPR / clusters but never feeds the 10-pillar audit. The homepage's real HTML is sitting in DFS's response and we discard it.

## Goal

When Playwright is bot-challenged AND DFS has the homepage, use DFS-rendered HTML as the authoritative source for the 10 pillars. The user gets a real audit instead of "Scan incomplete."

## Locked direction

**Approach B — Playwright first, DFS Instant Pages on bot-challenge.** Today's flow unchanged for clean fetches. When D1 detects bot challenge, fire a fresh DFS Instant Pages call (cheap, synchronous, ~1s) and use that HTML for pillars.

Locked per scoping decision 2026-04-27. Other approaches (A: DFS-first, C: post-hoc reconcile) considered and rejected:
- A would slow every premium audit to DFS-pace (3-30 min) and break free-tier (no DFS).
- C is two-phase scoring UX confusion — initial "Scan incomplete" → later swap to a real score.

## Open questions to resolve before this becomes an executable plan

1. ~~**DFS Instant Pages WAF coverage**~~ — **RESOLVED 2026-04-28 via Bucket 4 polish-sprint spike. See "Spike findings" section below.**
2. **Cost guardrail** — DFS Instant Pages is ~$0.0042 per request (measured during the spike, with `enable_browser_rendering: true` — about 7x the documented $0.0006 baseline rate); the incremental cost is small per audit but multiplies if bot-challenge rate is high. Acceptable, or do we want a per-audit budget cap?
3. **UX framing** — when the dual-source fallback succeeds, should the dashboard show a small badge ("served via DataForSEO secondary fetch") or is that noise?
4. **Free tier** — Approach B is premium-only because DFS isn't configured for free. Free-tier bot-protected audits stay at "Scan incomplete." Acceptable?
5. **Reconciliation rules** — what happens if DFS Instant Pages returns substantially different HTML than Playwright (different content, different JS execution state)? Trust DFS verbatim, or merge?

## Spike findings (2026-04-28 — Bucket 4 of polish sprint)

**Empirical test:** three POSTs to `/v3/on_page/instant_pages` with `enable_javascript: true, enable_browser_rendering: true, load_resources: true`, against the three diagnostic targets that defeated default DFS On-Page crawler in production (Ticketmaster `9a954c09`, cvent `20685624`, sched.com `563145e4`). Each call cost $0.00425; total spike cost $0.01275.

| Target | DFS task status | HTTP status | resource_type | Real content rendered? | Cost | DFS gateway IP |
|---|---|---|---|---|---|---|
| `https://www.ticketmaster.com/` | 20000 (Ok) | **403** | **broken** | **No — WAF blocked** (158K body = challenge HTML; `is_4xx_code: true`, `is_broken: true`, no `meta` block at all) | $0.00425 | 68.183.60.34 |
| `https://www.cvent.com/` | 20000 (Ok) | 200 | html | **Yes** — `h1: "Get better results from your events"`, 9 h2s, 8 h3s, 116 internal links, 20 external, 30 scripts, 26 images, 159-char meta description | $0.00425 | 168.119.99.194 |
| `https://sched.com/` | 20000 (Ok) | 200 | html | **Yes** — `h1: "Event management software"`, 7 h2s, 63 h3s, 77 internal links, 6 external, 17 scripts, 19 images, 156-char meta description | $0.00425 | 168.119.141.170 |

**Verdict: 2 of 3 bypassed.** DFS Instant Pages with browser rendering DOES defeat moderate bot protection (cvent, sched.com), but DOES NOT defeat aggressive bot protection (Ticketmaster's Cloudflare returns 403 to DFS's gateway IP just as it does to our Playwright instance).

**Recommendation: F continues as scoped (Approach B preserved).** F's dual-source path is empirically valuable for cvent-class and sched-class sites where the default DFS crawler stalls but Instant Pages-with-browser-rendering succeeds. F is NOT a complete fix for Ticketmaster-class sites (heavy Cloudflare bot fight mode); those still need G's residential-proxy fallback. F and G are complementary, not redundant.

**Implications for next steps:**
- F can move to executable-plan stage. The dual-source fallback will yield a real audit on a meaningful fraction of bot-protected sites.
- G's investigation spike is still warranted — F doesn't close the Ticketmaster-class gap. G's email (drafted in Bucket 5, sitting in this doc's tail section ready to send) becomes the primary path for that class.
- Cost guardrail (Open Question #2) updated: spike measured $0.00425/call with browser rendering, ~7x the documented $0.0006 baseline. Per-audit incremental cost on a bot-challenged site is ~$0.00425 (one call). At our current bot-challenge rate (~3-4 incidents observed in the last week against ~10 premium audits run = ~30-40%), the budget impact is roughly $0.0017/audit averaged. Below the noise floor of overall audit cost ($1-3 per premium). No per-audit budget cap needed.
- Open Question #1 is closed; remaining open questions (#2 cost guardrail above is now answered too, leaving #3 UX framing, #4 free-tier handling, #5 reconciliation rules) are scoping-time questions that get answered when F's executable plan is written.

**Detail:** raw JSON responses from the spike were saved locally to `/tmp/dfs-spike-{ticketmaster,cvent,sched}.json` and inspected via `jq` against the `tasks[0].result[0].items[0]` shape. Not committed (transient). Reproducible by re-running the same three POSTs.



- When D1 detects bot challenge, the system attempts DFS Instant Pages as a second source.
- If DFS Instant Pages produces real content (passes the same `detect_bot_challenge` check), the 10 pillars run on it and emit normal scores.
- Report carries `homepage_source: "dataforseo"` alongside the existing `bot_challenge` block. Dashboard surfaces a "served via DataForSEO secondary fetch" indicator.
- If both sources are bot-challenged, current D-stack behavior is preserved (suppress + banner).
- Smoke test on Ticketmaster (Playwright clean, DFS no_data) and sched.com.

## Pre-execution requirements

- Workstream E shipped (accessibility shared context — keeps the orchestrator change surface contained for sequencing).
- Investigation spike answering Q1 above. If DFS Instant Pages doesn't bypass the same WAFs, this workstream pivots — possibly merging into Workstream G.

## Execution structure (when ready)

Subagent-driven, 1-2 commits, similar shape to D2 or D5. Will be expanded into per-task breakdown (F.1, F.2, ...) once the open questions resolve.

## Out of scope (explicitly NOT in F)

- Residential-proxy DFS configuration (Workstream G).
- Telemetry collection (small standalone task in BACKLOG).
- Free-tier bot-protected handling.
- DFS contract renegotiation.
