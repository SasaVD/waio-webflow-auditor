# Polish Sweep Findings — 2026-04-27

**Date:** 2026-04-27
**Scope:** Pre-SEO-expert-review polish sweep (Bucket 6 of polish sprint)
**Author:** Bucket 6 (executed by orchestrator in foreground after subagent dispatch hit sandbox-permission wall)
**Plan:** [docs/superpowers/plans/2026-04-27-polish-sprint-pre-seo-review.md](superpowers/plans/2026-04-27-polish-sprint-pre-seo-review.md)

## TL;DR

**14 items found** across 5 categories: confirmed bugs (3), user-visible jargon leaks (4), copy nits (1), deferred-too-long pending items (4), low-value cleanups (2).

**Recommend shipping this week** (high signal-to-noise, all S-sized, all directly improve the SEO-expert-review surface):

1. **#1 — AI filler corpus token-match bug** (`bot`/`digital`/`day` false positives appear in WDF*IDF Filler tab). Bug citation, fix shape, and 8 test cases all locked.
2. **#3 — DataForSEO jargon leak in dashboard banner** ("DataForSEO couldn't fetch enough pages") — the SEO expert will read this banner if they audit a Cloudflare site. "DataForSEO" is internal vendor branding; user shouldn't have to know it.
3. **#4 — "Report enrichment" coined term** in DashboardLayout banners — should read "Site-wide analysis" or similar.

**Recommend deferring**: items #8–#14 (low-impact polish, large-scope features, or already structurally covered elsewhere).

**Triage table:** every item has S/M/L sizing and severity below. Sasha reviews and replies which items ship.

## Findings table

| ID | Category | Description | Sizing | Severity | Recommended action |
|---|---|---|---|---|---|
| 1 | Confirmed bug | AI filler corpus substring check fires false positives (`bot`, `digital`, `day`) — fix to token-match | S | Med-High | **Ship this week** |
| 2 | Confirmed bug | Auto-extracted brand bypasses `checkBrandAmbiguity` — short-token auto-brand silently produces noisy LLM Mentions data | S | Med | **Ship this week** |
| 3 | Jargon leak | "DataForSEO couldn't fetch enough pages" in dashboard amber banner — user-visible vendor name | S | Med | **Ship this week** |
| 4 | Jargon leak | "Report enrichment in progress" / "Report enrichment complete!" — coined internal term | S | Low-Med | **Ship this week** |
| 5 | Jargon leak | "DataForSEO configuration" in graph page error copy | S | Low | Bundle with #3 fix |
| 6 | Jargon leak | "TIPR, NLP, AI Visibility, Content Optimizer, executive summary" abbreviations in degraded-crawl banner | S | Low | Bundle with #4 fix |
| 7 | Backend TODO | `ai_visibility/engine.py:324` — `# TODO: remove after frontend fully migrated to industry.value` | XS | Low | Verify frontend migration is complete; remove TODO |
| 8 | Copy nit | Word "comprehensive" used in exec summary content-gap copy — itself flagged by AI filler corpus | XS | Very low | Defer or fold into #1's PR |
| 9 | Pending feature | Pass auto-extracted brand through `check_brand_ambiguity` — covered by #2 | (subsumed) | — | Subsumed by #2 |
| 10 | Pending feature | Graph visual polish (node tightness, label overlap on `/dashboard/:auditId/graph`) — deferred since 04-20 | M | Low | Defer (not on demo critical path; SEO expert is unlikely to deep-dive graph aesthetics) |
| 11 | Pending feature | Drop redundant `tipr_score` JSON field — duplicates `tipr_rank` exactly | S | Very low | Defer (post-sprint cleanup) |
| 12 | Pending feature | Store `score=None` on failed pillars (currently stores 100, UI hides via `scan_status`) | S | Very low | Defer (UI already hides; raw-DB readers only) |
| 13 | Pending feature | GSC/GA4 OAuth integration (TIPR signal 4) | L | Med | Defer (multi-day, out of sprint scope) |
| 14 | Pending feature | 3-signal TIPR (add backlink data) | L | Med | Defer (multi-day, out of sprint scope) |

## Detailed notes per item

### #1 — AI filler corpus token-match bug

