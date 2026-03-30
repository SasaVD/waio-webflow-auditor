# Code Style Rules — WAIO Audit Tool

## Python (Backend)

### General
- Python 3.10+ syntax. Use `str | None` union syntax, not `Optional[str]`.
- All async functions use `async def` with proper `await`.
- Type hints on all function signatures. Use `Dict[str, Any]` for complex returns.
- Imports: stdlib first, then third-party, then local modules. One blank line between groups.

### Auditor Module Pattern
Every auditor file follows this exact pattern:

```python
from bs4 import BeautifulSoup
from typing import Dict, Any, List

def run_[pillar]_audit(soup: BeautifulSoup, html_content: str, ...) -> Dict[str, Any]:
    checks = {}
    positive_findings = []
    category_findings = []

    checks["check_name"] = check_function(soup, ...)

    # Collect findings and positives from all checks
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
```

### Finding Severities
- `critical`: Fundamental issue breaking standards compliance (deducts ~15-18 pts)
- `high`: Significant impact on SEO/accessibility (deducts ~8-10 pts)
- `medium`: Minor issue or missing enhancement (deducts ~3-4 pts)

### Credibility Anchors
Every finding SHOULD include a `why_it_matters` or `credibility_anchor` field with a specific statistic from a verified study. Format: "Statistic + (Source, Year)."
Example: "Readable text at Flesch-Kincaid Grade 6-8 earns 15% more AI citations (SE Ranking, 2025)."

## TypeScript (Frontend)

### General
- Strict mode enabled. No implicit `any`.
- Functional components only. Use hooks (`useState`, `useEffect`, `useMemo`).
- Props interfaces defined inline or in the same file.

### Component Pattern
```tsx
interface ComponentProps {
  data: SomeType;
  onAction: () => void;
}

export const Component: React.FC<ComponentProps> = ({ data, onAction }) => {
  // component logic
};
```

### Styling
- Tailwind utility classes exclusively. No inline `style` attributes except for dynamic values (colors from data).
- Use design tokens from `frontend/src/index.css` @theme block.
- Color tokens: `text-primary`, `bg-surface-secondary`, `border-border-light`, etc.
- Score colors: `text-score-excellent`, `text-score-good`, `text-score-needs`, `text-score-poor`, `text-score-critical`.
- Severity colors: `text-severity-critical`, `bg-severity-critical-bg`, etc.

### Animation
- Use Framer Motion for enter/exit animations.
- Pattern: `initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}`
- Keep animations subtle and fast (300-500ms).

### Pillar Registration
When adding a new pillar, update the `pillarMeta` object in `AuditReport.tsx`:
```tsx
const pillarMeta: Record<string, { icon: any; label: string }> = {
  semantic_html: { icon: FileCode, label: 'Semantic HTML' },
  // ... add new pillar here
};
```
Also update: `LoadingState.tsx` steps array, `scoring.py` weights, `report_generator.py` categories.
