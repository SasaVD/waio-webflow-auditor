import { useState, useEffect } from 'react';
import { Plus, Trash2, ToggleLeft, ToggleRight, ArrowLeft } from 'lucide-react';

const API_BASE = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

interface ScheduleManagerProps {
  onBack: () => void;
}

export const ScheduleManager: React.FC<ScheduleManagerProps> = ({ onBack }) => {
  const [schedules, setSchedules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formUrl, setFormUrl] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formFrequency, setFormFrequency] = useState('weekly');
  const [formMaxPages, setFormMaxPages] = useState(1);

  const fetchSchedules = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/schedules`);
      const data = await res.json();
      setSchedules(data.schedules || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchSchedules(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    let url = formUrl.trim();
    if (!url) return;
    if (!url.startsWith('http')) url = 'https://' + url;

    await fetch(`${API_BASE}/api/schedules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, email: formEmail, frequency: formFrequency, max_pages: formMaxPages }),
    });
    setFormUrl(''); setFormEmail(''); setShowForm(false);
    fetchSchedules();
  };

  const handleToggle = async (id: number, currentEnabled: boolean) => {
    await fetch(`${API_BASE}/api/schedules/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !currentEnabled }),
    });
    fetchSchedules();
  };

  const handleDelete = async (id: number) => {
    await fetch(`${API_BASE}/api/schedules/${id}`, { method: 'DELETE' });
    fetchSchedules();
  };

  return (
    <div className="bg-surface-secondary min-h-screen pb-12">
      <div className="bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-6 py-6 flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-text-muted uppercase tracking-widest mb-1">Scheduled Audits</div>
            <h2 className="text-lg font-bold text-text-primary">Manage recurring audits with regression alerts</h2>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white font-semibold px-4 py-2.5 rounded-xl transition-all text-sm"
            >
              <Plus size={16} /> New Schedule
            </button>
            <button onClick={onBack} className="flex items-center gap-2 bg-white hover:bg-surface-secondary border border-border text-text-primary font-semibold px-4 py-2.5 rounded-xl transition-all text-sm">
              <ArrowLeft size={16} /> Back
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {showForm && (
          <form onSubmit={handleCreate} className="bg-white border border-border-light rounded-2xl p-6 mb-8 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-text-muted uppercase tracking-wider mb-1.5">Website URL</label>
                <input
                  type="text"
                  value={formUrl}
                  onChange={e => setFormUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="w-full px-4 py-2.5 border border-border rounded-xl text-sm focus:outline-none focus:border-primary/40"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-text-muted uppercase tracking-wider mb-1.5">Alert Email</label>
                <input
                  type="email"
                  value={formEmail}
                  onChange={e => setFormEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="w-full px-4 py-2.5 border border-border rounded-xl text-sm focus:outline-none focus:border-primary/40"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-text-muted uppercase tracking-wider mb-1.5">Frequency</label>
                <select
                  value={formFrequency}
                  onChange={e => setFormFrequency(e.target.value)}
                  className="w-full px-4 py-2.5 border border-border rounded-xl text-sm focus:outline-none focus:border-primary/40 bg-white"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold text-text-muted uppercase tracking-wider mb-1.5">Max Pages</label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={formMaxPages}
                  onChange={e => setFormMaxPages(parseInt(e.target.value) || 1)}
                  className="w-full px-4 py-2.5 border border-border rounded-xl text-sm focus:outline-none focus:border-primary/40"
                />
              </div>
            </div>
            <button type="submit" className="bg-primary hover:bg-primary/90 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-all">
              Create Schedule
            </button>
          </form>
        )}

        {loading && <div className="text-center py-12 text-text-muted">Loading schedules...</div>}

        {!loading && schedules.length === 0 && !showForm && (
          <div className="text-center py-12 text-text-muted">No scheduled audits yet. Click "New Schedule" to create one.</div>
        )}

        {!loading && schedules.length > 0 && (
          <div className="space-y-3">
            {schedules.map(s => (
              <div key={s.id} className={`bg-white border rounded-xl p-5 flex items-center justify-between transition-all ${s.enabled ? 'border-border-light' : 'border-border opacity-60'}`}>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-text-primary truncate">{s.url}</div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-text-muted">{s.email}</span>
                    <span className="text-[10px] font-bold uppercase tracking-wider bg-surface-secondary px-2 py-0.5 rounded text-text-muted">{s.frequency}</span>
                    <span className="text-[10px] text-text-muted">{s.max_pages > 1 ? `${s.max_pages} pages` : 'Single page'}</span>
                    {s.last_run && <span className="text-[10px] text-text-muted">Last: {new Date(s.last_run).toLocaleDateString()}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => handleToggle(s.id, s.enabled)}
                    className={`p-2 rounded-lg transition-colors ${s.enabled ? 'text-primary hover:bg-primary/5' : 'text-text-muted hover:bg-surface-secondary'}`}
                    title={s.enabled ? 'Disable' : 'Enable'}
                  >
                    {s.enabled ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
                  </button>
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="p-2 rounded-lg text-text-muted hover:text-red-500 hover:bg-red-50 transition-colors"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
