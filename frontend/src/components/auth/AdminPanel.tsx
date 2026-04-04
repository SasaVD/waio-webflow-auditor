import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Users,
  Plus,
  Shield,
  ShieldCheck,
  Loader2,
  AlertCircle,
  CheckCircle2,
  X,
  History,
  ExternalLink,
} from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { useNavigate } from 'react-router';

const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

interface UserRecord {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  auth_provider: string;
  avatar_url?: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

interface AuditRecord {
  id: string;
  url: string;
  tier: string;
  audit_type: string;
  overall_score: number;
  overall_label: string;
  created_at: string;
  detected_cms: string | null;
}

const scoreColor = (score: number): string => {
  if (score >= 90) return 'text-success';
  if (score >= 75) return 'text-score-good';
  if (score >= 55) return 'text-warning';
  if (score >= 35) return 'text-severity-high';
  return 'text-severity-critical';
};

export default function AdminPanel() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuthStore();
  const navigate = useNavigate();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [audits, setAudits] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [newRole, setNewRole] = useState<'user' | 'admin'>('user');
  const [newPassword, setNewPassword] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!authLoading && (!isAuthenticated || user?.role !== 'admin')) {
      navigate('/');
    }
  }, [authLoading, isAuthenticated, user, navigate]);

  const fetchUsers = async () => {
    try {
      const res = await fetch(`${apiBase}/api/auth/admin/users`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to fetch users');
      const data = await res.json();
      setUsers(data.users);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const fetchAudits = async () => {
    try {
      const res = await fetch(`${apiBase}/api/audits?limit=50`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to fetch audits');
      const data = await res.json();
      setAudits(data.audits);
    } catch {
      // Non-fatal — audit history is supplementary
    }
  };

  useEffect(() => {
    if (isAuthenticated && user?.role === 'admin') {
      fetchUsers();
      fetchAudits();
    }
  }, [isAuthenticated, user]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    setSuccess(null);

    try {
      const res = await fetch(`${apiBase}/api/auth/admin/create-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          email: newEmail,
          name: newName,
          role: newRole,
          temporary_password: newPassword,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create user');
      }
      setSuccess(`User ${newEmail} created successfully`);
      setNewEmail('');
      setNewName('');
      setNewRole('user');
      setNewPassword('');
      setShowCreate(false);
      fetchUsers();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create user');
    } finally {
      setCreating(false);
    }
  };

  const toggleActive = async (userId: string, active: boolean) => {
    try {
      const res = await fetch(
        `${apiBase}/api/auth/admin/users/${userId}/active?active=${active}`,
        { method: 'PUT', credentials: 'include' }
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to update user');
      }
      fetchUsers();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update user');
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <Loader2 size={24} className="animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center">
              <Users size={20} className="text-accent" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-text font-heading">
                User Management
              </h1>
              <p className="text-sm text-text-muted">
                Manage accounts and access to Pro features
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white font-semibold px-4 py-2.5 rounded-xl transition-all text-sm"
          >
            <Plus size={16} />
            Create User
          </button>
        </div>

        {/* Feedback */}
        {error && (
          <div className="flex items-center gap-2 bg-severity-critical-bg text-severity-critical border border-severity-critical/20 rounded-xl px-4 py-3 mb-6 text-sm">
            <AlertCircle size={16} />
            {error}
            <button onClick={() => setError(null)} className="ml-auto">
              <X size={14} />
            </button>
          </div>
        )}
        {success && (
          <div className="flex items-center gap-2 bg-success/10 text-success border border-success/20 rounded-xl px-4 py-3 mb-6 text-sm">
            <CheckCircle2 size={16} />
            {success}
            <button onClick={() => setSuccess(null)} className="ml-auto">
              <X size={14} />
            </button>
          </div>
        )}

        {/* Create User Form */}
        {showCreate && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="bg-surface-raised border border-border rounded-xl p-6 mb-6 overflow-hidden"
          >
            <h3 className="text-sm font-bold text-text mb-4">
              Create New Account
            </h3>
            <form onSubmit={handleCreate} className="grid grid-cols-2 gap-3">
              <input
                type="email"
                placeholder="Email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className="bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
                required
              />
              <input
                type="text"
                placeholder="Name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
                required
              />
              <input
                type="password"
                placeholder="Temporary password (min 8 chars)"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
                required
                minLength={8}
              />
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as 'user' | 'admin')}
                className="bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent/30"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
              <div className="col-span-2 flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 text-sm font-medium text-text-muted hover:text-text transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="bg-accent hover:bg-accent-hover text-white font-semibold px-4 py-2 rounded-lg text-sm disabled:opacity-50 flex items-center gap-2"
                >
                  {creating && <Loader2 size={14} className="animate-spin" />}
                  Create Account
                </button>
              </div>
            </form>
          </motion.div>
        )}

        {/* Users Table */}
        <div className="bg-surface-raised border border-border rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                  User
                </th>
                <th className="text-left px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                  Role
                </th>
                <th className="text-left px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-wider hidden md:table-cell">
                  Last Login
                </th>
                <th className="text-left px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr
                  key={u.id}
                  className="border-b border-border last:border-b-0 hover:bg-surface-overlay/50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {u.avatar_url ? (
                        <img
                          src={u.avatar_url}
                          alt=""
                          className="w-8 h-8 rounded-full"
                        />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center text-xs font-bold text-accent">
                          {(u.name || u.email)[0].toUpperCase()}
                        </div>
                      )}
                      <div>
                        <div className="text-sm font-medium text-text">
                          {u.name || '—'}
                        </div>
                        <div className="text-xs text-text-muted">{u.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 text-xs font-semibold">
                      {u.role === 'admin' ? (
                        <>
                          <ShieldCheck size={12} className="text-accent" />
                          <span className="text-accent">Admin</span>
                        </>
                      ) : (
                        <>
                          <Shield size={12} className="text-text-muted" />
                          <span className="text-text-secondary">User</span>
                        </>
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-text-muted hidden md:table-cell">
                    {u.last_login
                      ? new Date(u.last_login).toLocaleDateString()
                      : 'Never'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs font-semibold ${u.is_active ? 'text-success' : 'text-text-muted'}`}
                    >
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {u.id !== user?.id && (
                      <button
                        onClick={() => toggleActive(u.id, !u.is_active)}
                        className={`text-xs font-semibold px-3 py-1 rounded-lg transition-colors ${
                          u.is_active
                            ? 'text-text-muted hover:text-severity-critical hover:bg-severity-critical-bg'
                            : 'text-success hover:bg-success/10'
                        }`}
                      >
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-sm text-text-muted"
                  >
                    No users found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Audit History */}
        <div className="mt-10">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center">
              <History size={20} className="text-accent" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-text font-heading">
                Audit History
              </h2>
              <p className="text-sm text-text-muted">
                All audits across free and premium tiers
              </p>
            </div>
          </div>

          <div className="bg-surface-raised border border-border rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                    URL
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                    Tier
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                    Score
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-wider hidden md:table-cell">
                    CMS
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-bold text-text-muted uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {audits.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-border last:border-b-0 hover:bg-surface-overlay/50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-text truncate max-w-[240px]">
                        {a.url}
                      </div>
                      <div className="text-[10px] text-text-muted">
                        {a.audit_type}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                          a.tier === 'premium'
                            ? 'bg-accent/10 text-accent'
                            : 'bg-surface-overlay text-text-muted'
                        }`}
                      >
                        {a.tier}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-lg font-extrabold font-heading ${scoreColor(a.overall_score)}`}
                      >
                        {a.overall_score}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-text-muted hidden md:table-cell">
                      {a.detected_cms || '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-text-muted">
                      {a.created_at
                        ? new Date(a.created_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => {
                          const path =
                            a.tier === 'premium'
                              ? `/dashboard/${a.id}`
                              : `/audit/${a.id}`;
                          navigate(path);
                        }}
                        className="text-xs font-semibold text-accent hover:text-accent-hover flex items-center gap-1 ml-auto transition-colors"
                      >
                        View
                        <ExternalLink size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
                {audits.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-8 text-center text-sm text-text-muted"
                    >
                      No audits found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
