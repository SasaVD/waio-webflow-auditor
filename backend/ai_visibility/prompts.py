"""Build the 4 canonical prompts for AI Visibility live engine tests."""
from .schema import PromptTemplate


def _extract_industry_leaf(industry: str) -> str:
    """Extract the leaf category from a hierarchical NLP classification path.

    Example: "/Business & Industrial/Advertising & Marketing" → "advertising & marketing"

    Workstream D3: This helper now refuses to substitute a fallback leaf
    when ``industry`` is None or empty. Previously it silently returned
    ``"business services"``, which caused the sched.com incident
    2026-04-23 (event-management SaaS benchmarked against Accenture /
    McKinsey / Deloitte). The caller (engine.run_ai_visibility_analysis)
    is responsible for calling resolve_industry() first and short-circuiting
    to "needs_industry_confirmation" before this function is ever reached.
    """
    if not industry or not industry.strip():
        raise ValueError(
            "industry must be a non-empty string — callers must resolve "
            "through ai_visibility.engine.resolve_industry() and short-circuit "
            "on (None, None) rather than calling build_prompts with a missing "
            "industry. See Workstream D3 contract."
        )
    parts = industry.strip("/").split("/")
    leaf = parts[-1].lower() if parts else ""
    if not leaf:
        raise ValueError(
            f"industry path {industry!r} contained no usable leaf segment"
        )
    return leaf


def build_prompts(
    industry: str,
    top_entity: str | None,
    brand_name: str,
) -> list[PromptTemplate]:
    """Build 4 canonical prompts: 3 discovery + 1 reputation.

    Discovery prompts use the resolved industry leaf + top NLP entity.
    The reputation prompt uses the brand name directly.

    Raises:
        ValueError: if ``industry`` is None or empty. Callers must resolve
            through ``ai_visibility.engine.resolve_industry()`` and skip
            prompt generation when the resolver returns ``(None, None)``.
    """
    leaf = _extract_industry_leaf(industry)
    entity = top_entity.lower() if top_entity else leaf

    return [
        PromptTemplate(
            id=1,
            category="discovery",
            text=f"best {leaf} agencies",
        ),
        PromptTemplate(
            id=2,
            category="discovery",
            text=f"top {leaf} companies",
        ),
        PromptTemplate(
            id=3,
            category="discovery",
            text=f"{leaf} services for {entity}" if entity != leaf else f"{leaf} services for small business",
        ),
        PromptTemplate(
            id=4,
            category="reputation",
            text=f"{brand_name} reviews",
        ),
    ]
