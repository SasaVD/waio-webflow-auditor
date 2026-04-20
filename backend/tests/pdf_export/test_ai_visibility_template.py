"""Tests verifying the AI Visibility section renders competitive brands + status."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pdf_export_generator as pdf_mod


def test_mentions_exclude_reputation_prompt_4():
    """Reputation prompt (ID 4) mentions must not count toward discovery mentions."""
    report = {
        "ai_visibility": {
            "brand_name": "Belt Creative",
            "brand_name_source": "nlp",
            "live_test": {
                "engines": {
                    "chatgpt": {
                        "brand_mentioned_in": 1,  # inflated — counts reputation
                        "status": "ok",
                        "responses_by_prompt": {
                            "1": {"text": "Top agencies: Huge, Clay."},  # no mention
                            "2": {"text": "Consider Blue Fountain Media."},  # no mention
                            "3": {"text": "Big Drop Inc stands out."},  # no mention
                            "4": {"text": "Belt Creative is a Miami agency."},  # reputation
                        },
                    },
                    "claude": {
                        "brand_mentioned_in": 1,  # inflated — counts reputation
                        "status": "ok",
                        "responses_by_prompt": {
                            "1": {"text": "Top Miami agencies: Lounge Lizard."},
                            "4": {"text": "Belt Creative is known for..."},  # reputation
                        },
                    },
                },
                "prompts_used": [],
            },
            "mentions_database": {"total": 0},
        }
    }
    ctx = pdf_mod._build_ai_visibility(report)
    platforms_by_name = {p["name"]: p for p in ctx["platforms"]}
    assert platforms_by_name["ChatGPT"]["mentions"] == 0
    assert platforms_by_name["Claude"]["mentions"] == 0
    assert ctx["total_mentions"] == 0
    # Zero-state message triggers because discovery mentions are 0
    assert ctx["zero_state"] is True


def test_mentions_count_discovery_prompts_when_brand_appears():
    """If brand shows up in a discovery response, it should be counted."""
    report = {
        "ai_visibility": {
            "brand_name": "Belt Creative",
            "brand_name_source": "nlp",
            "live_test": {
                "engines": {
                    "chatgpt": {
                        "brand_mentioned_in": 0,  # stale
                        "status": "ok",
                        "responses_by_prompt": {
                            "1": {"text": "Miami agencies include Belt Creative and Huge."},
                            "2": {"text": "Blue Fountain Media."},
                            "4": {"text": "Belt Creative is well known."},
                        },
                    },
                },
                "prompts_used": [],
            },
            "mentions_database": {"total": 0},
        }
    }
    ctx = pdf_mod._build_ai_visibility(report)
    assert ctx["platforms"][0]["mentions"] == 1  # only prompt 1, not prompt 4
    assert ctx["total_mentions"] == 1


def test_brand_source_translates_internal_keys_to_plain_english():
    """'override' / 'nlp' are internal; the report must show a readable label."""
    override_report = {
        "ai_visibility": {
            "brand_name": "Belt Creative",
            "brand_name_source": "override",
            "live_test": {"engines": {}, "prompts_used": []},
            "mentions_database": {"total": 0},
        }
    }
    ctx = pdf_mod._build_ai_visibility(override_report)
    assert ctx["brand_source"] == "manually verified"

    nlp_report = {
        "ai_visibility": {
            "brand_name": "Belt Creative",
            "brand_name_source": "nlp",
            "live_test": {"engines": {}, "prompts_used": []},
            "mentions_database": {"total": 0},
        }
    }
    ctx_nlp = pdf_mod._build_ai_visibility(nlp_report)
    assert "auto-detected" in ctx_nlp["brand_source"]


def test_ai_visibility_template_avoids_internal_jargon():
    """Rendered HTML must not expose 'Source: override' internal strings."""
    report = {
        "url": "https://example.com",
        "ai_visibility": {
            "brand_name": "Belt Creative",
            "brand_name_source": "override",
            "live_test": {"engines": {"chatgpt": {"brand_mentioned_in": 0, "status": "ok"}}, "prompts_used": []},
            "mentions_database": {"total": 0},
        },
    }
    ctx = pdf_mod._prepare_context(report)
    template = pdf_mod._jinja_env.from_string(pdf_mod._TEMPLATE)
    html = template.render(**ctx)
    assert "Source: override" not in html
    assert "manually verified" in html


def test_extract_discovery_brands_filters_purchase_decision_stopwords():
    """Selection-guide labels like Budget/Timeline/Scope must not appear as brands."""
    engines = {
        "chatgpt": {
            "responses_by_prompt": {
                "1": {
                    "text": (
                        "When choosing an agency, consider these factors: "
                        "**Budget**, **Timeline**, **Scope**, and **Experience**. "
                        "Top agencies: **Lounge Lizard**, **Huge**."
                    )
                },
            }
        }
    }
    brands = pdf_mod._extract_discovery_brands(engines, own_brand="Belt Creative")
    names = {b["name"].lower() for b in brands}
    for junk in ("budget", "timeline", "scope", "experience"):
        assert junk not in names, f"Stopword '{junk}' must not appear as a brand"
    # Real brands must still survive
    assert "Lounge Lizard" in {b["name"] for b in brands}
    assert "Huge" in {b["name"] for b in brands}


def _render_html(report: dict) -> str:
    """Render just the template HTML (skip WeasyPrint) for fast assertion."""
    ctx = pdf_mod._prepare_context(report or {})
    template = pdf_mod._jinja_env.from_string(pdf_mod._TEMPLATE)
    return template.render(**ctx)


def _minimal_report_zero_state() -> dict:
    """Belt Creative shape: 4/4 reputation, 0 discovery mentions."""
    return {
        "url": "https://beltcreative.com",
        "overall_score": 62,
        "overall_label": "Needs Improvement",
        "ai_visibility": {
            "brand_name": "Belt Creative",
            "brand_name_source": "nlp",
            "live_test": {
                "engines": {
                    "chatgpt": {
                        "brand_mentioned_in": 0,
                        "status": "ok",
                        "responses_by_prompt": {
                            "1": {"text": "Top agencies include **Lounge Lizard**, **Huge**, **Clay**."},
                            "2": {"text": "Consider **Blue Fountain Media** and **Clay**."},
                            "3": {"text": "**Big Drop Inc** stands out."},
                            "4": {"text": "Belt Creative is a Miami agency."},  # reputation — excluded
                        },
                    },
                    "perplexity": {
                        "brand_mentioned_in": 0,
                        "status": "ok",
                        "responses_by_prompt": {
                            "1": {"text": "**Lounge Lizard** and **Huge** are strong picks."},
                        },
                    },
                },
                "prompts_used": [
                    {"id": 1, "category": "discovery", "text": "Top web design agencies in Miami?"},
                ],
            },
            "mentions_database": {"total": 0, "ai_search_volume": 0, "impressions": 0},
        },
    }


def test_template_renders_discovery_brands_section():
    html = _render_html(_minimal_report_zero_state())
    # Heading identifying the competitive-brands subsection
    assert "Brands Appearing in Your Category" in html
    # Competitor brands from the fixture
    assert "Lounge Lizard" in html
    assert "Huge" in html
    assert "Clay" in html
    assert "Blue Fountain Media" in html
    # Each brand should have a count badge next to it
    assert "×" in html or "mentions" in html.lower()


def test_template_renders_zero_state_status():
    html = _render_html(_minimal_report_zero_state())
    # Zero-state headline + body from _build_ai_visibility
    assert "Untapped AI discovery channel" in html


def test_template_excludes_own_brand_from_discovery_list():
    """Own brand must never appear in the discovery brands table."""
    report = _minimal_report_zero_state()
    # Add a response that mentions Belt Creative in a discovery prompt
    report["ai_visibility"]["live_test"]["engines"]["chatgpt"]["responses_by_prompt"]["1"]["text"] = (
        "Top agencies include **Belt Creative**, **Huge**, **Clay**."
    )
    html = _render_html(report)
    idx = html.find("Brands Appearing in Your Category")
    assert idx > 0
    block = html[idx:idx + 3000]
    assert "Huge" in block
    assert "Clay" in block
    # Own brand excluded by _extract_discovery_brands
    assert "<td>Belt Creative</td>" not in block


def test_template_omits_section_when_no_discovery_brands():
    """If every engine is empty, don't render the competitive-brands section."""
    report = _minimal_report_zero_state()
    # Wipe all responses
    for eng in report["ai_visibility"]["live_test"]["engines"].values():
        eng["responses_by_prompt"] = {}
    html = _render_html(report)
    assert "Brands Appearing in Your Category" not in html
