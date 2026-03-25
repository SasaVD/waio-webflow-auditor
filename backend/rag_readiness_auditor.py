"""
Pillar 7: RAG & Chunking Readiness Auditor
============================================
Analyzes whether the page content is structured in a way that is optimal
for Retrieval-Augmented Generation (RAG) systems and AI agents that
consume content in chunks.

All checks are deterministic and code-based. Zero LLM dependency.

References:
- LangChain Chunking Best Practices: https://python.langchain.com/docs/concepts/text_splitters/
- LlamaIndex Node Parsing: https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/
- Pinecone Chunking Strategies: https://www.pinecone.io/learn/chunking-strategies/
"""

from bs4 import BeautifulSoup, Tag  # type: ignore
import re
from typing import Dict, Any, List


def run_rag_readiness_audit(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    """Main entry point for Pillar 7 audit."""
    checks = {}
    positive_findings = []
    category_findings = []

    # Check 7.1: Section Length Analysis (Chunk Size Readiness)
    checks["section_length"] = check_section_length(soup)

    # Check 7.2: Self-Contained Sections (Context Independence)
    checks["context_independence"] = check_context_independence(soup)

    # Check 7.3: Content-to-Noise Ratio
    checks["content_noise_ratio"] = check_content_noise_ratio(soup)

    # Check 7.4: Heading-Content Pairing (Chunk Boundaries)
    checks["heading_content_pairing"] = check_heading_content_pairing(soup)

    # Check 7.5: List & Table Structure (Structured Data Chunks)
    checks["structured_content"] = check_structured_content(soup)

    # Check 7.6: Internal Linking Context
    checks["internal_link_context"] = check_internal_link_context(soup)

    for check_key, check_val in checks.items():
        if check_val.get("status") in ["pass", "info"]:
            if "positive_message" in check_val:
                positive_findings.append(check_val["positive_message"])
                check_val.pop("positive_message", None)
        if "findings" in check_val:
            category_findings.extend(check_val["findings"])

    return {
        "checks": checks,
        "positive_findings": positive_findings,
        "findings": category_findings
    }


def create_finding(severity: str, description: str, recommendation: str, reference: str, why_it_matters: str = "") -> Dict[str, str]:
    finding = {
        "severity": severity,
        "description": description,
        "recommendation": recommendation,
        "reference": reference
    }
    if why_it_matters:
        finding["why_it_matters"] = why_it_matters
    return finding


def _get_text_sections(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Extract logical content sections from the page.
    A section is defined as a heading element followed by its content
    until the next heading of the same or higher level.
    """
    sections = []
    body = soup.find('body')
    if not body:
        return sections

    headings = body.find_all(re.compile(r'^h[1-6]$'))

    if not headings:
        # No headings: treat entire body text as one section
        text = body.get_text(separator=' ', strip=True)
        if text:
            sections.append({
                "heading": None,
                "heading_level": 0,
                "text": text,
                "word_count": len(text.split())
            })
        return sections

    for i, heading in enumerate(headings):
        heading_text = heading.get_text(strip=True)
        heading_level = int(heading.name[1])

        # Collect text between this heading and the next heading
        content_parts = []
        sibling = heading.next_sibling
        while sibling:
            if isinstance(sibling, Tag):
                if sibling.name and re.match(r'^h[1-6]$', str(sibling.name)):  # type: ignore
                    break
                # Also check if the sibling contains a heading
                inner_heading = sibling.find(re.compile(r'^h[1-6]$'))  # type: ignore
                if inner_heading:
                    break
                content_parts.append(sibling.get_text(separator=' ', strip=True))  # type: ignore
            sibling = sibling.next_sibling

        section_text = ' '.join(content_parts).strip()
        word_count = len(section_text.split()) if section_text else 0

        sections.append({
            "heading": heading_text,
            "heading_level": heading_level,
            "text": section_text,
            "word_count": word_count
        })

    return sections


def check_section_length(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Check 7.1: Section Length Analysis
    RAG systems typically chunk content into 100-500 word segments.
    Sections that are too short (<50 words) lack context.
    Sections that are too long (>800 words) are hard to chunk cleanly.
    """
    sections = _get_text_sections(soup)
    findings = []

    if not sections:
        findings.append(create_finding(
            "high",
            "No identifiable content sections found on the page.",
            "Structure your content with clear heading-content pairs. Each section should have a heading (H2-H4) followed by 100-300 words of content.",
            "https://www.pinecone.io/learn/chunking-strategies/",
            "RAG systems rely on well-defined content sections to create meaningful chunks. Pages without clear sections produce poor retrieval results."
        ))
        return {"status": "fail", "details": {"section_count": 0}, "findings": findings}

    too_short = []
    too_long = []
    optimal = []

    for s in sections:
        wc = s["word_count"]
        if wc < 30:
            too_short.append(s)
        elif wc > 800:
            too_long.append(s)
        else:
            optimal.append(s)

    avg_words = sum(s["word_count"] for s in sections) / len(sections) if sections else 0

    if too_long:
        findings.append(create_finding(
            "high",
            f"Found {len(too_long)} section(s) exceeding 800 words. Longest section has {max(s['word_count'] for s in too_long)} words.",
            "Break up long sections into smaller subsections of 100-300 words each, each with its own descriptive heading.",
            "https://keomarketing.com/query-fan-out-b2b-seo-strategy/",
            "AI models fan out a single user query into 7-12 sub-queries (Stanford HAI). Well-defined content sections are essential for your content to be retrieved and cited across these sub-queries."
        ))

    short_with_headings = [s for s in too_short if s["heading"]]
    if len(short_with_headings) > 3:
        findings.append(create_finding(
            "medium",
            f"Found {len(short_with_headings)} sections with fewer than 30 words. These sections lack sufficient context for standalone retrieval.",
            "Expand thin sections with more descriptive content, or merge them with adjacent sections under a shared heading.",
            "https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/",
            "Very short content sections produce chunks that lack enough context for an AI agent to generate a meaningful answer."
        ))

    details = {
        "section_count": len(sections),
        "avg_word_count": round(float(avg_words), 1),  # type: ignore
        "optimal_sections": len(optimal),
        "too_short": len(too_short),
        "too_long": len(too_long)
    }

    if not findings:
        return {
            "status": "pass",
            "details": details,
            "positive_message": f"Content is well-segmented into {len(sections)} sections with an average of {round(float(avg_words))} words per section — optimal for RAG chunking."  # type: ignore
        }

    return {"status": "fail", "details": details, "findings": findings}


def check_context_independence(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Check 7.2: Self-Contained Sections (Context Independence)
    Each section should be understandable without reading the previous section.
    Detects sections that start with pronouns or references that require prior context.
    """
    sections = _get_text_sections(soup)
    findings = []

    dependent_sections = []
    context_dependent_starters = [
        r'^(This|These|That|Those|It|Its|They|Their|Them)\s',
        r'^(As mentioned|As noted|As discussed|As stated|See above|Continued from)',
        r'^(Additionally|Furthermore|Moreover|Also|In addition)\s',
    ]

    for s in sections:
        text = s.get("text", "").strip()
        if not text or s["word_count"] < 10:
            continue

        # Check first sentence
        first_sentence = text.split('.')[0] if '.' in text else text[:200]

        for pattern in context_dependent_starters:
            if re.match(pattern, first_sentence, re.IGNORECASE):
                dependent_sections.append({
                    "heading": s.get("heading", "Untitled"),
                    "starter": first_sentence[:80]
                })
                break

    if len(dependent_sections) > 3:
        findings.append(create_finding(
            "medium",
            f"Found {len(dependent_sections)} sections that begin with context-dependent language (e.g., 'This', 'These', 'As mentioned').",
            "Rewrite section openings to be self-contained. Instead of 'This service includes...', write 'The [Product Name] service includes...' so each section can stand alone when retrieved by an AI agent.",
            "https://python.langchain.com/docs/concepts/text_splitters/",
            "When an AI agent retrieves a single chunk, context-dependent openings produce confusing or incomplete answers because the agent does not have the preceding section."
        ))

    details = {
        "sections_analyzed": len(sections),
        "context_dependent_sections": len(dependent_sections)
    }

    if not findings:
        return {
            "status": "pass",
            "details": details,
            "positive_message": "Content sections are largely self-contained — each section can be understood independently, which is ideal for RAG retrieval."
        }

    return {"status": "fail", "details": details, "findings": findings}


def check_content_noise_ratio(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Check 7.3: Content-to-Noise Ratio
    Measures the ratio of meaningful content to boilerplate/navigation/footer text.
    High noise makes chunking less effective.
    """
    findings = []
    body = soup.find('body')
    if not body:
        return {"status": "fail", "details": {}, "findings": [create_finding(
            "high", "No <body> element found.", "Ensure the page has a valid HTML body.", "https://www.w3.org/TR/html5/"
        )]}

    # Get main content area text
    main_el = soup.find('main') or soup.find('article') or soup.find(role='main')
    total_text = body.get_text(separator=' ', strip=True)
    total_words = len(total_text.split())

    if main_el:
        main_text = main_el.get_text(separator=' ', strip=True)
        main_words = len(main_text.split())
    else:
        # Estimate: remove header, nav, footer text
        noise_words: int = 0
        for tag_name in ['header', 'nav', 'footer']:
            for el in soup.find_all(tag_name):
                noise_words = noise_words + len(el.get_text(separator=' ', strip=True).split())  # type: ignore
        main_words = total_words - noise_words  # type: ignore

    ratio = (main_words / total_words * 100) if total_words > 0 else 0

    if ratio < 40:
        findings.append(create_finding(
            "high",
            f"Content-to-noise ratio is low ({ratio:.0f}%). The majority of page text is in navigation, headers, or footers.",
            "Ensure the primary content is wrapped in a <main> element and that navigation/footer boilerplate is minimal. RAG crawlers prioritize <main> content.",
            "https://www.w3.org/TR/html5/grouping-content.html#the-main-element",
            "AI crawlers that chunk page content will include navigation and footer text in their chunks, diluting the quality of retrieved information."
        ))
    elif ratio < 60:
        findings.append(create_finding(
            "medium",
            f"Content-to-noise ratio is moderate ({ratio:.0f}%). Consider reducing boilerplate text.",
            "Minimize repetitive navigation text and footer content. Use a <main> element to clearly delineate primary content for AI crawlers.",
            "https://www.w3.org/TR/html5/grouping-content.html#the-main-element",
            "A higher content-to-noise ratio improves the quality of chunks extracted by RAG systems."
        ))

    details = {
        "total_words": total_words,
        "main_content_words": main_words,
        "content_ratio_pct": round(float(ratio), 1),  # type: ignore
        "has_main_element": main_el is not None
    }

    if not findings:
        return {
            "status": "pass",
            "details": details,
            "positive_message": f"Content-to-noise ratio is healthy ({ratio:.0f}%). Primary content dominates the page, which is ideal for RAG extraction."
        }

    return {"status": "fail", "details": details, "findings": findings}


def check_heading_content_pairing(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Check 7.4: Heading-Content Pairing
    Every heading should be followed by substantive content.
    Orphan headings (headings with no content before the next heading)
    create empty or misleading chunks.
    """
    sections = _get_text_sections(soup)
    findings = []

    orphan_headings: List[str] = []
    for s in sections:
        if s["heading"] and s["word_count"] < 5:
            orphan_headings.append(str(s["heading"]))

    if len(orphan_headings) > 2:
        examples = orphan_headings[:3]  # type: ignore
        findings.append(create_finding(
            "medium",
            f"Found {len(orphan_headings)} headings with little or no content following them (e.g., '{examples[0]}').",
            "Ensure every heading is followed by at least one paragraph of descriptive content. Remove decorative headings that serve no informational purpose.",
            "https://www.w3.org/WAI/tutorials/page-structure/headings/",
            "Orphan headings create empty chunks in RAG systems. An AI agent retrieving a chunk with only a heading and no content cannot generate a useful answer."
        ))

    # Check for content without headings (large blocks)
    body = soup.find('body')
    if body:
        # Check if there are large text blocks before the first heading
        first_heading = body.find(re.compile(r'^h[1-6]$'))
        if first_heading:
            pre_heading_text: str = ""
            for el in first_heading.previous_siblings:
                if isinstance(el, Tag):
                    pre_heading_text = pre_heading_text + str(el.get_text(separator=' ', strip=True)) + " "  # type: ignore
            pre_words = len(str(pre_heading_text).split())
            if pre_words > 200:
                findings.append(create_finding(
                    "medium",
                    f"Found {pre_words} words of content before the first heading. This content has no heading context for chunk labeling.",
                    "Add a descriptive heading before the introductory content block so RAG systems can properly label this chunk.",
                    "https://www.w3.org/WAI/tutorials/page-structure/headings/",
                    "Content without a heading label is harder for RAG systems to categorize and retrieve accurately."
                ))

    details = {
        "total_sections": len(sections),
        "orphan_headings": len(orphan_headings)
    }

    if not findings:
        return {
            "status": "pass",
            "details": details,
            "positive_message": "All headings are properly paired with substantive content — clean chunk boundaries for RAG systems."
        }

    return {"status": "fail", "details": details, "findings": findings}


def check_structured_content(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Check 7.5: List & Table Structure
    Well-structured lists and tables are easier for AI agents to parse
    and convert into structured knowledge.
    """
    findings = []

    lists = soup.find_all(['ul', 'ol'])
    tables = soup.find_all('table')

    # Check for lists without context
    orphan_lists = 0
    for lst in lists:
        prev = lst.find_previous_sibling()
        if not prev or (isinstance(prev, Tag) and not prev.get_text(strip=True)):
            orphan_lists += 1

    if orphan_lists > 2:
        findings.append(create_finding(
            "medium",
            f"Found {orphan_lists} lists without a preceding descriptive paragraph or heading.",
            "Add a descriptive sentence or heading before each list to provide context. For example, 'Our services include:' before a service list.",
            "https://www.w3.org/WAI/tutorials/page-structure/content/",
            "Lists without context are ambiguous when extracted as chunks. An AI agent cannot determine what the list items refer to."
        ))

    # Check tables for headers
    tables_without_headers: int = 0
    for table in tables:
        thead = table.find('thead')
        th_elements = table.find_all('th')
        if not thead and not th_elements:
            tables_without_headers = tables_without_headers + 1  # type: ignore

    if tables_without_headers > 0:
        findings.append(create_finding(
            "medium",
            f"Found {tables_without_headers} table(s) without header rows (<thead> or <th>).",
            "Add <thead> and <th> elements to all data tables. This allows AI agents to understand column semantics when parsing table data.",
            "https://www.w3.org/WAI/tutorials/tables/",
            "Tables without headers are opaque to AI agents — they cannot determine what each column represents."
        ))

    details = {
        "list_count": len(lists),
        "table_count": len(tables),
        "orphan_lists": orphan_lists,
        "tables_without_headers": tables_without_headers
    }

    if not findings:
        msg_parts = []
        if lists:
            msg_parts.append(f"{len(lists)} well-structured lists")
        if tables:
            msg_parts.append(f"{len(tables)} properly headed tables")
        if msg_parts:
            return {
                "status": "pass",
                "details": details,
                "positive_message": f"Found {' and '.join(msg_parts)} — structured content is easily parseable by AI agents."
            }
        return {"status": "pass", "details": details}

    return {"status": "fail", "details": details, "findings": findings}


def check_internal_link_context(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Check 7.6: Internal Linking Context
    When an AI agent extracts a chunk that contains a link, the link text
    should provide enough context to understand what it points to.
    """
    findings = []
    body = soup.find('body')
    if not body:
        return {"status": "pass", "details": {}}

    links = body.find_all('a', href=True)
    vague_links = []

    vague_patterns = [
        'click here', 'read more', 'learn more', 'here', 'more',
        'link', 'this', 'see more', 'view more', 'details'
    ]

    for link in links:
        text = link.get_text(strip=True).lower()
        href = link.get('href', '')

        # Skip navigation/footer links and anchors
        if href.startswith('#') or href.startswith('javascript:'):
            continue

        if text in vague_patterns or len(text) < 3:
            vague_links.append({"text": link.get_text(strip=True), "href": href})

    if len(vague_links) > 3:
        findings.append(create_finding(
            "medium",
            f"Found {len(vague_links)} links with vague anchor text (e.g., 'click here', 'read more').",
            "Replace vague link text with descriptive text that makes sense out of context. Instead of 'Read more', use 'Read our pricing guide' or 'View the full case study'.",
            "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#use-links-wisely",
            "When an AI agent retrieves a chunk containing a vague link, it cannot determine what the link leads to without reading the surrounding paragraph."
        ))

    details = {
        "total_links": len(links),
        "vague_links": len(vague_links)
    }

    if not findings:
        return {
            "status": "pass",
            "details": details,
            "positive_message": "Internal links use descriptive anchor text — AI agents can understand link destinations without additional context."
        }

    return {"status": "fail", "details": details, "findings": findings}
