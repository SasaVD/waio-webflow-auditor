"""Tests for AI Visibility prompt builder."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai_visibility.prompts import build_prompts
from ai_visibility.schema import PromptTemplate


def test_returns_four_prompts():
    prompts = build_prompts(
        industry="/Business & Industrial/Advertising & Marketing",
        top_entity="web design",
        brand_name="Belt Creative",
    )
    assert len(prompts) == 4


def test_first_three_are_discovery():
    prompts = build_prompts(
        industry="/Business & Industrial/Advertising & Marketing",
        top_entity="web design",
        brand_name="Belt Creative",
    )
    for p in prompts[:3]:
        assert p.category == "discovery"


def test_fourth_is_reputation():
    prompts = build_prompts(
        industry="/Business & Industrial/Advertising & Marketing",
        top_entity="web design",
        brand_name="Belt Creative",
    )
    assert prompts[3].category == "reputation"


def test_reputation_prompt_contains_brand_name():
    prompts = build_prompts(
        industry="/Finance/Personal Finance",
        top_entity="insurance",
        brand_name="Acme Corp",
    )
    assert "Acme Corp" in prompts[3].text


def test_discovery_prompts_contain_industry_leaf():
    prompts = build_prompts(
        industry="/Business & Industrial/Advertising & Marketing",
        top_entity="web design",
        brand_name="Test Co",
    )
    texts = " ".join(p.text for p in prompts[:3]).lower()
    assert "advertising" in texts or "marketing" in texts


def test_ids_are_sequential():
    prompts = build_prompts(
        industry="/Tech",
        top_entity="software",
        brand_name="X",
    )
    assert [p.id for p in prompts] == [1, 2, 3, 4]


def test_prompts_are_prompt_template_instances():
    prompts = build_prompts(
        industry="/Tech",
        top_entity="software",
        brand_name="X",
    )
    for p in prompts:
        assert isinstance(p, PromptTemplate)


def test_fallback_when_no_top_entity():
    prompts = build_prompts(
        industry="/Health",
        top_entity=None,
        brand_name="HealthCo",
    )
    assert len(prompts) == 4
    for p in prompts[:3]:
        assert len(p.text) > 10


def test_fallback_when_no_industry():
    prompts = build_prompts(
        industry=None,
        top_entity="web design",
        brand_name="Studio X",
    )
    assert len(prompts) == 4
    assert "Studio X" in prompts[3].text
