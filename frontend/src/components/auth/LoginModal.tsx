import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Mail, Lock, Loader2, AlertCircle } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { GoogleAuthButton } from './GoogleAuthButton';

export function LoginModal() {
  const { showLoginModal, closeLoginModal, login, loginError, isAuthenticated } =
    useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);

  // Close on successful auth
  useEffect(() => {
    if (isAuthenticated && showLoginModal) {
      closeLoginModal();
    }
  }, [isAuthenticated, showLoginModal, closeLoginModal]);

  // Focus email input on open
  useEffect(() => {
    if (showLoginModal) {
      setTimeout(() => emailRef.current?.focus(), 100);
    } else {
      setEmail('');
      setPassword('');
      setSubmitting(false);
    }
  }, [showLoginModal]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    setSubmitting(true);
    await login(email, password);
    setSubmitting(false);
  };

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showLoginModal) closeLoginModal();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [showLoginModal, closeLoginModal]);

  return (
    <AnimatePresence>
      {showLoginModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
        >
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={closeLoginModal}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="relative w-full max-w-md bg-surface border border-border rounded-2xl shadow-card-hover overflow-hidden"
            role="dialog"
            aria-modal="true"
            aria-label="Sign in"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 pt-6 pb-2">
              <div>
                <h2 className="text-xl font-bold text-text font-heading">
                  Sign in
                </h2>
                <p className="text-sm text-text-muted mt-1">
                  Access Pro features and comprehensive audits
                </p>
              </div>
              <button
                onClick={closeLoginModal}
                className="p-2 rounded-lg text-text-muted hover:text-text hover:bg-surface-raised transition-colors"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <div className="px-6 pb-6 pt-4 space-y-5">
              {/* Google Sign-In */}
              <GoogleAuthButton />

              {/* Divider */}
              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-border" />
                <span className="text-xs font-medium text-text-muted">or</span>
                <div className="flex-1 h-px bg-border" />
              </div>

              {/* Email/Password Form */}
              <form onSubmit={handleSubmit} className="space-y-3">
                <div className="relative">
                  <Mail
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
                  />
                  <input
                    ref={emailRef}
                    type="email"
                    placeholder="Email address"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-surface-raised border border-border rounded-xl pl-10 pr-4 py-3 text-sm font-medium text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/30 transition-all"
                    required
                    autoComplete="email"
                  />
                </div>
                <div className="relative">
                  <Lock
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
                  />
                  <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-surface-raised border border-border rounded-xl pl-10 pr-4 py-3 text-sm font-medium text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/30 transition-all"
                    required
                    minLength={8}
                    autoComplete="current-password"
                  />
                </div>

                {/* Error */}
                {loginError && (
                  <motion.div
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-2 text-sm text-severity-critical bg-severity-critical-bg border border-severity-critical/20 rounded-lg px-3 py-2"
                  >
                    <AlertCircle size={14} className="flex-shrink-0" />
                    {loginError}
                  </motion.div>
                )}

                <button
                  type="submit"
                  disabled={submitting || !email || !password}
                  className="w-full bg-accent hover:bg-accent-hover text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : null}
                  Sign in
                </button>
              </form>

              {/* Invite-only notice */}
              <p className="text-xs text-text-muted text-center">
                Accounts are invite-only. Contact your administrator for access.
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
