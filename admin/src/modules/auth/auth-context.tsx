'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { getSession } from '@/lib/auth-storage';
import { fetchMe, logout as doLogout } from './api';
import type { AdminUser } from './types';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

interface AuthContextValue {
  status: AuthStatus;
  user: AdminUser | null;
  reload: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<AdminUser | null>(null);

  const reload = useCallback(async () => {
    if (!getSession()) {
      setUser(null);
      setStatus('unauthenticated');
      return;
    }
    const result = await fetchMe();
    if (result.ok) {
      setUser(result.data);
      setStatus('authenticated');
    } else {
      setUser(null);
      setStatus('unauthenticated');
    }
  }, []);

  const signOut = useCallback(async () => {
    await doLogout();
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  useEffect(() => {
    void reload();
    const onExpired = (): void => {
      setUser(null);
      setStatus('unauthenticated');
    };
    window.addEventListener('ecom:session-expired', onExpired);
    return () => window.removeEventListener('ecom:session-expired', onExpired);
  }, [reload]);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, reload, signOut }),
    [status, user, reload, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAdminAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAdminAuth deve ser usado dentro de <AdminAuthProvider>.');
  return ctx;
}
