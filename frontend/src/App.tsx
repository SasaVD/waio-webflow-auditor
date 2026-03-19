import { useState } from 'react';
import { AuditForm } from './components/AuditForm';
import { LoadingState } from './components/LoadingState';
import { AuditReport } from './components/AuditReport';

function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [auditedUrl, setAuditedUrl] = useState<string>('');

  const handleRunAudit = async (url: string) => {
    setIsLoading(true);
    setError(null);
    setReport(null);
    setAuditedUrl(url);

    const apiUrl = import.meta.env.PROD ? '/api/audit' : 'http://127.0.0.1:8000/api/audit';

    try {
      const res = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to complete audit');
      }

      const data = await res.json();
      setReport(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewAudit = () => {
    setReport(null);
    setError(null);
    setAuditedUrl('');
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
            <span className="text-lg font-bold tracking-tight text-text-primary">
              WAIO <span className="text-text-muted font-medium">Audit Engine</span>
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden sm:inline text-xs font-medium text-text-muted uppercase tracking-widest">
              by Veza Digital
            </span>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main>
        {!report && !isLoading && (
          <AuditForm onRunAudit={handleRunAudit} isLoading={isLoading} error={error} />
        )}

        {isLoading && <LoadingState url={auditedUrl} />}

        {report && !isLoading && (
          <AuditReport report={report} onNewAudit={handleNewAudit} />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-surface-dark text-text-on-dark-muted py-12 mt-auto">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 bg-primary rounded-md flex items-center justify-center">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
            <span className="text-sm font-semibold text-text-on-dark">WAIO Audit Engine</span>
          </div>
          <p className="text-xs text-text-on-dark-muted">
            Built on W3C, Schema.org & WCAG 2.1 standards. No AI hallucinations — deterministic analysis only.
          </p>
          <a
            href="https://www.vezadigital.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-semibold text-primary hover:text-white transition-colors"
          >
            vezadigital.com
          </a>
        </div>
      </footer>
    </div>
  );
}

export default App;
