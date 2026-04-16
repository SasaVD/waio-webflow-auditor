"""Build the 4 canonical prompts for AI Visibility live engine tests."""
from .schema import PromptTemplate


def _extract_industry_leaf(industry: str | None) -> str:
    """Extract the leaf category from a hierarchical NLP classification path.

    Example: "/Business & Industrial/Advertising & Marketing" → "advertising & marketing"
    """
    if not industry:
        return "business services"
    parts = industry.strip("/").split("/")
    return parts[-1].lower() if parts else "business services"


def build_prompts(
    industry: str | None,
    top_entity: str | None,
    brand_name: str,
) -> list[PromptTemplate]:
    """Build 4 canonical prompts: 3 discovery + 1 reputation.

    Discovery prompts use the detected industry leaf + top NLP entity.
    The reputation prompt uses the brand name directly.
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
