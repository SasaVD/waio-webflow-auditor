import asyncio
from bs4 import BeautifulSoup
from internal_linking_auditor import run_internal_linking_audit
from css_js_auditor import check_framework_detection
from scoring import calculate_score

def test_il():
    html = "<html><body><a href='/about'>About</a><a href='https://example.com/contact'>Contact</a></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    res = run_internal_linking_audit(soup, html, 'https://example.com', None)
    print("Internal Linking Res:")
    print(res)

    print("\nCSS Framework Check:")
    css = {"positive_message": "", "findings": [], "status": "pass", "details": {"unique_classes": 40}}
    # Wait, check_framework_detection takes soup and class_data. Wait, I'll just skip testing css framework since it requires fetching sheets
    
test_il()
