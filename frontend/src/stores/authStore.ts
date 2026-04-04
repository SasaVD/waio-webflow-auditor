import { create } from 'zustand';

const apiBase = import.meta.env.PROD ? '' : 'http://127.0.0.1:8000';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  avatar_url?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  showLoginModal: boolean;
  loginError: string | null;

  checkAuth: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => Promise<void>;
  openLoginModal: () => void;
  closeLoginModal: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  showLoginModal: false,
  loginError: null,

  checkAuth: async () => {
    try {
      const res = await fetch(`${apiBase}/api/auth/me`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        set({ user: data.user, isAuthenticated: true, isLoading: false });
      } else {
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  login: async (email, password) => {
    set({ loginError: null });
    try {
      const res = await fetch(`${apiBase}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json();
        set({ loginError: err.detail || 'Login failed' });
        return;
      }
      const data = await res.json();
      set({
        user: data.user,
        isAuthenticated: true,
        showLoginModal: false,
        loginError: null,
      });
    } catch {
      set({ loginError: 'Network error. Please try again.' });
    }
  },

  loginWithGoogle: async (credential) => {
    set({ loginError: null });
    try {
      const res = await fetch(`${apiBase}/api/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ credential }),
      });
      if (!res.ok) {
        const err = await res.json();
        set({ loginError: err.detail || 'Google login failed' });
        return;
      }
      const data = await res.json();
      set({
        user: data.user,
        isAuthenticated: true,
        showLoginModal: false,
        loginError: null,
      });
    } catch {
      set({ loginError: 'Network error. Please try again.' });
    }
  },

  logout: async () => {
    try {
      await fetch(`${apiBase}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch {
      // Ignore — clear local state regardless
    }
    set({ user: null, isAuthenticated: false });
  },

  openLoginModal: () => set({ showLoginModal: true, loginError: null }),
  closeLoginModal: () => set({ showLoginModal: false, loginError: null }),
}));
