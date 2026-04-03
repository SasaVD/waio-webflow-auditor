"""
Shared utility functions for WAIO auditors.
"""
import re
from typing import Dict, List
from bs4 import Tag


def get_css_selector(element: Tag, max_depth: int = 5) -> str:
    """Generate a readable CSS selector path for a BeautifulSoup element.

    Walks up the DOM tree up to *max_depth* levels, producing a selector
    like ``body > main > div:nth-of-type(3) > h3``.

    If an element has an ``id``, the walk stops early (IDs are unique).
    """
    parts: List[str] = []
    current = element

    for _ in range(max_depth):
        if current is None or not hasattr(current, "name") or current.name is None:
            break
        if current.name == "[document]":
            break

        selector = current.name

        # ID shortcut — unique, stop here
        el_id = current.get("id")
        if el_id and isinstance(el_id, str):
            parts.insert(0, f"{current.name}#{el_id}")
            break

        # Disambiguate among same-tag siblings with nth-of-type
        parent = current.parent
        if parent and hasattr(parent, "name") and parent.name and parent.name != "[document]":
            siblings = [
                s for s in parent.children
                if isinstance(s, Tag) and s.name == current.name
            ]
            if len(siblings) > 1:
                idx = siblings.index(current) + 1
                selector = f"{current.name}:nth-of-type({idx})"

        parts.insert(0, selector)
        current = parent

    return " > ".join(parts)


def truncate_html(html_str: str, max_len: int = 200) -> str:
    """Truncate an HTML snippet string to *max_len* characters."""
    if len(html_str) <= max_len:
        return html_str
    return html_str[:max_len] + "…"


def get_element_location(element: Tag) -> str:
    """Return a human-readable location description for an element.

    Examples: ``"navigation section"``, ``"main content"``,
    ``"section: Our Services"``, ``"footer section"``.
    """
    landmarks = ["header", "nav", "main", "footer", "aside"]
    for landmark in landmarks:
        if element.find_parent(landmark):
            if landmark == "nav":
                return "navigation section"
            if landmark == "main":
                # Try to find nearest heading for more context
                section = element.find_parent("section")
                if section:
                    heading = section.find(re.compile(r"^h[1-6]$"))
                    if heading:
                        text = heading.get_text(strip=True)[:50]
                        return f"main content, section: {text}"
                return "main content"
            return f"{landmark} section"

    section = element.find_parent("section")
    if section:
        heading = section.find(re.compile(r"^h[1-6]$"))
        if heading:
            text = heading.get_text(strip=True)[:50]
            return f"section: {text}"
        return "unnamed section"

    article = element.find_parent("article")
    if article:
        return "article content"

    return "page content"


def make_element_entry(element: Tag, max_snippet: int = 200) -> Dict[str, str]:
    """Build a single element entry dict for a finding's ``elements`` list.

    Returns ``{"selector": ..., "html_snippet": ..., "location": ...}``.
    """
    return {
        "selector": get_css_selector(element),
        "html_snippet": truncate_html(str(element), max_snippet),
        "location": get_element_location(element),
    }
