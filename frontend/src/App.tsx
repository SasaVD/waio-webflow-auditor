import { useEffect } from 'react';
import { RouterProvider } from 'react-router';
import { router } from './router';
import { useAuthStore } from './stores/authStore';
import { LoginModal } from './components/auth/LoginModal';

function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <>
      <RouterProvider router={router} />
      <LoginModal />
    </>
  );
}

export default App;
