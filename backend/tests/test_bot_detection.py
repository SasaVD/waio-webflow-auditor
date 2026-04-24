"""Unit tests for bot_detection.detect_bot_challenge.

Workstream D1: detects bot-challenge / verification-wall pages returned by
Cloudflare, Akamai, DataDome, PerimeterX (signature layer) plus a content
heuristic fallback for unknown vendors. The motivating incident is sched.com
audit 563145e4 where a Cloudflare Turnstile page produced a 100/100 score
because the auditors couldn't tell they were looking at a decoy.
"""
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from bot_detection import detect_bot_challenge, BotChallengeResult  # noqa: E402


# ---------------------------------------------------------------------------
# Signature-based detection (Approach 1) — high confidence
# ---------------------------------------------------------------------------


def test_cloudflare_turnstile_detected():
    html = '<html><body><div class="cf-turnstile"></div><h2 id="challenge-success-text">Success</h2></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(soup=soup, html=html, headers={}, cookies={})
    assert result.detected is True
    assert result.vendor == "cloudflare"
    assert "cf-turnstile" in result.signals


def test_cloudflare_challenge_success_text_detected():
    """This is the exact signal sched.com returned — locks the regression."""
    html = '<html><body><h2 id="challenge-success-text">Verifying you are human.</h2></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(soup=soup, html=html, headers={}, cookies={})
    assert result.detected is True
    assert result.vendor == "cloudflare"
    assert "challenge-success-text" in result.signals


def test_cloudflare_browser_verification_detected():
    html = '<html><body><div class="cf-browser-verification">Checking your browser</div></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(soup=soup, html=html, headers={}, cookies={})
    assert result.detected is True
    assert result.vendor == "cloudflare"


def test_cloudflare_cookie_detected():
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(
        soup=soup, html=html, headers={}, cookies={"__cf_bm": "abc", "cf_chl_opt": "x"}
    )
    assert result.detected is True
    assert result.vendor == "cloudflare"


def test_cloudflare_script_pattern_detected():
    html = '<html><body><script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(soup=soup, html=html, headers={}, cookies={})
    assert result.detected is True
    assert result.vendor == "cloudflare"


def test_akamai_bot_manager_detected():
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(
        soup=soup, html=html, headers={}, cookies={"_abck": "x", "bm_sz": "y"}
    )
    assert result.detected is True
    assert result.vendor == "akamai"


def test_datadome_captcha_detected():
    html = '<html><body><div id="datadome-captcha">Please verify</div></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(
        soup=soup, html=html, headers={}, cookies={"datadome": "x"}
    )
    assert result.detected is True
    assert result.vendor == "datadome"


def test_perimeterx_captcha_detected():
    html = '<html><body><div id="px-captcha"></div></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(
        soup=soup, html=html, headers={}, cookies={"_px": "x"}
    )
    assert result.detected is True
    assert result.vendor == "perimeterx"


# ---------------------------------------------------------------------------
# Content heuristic detection (Approach 2) — lower confidence fallback
# ---------------------------------------------------------------------------


def test_content_heuristic_low_word_high_scripts_keyword():
    """Challenge pages have tiny body text + many scripts + keyword markers."""
    html = """
    <html><body>
        <script>a</script><script>b</script><script>c</script>
        <script>d</script><script>e</script><script>f</script>
        <p>Verifying you are human. This may take a few seconds.</p>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(soup=soup, html=html, headers={}, cookies={})
    assert result.detected is True
    assert result.vendor == "unknown"
    assert "content_heuristic" in result.signals


def test_content_heuristic_access_denied_page():
    html = """
    <html><body>
        <script>1</script><script>2</script><script>3</script>
        <script>4</script><script>5</script><script>6</script>
        <h1>Access denied</h1><p>Error reference 1020</p>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(soup=soup, html=html, headers={}, cookies={})
    assert result.detected is True


# ---------------------------------------------------------------------------
# Negative cases (must NOT false-positive)
# ---------------------------------------------------------------------------


def test_clean_html_not_flagged():
    html = """
    <html><body>
        <header><nav>Home About Services</nav></header>
        <main>
            <h1>Welcome to Example Corp</h1>
            <p>We provide industry-leading widgets. Our team has been serving customers
            since 2010. Read about our mission, our products, and our commitment to quality.
            Contact us today to learn more about what we offer.</p>
            <section><h2>Our services</h2><p>We do many things well, here is a longer paragraph.</p></section>
        </main>
        <footer>© 2026 Example</footer>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(soup=soup, html=html, headers={}, cookies={})
    assert result.detected is False


def test_short_landing_page_not_flagged():
    """Legitimate splash/coming-soon pages have low words but normal script counts
    and real semantic landmarks. Must clear all three heuristic gates."""
    html = """
    <html><body>
        <header><nav>Home</nav></header>
        <main><h1>Coming soon</h1><p>Stay tuned.</p></main>
        <footer>©</footer>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(soup=soup, html=html, headers={}, cookies={})
    assert result.detected is False


def test_spa_with_many_scripts_but_real_content_not_flagged():
    """Heavy SPA marketing sites have many scripts but also >100 words and
    proper semantic structure — must not fire the heuristic."""
    body_text = " ".join(["meaningful content paragraph here."] * 30)
    scripts = "".join(f"<script>s{i}</script>" for i in range(15))
    html = f"""
    <html><body>
        {scripts}
        <header><nav>Home About</nav></header>
        <main><h1>Our product</h1><p>{body_text}</p></main>
        <footer>Copyright 2026</footer>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(soup=soup, html=html, headers={}, cookies={})
    assert result.detected is False


# ---------------------------------------------------------------------------
# Result shape contract
# ---------------------------------------------------------------------------


def test_result_shape_on_detection():
    html = '<html><body><div class="cf-turnstile"></div></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(soup=soup, html=html, headers={}, cookies={})
    assert isinstance(result, BotChallengeResult)
    assert result.detected is True
    assert isinstance(result.vendor, str)
    assert isinstance(result.signals, list) and len(result.signals) >= 1
    assert isinstance(result.confidence, float) and 0.0 <= result.confidence <= 1.0
    assert result.reason is not None


def test_result_shape_on_no_detection():
    html = (
        "<html><body><main><p>"
        + ("A real page with actual content goes here. " * 20)
        + "</p></main></body></html>"
    )
    soup = BeautifulSoup(html, "html.parser")
    result = detect_bot_challenge(soup=soup, html=html, headers={}, cookies={})
    assert result.detected is False
    assert result.vendor is None
    assert result.signals == []
    assert result.confidence == 0.0
