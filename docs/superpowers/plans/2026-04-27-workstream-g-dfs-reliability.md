# Workstream G — DataForSEO crawl reliability investigation

**Status:** Investigation spike. Not yet ready for execution.
**Date drafted:** 2026-04-27.
**Filed in:** [docs/BACKLOG.md](../../BACKLOG.md).

## Why this exists

Three production audits during Workstream D verification produced trivial DFS crawls:

- Ticketmaster (`9a954c09`, 04-27): DFS returned 1 page, 0 links → `crawl_status: "no_data"`
- Cvent (`20685624`, 04-27): DFS task stayed in `progress=in_progress, pages=0/0` for 60 polls → `enrichment_status: "timed_out"`
- sched.com (`563145e4`, 04-23): DFS produced 474 nodes / 366 links — the partial-success path (worked there)

DFS's default `On-Page` crawler doesn't always defeat enterprise WAFs. Today's handling is graceful (D4 + D5 + e7aede9 banner) but the underlying crawl never recovers. There's no path from "trivial" to "real graph data."

## Goal

Increase the DFS crawl success rate on bot-protected enterprise sites. Move some fraction of today's `no_data` / `timed_out` outcomes into `complete`.

## Phase 1 — Investigation spike (1 week)

**Do this BEFORE writing the implementation plan.** No code changes during the spike.

### Spike tasks

1. **Contact DataForSEO support** — ask:
   - Do you offer residential-proxy or premium-proxy mode for the On-Page API?
   - What's the pricing differential vs the default crawler?
   - What integration changes are needed (config flag, separate endpoint, separate API key)?
   - What success-rate improvement do you typically see on Cloudflare / Akamai / DataDome-protected enterprise sites?
   - Are there other config knobs (custom user-agent, longer wait times, browser fingerprint randomization) we should try first?

2. **Run a controlled test** on one of our own production-blocked sites (Ticketmaster or cvent — pick one):
   - Submit the same URL via the default DFS On-Page (current production config).
   - Submit again via residential-proxy mode (if DFS provides a free trial credit) OR via the most-aggressive default-tier config DFS recommends.
   - Compare: pages crawled, links extracted, time to completion.

3. **Document findings** in this file — replace this Phase 1 section with the results.

### Deliverable

A short report with three numbers and a recommendation:
- Cost differential (default vs upgraded mode)
- Success-rate improvement (controlled test result)
- Recommended path: implement, defer, or skip

## Phase 2 — Implementation plan (only after Phase 1 returns)

The shape of the implementation depends on Phase 1's findings. Three candidate paths:

| Path | Triggered if Phase 1 shows... | Implementation surface |
|---|---|---|
| **G-impl** (full implementation) | Residential proxy gives ≥50% improvement on protected sites at <2x cost | Add config flag to `DataForSEOClient`, gate on premium tier, surface as "advanced crawl" feature |
| **G-defer** (defer with monitoring) | Improvement is real but cost is too high for current pricing tiers | Add up-front UX warning ("DataForSEO may not be able to crawl this site") on submission for known-WAF sites; implement Workstream G when pricing tier supports it |
| **G-skip** (close as not actionable) | DFS doesn't offer better config, or improvement is minimal | Close this workstream; rely on Workstream F (dual-source homepage) for protected sites; mark DFS as "graceful degradation only" architecturally |

The full implementation plan only gets written under the G-impl branch.

## Open questions to resolve in Phase 1

1. What's our current DataForSEO contract tier? Do we already have access to residential-proxy mode, or do we need to upgrade?
2. What does DFS support recommend BEFORE going to residential proxy (browser fingerprint config, longer waits, user-agent rotation)?
3. Is there a per-task config flag, or is residential proxy account-wide (would affect every audit's crawl cost)?
4. Acceptable cost ceiling per premium audit — what's the willing pay-up for "got the audit through Cloudflare"?

## Pre-execution requirements

- Workstream F shipped first. F's dual-source approach may close most of the gap that G is trying to address — if Playwright bot-challenge is recoverable via DFS Instant Pages, the residential-proxy pressure on G drops significantly.
- Phase 1 spike completed and documented in this file.

## Out of scope (explicitly NOT in G Phase 1)

- Code changes — this is a research spike.
- Procurement decisions — surface findings; user makes the call.
- Anything that depends on DFS contract terms we don't yet know.

## What lands in BACKLOG.md

A pointer to this file with status "Investigation spike pending — ~1 week scoped". The spike isn't blocked; it just needs an explicit kickoff (someone has to actually email DFS support).

## Email draft for sasa@vezadigital.com to send (drafted Bucket 5, polish sprint)

> Send timing: as soon as possible. DFS support response time is typically 24-72 hours; we want their answer landing within the SEO-expert-review window.

**To:** support@dataforseo.com (verify the right address before sending — possibly help@dataforseo.com, or use the support form inside the DFS dashboard)
**From:** sasa@vezadigital.com
**Subject:** Question: residential proxy / premium crawl options for On-Page API on WAF-protected sites

---

Hi DataForSEO team,

We're an existing On-Page API customer running a SaaS audit tool (https://waio.up.railway.app) that submits sites to your crawler with `enable_javascript_rendering: true`. Recent production audits on enterprise sites with WAF protection (Cloudflare / Akamai / DataDome) have produced trivial or empty results, and I'd like your guidance before we change anything on our side.

Three recent examples from our logs:

1. `https://www.ticketmaster.com` — task completed but returned only 1 page and 0 internal links.
2. `https://www.cvent.com` — task remained `in_progress` with `pages_crawled=0` across our full polling window (~10 minutes) and never advanced.
3. `https://sched.com` — partial success (474 pages, 366 links extracted), so our integration itself is working; the difference appears to be on the crawl side.

A few questions:

1. Do you offer a residential-proxy or premium-proxy mode for the On-Page API? If yes, is it enabled per-task (e.g. a config flag in the task POST), per-account, or via a separate endpoint or API key?
2. What is the pricing differential vs the default crawler — both per-page and any base-tier or minimum-spend requirement?
3. What success-rate uplift do you typically see on Cloudflare / Akamai / DataDome-protected enterprise sites when customers move from default to upgraded crawl mode?
4. Before going to residential proxy, are there other configuration knobs we should try first — custom user-agent, longer wait/load times, browser fingerprint randomization, slower request pacing, headers we should set, etc.?
5. Is there anything in our current task config (we use `enable_javascript_rendering: true`, default user-agent, default wait times) that you'd recommend changing for WAF-protected targets?

Happy to share full task IDs from our DFS dashboard for any of the three examples above if that helps you reproduce.

Looking forward to your guidance.

Best,
Sasa Vukotic
Veza Digital
sasa@vezadigital.com
