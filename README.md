# WAIO Webflow Audit Tool - 10-Pillar Deterministic Analysis

The **WAIO Webflow Audit Tool** is a high-performance programmatic engine designed to perform evidence-based technical audits of Webflow websites. Unlike general SEO tools, it relies on deterministic rules and W3C/Schema standards to provide a clear, zero-hallucination health score.

## The 10 Audit Pillars

The tool now performs a comprehensive analysis across 10 specialized categories:

1.  **Semantic HTML**: W3C-standard structure validation and heading hierarchy.
2.  **Structured Data**: JSON-LD & Microdata integrity (Schema.org) including dual-format FAQPage checks.
3.  **AEO Content (Generative Engine Optimization)**: AI citation readiness and structure audit for Answer Engines (e.g., Conclusion-First logic, 2023 Princeton/Stanford HAI data metrics).
4.  **CSS Quality**: Framework detection (Client-First, Relume) and naming consistency.
5.  **JS Bloat**: Deep analysis of Webflow-specific and third-party script overhead.
6.  **WCAG Accessibility**: WCAG 2.1 AA compliance scans via Playwright engine.
7.  **RAG Readiness**: Chunking and context quality for LLM/RAG integration.
8.  **Agentic Protocols**: Verification of `llms.txt`, `robots.txt`, and MCP/A2A readiness.
9.  **Data Integrity**: Conflict detection and data-integrity issues in the DOM.
10. **Internal Linking**: Analysis of site-wide internal link structure, dead links, and orphan pages.

---

## Tech Stack

-   **Backend**: Python, FastAPI, Playwright (for dynamic DOM rendering), BeautifulSoup4, Extruct.
-   **Frontend**: React, TypeScript, Vite, TailwindCSS, Framer Motion (animations), Lucide React (icons).
-   **Exporting**: PDF, Markdown, and Direct Emailing via SendGrid/SMTP.
-   **Database**: aiosqlite (Async SQLite) natively integrated for fast, non-blocking storage.

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
    *Note: Ensure the virtual environment is activated during installation, otherwise packages like `requests`, `bs4`, and `aiosqlite` might throw global ImportErrors.*
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

## Deployment (Railway)

This application is fully containerized and configured for deployment on Railway:
1.  **Backend**: Uses the provided Dockerfile. It installs OS-level dependencies, Python packages (including Playwright and Chromium), and runs the Uvicorn server automatically.
2.  **Frontend**: Deployed via standard Node.js/Vite build steps. *Make sure all TypeScript type-checking errors (e.g., implicitly `any` types) are resolved before deployment, as Railway enforces strict compilation.*

---

## Project Structure

-   `/backend`: API logic, reporting engines, and the 10 specialized auditor modules.
-   `/frontend`: React components, including the 10-pillar dashboard and deterministic loading state.
-   `/waio_webflow_audit_tool_master_prompt_v1.2.md`: The master architecture and prompt log.

---

## License
Built by Veza Digital. Use for deterministic analysis of Webflow foundations.
