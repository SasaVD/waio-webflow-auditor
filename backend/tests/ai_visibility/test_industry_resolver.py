"""Unit tests for resolve_industry() — Workstream D3 (Contract 5).

The resolver replaces the silent ``"business services"`` fallback that caused
the 2026-04-23 sched.com incident (an event-management SaaS benchmarked against
Accenture / McKinsey / Deloitte because ``detected_industry=None`` and the
fallback kicked in).

Priority order (documented in :func:`resolve_industry` and the D3.0 contract):
  1. ``target_industry``  → ``(target_industry, "user_declared")``
  2. ``detected_industry`` → ``(detected_industry, "nlp_detected")``
  3. both empty           → ``(None, None)`` — caller MUST render
     "Needs attention" and skip prompt generation.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai_visibility.engine import resolve_industry


def test_user_declared_takes_precedence_over_nlp():
    """target_industry always wins, even when NLP detected something."""
    value, source = resolve_industry(
        target_industry="/Arts & Entertainment/Events",
        detected_industry="/Business & Industrial",
    )
    assert value == "/Arts & Entertainment/Events"
    assert source == "user_declared"


def test_user_declared_when_nlp_none():
    """target_industry used when NLP returns None."""
    value, source = resolve_industry(
        target_industry="/Arts & Entertainment/Events",
        detected_industry=None,
    )
    assert value == "/Arts & Entertainment/Events"
    assert source == "user_declared"


def test_nlp_detected_when_no_user_override():
    """Falls back to NLP detected_industry when user did not declare."""
    value, source = resolve_industry(
        target_industry=None,
        detected_industry="/Business & Industrial/Advertising & Marketing",
    )
    assert value == "/Business & Industrial/Advertising & Marketing"
    assert source == "nlp_detected"


def test_both_none_returns_none_tuple_no_fallback():
    """CRITICAL regression test: sched.com incident.

    When both target and detected are None, the resolver MUST return
    (None, None) — NEVER "business services" or any other hardcoded
    fallback. The caller surfaces a "Needs attention" state and skips
    prompt generation entirely.
    """
    value, source = resolve_industry(
        target_industry=None,
        detected_industry=None,
    )
    assert value is None
    assert source is None
    # Explicit anti-regression guard: the string that caused the sched.com
    # incident must never leak through resolve_industry.
    assert value != "business services"
    assert value != "business_services"


def test_empty_string_target_treated_as_none():
    """Empty-string target_industry (e.g. from a blank form field) must not
    count as user-declared; it is effectively "not provided"."""
    value, source = resolve_industry(
        target_industry="",
        detected_industry=None,
    )
    assert value is None
    assert source is None


def test_whitespace_only_target_treated_as_none():
    """Whitespace-only target_industry is also treated as not provided —
    users who accidentally type spaces should get the NLP fallback or
    the "Needs attention" state, not a bogus industry of spaces."""
    value, source = resolve_industry(
        target_industry="   ",
        detected_industry=None,
    )
    assert value is None
    assert source is None


def test_empty_string_target_with_nlp_uses_nlp():
    """If the form field is blank but NLP detected something, fall through
    to the NLP value rather than honoring the blank as user intent."""
    value, source = resolve_industry(
        target_industry="",
        detected_industry="/Finance",
    )
    assert value == "/Finance"
    assert source == "nlp_detected"


def test_target_industry_is_trimmed():
    """Leading/trailing whitespace around a real target_industry is stripped
    so it matches exact strings downstream (prompt templates compare leaves)."""
    value, source = resolve_industry(
        target_industry="  /Arts & Entertainment/Events  ",
        detected_industry=None,
    )
    assert value == "/Arts & Entertainment/Events"
    assert source == "user_declared"


def test_empty_string_detected_industry_also_treated_as_none():
    """Defense-in-depth: if NLP stores an empty string instead of None,
    still resolve to (None, None) — consistent with the target side."""
    value, source = resolve_industry(
        target_industry=None,
        detected_industry="",
    )
    assert value is None
    assert source is None
