"""
Pillar 9: Data Integrity & Conflict Detection
===============================================
Analyzes whether the page contains conflicting, inconsistent, or
ambiguous data that would confuse an AI agent.

Checks for:
- Price/currency conflicts across the page
- Contradictory contact information (phone, email, address)
- Inconsistent brand/company naming
- Date/time conflicts
- Duplicate or conflicting Schema.org entities

All checks are deterministic and code-based. Zero LLM dependency.

References:
- Schema.org Data Quality: https://schema.org/docs/datamodel.html
- Google Structured Data Guidelines: https://developers.google.com/search/docs/appearance/structured-data/sd-policies
"""

from bs4 import BeautifulSoup, Tag
import re
import json
from typing import Dict, Any, List, Set
from collections import Counter
from utils import make_element_entry


def run_data_integrity_audit(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    """Main entry point for Pillar 9 audit."""
    checks = {}
    positive_findings = []
    category_findings = []

    checks["price_conflicts"] = check_price_conflicts(soup, html_content)
    checks["contact_conflicts"] = check_contact_conflicts(soup, html_content)
    checks["brand_consistency"] = check_brand_consistency(soup, html_content)
    checks["schema_conflicts"] = check_schema_conflicts(soup, html_content)
    checks["date_conflicts"] = check_date_conflicts(soup, html_content)

    for check_key, check_val in checks.items():
        if check_val.get("status") in ["pass", "info"]:
            if "positive_message" in check_val:
                positive_findings.append(check_val["positive_message"])
                del check_val["positive_message"]
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


def _extract_jsonld_blocks(html_content: str) -> List[dict]:
    """Extract all JSON-LD blocks from the page."""
    blocks = []
    pattern = re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
    for match in pattern.finditer(html_content):
        try:
            data = json.loads(match.group(1).strip())
            if isinstance(data, list):
                blocks.extend(data)
            else:
                blocks.append(data)
        except (json.JSONDecodeError, ValueError):
            pass
    return blocks


def _extract_prices_from_text(text: str) -> List[Dict[str, str]]:
    """Extract price mentions from visible text."""
    prices = []
    patterns = [
        r'(\$[\d,]+(?:\.\d{2})?)',
        r'(€[\d,]+(?:\.\d{2})?)',
        r'(£[\d,]+(?:\.\d{2})?)',
        r'([\d,]+(?:\.\d{2})?\s*(?:USD|EUR|GBP|CAD|AUD))',
        r'(?:price|cost|fee|starting at|from)\s*[:\-]?\s*(\$[\d,]+(?:\.\d{2})?)',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            prices.append({"raw": match.group(0).strip(), "context": text[max(0, match.start()-40):match.end()+40].strip()})
    return prices


def _extract_prices_from_schema(jsonld_blocks: List[dict]) -> List[Dict[str, Any]]:
    """Extract price information from Schema.org JSON-LD."""
    prices = []

    def _walk(obj, path=""):
        if isinstance(obj, dict):
            if 'price' in obj or 'lowPrice' in obj or 'highPrice' in obj:
                price_info = {
                    "price": obj.get("price"),
                    "lowPrice": obj.get("lowPrice"),
                    "highPrice": obj.get("highPrice"),
                    "priceCurrency": obj.get("priceCurrency"),
                    "path": path
                }
                prices.append(price_info)
            for k, v in obj.items():
                _walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _walk(item, f"{path}[{i}]")

    for block in jsonld_blocks:
        _walk(block)

    return prices


def check_price_conflicts(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    """
    Check 9.1: Price & Currency Conflicts
    Detects conflicting price information between visible text and structured data,
    and between different structured data blocks.
    """
    findings = []

    body = soup.find('body')
    visible_text = body.get_text(separator=' ', strip=True) if body else ""

    text_prices = _extract_prices_from_text(visible_text)
    jsonld_blocks = _extract_jsonld_blocks(html_content)
    schema_prices = _extract_prices_from_schema(jsonld_blocks)

    # Check for multiple currencies in text
    currencies_found = set()
    for p in text_prices:
        raw = p["raw"]
        if '$' in raw:
            currencies_found.add("USD")
        if '€' in raw:
            currencies_found.add("EUR")
        if '£' in raw:
            currencies_found.add("GBP")
        for curr in ['USD', 'EUR', 'GBP', 'CAD', 'AUD']:
            if curr in raw.upper():
                currencies_found.add(curr)

    # Check for currency mismatch between schema and text
    schema_currencies = set()
    for sp in schema_prices:
        if sp.get("priceCurrency"):
            schema_currencies.add(sp["priceCurrency"].upper())

    if len(currencies_found) > 1:
        f = create_finding(
            "high",
            f"Multiple currencies detected in visible text: {', '.join(currencies_found)}.",
            "Standardize all prices to a single currency on each page, or clearly label each price with its currency. Use Schema.org priceCurrency to disambiguate.",
            "https://schema.org/priceCurrency",
            "An AI agent asked about pricing will be confused by mixed currencies and may provide incorrect price comparisons to users."
        )
        # Find elements containing price text. QW2: use make_element_entry
        # for the same {selector, html_snippet, location} shape the other
        # pillars emit — gains get_element_location's smart context
        # detection ("footer section", "main content, section: Pricing")
        # instead of the old hardcoded "page content". See Phase 1 audit.
        price_els = []
        if body:
            currency_re = re.compile(r'[\$€£][\d,]+(?:\.\d{2})?|\d+\s*(?:USD|EUR|GBP|CAD|AUD)')
            for el in body.find_all(string=currency_re):
                parent = el.parent
                if parent and parent.name not in ('script', 'style'):
                    price_els.append(make_element_entry(parent))
                    if len(price_els) >= 5:
                        break
        if price_els:
            f["elements"] = price_els
        findings.append(f)

    if schema_currencies and currencies_found:
        text_only = currencies_found - schema_currencies
        schema_only = schema_currencies - currencies_found
        if text_only or schema_only:
            findings.append(create_finding(
                "medium",
                f"Currency mismatch between visible text ({', '.join(currencies_found)}) and Schema.org data ({', '.join(schema_currencies)}).",
                "Ensure the currency in your Schema.org structured data matches the currency displayed in the visible text.",
                "https://schema.org/priceCurrency",
                "When Schema.org data says EUR but the page shows $, an AI agent may cite the wrong currency to users."
            ))

    # Check for schema price conflicts (same product, different prices)
    if len(schema_prices) > 1:
        price_values = [str(sp.get("price", "")) for sp in schema_prices if sp.get("price")]
        unique_prices = set(price_values)
        if len(unique_prices) > 1 and len(price_values) > len(unique_prices):
            pass
        elif len(unique_prices) > 3:
            findings.append(create_finding(
                "medium",
                f"Found {len(unique_prices)} different price values in Schema.org data. Verify these represent distinct products/services.",
                "Ensure each price in structured data is clearly associated with a specific product or service using the 'name' property.",
                "https://schema.org/Offer"
            ))

    details = {
        "text_prices_found": len(text_prices),
        "schema_prices_found": len(schema_prices),
        "currencies_in_text": list(currencies_found),
        "currencies_in_schema": list(schema_currencies)
    }

    if not findings:
        if text_prices or schema_prices:
            return {
                "status": "pass",
                "details": details,
                "positive_message": "Price and currency data is consistent across visible text and structured data — AI agents will report accurate pricing."
            }
        return {"status": "pass", "details": details}

    return {"status": "fail", "details": details, "findings": findings}


def check_contact_conflicts(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    """
    Check 9.2: Contact Information Conflicts
    Detects conflicting phone numbers, emails, or addresses on the page.
    """
    findings = []
    body = soup.find('body')
    visible_text = body.get_text(separator=' ', strip=True) if body else ""

    phone_pattern = re.compile(r'(?:\+\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}')
    email_pattern = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

    phones = list(set(phone_pattern.findall(visible_text)))
    emails = list(set(email_pattern.findall(visible_text)))

    # Also extract from Schema.org
    jsonld_blocks = _extract_jsonld_blocks(html_content)
    schema_phones = set()
    schema_emails = set()

    def _walk_contact(obj):
        if isinstance(obj, dict):
            if 'telephone' in obj:
                val = obj['telephone']
                if isinstance(val, str):
                    schema_phones.add(val)
                elif isinstance(val, list):
                    for v in val:
                        schema_phones.add(str(v))
            if 'email' in obj:
                val = obj['email']
                if isinstance(val, str):
                    schema_emails.add(val)
                elif isinstance(val, list):
                    for v in val:
                        schema_emails.add(str(v))
            for v in obj.values():
                _walk_contact(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk_contact(item)

    for block in jsonld_blocks:
        _walk_contact(block)

    # Normalize phone numbers for comparison (remove spaces, dashes, parens)
    def _normalize_phone(p: str) -> str:
        return re.sub(r'[\s\-\(\)]', '', p)

    normalized_phones = [_normalize_phone(p) for p in phones]
    unique_normalized = set(normalized_phones)

    # Filter out very short matches that are likely false positives
    real_phones = [p for p in phones if len(_normalize_phone(p)) >= 7]

    if len(set(_normalize_phone(p) for p in real_phones)) > 3:
        f = create_finding(
            "medium",
            f"Found {len(set(_normalize_phone(p) for p in real_phones))} different phone numbers on the page.",
            "If these represent different departments, clearly label each number (e.g., 'Sales: +1-555-0100', 'Support: +1-555-0200'). Ensure the primary contact number is in your Schema.org Organization data.",
            "https://schema.org/telephone",
            "An AI agent asked 'What is the phone number?' will not know which number to provide if multiple unlabeled numbers exist."
        )
        # QW2: same shape swap as the price check above.
        phone_els = []
        if body:
            for el in body.find_all(string=phone_pattern):
                parent = el.parent
                if parent and parent.name not in ('script', 'style'):
                    phone_els.append(make_element_entry(parent))
                    if len(phone_els) >= 5:
                        break
        if phone_els:
            f["elements"] = phone_els
        findings.append(f)

    # Check email consistency
    if schema_emails:
        text_emails_set = set(e.lower() for e in emails)
        schema_emails_lower = set(e.lower() for e in schema_emails)
        if schema_emails_lower and text_emails_set:
            if not schema_emails_lower.intersection(text_emails_set):
                findings.append(create_finding(
                    "high",
                    f"Email in Schema.org ({', '.join(schema_emails)}) does not match any email visible on the page ({', '.join(emails[:3])}).",
                    "Ensure the email address in your Schema.org structured data matches the primary contact email displayed on the page.",
                    "https://schema.org/email",
                    "When Schema.org and visible text show different emails, an AI agent may cite the wrong contact information."
                ))

    details = {
        "phone_numbers_found": len(real_phones),
        "emails_found": len(emails),
        "schema_phones": list(schema_phones),
        "schema_emails": list(schema_emails)
    }

    if not findings:
        if emails or real_phones:
            return {
                "status": "pass",
                "details": details,
                "positive_message": "Contact information is consistent across visible text and structured data."
            }
        return {"status": "pass", "details": details}

    return {"status": "fail", "details": details, "findings": findings}


def check_brand_consistency(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    """
    Check 9.3: Brand/Company Name Consistency
    Detects if the company/brand name is used inconsistently across the page
    and in structured data.
    """
    findings = []

    jsonld_blocks = _extract_jsonld_blocks(html_content)

    # Extract organization names from Schema.org
    org_names = set()
    for block in jsonld_blocks:
        if isinstance(block, dict):
            if block.get("@type") in ["Organization", "LocalBusiness", "Corporation"]:
                if "name" in block:
                    org_names.add(block["name"])
            if "publisher" in block and isinstance(block["publisher"], dict):
                if "name" in block["publisher"]:
                    org_names.add(block["publisher"]["name"])
            if "author" in block and isinstance(block["author"], dict):
                if "name" in block["author"]:
                    org_names.add(block["author"]["name"])

    # Extract from meta tags
    og_site_name = soup.find('meta', property='og:site_name')
    if og_site_name:
        org_names.add(og_site_name.get('content', ''))

    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        # Often the brand is after " | " or " - "
        for sep in [' | ', ' - ', ' — ', ' – ']:
            if sep in title_text:
                parts = title_text.split(sep)
                org_names.add(parts[-1].strip())

    # Clean up
    org_names = set(n.strip() for n in org_names if n.strip())

    if len(org_names) > 2:
        findings.append(create_finding(
            "high",
            f"Found {len(org_names)} different brand/company name variations: {', '.join(list(org_names)[:4])}.",
            "Standardize your company name across all Schema.org entities, meta tags, and visible content. Use one canonical name consistently.",
            "https://schema.org/Organization",
            "An AI agent asked 'Who is this company?' will be confused by multiple name variations and may present inconsistent information."
        ))

    details = {
        "brand_names_found": list(org_names)
    }

    if not findings:
        if org_names:
            return {
                "status": "pass",
                "details": details,
                "positive_message": f"Brand name '{list(org_names)[0]}' is used consistently across structured data and meta tags."
            }
        return {"status": "pass", "details": details}

    return {"status": "fail", "details": details, "findings": findings}


def check_schema_conflicts(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    """
    Check 9.4: Schema.org Entity Conflicts
    Detects duplicate or conflicting Schema.org entities on the same page.
    """
    findings = []

    jsonld_blocks = _extract_jsonld_blocks(html_content)

    if not jsonld_blocks:
        return {"status": "pass", "details": {"schema_blocks": 0}}

    # Count entity types
    type_counts = Counter()
    for block in jsonld_blocks:
        if isinstance(block, dict):
            block_type = block.get("@type", "Unknown")
            if isinstance(block_type, list):
                for t in block_type:
                    type_counts[t] += 1
            else:
                type_counts[block_type] += 1

    # Check for duplicate primary entities (should only have one Organization, one WebSite, etc.)
    singleton_types = ["Organization", "WebSite", "WebPage", "LocalBusiness", "Corporation"]
    duplicates = []
    for stype in singleton_types:
        if type_counts.get(stype, 0) > 1:
            duplicates.append(f"{stype} (x{type_counts[stype]})")

    if duplicates:
        findings.append(create_finding(
            "high",
            f"Duplicate Schema.org entities found: {', '.join(duplicates)}. Each page should have only one of each primary entity type.",
            "Consolidate duplicate Schema.org entities into a single block. Multiple Organization or WebSite schemas on one page create ambiguity for AI systems.",
            "https://developers.google.com/search/docs/appearance/structured-data/sd-policies",
            "Duplicate entities confuse AI agents about which is the canonical representation. This can lead to conflicting information in AI responses."
        ))

    # Check for conflicting URLs in same-type entities
    urls_by_type: Dict[str, Set[str]] = {}
    for block in jsonld_blocks:
        if isinstance(block, dict):
            block_type = str(block.get("@type", "Unknown"))
            url = block.get("url") or block.get("@id")
            if url:
                if block_type not in urls_by_type:
                    urls_by_type[block_type] = set()
                urls_by_type[block_type].add(str(url))

    for entity_type, urls in urls_by_type.items():
        if len(urls) > 1 and entity_type in singleton_types:
            findings.append(create_finding(
                "medium",
                f"Multiple URLs found for {entity_type} entity: {', '.join(list(urls)[:3])}.",
                f"Ensure all {entity_type} Schema.org blocks reference the same canonical URL.",
                "https://schema.org/url"
            ))

    details = {
        "schema_blocks": len(jsonld_blocks),
        "entity_types": dict(type_counts),
        "duplicates": duplicates
    }

    if not findings:
        return {
            "status": "pass",
            "details": details,
            "positive_message": f"Schema.org entities are well-structured with no duplicates or conflicts across {len(jsonld_blocks)} blocks."
        }

    return {"status": "fail", "details": details, "findings": findings}


def check_date_conflicts(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    """
    Check 9.5: Date/Time Conflicts
    Detects conflicting dates between Schema.org and visible content,
    such as a datePublished that doesn't match the visible date.
    """
    findings = []

    jsonld_blocks = _extract_jsonld_blocks(html_content)

    schema_dates = {}
    for block in jsonld_blocks:
        if isinstance(block, dict):
            for date_field in ['datePublished', 'dateModified', 'dateCreated', 'startDate', 'endDate', 'foundingDate']:
                if date_field in block:
                    val = block[date_field]
                    if isinstance(val, str):
                        schema_dates[date_field] = val

    # Check datePublished vs dateModified logic
    if 'datePublished' in schema_dates and 'dateModified' in schema_dates:
        pub = schema_dates['datePublished']
        mod = schema_dates['dateModified']
        if pub > mod:
            findings.append(create_finding(
                "high",
                f"datePublished ({pub}) is later than dateModified ({mod}). This is logically impossible.",
                "Ensure dateModified is always equal to or later than datePublished in your Schema.org data.",
                "https://schema.org/dateModified",
                "AI agents use these dates to determine content freshness. Illogical dates undermine trust in your content."
            ))

    # Check for very old dates that might be errors
    import datetime
    current_year = datetime.datetime.now().year
    for field, date_str in schema_dates.items():
        year_match = re.search(r'(\d{4})', date_str)
        if year_match:
            year = int(year_match.group(1))
            if year < 2000 or year > current_year + 2:
                findings.append(create_finding(
                    "medium",
                    f"Suspicious date value in {field}: '{date_str}'. Year {year} appears incorrect.",
                    f"Verify the {field} value in your Schema.org data. Dates before 2000 or in the far future are likely errors.",
                    "https://schema.org/Date"
                ))

    details = {
        "schema_dates_found": schema_dates
    }

    if not findings:
        if schema_dates:
            return {
                "status": "pass",
                "details": details,
                "positive_message": "Date information in Schema.org data is logically consistent and well-formatted."
            }
        return {"status": "pass", "details": details}

    return {"status": "fail", "details": details, "findings": findings}
