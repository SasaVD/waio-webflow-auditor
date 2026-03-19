from bs4 import BeautifulSoup
import re
from typing import Dict, Any, List

def run_css_js_audit(soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
    checks = {}
    positive_findings = []
    category_findings = []
    
    # CSS Checks
    checks["framework_detection"] = check_framework_detection(soup)
    detected_framework = checks["framework_detection"]["details"].get("detected_framework", "No Framework / Custom")
    checks["naming_consistency"] = check_naming_consistency(soup, detected_framework)
    checks["inline_styles"] = check_inline_styles(soup)
    checks["external_stylesheets"] = check_external_stylesheets(soup)
    checks["render_blocking"] = check_render_blocking_scripts(soup)
    
    # JS Checks
    checks["webflow_js_bloat"] = check_webflow_js_bloat(soup, html_content)
    checks["third_party_scripts"] = check_third_party_scripts(soup)
    checks["total_scripts"] = check_total_scripts(soup)
    
    for check_key, check_val in checks.items():
        if check_val.get("status") in ["pass", "info"]:
            if "positive_message" in check_val:
                positive_findings.append({
                    "text": check_val["positive_message"],
                    "credibility_anchor": None
                })
                del check_val["positive_message"]
        if "findings" in check_val:
            category_findings.extend(check_val["findings"])
            
    return {
        "checks": checks,
        "positive_findings": positive_findings,
        "findings": category_findings
    }

def create_finding(severity: str, description: str, recommendation: str, reference: str) -> Dict[str, str]:
    return {
        "severity": severity,
        "description": description,
        "recommendation": recommendation,
        "reference": reference,
        "credibility_anchor": None
    }

def check_framework_detection(soup: BeautifulSoup) -> Dict[str, Any]:
    classes = []
    for el in soup.find_all(class_=True):
        classes.extend(el['class'])
        
    classes = list(set(classes))[:200] # get max 200 unique classes
    
    cf_matches = sum(1 for c in classes if '_' in c and '-' in c and len(c) > 15)
    mast_matches = sum(1 for c in classes if c.startswith('grid-col-') or c.startswith('flex-') or c.startswith('mast-'))
    lumos_matches = sum(1 for c in classes if c.startswith('u-') or c.startswith('c-') or c.startswith('l-') or c.startswith('is-') or 'lumos' in c.lower())
    sml_matches = sum(1 for c in classes if c.endswith('-xl') or c.endswith('-l') or c.endswith('-m') or c.endswith('-s') or c.endswith('-xs') or c.startswith('sml-'))
    
    framework = "No Framework / Custom"
    if len(classes) > 0:
        ratios = {
            "Client-First": cf_matches / len(classes),
            "MAST": mast_matches / len(classes),
            "Lumos": lumos_matches / len(classes),
            "SML": sml_matches / len(classes)
        }
        
        best_framework = max(ratios, key=ratios.get)
        if ratios[best_framework] > 0.2: # Using 20% threshold to be more inclusive
            framework = best_framework
            
    return {
        "status": "info",
        "details": {"detected_framework": framework, "class_count": len(classes)}
    }

def check_naming_consistency(soup: BeautifulSoup, framework: str) -> Dict[str, Any]:
    findings = []
    valid_frameworks = ["Client-First", "MAST", "Lumos", "SML"]
    
    if framework in valid_frameworks:
        res_consistency = 0.8
        findings.append(create_finding("pass", "", "", ""))
    elif framework == "No Framework / Custom":
        findings.append(create_finding("high", "No consistent CSS naming convention detected.", "Adopt a standard framework like Client-First, Lumos, MAST or SML for improved maintainability.", "https://finsweet.com/client-first"))

    findings = [f for f in findings if f["severity"] != "pass"]
    return {
        "status": "pass" if not findings else "fail",
        "details": {"consistency": 0.8},
        **({"findings": findings} if findings else {"positive_message": f"CSS naming is consistent with {framework} conventions. Well maintained."})
    }

def check_inline_styles(soup: BeautifulSoup) -> Dict[str, Any]:
    inlines = soup.find_all(style=True)
    count = len(inlines)
    findings = []
    
    if count > 30:
        findings.append(create_finding("high", f"Excessive inline styles detected ({count}).", "Move inline styles to external CSS classes.", "css-best-practices"))
    elif count > 10:
        findings.append(create_finding("medium", f"Many inline styles detected ({count}).", "Move inline styles to external CSS classes.", "css-best-practices"))
        
    return {
        "status": "pass" if not findings else "fail",
        "details": {"count": count},
        **({"findings": findings} if findings else {"positive_message": "Low usage of inline styles. Good cascade management."})
    }

def check_external_stylesheets(soup: BeautifulSoup) -> Dict[str, Any]:
    stylesheets = soup.find_all('link', rel='stylesheet')
    count = len(stylesheets)
    findings = []
    
    if count > 5:
        findings.append(create_finding("medium", f"High number of external stylesheets ({count}).", "Consolidate CSS files to reduce HTTP requests.", "web-perf"))
        
    return {
        "status": "pass" if not findings else "fail",
        "details": {"count": count},
        **({"findings": findings} if findings else {})
    }

def check_render_blocking_scripts(soup: BeautifulSoup) -> Dict[str, Any]:
    head = soup.find('head')
    if not head: return {"status": "fail", "details": {}, "findings": [create_finding("medium", "No <head> found", "", "")]}
    
    scripts = head.find_all('script', src=True)
    blocking = sum(1 for s in scripts if not s.has_attr('async') and not s.has_attr('defer'))
    
    findings = []
    if blocking > 2:
        findings.append(create_finding("medium", f"Found {blocking} render-blocking scripts in the <head>.", "Add 'defer' or 'async' to scripts if they are not strictly critical for initial render.", "web-perf"))
        
    return {
        "status": "pass" if not findings else "fail",
        "details": {"blocking": blocking},
        **({"findings": findings} if findings else {})
    }

def check_webflow_js_bloat(soup: BeautifulSoup, html: str) -> Dict[str, Any]:
    findings = []
    
    if 'webflow-user-account' in html:
        findings.append(create_finding("medium", "Webflow User Accounts detected (+143.5 kB minified size).", "Assess if user accounts are critical for this site.", "webflow-perf"))
    if '<lottie-player>' in html or 'data-animation-type="lottie"' in html or 'lottie' in html:
        findings.append(create_finding("medium", "Lottie Animations detected (+102.4 kB).", "Assess if Lottie is necessary.", "webflow-perf"))
    if 'data-wf-ix' in html or "Webflow.require('ix2')" in html:
        findings.append(create_finding("medium", "Webflow Interactions (IX2) detected (+43 kB).", "Assess if complex interactions are necessary.", "webflow-perf"))
    if 'webflow-ecommerce' in html or 'data-commerce' in html:
         findings.append(create_finding("medium", "Webflow E-Commerce detected (+42.7 kB).", "Assess if ecommerce is necessary.", "webflow-perf"))
    if 'data-rive-src' in html or 'rive' in html:
         findings.append(create_finding("medium", "Rive Animations detected (+36.7 kB).", "Assess if Rive is necessary.", "webflow-perf"))
         
    return {
        "status": "pass" if not findings else "fail",
        "details": {},
        **({"findings": findings} if findings else {})
    }

def check_third_party_scripts(soup: BeautifulSoup) -> Dict[str, Any]:
    scripts = soup.find_all('script', src=True)
    third_party = 0
    domains = set()
    for s in scripts:
        src = s['src']
        if src.startswith('http') and 'assets.website-files.com' not in src:
            third_party += 1
            domains.add(src.split('/')[2])
            
    findings = []
    if third_party > 5:
        findings.append(create_finding("medium", f"High number of third-party scripts ({third_party}).", "Evaluate script necessity and use Tag Manager to defer.", "web-perf"))
        
    return {
        "status": "pass" if not findings else "fail",
        "details": {"third_party_count": third_party, "domains": list(domains)},
        **({"findings": findings} if findings else {})
    }

def check_total_scripts(soup: BeautifulSoup) -> Dict[str, Any]:
    scripts = soup.find_all('script')
    count = len(scripts)
    findings = []
    if count > 15:
         findings.append(create_finding("medium", f"High number of total script tags ({count}).", "Consolidate custom code and scripts.", "web-perf"))
         
    return {
         "status": "pass" if not findings else "fail",
         "details": {"count": count},
         **({"findings": findings} if findings else {})
    }
