import { useState, useRef, useEffect } from 'react';
import { LogOut, Settings, ChevronDown } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { Link } from 'react-router';

export function UserMenu() {
  const { user, isAuthenticated, logout, openLoginModal } = useAuthStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  if (!isAuthenticated || !user) {
    return (
      <button
        onClick={openLoginModal}
        className="text-xs font-semibold text-text-muted hover:text-accent transition-colors uppercase tracking-wider"
      >
        Sign In
      </button>
    );
  }

  const initials = (user.name || user.email)
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 hover:bg-surface-raised rounded-lg px-2 py-1.5 transition-colors"
      >
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt=""
            className="w-7 h-7 rounded-full object-cover"
          />
        ) : (
          <div className="w-7 h-7 rounded-full bg-accent/10 flex items-center justify-center text-xs font-bold text-accent">
            {initials}
          </div>
        )}
        <span className="text-sm font-medium text-text hidden sm:inline max-w-[120px] truncate">
          {user.name || user.email}
        </span>
        <ChevronDown
          size={14}
          className={`text-text-muted transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-52 bg-surface border border-border rounded-xl shadow-card overflow-hidden z-50">
          <div className="px-4 py-3 border-b border-border">
            <div className="text-sm font-semibold text-text truncate">
              {user.name || 'User'}
            </div>
            <div className="text-xs text-text-muted truncate">{user.email}</div>
          </div>

          {user.role === 'admin' && (
            <Link
              to="/admin"
              onClick={() => setOpen(false)}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-text hover:bg-surface-raised transition-colors"
            >
              <Settings size={15} className="text-text-muted" />
              Admin Panel
            </Link>
          )}

          <button
            onClick={() => {
              setOpen(false);
              logout();
            }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-text hover:bg-surface-raised transition-colors"
          >
            <LogOut size={15} className="text-text-muted" />
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}
