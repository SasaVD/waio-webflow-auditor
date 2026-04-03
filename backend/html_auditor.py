from bs4 import BeautifulSoup, Tag
import re
from typing import Dict, Any, List
from utils import make_element_entry

def run_html_audit(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    checks = {}
    total_findings = 0
    
    # Check 1.1: Document Foundation
    checks["document_foundation"] = check_document_foundation(soup, html_content)
    
    # Check 1.2: Single H1 Tag
    checks["heading_h1"] = check_single_h1(soup)
    
    # Check 1.3: Heading Hierarchy
    checks["heading_hierarchy"] = check_heading_hierarchy(soup)
    
    # Check 1.4: Landmark Elements
    checks["landmark_elements"] = check_landmark_elements(soup)
    
    # Check 1.5: Semantic Richness
    checks["semantic_richness"] = check_semantic_richness(soup)
    
    # Check 1.6: Image Alt Text Coverage
    checks["image_alt_coverage"] = check_image_alt_coverage(soup)
    
    # Check 1.7: Form Accessibility
    checks["form_accessibility"] = check_form_accessibility(soup)
    
    # Check 1.8: Link Quality
    checks["link_quality"] = check_link_quality(soup)
    
    # Check 1.9: Meta Tags
    checks["meta_tags"] = check_meta_tags(soup)

    positive_findings = []
    category_findings = []
    for check_key, check_val in checks.items():
        if check_val.get("status") == "pass":
            if "positive_message" in check_val:
                positive_findings.append({
                    "text": check_val["positive_message"],
                    "credibility_anchor": check_val.get("credibility_anchor")
                })
                del check_val["positive_message"]
                if "credibility_anchor" in check_val:
                    del check_val["credibility_anchor"]
        if "findings" in check_val:
            category_findings.extend(check_val["findings"])
            
    return {
        "checks": checks,
        "positive_findings": positive_findings,
        "findings": category_findings
    }

def create_finding(severity: str, description: str, recommendation: str, reference: str, credibility_anchor: str = None) -> Dict[str, str]:
    return {
        "severity": severity,
        "description": description,
        "recommendation": recommendation,
        "reference": reference,
        "credibility_anchor": credibility_anchor
    }

def check_document_foundation(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    findings = []
    anchor = "Clean HTML and proper document structure are prerequisites for AI crawlability (Semrush AI Search Study, 2026)."
    
    has_doctype = bool(re.search(r'<!DOCTYPE\s+html>', html_content, re.IGNORECASE))
    html_tag = soup.find('html')
    has_html_lang = html_tag and html_tag.has_attr('lang') and bool(html_tag['lang'].strip())
    
    charset_meta = soup.find('meta', charset=True)
    has_charset = bool(charset_meta and charset_meta['charset'].lower() == 'utf-8')
    if not has_charset:
        has_charset = bool(soup.find('meta', attrs={'http-equiv': lambda x: x and x.lower() == 'content-type', 'content': re.compile(r'charset=utf-8', re.I)}))

    viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
    has_viewport = bool(viewport_meta)

    if not has_doctype:
        findings.append(create_finding(
            "critical", 
            "Missing HTML5 DOCTYPE declaration.", 
            "Add <!DOCTYPE html> at the very beginning of the document.", 
            "https://www.w3.org/TR/html5/syntax.html#the-doctype",
            anchor
        ))
    if not has_html_lang:
        findings.append(create_finding(
            "high", 
            "Missing lang attribute on HTML element.", 
            "Add a lang attribute to the <html> tag (e.g., <html lang=\"en\">).", 
            "https://www.w3.org/TR/WCAG21/#language-of-page",
            anchor
        ))
    if not has_charset:
        findings.append(create_finding(
            "high", 
            "Missing or non-UTF-8 charset meta tag.", 
            "Add <meta charset=\"utf-8\"> inside the <head>.", 
            "https://www.w3.org/TR/html5/document-metadata.html#charset",
            anchor
        ))
    if not has_viewport:
        findings.append(create_finding(
            "high", 
            "Missing viewport meta tag.", 
            "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> inside the <head>.", 
            "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#mobile",
            anchor
        ))

    passed = len(findings) == 0
    res = {
        "status": "pass" if passed else "fail",
        "details": {
            "doctype": has_doctype,
            "lang": has_html_lang,
            "charset": has_charset,
            "viewport": has_viewport
        }
    }
    if not passed:
        res["findings"] = findings
    else:
        res["positive_message"] = "Document foundation (DOCTYPE, lang, charset, viewport) is correctly implemented."
        res["credibility_anchor"] = anchor
        
    return res

def check_single_h1(soup: BeautifulSoup) -> Dict[str, Any]:
    h1_tags = soup.find_all('h1')
    count = len(h1_tags)
    findings = []
    status = "pass"
    anchor = "Pages with well-organized headings are 2.8x more likely to earn citations in AI search results (AirOps, 2026)."
    
    if count == 0:
        findings.append(create_finding(
            "critical",
            "No H1 tag found on the page.",
            "Add a single H1 tag that clearly describes the page content.",
            "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#use-heading-tags",
            anchor
        ))
        status = "fail"
    elif count > 1:
        f = create_finding(
            "high",
            f"Multiple ({count}) H1 tags found on the page.",
            "Ensure exactly one H1 tag per page. Change other H1s to H2 or lower.",
            "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#use-heading-tags",
            anchor
        )
        f["elements"] = [make_element_entry(h) for h in h1_tags]
        findings.append(f)
        status = "fail"

    res = {
        "status": status,
        "details": {"h1_count": count}
    }
    if findings:
        res["findings"] = findings
    else:
        res["positive_message"] = "Exactly one H1 tag found on the page."
        res["credibility_anchor"] = anchor
        
    return res

def check_heading_hierarchy(soup: BeautifulSoup) -> Dict[str, Any]:
    headings = soup.find_all(re.compile(r'^h[1-6]$'))
    hierarchy = [int(h.name[1]) for h in headings]
    skips = []
    anchor = "Pages with well-organized headings are 2.8x more likely to earn citations in AI search results (AirOps, 2026)."

    expected_level = 1
    for idx, level in enumerate(hierarchy):
        if level > expected_level + 1:
            skips.append((expected_level, level, idx))
        expected_level = level

    findings = []
    for skip in skips:
        f = create_finding(
            "high",
            f"Heading level skipped. Jumped from H{skip[0]} to H{skip[1]}.",
            "Heading levels should be sequential. Do not skip levels.",
            "https://www.w3.org/WAI/tutorials/page-structure/headings/",
            anchor
        )
        f["elements"] = [make_element_entry(headings[skip[2]])]
        findings.append(f)
        
    res = {
        "status": "pass" if not findings else "fail",
        "details": {"heading_tree": hierarchy}
    }
    if findings:
        res["findings"] = findings
    else:
        if len(hierarchy) > 0:
            res["positive_message"] = "Heading hierarchy is completely sequential with no skipped levels."
            res["credibility_anchor"] = anchor
    return res

def check_landmark_elements(soup: BeautifulSoup) -> Dict[str, Any]:
    landmarks = ['header', 'nav', 'main', 'footer', 'aside']
    found = {tag: bool(soup.find(tag)) for tag in landmarks}
    findings = []
    anchor = "Proper heading hierarchy and crawlable site structure are recommended for maintaining AI crawlability (Semrush AI Search Study, 2026)."
    
    if not found['main']:
        findings.append(create_finding(
            "critical",
            "Missing <main> landmark element.",
            "Wrap the primary content of the page in a <main> tag.",
            "https://www.w3.org/WAI/ARIA/apg/practices/landmark-regions/",
            anchor
        ))
    
    for tag in ['header', 'nav', 'footer']:
        if not found[tag]:
            findings.append(create_finding(
                "high",
                f"Missing {tag} landmark element.",
                f"Use a <{tag}> tag for {tag} sections instead of generic divs.",
                "https://www.w3.org/WAI/ARIA/apg/practices/landmark-regions/",
                anchor
            ))
            
    res = {
        "status": "pass" if not findings else "fail",
        "details": found
    }
    if findings:
        res["findings"] = findings
    else:
        res["positive_message"] = "Core semantic landmark elements (<header>, <nav>, <main>, <footer>) are present."
        res["credibility_anchor"] = anchor
        
    return res

def check_semantic_richness(soup: BeautifulSoup) -> Dict[str, Any]:
    semantics = ['header', 'nav', 'main', 'footer', 'article', 'section', 'aside', 'figure', 'figcaption', 'blockquote', 'time', 'address', 'details', 'summary', 'mark', 'dl', 'dt', 'dd']
    generics = ['div', 'span']
    
    semantic_count = sum(len(soup.find_all(tag)) for tag in semantics)
    generic_count = sum(len(soup.find_all(tag)) for tag in generics)
    
    total = semantic_count + generic_count
    ratio = semantic_count / total if total > 0 else 0
    
    findings = []
    status = "pass"
    
    if ratio < 0.15:
        findings.append(create_finding(
            "high",
            f"Low semantic HTML ratio ({ratio:.2%}). High reliance on div/span.",
            "Replace generic <div> and <span> tags with semantic equivalents to improve structure.",
            "https://www.w3.org/TR/html5/dom.html#semantic-elements"
        ))
        status = "fail"
    elif ratio <= 0.30:
        findings.append(create_finding(
            "medium",
            f"Moderate semantic HTML ratio ({ratio:.2%}).",
            "Consider using more semantic elements rather than generic containers.",
            "https://www.w3.org/TR/html5/dom.html#semantic-elements"
        ))
        status = "fail"

    res = {
        "status": status,
        "details": {
            "semantic_count": semantic_count,
            "generic_count": generic_count,
            "ratio": ratio
        }
    }
    if findings:
        res["findings"] = findings
    else:
        res["positive_message"] = f"Healthy semantic HTML ratio ({ratio:.2%}). Good use of semantic tags."
        
    return res

def check_image_alt_coverage(soup: BeautifulSoup) -> Dict[str, Any]:
    images = soup.find_all('img')
    total = len(images)
    with_alt = sum(1 for img in images if img.has_attr('alt') and img['alt'].strip() != '')
    
    coverage = with_alt / total if total > 0 else 1.0
    findings = []
    
    if total > 0 and coverage < 1.0:
        f = create_finding(
            "high",
            f"Missing alt text on {total - with_alt} out of {total} images (Coverage: {coverage:.0%}).",
            "Provide descriptive alt text for all meaningful images. Use empty alt=\"\" for decorative only.",
            "https://www.w3.org/TR/WCAG21/#non-text-content"
        )
        missing = [img for img in images if not img.has_attr('alt') or img['alt'].strip() == '']
        f["elements"] = [make_element_entry(img) for img in missing[:5]]
        findings.append(f)
        
    res = {
        "status": "pass" if not findings else "fail",
        "details": {
            "total_images": total,
            "images_with_alt": with_alt,
            "coverage": coverage
        }
    }
    if findings:
        res["findings"] = findings
    else:
        if total > 0:
            res["positive_message"] = "100% of images have alternative text."
            
    return res

def check_form_accessibility(soup: BeautifulSoup) -> Dict[str, Any]:
    inputs = soup.find_all(['input', 'textarea', 'select'])
    missing = 0
    missing_els = []
    total = len(inputs)
    
    for el in inputs:
        # Ignore hidden inputs and buttons
        if el.name == 'input' and el.get('type') in ['hidden', 'submit', 'button', 'reset', 'image']:
            total -= 1
            continue
            
        has_aria_label = el.has_attr('aria-label') and bool(el['aria-label'].strip())
        el_id = el.get('id')
        
        has_linked_label = False
        if el_id:
            label = soup.find('label', attrs={'for': el_id})
            if label:
                has_linked_label = True
                
        # Implicitly wrapped label check
        is_wrapped = el.find_parent('label') is not None
        
        if not (has_aria_label or has_linked_label or is_wrapped):
            missing += 1
            missing_els.append(el)

    findings = []
    if missing > 0:
        f = create_finding(
            "high",
            f"{missing} form inputs are missing associated <label> or aria-label.",
            "Ensure every form input has a linked <label for=\"id\"> or an aria-label attribute.",
            "https://www.w3.org/TR/WCAG21/#info-and-relationships"
        )
        f["elements"] = [make_element_entry(el) for el in missing_els[:5]]
        findings.append(f)

    res = {
        "status": "pass" if missing == 0 else "fail",
        "details": {
            "total_inputs": total,
            "missing_labels": missing
        }
    }
    if findings:
        res["findings"] = findings
    else:
        if total > 0:
            res["positive_message"] = "All form inputs have accessible labels."
            
    return res

def check_link_quality(soup: BeautifulSoup) -> Dict[str, Any]:
    links = soup.find_all('a')
    bad_hrefs = 0
    generic_text = 0
    
    generic_words = ["click here", "read more", "learn more", "more", "here", "link"]
    
    bad_href_els = []
    generic_text_els = []

    for a in links:
        href = a.get('href', '').strip()
        if not href or href == '#' or href.startswith('javascript:void(0)'):
            bad_hrefs += 1
            bad_href_els.append(a)

        text = a.get_text().strip().lower()
        if text in generic_words:
            generic_text += 1
            generic_text_els.append(a)

    findings = []
    if bad_hrefs > 0:
        f = create_finding(
            "medium",
            f"Found {bad_hrefs} links with empty href, \"#\", or \"javascript:void(0)\".",
            "Ensure all <a> tags have a valid URL in their href attribute.",
            "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#links"
        )
        f["elements"] = [make_element_entry(a) for a in bad_href_els[:5]]
        findings.append(f)
    if generic_text > 0:
        f = create_finding(
            "medium",
            f"Found {generic_text} links with generic anchor text (e.g., 'click here', 'read more').",
            "Use descriptive anchor text that provides context about the link destination.",
            "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#write-good-link-text"
        )
        f["elements"] = [make_element_entry(a) for a in generic_text_els[:5]]
        findings.append(f)
        
    res = {
        "status": "pass" if not findings else "fail",
        "details": {
            "total_links": len(links),
            "bad_hrefs": bad_hrefs,
            "generic_texts": generic_text
        }
    }
    if findings:
        res["findings"] = findings
    else:
        if len(links) > 0:
            res["positive_message"] = "All links use descriptive text and valid destinations."
            
    return res

def check_meta_tags(soup: BeautifulSoup) -> Dict[str, Any]:
    title_el = soup.title
    title = title_el.string.strip() if title_el and title_el.string else None
    
    desc_el = soup.find('meta', attrs={'name': 'description'})
    desc = desc_el.get('content', '').strip() if desc_el else None
    
    og_title_el = soup.find('meta', property='og:title')
    og_title = og_title_el.get('content', '').strip() if og_title_el else None
    
    og_desc_el = soup.find('meta', property='og:description')
    og_desc = og_desc_el.get('content', '').strip() if og_desc_el else None
    
    og_image_el = soup.find('meta', property='og:image')
    og_image = og_image_el.get('content', '').strip() if og_image_el else None
    
    findings = []
    anchor_og = "Open Graph tags are present on ~60% of AI-cited pages in Google AI Mode and ~40% in ChatGPT (Semrush AI Search Study, 2026)."
    
    if not title:
        findings.append(create_finding("high", "Missing <title> tag.", "Add a title tag to the document head.", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#title-tags"))
    elif len(title) < 30 or len(title) > 65:
        findings.append(create_finding("medium", f"Title length ({len(title)} chars) is outside optimal range (45-60).", "Adjust title length.", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#title-tags"))
        
    if not desc:
        findings.append(create_finding("high", "Missing meta description.", "Add a meta description to the document head.", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#meta-descriptions"))
    elif len(desc) < 50 or len(desc) > 165:
        findings.append(create_finding("medium", f"Meta description length ({len(desc)} chars) is outside optimal range (135-160).", "Adjust meta description length.", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide#meta-descriptions"))

    missing_og = []
    if not og_title: missing_og.append('og:title')
    if not og_desc: missing_og.append('og:description')
    if not og_image: missing_og.append('og:image')
    
    if missing_og:
        findings.append(create_finding("medium", f"Missing Open Graph tags: {', '.join(missing_og)}.", "Add Open Graph tags for better social sharing.", "https://ogp.me/", anchor_og))

    res = {
        "status": "pass" if not findings else "fail",
        "details": {
            "title_length": len(title) if title else 0,
            "desc_length": len(desc) if desc else 0,
            "has_og_title": bool(og_title),
            "has_og_desc": bool(og_desc),
            "has_og_image": bool(og_image)
        }
    }
    if findings:
        res["findings"] = findings
    else:
        res["positive_message"] = "Essential SEO meta tags and Open Graph tags are well-formatted and present."
        res["credibility_anchor"] = anchor_og
        
    return res
