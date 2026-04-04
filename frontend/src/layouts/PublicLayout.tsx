import { Outlet, Link } from 'react-router';
import { UserMenu } from '../components/auth/UserMenu';

export function PublicLayout() {
  return (
    <div className="min-h-screen bg-surface flex flex-col">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-surface/80 backdrop-blur-lg border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
            <span className="text-lg font-bold tracking-tight text-text">
              WAIO <span className="text-text-muted font-medium">Audit Engine</span>
            </span>
          </Link>
          <div className="flex items-center gap-4">
            <Link
              to="/schedules"
              className="text-xs font-semibold text-text-muted hover:text-accent transition-colors uppercase tracking-wider"
            >
              Schedules
            </Link>
            <span className="hidden sm:inline text-xs font-medium text-text-muted uppercase tracking-widest">
              by Veza Digital
            </span>
            <UserMenu />
          </div>
        </div>
      </nav>

      {/* Page Content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-surface text-text-muted py-12 mt-auto border-t border-border">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 bg-accent rounded-md flex items-center justify-center">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
            <span className="text-sm font-semibold text-text">WAIO Audit Engine</span>
          </div>
          <p className="text-xs text-text-muted">
            Built on W3C, Schema.org & WCAG 2.1 standards. Deterministic analysis only.
          </p>
          <a
            href="https://www.vezadigital.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-semibold text-accent hover:text-text transition-colors"
          >
            vezadigital.com
          </a>
        </div>
      </footer>
    </div>
  );
}