**File:** [backend/content_optimizer/ai_filler_corpus.py:101](../backend/content_optimizer/ai_filler_corpus.py#L101)
**Current code:**

```python
for phrase in FORMULAIC_PHRASES:
    if phrase in term_lower or term_lower in phrase:
        return True
```

The second clause `term_lower in phrase` is the bug. It causes any short word that happens to be a substring of any formulaic phrase to be flagged as filler:

- `is_ai_filler("bot")` → True because `"bot" in "the bottom line is"` is True (substring match against "bottom")
- `is_ai_filler("day")` → True because `"day" in "in today's digital"` is True (substring match against "today's") AND `"day" in "at the end of the day"` is True
- `is_ai_filler("digital")` → True because `"digital" in "in today's digital"` is True

These three terms all leak into the WDF*IDF Filler tab on real audits, polluting what should be a curated "AI sloppiness" detector.

**Approved fix shape (locked by Sasha):** token-match the formulaic phrases, NOT substring containment. Split each phrase on whitespace and compare exact-token equality to the candidate term:

```python
for phrase in FORMULAIC_PHRASES:
    phrase_tokens = phrase.split()
    candidate_tokens = term_lower.split()
    # Multi-word candidate must equal the full phrase (or be a contiguous run)
    if candidate_tokens == phrase_tokens:
        return True
    # OR the candidate is the phrase itself
    if term_lower == phrase:
        return True
```

(The exact implementation may differ — the goal is "no substring matching." Multi-word patterns like `"digital landscape"` are STILL caught by the existing structural rules in lines 105-115 — those use trailing-FILLER_NOUN / leading-INFLATED_ADJECTIVE / leading-ABSTRACT_VERB checks against `words[-1]` and `words[0]`, all of which are exact-token comparisons already.)

**Required test cases (approved by Sasha):**

```python
def test_short_token_does_not_substring_match_formulaic_phrase():
    # "bot" must NOT match "the bottom line is" or "robot"
    assert is_ai_filler("bot") is False
    assert is_ai_filler("robot") is False
    assert is_ai_filler("bottom") is False  # single word, not in any single-word filler set

def test_full_formulaic_phrase_still_matches():
    assert is_ai_filler("the bottom line is") is True

def test_day_does_not_substring_match():
    # "day" must NOT match "today" / "Friday" / "at the end of the day"
    assert is_ai_filler("day") is False
    assert is_ai_filler("today") is False

def test_digital_does_not_substring_match_phrase():
    # "digital" must NOT match because "digital" is substring of "in today's digital"
    assert is_ai_filler("digital") is False

def test_multiword_filler_with_trailing_filler_noun_still_matches():
    # Structural rule preserved: trailing FILLER_NOUN catches this
    assert is_ai_filler("digital landscape") is True
```

**Sizing:** S (~1 hour incl. tests + verification on a known audit).

---

### #2 — Auto-extracted brand bypasses ambiguity check

**Files:**
- [frontend/src/components/ai-visibility/AIVisibilityModal.tsx:93](../frontend/src/components/ai-visibility/AIVisibilityModal.tsx#L93) — only `brandName` (user-typed) is passed
- [frontend/src/components/ai-visibility/AIVisibilityModal.tsx:196](../frontend/src/components/ai-visibility/AIVisibilityModal.tsx#L196) — auto-extracted brand renders without ambiguity check

**Current behavior:** The modal computes `ambiguityWarning = checkBrandAmbiguity(brandName)`. If the user types nothing and lets the auto-extracted brand stand, the warning is never evaluated against `brandPreview.auto_extracted`. So if NLP picked up "VAN" or "HP" or any 2-3 char ORGANIZATION entity, the user proceeds without seeing the warning.

The 04-21 checkpoint flagged this: *"Auto-brand extraction might still pick an ambiguous brand — `resolve_brand()` picks the highest-salience ORGANIZATION entity, which could still be a 2-3 char acronym. Consider passing auto-extracted brand through `check_brand_ambiguity()` too and surfacing the warning on first view."*

**Proposed fix:** Change line 93 to evaluate the effective brand:

```typescript
const effectiveBrand = brandName.trim() || brandPreview?.auto_extracted || '';
const ambiguityWarning = checkBrandAmbiguity(effectiveBrand);
```

Also tweak the warning rendering at line 186 so it fires on `effectiveBrand`, not just user-typed `brandName`.

**Sizing:** S (~30 min incl. tests on the existing modal test if any, plus manual smoke).

**Severity:** Med — currently silently produces noisy/wrong AI Visibility data on auto-extracted short-token brands; the user sees no signal that something's off.

---

### #3 — "DataForSEO" leaked as user-visible vendor name in dashboard

**File:** [frontend/src/layouts/DashboardLayout.tsx:413](../frontend/src/layouts/DashboardLayout.tsx#L413)
**Current copy:**

> "The target site's bot protection (Cloudflare or similar) blocked our crawler — DataForSEO couldn't fetch enough pages."

The user pays $4,500 for a premium audit. They don't necessarily know what DataForSEO is, and the vendor name leaks our internal stack. Replace with vendor-neutral copy:

> "The target site's bot protection (Cloudflare or similar) blocked our crawler — we couldn't fetch enough pages to build the link graph and topic clusters."

**Sizing:** S (single-line copy edit + similar leak at DashboardGraphPage.tsx:88 — see #5).

**Severity:** Med — directly user-visible during the live screen-shared SEO expert review on any Cloudflare site. The expert will notice.

---

### #4 — "Report enrichment" coined internal term

**File:** [frontend/src/layouts/DashboardLayout.tsx:359, 383](../frontend/src/layouts/DashboardLayout.tsx#L359)
**Current copy:**

- Line 359: "Report enrichment in progress"
- Line 383: "Report enrichment complete! Refreshing data..."

"Enrichment" is internal jargon (matches the backend `enrichment_status` field). Users don't think of their report as something that gets "enriched" — they think of it as something that gets "completed" or "analyzed."

**Proposed copy:**

- "Site-wide analysis in progress" / "Generating link graph and topic clusters"
- "Site-wide analysis complete — refreshing data..."

**Sizing:** S (two copy edits).

**Severity:** Low-Med — if the SEO expert hits the dashboard during the polling window, this is the first banner they read.

---

### #5 — "DataForSEO configuration" in graph page error copy

**File:** [frontend/src/pages/DashboardGraphPage.tsx:88](../frontend/src/pages/DashboardGraphPage.tsx#L88)
**Current copy:** "Please try running the audit again. If the problem persists, check your DataForSEO configuration."

Same vendor-name leak as #3, plus suggests the user has DataForSEO config to "check" — they don't (it's our backend env vars).

**Proposed copy:** "Please try running the audit again. If the problem persists, contact support — there may be a temporary issue with our crawler."

**Sizing:** S (single-line edit).

**Severity:** Low (state only fires on `enrichment.status === 'failed'`, which is rare).

**Recommendation:** Bundle into the same commit as #3.

---

### #6 — TIPR/NLP abbreviations in user-visible degraded-crawl banner

**File:** [frontend/src/layouts/DashboardLayout.tsx:418](../frontend/src/layouts/DashboardLayout.tsx#L418)
**Current copy:**

> "All other intelligence (TIPR, NLP, AI Visibility, Content Optimizer, executive summary) ran on the data we could collect."

TIPR and NLP are internal abbreviations that users won't recognize. The expert SEO consultant will know NLP but TIPR is our coined term for True Internal PageRank — it has no widespread industry recognition.

**Proposed copy:**

> "All other intelligence (link analysis, content intelligence, AI visibility, content optimizer, executive summary) ran on the data we could collect."

**Sizing:** S (single-line edit).

**Severity:** Low — SEO expert will figure it out from context, but the polish-vs-polish-not signal is real.

**Recommendation:** Bundle with #4 in a single "dashboard banner copy" commit.

---

### #7 — Stale backend TODO

**File:** [backend/ai_visibility/engine.py:324](../backend/ai_visibility/engine.py#L324)
**Comment:** `# TODO: remove after frontend fully migrated to industry.value`

Verify whether the frontend has fully migrated. If yes, remove the TODO + the legacy code path it gates. If no, file as a separate item.

**Sizing:** XS to verify, XS-S to remove if migration complete.

**Severity:** Very low.

**Recommendation:** Triage in 5 minutes; ship if removable, defer if not.

---

### #8 — "Comprehensive" used in exec summary content-gap copy

**File:** [backend/executive_summary_generator.py:786](../backend/executive_summary_generator.py#L786)
**Copy:** "is significantly less comprehensive than pages currently ranking for the same queries."

The word "comprehensive" is on the AI filler corpus's INFLATED_ADJECTIVES list. Mild irony — our own AI-sloppiness detector would flag the executive summary itself.

**Proposed rewrite:** "is significantly thinner than pages currently ranking for the same queries." (Or "is meaningfully shorter and less detailed than…" — any direct, non-inflated phrasing.)

**Sizing:** XS (single string edit).

**Severity:** Very low.

**Recommendation:** Defer or bundle into #1's commit (same audit-quality theme).

---

### #9 — Auto-extracted brand → ambiguity check (subsumed)

This is the same item as #2. Listed separately in 04-21 / 04-22 / 04-23 checkpoint pending lists; resolved by shipping #2.

---

### #10 — Graph visual polish

**Pending since:** 2026-04-20 checkpoint
**Description:** Force-directed graph nodes too tight together at default zoom; labels overlap. The interactive graph at `/dashboard/:auditId/graph` works but doesn't look as crisp as the Obsidian-style reference.

**Sizing:** M (~half day) — likely tweaks to `react-force-graph-2d` `linkDistance`, `chargeStrength`, and label-rendering threshold.

**Severity:** Low — SEO expert will spend most of their time on findings/scores, not graph aesthetics.

**Recommendation:** Defer. Not on the demo critical path.

---

### #11 — Drop redundant `tipr_score` JSON field

**File:** [backend/tipr_engine.py:681](../backend/tipr_engine.py#L681)
**Current code:** `"tipr_score": round(float(tipr_ranks[i]), 1),`

Literally the rank cast to float. `tipr_rank` already exists at line 680. Field is preserved for backward compat with earlier PDF templates.

**Sizing:** S — needs grep across backend + frontend + PDF templates to find consumers, then a deprecation pass.

**Severity:** Very low — confuses raw-JSON-export readers, no UI impact.

**Recommendation:** Defer to post-sprint cleanup.

---

### #12 — Store `score=None` on failed pillars

**File:** [backend/scoring.py](../backend/scoring.py) (failed-pillar handling)
**Current behavior:** When `scan_status="failed"`, pillar has no findings, so `calculate_score([]) == 100`. UI correctly branches on `scan_status` and renders "—" with "Scan incomplete" caption, hiding the stored 100.

**Issue:** Raw DB readers (admin queries, future analytics jobs) might be misled by the stored 100.

**Sizing:** S — change calculate_score signature or add a guard in the orchestrator.

**Severity:** Very low — UI is correct; only matters for raw-DB consumers.

**Recommendation:** Defer.

---

### #13 — GSC/GA4 OAuth (TIPR signal 4)

**Pending since:** sprint plan
**Description:** Adds Google Search Console + GA4 Data API integration to surface real crawl-frequency data for TIPR's signal 4.

**Sizing:** L — multi-day OAuth flow + token storage + per-URL inspection batching.

**Severity:** Med — premium-tier differentiator, but not blocking for SEO-expert demo (TIPR works on its first 3 signals already).

**Recommendation:** Defer beyond this sprint.

---

### #14 — 3-signal TIPR (backlinks)

**Pending since:** sprint plan
**Description:** Add backlink data (Ahrefs API or equivalent) as TIPR's third external signal.

**Sizing:** L — external API integration + cost/contract decision needed.

**Severity:** Med — improves TIPR fidelity, but not blocking for demo.

**Recommendation:** Defer beyond this sprint.

---

## What was scanned (for completeness)

- `docs/BACKLOG.md` — Open section (5 items, 4 already covered by buckets, 1 = Workstream C structurally deferred)
- `grep -rn 'TODO\|FIXME' backend/ frontend/src/` — 1 TODO (item #7)
- `WAIO-Checkpoint-2026-04-21.md` — "New from April 21" + "Outstanding"
- `WAIO-Checkpoint-2026-04-22.md` — "Outstanding" + "New from April 22"
- `WAIO-Checkpoint-2026-04-23.md` — "Pending from earlier" + "New items surfaced"
- Frontend grep for `enrichment_status`, `needs_industry_confirmation`, `no_data`, `timed_out`, `polling`, `failed`, `override_unverified`, `last_computed_status` — confirmed all state-machine strings stay in TypeScript code, never leak to user-visible UI as raw values
- Frontend grep for vendor-name leaks (`DataForSEO`, `Trafilatura`, `WeasyPrint`) — surfaced items #3, #5
- `backend/executive_summary_generator.py` for AI-filler-flavored phrases — only #8 (comprehensive)
- `backend/pdf_export_generator.py` lede paragraphs — read all 6, none pop as robotic
- `frontend/src/pages/Dashboard*.tsx` page headers — no robotic copy beyond #4, #6

## Recommendation summary

**Ship before SEO review (Day 4 buffer slot, ~half-day total):**
- #1 AI filler corpus token-match — Med-High severity, S sized
- #2 Auto-brand ambiguity check — Med severity, S sized
- #3 + #5 DataForSEO vendor-name leaks (one commit) — Med + Low severity, S sized
- #4 + #6 Dashboard banner copy (one commit) — Low-Med + Low severity, S sized
- #7 Stale TODO — XS sized, ship if removable
- #8 "comprehensive" copy nit — fold into #1's commit

**Defer to post-SEO-review:**
- #10–#14 (graph polish, tipr_score cleanup, score=None semantics, GSC/GA4 OAuth, 3-signal TIPR)

This list is honest. Sasha triages.
