# WAIO Webflow Audit Tool - 9-Pillar Deterministic Analysis

The **WAIO Webflow Audit Tool** is a high-performance programmatic engine designed to perform evidence-based technical audits of Webflow websites. Unlike general SEO tools, it relies on deterministic rules and W3C/Schema standards to provide a clear, zero-hallucination health score.

## The 9 Audit Pillars

The tool now performs a comprehensive analysis across 9 specialized categories:

1.  **Semantic HTML**: W3C-standard structure validation and heading hierarchy.
2.  **Structured Data**: JSON-LD & Microdata integrity (Schema.org).
3.  **AEO Content**: AI citation readiness and structure audit for Answer Engines.
4.  **CSS Quality**: Framework detection (Client-First, Relume) and naming consistency.
5.  **JS Bloat**: Deep analysis of Webflow-specific and third-party script overhead.
6.  **WCAG Accessibility**: WCAG 2.1 AA compliance scans via Playwright engine.
7.  **RAG Readiness**: Chunking and context quality for LLM/RAG integration.
8.  **Agentic Protocols**: Verification of `llms.txt`, `robots.txt`, and MCP/A2A readiness.
9.  **Data Integrity**: Conflict detection and data-integrity issues in the DOM.

---

## Tech Stack

-   **Backend**: Python, FastAPI, Playwright (for dynamic DOM rendering), BeautifulSoup4, Extruct.
-   **Frontend**: React, TypeScript, Vite, TailwindCSS, Framer Motion (animations), Lucide React (icons).
-   **Exporting**: PDF, Markdown, and Direct Emailing via SendGrid/SMTP.

---

## Getting Started

### Prerequisites

-   Python 3.10+
-   Node.js 18+
-   `playwright` browser binaries

### Backend Setup

1.  Navigate to the `backend` directory.
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```
4.  Run the development server:
    ```bash
    python -m uvicorn main:app --reload --port 8000
    ```

### Frontend Setup

1.  Navigate to the `frontend` directory.
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the development server:
    ```bash
    npm run dev
    ```

---

## Project Structure

-   `/backend`: API logic, reporting engines, and the 9 specialized auditor modules.
-   `/frontend`: React components, including the 9-pillar dashboard and deterministic loading state.
-   `/waio_webflow_audit_tool_master_prompt_v1.2.md`: The updated master architecture and prompt log.

---

## License
Built by Veza Digital. Use for deterministic analysis of Webflow foundations.
