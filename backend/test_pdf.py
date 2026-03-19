import json
from pdf_generator import generate_pdf

# Minimal dummy report
report = {
    "url": "https://example.com",
    "audit_timestamp": "2026-03-09T17:00:00Z",
    "overall_score": 85,
    "overall_label": "Good",
    "summary": {
        "total_findings": 10,
        "critical": 1,
        "high": 2,
        "medium": 7,
        "top_priorities": ["Fix accessibility", "Add alt text"]
    },
    "categories": {
        "semantic_html": {
            "score": 90,
            "label": "Excellent",
            "checks": {
                "headings": {"findings": [{"severity": "medium", "description": "Too few headings", "recommendation": "Add more H2s"}]}
            }
        }
    },
    "positive_findings": [
        {"text": "Good alt text ratio", "credibility_anchor": "Research shows alt text improves SEO by 20%"}
    ]
}

try:
    pdf_bytes = generate_pdf(report)
    with open("test.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("PDF OK")
except Exception as e:
    import traceback
    traceback.print_exc()
