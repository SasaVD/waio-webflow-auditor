import { Component } from 'react';
import type { ReactNode, ErrorInfo } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class DashboardErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Dashboard error:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-surface flex items-center justify-center p-6">
          <div className="max-w-md text-center">
            <div className="w-14 h-14 mx-auto mb-5 bg-severity-critical/10 rounded-2xl flex items-center justify-center">
              <AlertTriangle size={24} className="text-severity-critical" />
            </div>
            <h1 className="text-xl font-bold text-text font-heading mb-2">
              Something went wrong
            </h1>
            <p className="text-sm text-text-secondary mb-1">
              The dashboard encountered an unexpected error.
            </p>
            <p className="text-xs text-text-muted mb-6 font-mono bg-surface-raised border border-border rounded-lg px-3 py-2 break-all">
              {this.state.error?.message || 'Unknown error'}
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => this.setState({ hasError: false, error: null })}
                className="bg-surface-overlay hover:bg-surface-raised border border-border text-text font-semibold px-4 py-2.5 rounded-xl transition-all text-sm"
              >
                Try Again
              </button>
              <a
                href="/"
                className="bg-accent hover:bg-accent-hover text-white font-semibold px-4 py-2.5 rounded-xl transition-all text-sm"
              >
                Back to Home
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
