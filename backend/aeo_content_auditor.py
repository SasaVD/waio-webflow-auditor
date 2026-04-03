"""
Pillar 3: AEO Content Auditor
==============================
Analyzes whether the page content is optimized for Answer Engine Optimization (AEO).
Checks readability, section structure, citation density, and content patterns
that influence AI search citation likelihood.

All checks are deterministic and code-based. Zero LLM dependency.

References:
- SE Ranking AI Search Study (2.3M pages, 2025): https://seranking.com/blog/ai-overview-study/
- Princeton GEO Research: https://arxiv.org/abs/2311.09735
- AirOps Content Structure Study (2026): https://www.airops.com/blog/aeo-content-structure
- BrightEdge AI Citation Research (2026): https://www.brightedge.com/resources/research-reports
"""

from bs4 import BeautifulSoup, Tag  # type: ignore
import re
import math
from typing import Dict, Any, List
from utils import make_element_entry


def run_aeo_content_audit(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    """Main entry point for Pillar 3 audit."""
    checks = {}
    positive_findings = []
    category_findings = []

    checks["readability"] = check_readability(soup)
    checks["section_length"] = check_section_length(soup)
    checks["citations_statistics"] = check_citations_statistics(soup)
    checks["conclusion_first"] = check_conclusion_first(soup)
    checks["question_answer_patterns"] = check_qa_patterns(soup)
    checks["content_freshness_signals"] = check_freshness_signals(soup, html_content)
    checks["list_definition_patterns"] = check_list_definition_patterns(soup)

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


def _get_visible_text(soup: BeautifulSoup) -> str:
    main = soup.find("main")
    container = main if main else soup.find("body")
    if not container:
        return ""
    for tag in container.find_all(["script", "style", "noscript"]):
        tag.decompose()
    return container.get_text(separator=" ", strip=True)


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


def _count_syllables(word: str) -> int:
    word = word.lower().strip()
    if len(word) <= 3:
        return 1
    vowels = "aeiouy"
    count: int = 0
    prev_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_vowel:
            count = count + 1  # type: ignore
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count = count - 1  # type: ignore
    return max(1, count)


def check_readability(soup: BeautifulSoup) -> Dict[str, Any]:
    text = _get_visible_text(soup)
    if not text or len(text) < 100:
        return {
            "status": "info",
            "findings": [create_finding(
                "medium",
                "Insufficient text content to calculate readability score.",
                "Add more substantive text content to the page for meaningful readability analysis.",
                "https://seranking.com/blog/ai-overview-study/",
                "Readable text at Flesch-Kincaid Grade 6-8 earns 15% more AI citations on average than Grade 11+ content (SE Ranking study of 2.3M pages, 2025)."
            )]
        }

    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    words = text.split()
    word_count = len(words)
    sentence_count = max(1, len(sentences))

    total_syllables = sum(_count_syllables(w) for w in words)

    avg_words_per_sentence = word_count / sentence_count
    avg_syllables_per_word = total_syllables / max(1, word_count)

    grade_level = 0.39 * avg_words_per_sentence + 11.8 * avg_syllables_per_word - 15.59
    grade_level = round(max(0.0, float(grade_level)), 1)  # type: ignore

    findings = []

    # Score individual paragraphs to find worst offenders
    main = soup.find("main")
    container = main if main else soup.find("body")
    worst_paras = []
    if container:
        for p in container.find_all("p"):
            p_text = p.get_text(separator=" ", strip=True)
            p_words = p_text.split()
            if len(p_words) < 15:
                continue
            p_sents = [s.strip() for s in re.split(r'[.!?]+', p_text) if len(s.strip()) > 5]
            if not p_sents:
                continue
            p_syllables = sum(_count_syllables(w) for w in p_words)
            p_grade = 0.39 * (len(p_words) / max(1, len(p_sents))) + 11.8 * (p_syllables / len(p_words)) - 15.59
            p_grade = round(max(0.0, float(p_grade)), 1)
            if p_grade > 8:
                worst_paras.append((p_grade, p))
        worst_paras.sort(key=lambda x: x[0], reverse=True)

    if grade_level > 10:
        f = create_finding(
            "high",
            f"Content readability is at Grade {grade_level}, significantly above the optimal range of 6-8.",
            "Simplify sentence structure and use shorter words.",
            "https://seranking.com/blog/ai-overview-study/",
            "Readable text at Flesch-Kincaid Grade 6-8 earns 15% more AI citations on average than Grade 11+ content (SE Ranking study of 2.3M pages, 2025)."
        )
        if worst_paras:
            f["elements"] = [make_element_entry(p) for _, p in worst_paras[:3]]
        findings.append(f)
    elif grade_level > 8:
        f = create_finding(
            "medium",
            f"Content readability is at Grade {grade_level}, slightly above the optimal range of 6-8.",
            "Consider simplifying some complex sentences for better AI parsability.",
            "https://seranking.com/blog/ai-overview-study/",
            "Readable text at Flesch-Kincaid Grade 6-8 earns 15% more AI citations on average than Grade 11+ content (SE Ranking study of 2.3M pages, 2025)."
        )
        if worst_paras:
            f["elements"] = [make_element_entry(p) for _, p in worst_paras[:3]]
        findings.append(f)

    if not findings:
        return {
            "status": "pass",
            "positive_message": f"Content readability is at Grade {grade_level}, within the optimal range for AI citation.",
            "findings": []
        }

    return {
        "status": "fail",
        "findings": findings
    }


def check_section_length(soup: BeautifulSoup) -> Dict[str, Any]:
    main = soup.find("main")
    container = main if main else soup.find("body")
    if not container:
        return {"status": "info", "findings": []}

    headings = container.find_all(re.compile(r'^h[2-6]$'))
    if len(headings) < 2:
        return {
            "status": "info",
            "findings": [create_finding(
                "medium",
                "Too few headings to analyze section length distribution.",
                "Use H2-H6 headings to break content into well-defined sections of 100-200 words each.",
                "https://seranking.com/blog/ai-overview-study/",
                "Content with 100-150 words per section earns the most AI citations, with a sweet spot for AI parsability (SE Ranking study of 2.3M pages, 2025)."
            )]
        }

    section_word_counts = []
    for i, heading in enumerate(headings):
        section_text = ""
        sibling = heading.find_next_sibling()
        while sibling and not (sibling.name and re.match(r'^h[1-6]$', sibling.name)):
            section_text += sibling.get_text(separator=" ", strip=True) + " "
            sibling = sibling.find_next_sibling()
        word_count = len(section_text.split())
        section_word_counts.append(word_count)

    if not section_word_counts:
        return {"status": "info", "findings": []}

    avg_words = sum(section_word_counts) / len(section_word_counts)
    avg_words = round(avg_words)

    findings = []

    if avg_words < 50:
        findings.append(create_finding(
            "high",
            f"Average section length is {avg_words} words, significantly outside the optimal range.",
            "Break up long sections or expand very short ones to average 100-200 words.",
            "https://seranking.com/blog/ai-overview-study/",
            "Content with 100-150 words per section earns the most AI citations, with a sweet spot for AI parsability (SE Ranking study of 2.3M pages, 2025)."
        ))
    elif avg_words < 80 or avg_words > 300:
        findings.append(create_finding(
            "medium",
            f"Average section length is {avg_words} words, outside the optimal range of 100-200.",
            "Adjust section lengths to target 100-200 words per section for optimal AI parsability.",
            "https://seranking.com/blog/ai-overview-study/",
            "Content with 100-150 words per section earns the most AI citations, with a sweet spot for AI parsability (SE Ranking study of 2.3M pages, 2025)."
        ))

    if not findings:
        return {
            "status": "pass",
            "positive_message": f"Average section length is {avg_words} words, within the optimal range for AI content consumption.",
            "findings": []
        }

    return {
        "status": "fail",
        "findings": findings
    }


def check_citations_statistics(soup: BeautifulSoup) -> Dict[str, Any]:
    text = _get_visible_text(soup)
    if not text:
        return {"status": "info", "findings": []}

    stat_patterns = [
        r'\d+\.?\d*\s*%',
        r'\d+x\b',
        r'\$\d+',
        r'\u20ac\d+',
        r'\u00a3\d+',
        r'\d+\s*(million|billion|thousand|M|B|K)\b',
    ]

    stat_count = 0
    for pattern in stat_patterns:
        stat_count += len(re.findall(pattern, text, re.IGNORECASE))

    citation_patterns = [
        r'\([\w\s,]+\d{4}\)',
        r'according to\s+[\w\s]+',
        r'study\s+(by|from|shows|found)',
        r'research\s+(by|from|shows|found)',
        r'report\s+(by|from|shows|found)',
        r'source:\s*',
    ]

    citation_count = 0
    for pattern in citation_patterns:
        citation_count += len(re.findall(pattern, text, re.IGNORECASE))

    total = stat_count + citation_count
    findings = []

    if total == 0:
        findings.append(create_finding(
            "high",
            f"Very few statistics or citations found ({total}).",
            "Include more data points, statistics, and verifiable citations in your content.",
            "https://www.yotpo.com/blog/llm-optimization-guide/",
            "Citing sources increases AI citation likelihood by +115%, while adding statistics provides a +37% boost (Princeton GEO Study, 2023). This signals to the AI that your content is well-researched and trustworthy."
        ))
    elif total < 3:
        findings.append(create_finding(
            "medium",
            f"Only {total} statistics or citations found. More would strengthen AI citation likelihood.",
            "Add verifiable data points, named sources, and statistics throughout the content.",
            "https://www.yotpo.com/blog/llm-optimization-guide/",
            "Citing sources increases AI citation likelihood by +115%, while adding statistics provides a +37% boost (Princeton GEO Study, 2023). This signals to the AI that your content is well-researched and trustworthy."
        ))

    if not findings:
        return {
            "status": "pass",
            "positive_message": f"Found {total} statistics and citations, providing strong credibility signals for AI engines.",
            "findings": []
        }

    return {
        "status": "fail",
        "findings": findings
    }


def check_qa_patterns(soup: BeautifulSoup) -> Dict[str, Any]:
    text = _get_visible_text(soup)
    if not text:
        return {"status": "info", "findings": []}

    headings = soup.find_all(re.compile(r'^h[2-6]$'))
    question_headings: int = 0
    for h in headings:
        h_text = h.get_text(strip=True)
        if h_text.endswith("?") or h_text.lower().startswith(("what ", "how ", "why ", "when ", "where ", "who ", "which ", "can ", "does ", "is ", "are ")):
            question_headings = question_headings + 1  # type: ignore

    faq_schema = '"@type"' in str(soup) and '"FAQPage"' in str(soup)

    findings = []

    if question_headings == 0 and not faq_schema:
        f = create_finding(
            "medium",
            "No question-based headings or FAQ patterns detected on the page.",
            "Add question-based headings (e.g., 'What is...?', 'How does...?') to match common AI search queries.",
            "https://www.airops.com/blog/aeo-content-structure",
            "Pages with question-based headings are 2.3x more likely to be cited in AI-generated answers (AirOps, 2026)."
        )
        # Show headings that could be rephrased as questions
        candidates = [h for h in headings if len(h.get_text(strip=True)) > 5]
        if candidates:
            f["elements"] = [make_element_entry(h) for h in candidates[:3]]
        findings.append(f)

    if not findings:
        msg = f"Found {question_headings} question-based headings"
        if faq_schema:
            msg += " and FAQPage schema"
        msg += ", supporting AI query matching."
        return {
            "status": "pass",
            "positive_message": msg,
            "findings": []
        }

    return {
        "status": "fail",
        "findings": findings
    }


def check_freshness_signals(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    findings = []

    has_date_published = '"datePublished"' in html_content
    has_date_modified = '"dateModified"' in html_content

    time_tags = soup.find_all("time")
    has_time_element = len(time_tags) > 0

    date_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
    visible_dates = re.findall(date_pattern, _get_visible_text(soup), re.IGNORECASE)

    if not has_date_published and not has_date_modified and not has_time_element and not visible_dates:
        findings.append(create_finding(
            "medium",
            "No content freshness signals detected (no dates, no datePublished/dateModified in Schema).",
            "Add datePublished and dateModified to your Schema.org structured data, and display publication dates visibly.",
            "https://developers.google.com/search/docs/appearance/structured-data/article",
            "AI engines prioritize recent content. Pages with clear freshness signals receive 20-30% more citations in time-sensitive queries (BrightEdge, 2026)."
        ))

    if not findings:
        signals = []
        if has_date_published:
            signals.append("datePublished in Schema")
        if has_date_modified:
            signals.append("dateModified in Schema")
        if has_time_element:
            signals.append(f"{len(time_tags)} <time> elements")
        return {
            "status": "pass",
            "positive_message": f"Content freshness signals detected: {', '.join(signals)}.",
            "findings": []
        }

    return {
        "status": "fail",
        "findings": findings
    }


def check_list_definition_patterns(soup: BeautifulSoup) -> Dict[str, Any]:
    main = soup.find("main")
    container = main if main else soup.find("body")
    if not container:
        return {"status": "info", "findings": []}

    lists = container.find_all(["ul", "ol"])
    definition_lists = container.find_all("dl")
    tables = container.find_all("table")

    total_structured = len(lists) + len(definition_lists) + len(tables)

    text = _get_visible_text(soup)
    word_count = len(text.split()) if text else 0

    findings = []

    if word_count > 500 and total_structured == 0:
        findings.append(create_finding(
            "medium",
            "No structured content patterns (lists, tables, definition lists) found despite substantial text content.",
            "Break key information into bulleted lists, numbered steps, or comparison tables for better AI extraction.",
            "https://www.airops.com/blog/aeo-content-structure",
            "AI engines extract structured content (lists, tables) 40% more accurately than unstructured paragraphs (AirOps, 2026)."
        ))

    if not findings:
        return {
            "status": "pass",
            "positive_message": f"Found {total_structured} structured content elements (lists, tables) supporting AI content extraction.",
            "findings": []
        }

    return {"status": "fail", "findings": findings}


def check_conclusion_first(soup: BeautifulSoup) -> Dict[str, Any]:
    sections = _get_text_sections(soup)
    findings = []
    introductory_phrases = [
        r"^(In this section|In this article|In this post|This section will|Let's explore|Let's look at)",
        r"^(There are many|There are several|A number of)",
        r"^(When it comes to|Regarding|In terms of)"
    ]

    conclusion_first_count: int = 0
    for s in sections:
        text = s.get("text", "").strip()
        if not text or s["word_count"] < 20:
            continue

        first_sentence = text.split(".")[0]
        is_intro = any(re.match(p, first_sentence, re.IGNORECASE) for p in introductory_phrases)

        if not is_intro:
            conclusion_first_count = conclusion_first_count + 1  # type: ignore

    if len(sections) > 0 and (float(conclusion_first_count) / len(sections)) < 0.5:
        findings.append(create_finding(
            "medium",
            f"Only {conclusion_first_count} of {len(sections)} sections use Conclusion-First formatting.",
            "Rewrite section openings to provide the direct answer in the first sentence. This improves information density for AI retrieval.",
            "https://keomarketing.com/query-fan-out-b2b-seo-strategy/",
            "AI models prioritize content with high information density. Providing the answer upfront in the first sentence of a section increases the likelihood of citation."
        ))

    if not findings:
        return {
            "status": "pass",
            "positive_message": "Content sections effectively use Conclusion-First formatting, optimizing for AI information retrieval.",
            "findings": []
        }

    return {"status": "fail", "findings": findings}
