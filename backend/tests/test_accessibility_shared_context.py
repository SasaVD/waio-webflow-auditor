"""Workstream E — audit-scoped shared browser context.

Architectural lock for the accessibility-Playwright addendum:

  - When run_accessibility_audit receives a shared_context, it MUST call
    shared_context.new_page() and MUST NOT call browser.new_context().
  - When run_accessibility_audit receives a shared_context, it MUST NOT close
    the context (caller owns lifecycle). It SHOULD close the page it created.
  - When no shared_context is provided, behaviour is unchanged: the auditor
    opens its own context with the legacy hardcoded UA + viewport and closes
    it in the finally block.
  - Gating signal (test_shared_context_lets_accessibility_inherit_homepage_cookies):
    cookies stamped into the shared_context by the homepage Playwright fetch
    are visible to accessibility's page.context.cookies() at goto time.

Original incident: sched.com audit 0e2b5690-5de5-4228-90a5-b8c376991aa9
(2026-04-26) — homepage Playwright fetch passed Cloudflare's check, but
accessibility's separate Playwright timed out at Page.goto: Timeout 15000ms
exceeded because the second context started fresh with no cookies.
"""
import asyncio
import sys
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import accessibility_auditor  # noqa: E402


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─── Fakes ─────────────────────────────────────────────────────────────────

class _FakePage:
    """Stub Playwright Page. Accepts goto / load-state / press / evaluate /
    keyboard / close, records its parent context, and lets tests assert on
    cookies visible at goto time."""

    def __init__(self, parent_context):
        self.context = parent_context
        self.url = "about:blank"
        self.closed = False
        self.cookies_seen_at_goto = None
        self.keyboard = self  # so page.keyboard.press(...) routes here

    async def goto(self, url, **_kwargs):
        self.url = url
        # Capture the cookies present at the moment accessibility navigates.
        # This is the gating contract: shared_context cookies inherit here.
        self.cookies_seen_at_goto = await self.context.cookies()
        return None

    async def evaluate(self, _script):
        return 0

    async def press(self, _key):
        pass

    async def close(self):
        self.closed = True


class _FakeContext:
    """Stub Playwright BrowserContext. Tracks new_page / close calls and
    stores a cookie jar so tests can stamp cookies and assert on inheritance."""

    def __init__(self, name="ctx"):
        self.name = name
        self._cookies = []
        self.new_page_count = 0
        self.close_called = False
        self.created_pages = []

    def stamp_cookie(self, name, value):
        """Helper for tests: simulate the homepage fetch dropping a CF cookie
        into the live context. Real Playwright populates this via response."""
        self._cookies.append({"name": name, "value": value})

    async def new_page(self):
        self.new_page_count += 1
        page = _FakePage(self)
        self.created_pages.append(page)
        return page

    async def cookies(self):
        return list(self._cookies)

    async def close(self):
        self.close_called = True


class _FakeBrowser:
    def __init__(self):
        self.new_context_count = 0
        self.contexts_created = []

    async def new_context(self, **_kwargs):
        self.new_context_count += 1
        ctx = _FakeContext(name=f"own_{self.new_context_count}")
        self.contexts_created.append(ctx)
        return ctx


def _patch_check_internals(monkeypatch):
    """Stub the per-check helpers so tests don't need a real Playwright page.
    The shared-context contract is about WHICH context the page comes from;
    what the checks do is irrelevant to that contract."""
    async def _ok_axe(_page):
        return {"status": "pass", "details": {}, "positive_message": "axe ok"}

    async def _ok_touch(_page):
        return {"status": "pass", "details": {}}

    async def _ok_focus(_page):
        return {"status": "pass", "details": {}}

    async def _ok_keyboard(_page):
        return {"status": "pass", "details": {}}

    monkeypatch.setattr(accessibility_auditor, "check_axe_scan", _ok_axe)
    monkeypatch.setattr(accessibility_auditor, "check_touch_targets", _ok_touch)
    monkeypatch.setattr(accessibility_auditor, "check_focus_styles", _ok_focus)
    monkeypatch.setattr(accessibility_auditor, "check_keyboard_traps", _ok_keyboard)


# ─── Tests ─────────────────────────────────────────────────────────────────

def test_run_accessibility_audit_uses_shared_context_new_page(monkeypatch):
    """Contract 3: when given a shared_context, the auditor calls
    shared_context.new_page() and does NOT call browser.new_context()."""
    _patch_check_internals(monkeypatch)

    fake_browser = _FakeBrowser()

    async def _fake_get_browser():
        return fake_browser

    monkeypatch.setattr(accessibility_auditor, "get_browser", _fake_get_browser)

    shared = _FakeContext(name="shared_audit_context")

    result = _run(
        accessibility_auditor.run_accessibility_audit(
            "https://example.com",
            shared_context=shared,
        )
    )

    assert result["scan_status"] == "ok"
    assert shared.new_page_count == 1, "should have used shared_context.new_page()"
    assert fake_browser.new_context_count == 0, (
        "must NOT call browser.new_context() when shared_context is provided"
    )


