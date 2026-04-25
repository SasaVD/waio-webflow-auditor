"""Regression tests for scoring.compile_scores coverage handling.

Workstream D1: the bot_detection module produces pillar results with
scan_status="bot_challenged". compile_scores must treat these the same
as "failed" — exclude from coverage so that a homepage fully blocked by
Cloudflare/Akamai produces overall_score=None, not a confidently-wrong 100.

No code change to scoring.py is required for D1: the existing check at
line 144 (`scan_statuses.get(pillar, "ok") == "ok"`) is an allow-list, so
any non-"ok" status (including "bot_challenged") is automatically excluded.
These tests lock that behavior against future regressions.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from scoring import compile_scores, PILLAR_WEIGHTS, MIN_COVERAGE_FOR_SCORE  # noqa: E402


def _bot_challenged_result() -> dict:
    """Mirror _bot_challenged_pillar_result shape from main.py."""
    return {
        "checks": {},
        "positive_findings": [],
        "findings": [],
        "scan_status": "bot_challenged",
    }


def _ok_result(findings: list | None = None) -> dict:
    return {
        "checks": {},
        "positive_findings": [],
        "findings": findings or [],
        "scan_status": "ok",
    }


def test_bot_challenged_all_pillars_suppresses_overall_score():
    """When every pillar is bot_challenged (the sched.com scenario), the overall
    score must be None and coverage_weight must be 0.0. This prevents the
    confidently-wrong 100/100 that audit 563145e4 produced."""
    bot = _bot_challenged_result()
    # css_js_res is a single pillar result that feeds both css_quality and js_bloat
    # sub-pillars — a single bot_challenged css_js_res marks both non-ok.
    result = compile_scores(
        html_res=bot, sd_res=bot, aeo_res=bot, css_js_res=bot,
        a11y_res=bot, rag_res=bot, agent_res=bot, data_res=bot,
        internal_linking_res=bot,
    )
    assert result["overall_score"] is None
    assert result["overall_label"] == "Scan incomplete"
    assert result["coverage_weight"] == 0.0
    for pillar_key in PILLAR_WEIGHTS:
        assert result["scan_statuses"][pillar_key] == "bot_challenged", (
            f"Expected {pillar_key}=bot_challenged, got {result['scan_statuses'][pillar_key]}"
        )


def test_bot_challenged_mixed_with_one_ok_pillar_still_suppresses():
    """If only semantic_html (weight 0.12) is ok and the other 9 are
    bot_challenged, coverage = 0.12 < MIN_COVERAGE_FOR_SCORE=0.70, so the
    overall must still be suppressed. Guards against the case where a partial
    bot challenge (some auditors succeed on cached assets) inflates the score."""
    bot = _bot_challenged_result()
    ok = _ok_result()
    result = compile_scores(
        html_res=ok,      # ok, weight 0.12
        sd_res=bot, aeo_res=bot, css_js_res=bot, a11y_res=bot,
        rag_res=bot, agent_res=bot, data_res=bot, internal_linking_res=bot,
    )
    assert result["overall_score"] is None, (
        f"Expected None (coverage 0.12 < {MIN_COVERAGE_FOR_SCORE}), got {result['overall_score']}"
    )
    assert result["coverage_weight"] == 0.12
    assert result["scan_statuses"]["semantic_html"] == "ok"
    assert result["scan_statuses"]["structured_data"] == "bot_challenged"


def test_bot_challenged_is_treated_same_as_failed_in_coverage():
    """scan_status='failed' (from _failed_pillar_result, existing BUG-1 plumbing)
    and scan_status='bot_challenged' (from _bot_challenged_pillar_result, new in
    D1) must both exclude the pillar from coverage. Locks the behavior that the
    check at scoring.py:144 is an allow-list on 'ok', not a deny-list."""
    bot = _bot_challenged_result()
    failed = {**bot, "scan_status": "failed"}
    ok = _ok_result()

    result_all_bot = compile_scores(
        html_res=bot, sd_res=bot, aeo_res=bot, css_js_res=bot,
        a11y_res=bot, rag_res=bot, agent_res=bot, data_res=bot,
        internal_linking_res=bot,
    )
    result_all_failed = compile_scores(
        html_res=failed, sd_res=failed, aeo_res=failed, css_js_res=failed,
        a11y_res=failed, rag_res=failed, agent_res=failed, data_res=failed,
        internal_linking_res=failed,
    )

    # Both produce the same suppression outcome.
    assert result_all_bot["overall_score"] is None
    assert result_all_failed["overall_score"] is None
    assert result_all_bot["coverage_weight"] == result_all_failed["coverage_weight"] == 0.0

    # And mixing one ok with nine bot_challenged gives the same coverage as one
    # ok with nine failed.
    mixed_bot = compile_scores(
        html_res=ok, sd_res=bot, aeo_res=bot, css_js_res=bot, a11y_res=bot,
        rag_res=bot, agent_res=bot, data_res=bot, internal_linking_res=bot,
    )
    mixed_failed = compile_scores(
        html_res=ok, sd_res=failed, aeo_res=failed, css_js_res=failed, a11y_res=failed,
        rag_res=failed, agent_res=failed, data_res=failed, internal_linking_res=failed,
    )
    assert mixed_bot["coverage_weight"] == mixed_failed["coverage_weight"] == 0.12


def test_all_ok_pillars_produce_normal_overall_score():
    """Negative control: ensure D1 doesn't break the happy path. When every
    pillar scans ok with zero findings, overall should be 100 (no deductions)."""
    ok = _ok_result()
    result = compile_scores(
        html_res=ok, sd_res=ok, aeo_res=ok, css_js_res=ok, a11y_res=ok,
        rag_res=ok, agent_res=ok, data_res=ok, internal_linking_res=ok,
    )
    assert result["overall_score"] == 100
    assert result["overall_label"] == "Excellent"
    assert result["coverage_weight"] == 1.0
    assert all(s == "ok" for s in result["scan_statuses"].values())


# ─── Workstream D4: non-ok pillar scoring inversion ───
#
# Pre-D4: calculate_score(findings=[]) returns 100. Auditors that crashed or
# were bot-challenged emit empty findings + scan_status="failed" — so the raw
# scores dict showed 100 even though no analysis ran. Coverage renormalization
# (D1) suppressed the OVERALL score, but per-pillar consumers (exec summary,
# PDF tiles, dashboard cards) read scores[pillar] directly and saw a fake 100.
# D4 zeros these out at compile time so every consumer sees a safe integer.


def test_failed_pillar_scores_zero_not_hundred():
    """Regression: auditor exception path (scan_status='failed') used to emit
    score=100 because calculate_score with empty findings returns 100. D4
    forces score=0 for any non-ok pillar so downstream consumers don't see
    a confidently-wrong 'perfect' pillar."""
    failed = {"checks": {}, "findings": [], "positive_findings": [], "scan_status": "failed"}
    ok = {"checks": {}, "findings": [], "positive_findings": [], "scan_status": "ok"}
    result = compile_scores(
        html_res=ok, sd_res=failed, aeo_res=failed, css_js_res=failed,
        a11y_res=failed, rag_res=failed, agent_res=failed, data_res=failed,
        internal_linking_res=failed,
    )
    assert result["scores"]["structured_data"] == 0
    assert result["scores"]["semantic_html"] == 100  # ok pillar retains calculate_score result
    assert result["scores"]["accessibility"] == 0
    assert result["labels"]["structured_data"] == "Scan incomplete"
    assert result["labels"]["semantic_html"] != "Scan incomplete"


def test_bot_challenged_pillar_scores_zero():
    """All pillars bot_challenged → every score is 0, overall is None, labels
    are 'Scan incomplete'."""
    bot = {"checks": {}, "findings": [], "positive_findings": [], "scan_status": "bot_challenged"}
    result = compile_scores(
        html_res=bot, sd_res=bot, aeo_res=bot, css_js_res=bot,
        a11y_res=bot, rag_res=bot, agent_res=bot, data_res=bot,
        internal_linking_res=bot,
    )
    assert all(result["scores"][k] == 0 for k in result["scores"])
    assert all(result["labels"][k] == "Scan incomplete" for k in result["labels"])
    assert result["overall_score"] is None


def test_incomplete_pillar_scores_zero():
    """scan_status='incomplete' (partial auditor run) also scores 0."""
    incomplete = {"checks": {}, "findings": [], "positive_findings": [], "scan_status": "incomplete"}
    ok = {"checks": {}, "findings": [], "positive_findings": [], "scan_status": "ok"}
    result = compile_scores(
        html_res=ok, sd_res=ok, aeo_res=ok, css_js_res=ok, a11y_res=incomplete,
        rag_res=ok, agent_res=ok, data_res=ok, internal_linking_res=ok,
    )
    assert result["scores"]["accessibility"] == 0
    assert result["labels"]["accessibility"] == "Scan incomplete"


def test_css_js_paired_non_ok_zeroes_both_subpillars():
    """css_quality and js_bloat share a single auditor (css_js_res). When that
    auditor fails, both sub-pillars must score 0 — regression lock."""
    css_js_failed = {"checks": {}, "findings": [], "positive_findings": [], "scan_status": "failed"}
    ok = {"checks": {}, "findings": [], "positive_findings": [], "scan_status": "ok"}
    result = compile_scores(
        html_res=ok, sd_res=ok, aeo_res=ok, css_js_res=css_js_failed,
        a11y_res=ok, rag_res=ok, agent_res=ok, data_res=ok, internal_linking_res=ok,
    )
    assert result["scores"]["css_quality"] == 0
    assert result["scores"]["js_bloat"] == 0
    assert result["labels"]["css_quality"] == "Scan incomplete"
    assert result["labels"]["js_bloat"] == "Scan incomplete"


def test_ok_pillars_retain_calculate_score_result():
    """Negative control: D4 must not change ok-pillar scoring. With zero
    findings, score = 100 as before."""
    ok = {"checks": {}, "findings": [], "positive_findings": [], "scan_status": "ok"}
    result = compile_scores(
        html_res=ok, sd_res=ok, aeo_res=ok, css_js_res=ok, a11y_res=ok,
        rag_res=ok, agent_res=ok, data_res=ok, internal_linking_res=ok,
    )
    assert result["overall_score"] == 100
    assert all(v == 100 for v in result["scores"].values())
