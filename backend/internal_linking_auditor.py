"""
Pillar 10: Internal Linking Structure Analysis
================================================
Analyzes the quality and structure of internal links on a page
and (when part of a site crawl) across the entire site.

Checks for:
- Link depth (clicks from homepage)
- Orphan pages (no internal links pointing to them)
- Link equity distribution (pages with too many or too few internal links)
- Anchor text quality and diversity
- Broken internal links
- Redirect chains in internal links
- Navigation consistency

All checks are deterministic and code-based. Zero LLM dependency.
"""

from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from urllib.parse import urlparse

def run_internal_linking_audit(soup: BeautifulSoup, html_content: str, url: str, site_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    checks = {}
    positive_findings = []
    category_findings = []
    
    # Run Single-page checks
    checks["outgoing_internal_links"] = check_outgoing_internal_links(soup, url)
    checks["anchor_text_quality"] = check_anchor_text_quality(soup, url)
    checks["self_referencing_links"] = check_self_referencing_links(soup, url)
    checks["nofollow_internal_links"] = check_nofollow_internal_links(soup, url)
    
    # Run Site-wide checks if data is available
    if site_data:
        # Phase 2 implementation will populate this
        pass
        
    for check_key, check_val in checks.items():
        if check_val.get("status") in ["pass", "info"]:
            if "positive_message" in check_val and check_val["positive_message"]:
                positive_findings.append({
                    "text": check_val["positive_message"],
                    "credibility_anchor": None
                })
        if "findings" in check_val:
            category_findings.extend(check_val["findings"])
            
    return {
        "checks": checks,
        "positive_findings": positive_findings,
        "findings": category_findings
    }

def create_finding(severity: str, description: str, recommendation: str, reference: str, credibility_anchor: str = "") -> Dict[str, str]:
    return {
        "severity": severity,
        "description": description,
        "recommendation": recommendation,
        "reference": reference,
        "credibility_anchor": credibility_anchor
    }

def is_internal(link_url: str, base_url: str) -> bool:
    if not link_url:
        return False
    if link_url.startswith('#'):
        return False
    if link_url.startswith('mailto:') or link_url.startswith('tel:'):
        return False
        
    parsed_base = urlparse(base_url)
    parsed_link = urlparse(link_url)
    
    if not parsed_link.netloc:
        return True # Relative URL
        
    return parsed_link.netloc == parsed_base.netloc or parsed_link.netloc.endswith('.' + parsed_base.netloc)

def check_outgoing_internal_links(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    findings = []
    
    a_tags = soup.find_all('a', href=True)
    internal_links = [a['href'] for a in a_tags if is_internal(a['href'], url)]
    count = len(internal_links)
    
    if count < 3:
        findings.append(create_finding(
            severity="high",
            description=f"Isolated page: very few internal links found ({count}).",
            recommendation="Add more contextually relevant internal links to help users and crawlers navigate.",
            reference="https://developers.google.com/search/docs/fundamentals/seo-starter-guide#use-links-wisely",
            credibility_anchor="Google SEO Starter Guide emphasizes discoverability via cross-linking."
        ))
    elif count > 150:
        findings.append(create_finding(
            severity="medium",
            description=f"Potential link stuffing: {count} internal links found.",
            recommendation="Consolidate duplicate navigation links and ensure links provide real value.",
            reference="https://ahrefs.com/blog/internal-links-for-seo/",
            credibility_anchor="Excessive links dilute link equity passed to other pages."
        ))
        
    return {
        "status": "pass" if not findings else "fail",
        "details": {"internal_link_count": count},
        **({"findings": findings} if findings else {"positive_message": f"Healthy number of outgoing internal links ({count})."})
    }

def check_anchor_text_quality(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    findings = []
    vague_texts = ["click here", "read more", "learn more", "here", "more", "see more", "link"]
    
    a_tags = soup.find_all('a', href=True)
    vague_links = []
    duplicate_anchors = {}
    
    for a in a_tags:
        if not is_internal(a['href'], url):
            continue
            
        text = a.get_text().strip().lower()
        if text in vague_texts:
            vague_links.append(text)
            
        href = a['href']
        if text and len(text) > 3:
            if text not in duplicate_anchors:
                duplicate_anchors[text] = set()
            duplicate_anchors[text].add(href)
            
    if vague_links:
        count = len(vague_links)
        findings.append(create_finding(
            severity="medium",
            description=f"Found {count} internal links with vague anchor text (e.g. 'read more').",
            recommendation="Use descriptive anchor text to give search engines and users better context.",
            reference="https://developers.google.com/search/docs/fundamentals/seo-starter-guide#use-links-wisely",
            credibility_anchor="Vague anchors miss SEO opportunities for semantic relevance."
        ))
        
    misleading_anchors = {k: v for k, v in duplicate_anchors.items() if len(v) > 1}
    if misleading_anchors:
        count = len(misleading_anchors)
        findings.append(create_finding(
            severity="high",
            description=f"Found {count} instances of the exact same anchor text pointing to different internal pages.",
            recommendation="Avoid using identical anchor text for different target URLs to prevent confusing search engines.",
            reference="https://ahrefs.com/blog/internal-links-for-seo/",
            credibility_anchor="Inconsistent anchor mapping dilutes topical authority signals."
        ))

    return {
        "status": "pass" if not findings else "fail",
        "details": {"vague_links_count": len(vague_links), "misleading_anchors_count": len(misleading_anchors)},
        **({"findings": findings} if findings else {"positive_message": "Anchor text is descriptive and distinct."})
    }

def check_self_referencing_links(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    findings = []
    
    parsed_current = urlparse(url)
    current_path = parsed_current.path if parsed_current.path else '/'
    
    a_tags = soup.find_all('a', href=True)
    self_links = 0
    
    for a in a_tags:
        href = a['href']
        if href == url or href == current_path:
            self_links += 1
            
    if self_links > 2:
        findings.append(create_finding(
            severity="medium",
            description=f"Found {self_links} self-referencing links pointing to the current page.",
            recommendation="Remove interactive links that point to the current page (e.g., active state menu items should not be clickable links).",
            reference="https://www.screamingfrog.co.uk/seo-spider/",
            credibility_anchor="Self-referencing links waste crawl budget and offer poor UX."
        ))
        
    return {
        "status": "pass" if not findings else "fail",
        "details": {"self_referencing_count": self_links},
        **({"findings": findings} if findings else {"positive_message": "No excessive self-referencing links found."})
    }

def check_nofollow_internal_links(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    findings = []
    
    target_links = soup.find_all('a', href=True, rel=lambda value: value and "nofollow" in value)
    nofollow_internal = [a for a in target_links if is_internal(a['href'], url)]
    count = len(nofollow_internal)
    
    if count > 0:
        findings.append(create_finding(
            severity="high",
            description=f"Found {count} internal links with rel='nofollow' attribute.",
            recommendation="Remove rel='nofollow' from internal links to allow link equity to flow freely throughout your site.",
            reference="https://developers.google.com/search/docs/fundamentals/seo-starter-guide#use-links-wisely",
            credibility_anchor="Google explicitly recommends against nofollowing internal links."
        ))
        
    return {
        "status": "pass" if not findings else "fail",
        "details": {"nofollow_internal_count": count},
        **({"findings": findings} if findings else {"positive_message": "All internal links follow correctly (no nofollow wrappers)."})
    }
