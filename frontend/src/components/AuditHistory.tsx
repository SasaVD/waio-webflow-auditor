import { useState, useEffect } from 'react';
import { ArrowLeft, TrendingDown, TrendingUp, Minus } from 'lucide-react';

interface AuditHistoryProps {
  url: string;
  onBack: () => void;
}

const API_BASE = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

const scoreColor = (label: string): string => {
  const l = label?.toLowerCase() || '';
  if (l === 'excellent') return '#84CC16';
  if (l === 'good') return '#84CC16';
  if (l === 'needs improvement') return '#F59E0B';
  if (l === 'poor') return '#EF4444';
  return '#DC2626';
};

export const AuditHistory: React.FC<AuditHistoryProps> = ({ url, onBack }) => {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/history?url=${encodeURIComponent(url)}`)
      .then(res => res.json())
      .then(data => {
        setHistory(data.history || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [url]);

  const maxScore = 100;

  return (
    <div className="bg-surface-secondary min-h-screen pb-12">
      <div className="bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-6 py-6 flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-text-muted uppercase tracking-widest mb-1">Audit History</div>
            <h2 className="text-lg font-bold text-text-primary truncate max-w-xl">{url}</h2>
          </div>
          <button onClick={onBack} className="flex items-center gap-2 bg-white hover:bg-surface-secondary border border-border text-text-primary font-semibold px-4 py-2.5 rounded-xl transition-all text-sm">
            <ArrowLeft size={16} /> Back
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {loading && <div className="text-center py-12 text-text-muted">Loading history...</div>}

        {!loading && history.length === 0 && (
          <div className="text-center py-12 text-text-muted">No audit history found for this URL.</div>
        )}

        {!loading && history.length > 0 && (
          <>
            {/* Score trend bar chart */}
            <div className="bg-white border border-border-light rounded-2xl p-6 mb-8">
              <h3 className="text-sm font-bold text-text-primary mb-4">Score Trend</h3>
              <div className="flex items-end gap-2 h-40">
                {[...history].reverse().slice(-20).map((entry, i) => (
                  <div key={i} className="flex-1 flex flex-col items-center justify-end h-full">
                    <div className="text-[10px] font-bold text-text-muted mb-1">{entry.overall_score}</div>
                    <div
                      className="w-full rounded-t-md transition-all"
                      style={{
                        height: `${(entry.overall_score / maxScore) * 100}%`,
                        backgroundColor: scoreColor(entry.overall_label),
                        minHeight: '4px'
                      }}
                    />
                    <div className="text-[8px] text-text-muted mt-1 truncate w-full text-center">
                      {new Date(entry.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* History table */}
            <div className="bg-white border border-border-light rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="bg-surface-secondary border-b border-border">
                    <th className="text-left text-[10px] font-bold text-text-muted uppercase tracking-widest px-6 py-3">Date</th>
                    <th className="text-left text-[10px] font-bold text-text-muted uppercase tracking-widest px-6 py-3">Type</th>
                    <th className="text-left text-[10px] font-bold text-text-muted uppercase tracking-widest px-6 py-3">Score</th>
                    <th className="text-left text-[10px] font-bold text-text-muted uppercase tracking-widest px-6 py-3">Label</th>
                    <th className="text-left text-[10px] font-bold text-text-muted uppercase tracking-widest px-6 py-3">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((entry, i) => {
                    const prev = history[i + 1]; // history is DESC
                    const diff = prev ? entry.overall_score - prev.overall_score : 0;
                    return (
                      <tr key={entry.id} className="border-b border-border-light last:border-0 hover:bg-surface-secondary/50 transition-colors">
                        <td className="px-6 py-3 text-sm text-text-primary">
                          {new Date(entry.created_at).toLocaleString()}
                        </td>
                        <td className="px-6 py-3">
                          <span className="text-xs font-semibold bg-surface-secondary px-2 py-1 rounded text-text-muted uppercase">
                            {entry.audit_type}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-lg font-bold" style={{ color: scoreColor(entry.overall_label) }}>
                          {entry.overall_score}
                        </td>
                        <td className="px-6 py-3 text-xs font-bold uppercase" style={{ color: scoreColor(entry.overall_label) }}>
                          {entry.overall_label}
                        </td>
                        <td className="px-6 py-3">
                          {diff > 0 && (
                            <span className="inline-flex items-center gap-1 text-xs font-bold text-green-600">
                              <TrendingUp size={14} /> +{diff}
                            </span>
                          )}
                          {diff < 0 && (
                            <span className="inline-flex items-center gap-1 text-xs font-bold text-red-600">
                              <TrendingDown size={14} /> {diff}
                            </span>
                          )}
                          {diff === 0 && prev && (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-text-muted">
                              <Minus size={14} /> 0
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