def test_run_accessibility_audit_legacy_path_unchanged(monkeypatch):
    """Negative: no shared_context → current behaviour preserved.
    Auditor calls browser.new_context() and closes it in finally."""
    _patch_check_internals(monkeypatch)

    fake_browser = _FakeBrowser()

    async def _fake_get_browser():
        return fake_browser

    monkeypatch.setattr(accessibility_auditor, "get_browser", _fake_get_browser)

    result = _run(
        accessibility_auditor.run_accessibility_audit("https://example.com")
    )

    assert result["scan_status"] == "ok"
    assert fake_browser.new_context_count == 1, (
        "legacy path should call browser.new_context() exactly once"
    )
    own_ctx = fake_browser.contexts_created[0]
    assert own_ctx.close_called is True, (
        "legacy path must close its own context in finally"
    )


def test_run_accessibility_audit_does_not_close_shared_context(monkeypatch):
    """Contract 3: with shared_context, the auditor must NOT close the
    context. It should close only the page it created."""
    _patch_check_internals(monkeypatch)

    # get_browser must NOT be called at all when shared_context is provided.
    def _must_not_call():
        raise AssertionError(
            "get_browser called despite shared_context being provided"
        )

    monkeypatch.setattr(accessibility_auditor, "get_browser", _must_not_call)

    shared = _FakeContext(name="shared_audit_context")

    result = _run(
        accessibility_auditor.run_accessibility_audit(
            "https://example.com",
            shared_context=shared,
        )
    )

    assert result["scan_status"] == "ok"
    assert shared.close_called is False, (
        "auditor must not close the shared_context — caller owns lifecycle"
    )
    # Page is owned by the audit, must close.
    assert len(shared.created_pages) == 1
    assert shared.created_pages[0].closed is True, (
        "auditor should close the page it created on the shared context"
    )


def test_shared_context_lets_accessibility_inherit_homepage_cookies(monkeypatch):
    """GATING TEST — Workstream E architectural lock.

    Simulates the full audit flow:
      1. Orchestrator opens audit_context.
      2. Homepage fetch_page stamps __cf_bm cookie into audit_context (this
         is what real Playwright does after CF clears the homepage challenge).
      3. accessibility_auditor.run_accessibility_audit is invoked with
         shared_context=audit_context.
      4. ASSERT: at the moment accessibility's page.goto runs, the page's
         context.cookies() contains the stamped CF cookie.

    If this assertion holds → shared context worked, accessibility inherited
    the homepage's cleared session.

    If it fails → the orchestrator wired the wrong context, or accessibility
    opened a fresh one anyway. Either is the bug Workstream E exists to fix.
    """
    _patch_check_internals(monkeypatch)

    # Step 1: simulate orchestrator-opened audit context.
    audit_context = _FakeContext(name="audit_scoped_context")

    # Step 2: simulate the homepage Playwright fetch having dropped a CF
    # clearance cookie into the live context. This is what real fetch_page
    # would do when shared_context=audit_context is passed in and CF clears
    # the challenge — the cookie persists on the BrowserContext object.
    audit_context.stamp_cookie("__cf_bm", "cleared")
    audit_context.stamp_cookie("cf_clearance", "abcd1234")

    # Sentinel: get_browser MUST NOT be called when shared_context is provided.
    # That would mean accessibility opened a fresh, cookie-less context —
    # exactly the bug.
    def _must_not_call():
        raise AssertionError(
            "Accessibility opened its own context — shared_context plumbing broken"
        )

    monkeypatch.setattr(accessibility_auditor, "get_browser", _must_not_call)

    # Step 3: run accessibility with the shared context.
    _run(
        accessibility_auditor.run_accessibility_audit(
            "https://sched.com",
            shared_context=audit_context,
        )
    )

    # Step 4: assert the page used by accessibility saw the stamped cookies
    # at goto time. This is the deterministic architectural contract.
    assert len(audit_context.created_pages) == 1
    page = audit_context.created_pages[0]
    seen = page.cookies_seen_at_goto
    assert seen is not None, "page.goto never ran on the shared context"

    cookie_names = {c["name"] for c in seen}
    assert "__cf_bm" in cookie_names, (
        "Cloudflare clearance cookie did NOT inherit from the homepage fetch — "
        "shared context contract is broken (this is the sched.com bug)"
    )
    assert "cf_clearance" in cookie_names, (
        "cf_clearance cookie did not inherit — shared context not threaded correctly"
    )
