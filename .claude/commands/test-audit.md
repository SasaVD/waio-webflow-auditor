# /project:test-audit

Run a test audit against a URL and validate the output structure.

**Arguments:** url (optional, defaults to https://www.vezadigital.com)

**Steps:**

1. Start the backend: `cd backend && python -m uvicorn main:app --port 8000 &`
2. Wait 5 seconds for startup
3. Send POST request:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/audit \
     -H "Content-Type: application/json" \
     -d '{"url": "{url}"}'
   ```
4. Validate response structure:
   - Has `url`, `audit_timestamp`, `overall_score`, `overall_label`
   - Has `categories` with all registered pillars
   - Each category has `score`, `label`, `checks`
   - `positive_findings` is a non-empty list
   - `summary` has `total_findings`, `critical`, `high`, `medium`, `top_priorities`
5. Check for errors in the response
6. Print summary: overall score, pillar scores, finding counts by severity
7. Kill the background uvicorn process
