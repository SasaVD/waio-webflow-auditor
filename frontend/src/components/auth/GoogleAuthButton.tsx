import { useEffect, useRef } from 'react';
import { useAuthStore } from '../../stores/authStore';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: Record<string, unknown>) => void;
          renderButton: (
            parent: HTMLElement,
            options: Record<string, unknown>
          ) => void;
        };
      };
    };
  }
}

export function GoogleAuthButton() {
  const { loginWithGoogle } = useAuthStore();
  const buttonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !window.google?.accounts?.id || !buttonRef.current)
      return;

    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: (response: { credential: string }) => {
        loginWithGoogle(response.credential);
      },
    });

    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: 'outline',
      size: 'large',
      width: '100%',
      text: 'signin_with',
      shape: 'pill',
    });
  }, [loginWithGoogle]);

  if (!GOOGLE_CLIENT_ID) {
    return null;
  }

  return <div ref={buttonRef} className="w-full flex justify-center" />;
}
