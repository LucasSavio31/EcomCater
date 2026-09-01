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
import { customerApi } from './api';
import type { Customer } from './types';
import { getCustomerSession, setCustomerSession } from '@/lib/customer-auth-storage';
import { identify } from '@/modules/analytics';

interface AuthState {
  customer: Customer | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  register: (data: {
    full_name: string;
    email: string;
    password: string;
    phone?: string;
    cpf?: string;
  }) => Promise<{ ok: boolean; error?: string }>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!getCustomerSession()?.accessToken) {
      setCustomer(null);
      setLoading(false);
      return;
    }
    const res = await customerApi.me();
    setCustomer(res.ok ? res.data : null);
    setLoading(false);
    // Cliente logado → alimenta o Advanced Matching (Meta) e as Enhanced
    // Conversions (Google) em TODAS as páginas, não só no checkout.
    if (res.ok) {
      const [firstName, ...rest] = (res.data.full_name ?? '').trim().split(/\s+/);
      identify({
        email: res.data.email,
        phone: res.data.phone,
        firstName: firstName || undefined,
        lastName: rest.join(' ') || undefined,
        externalId: (res.data.cpf ?? '').replace(/\D/g, '') || undefined,
        country: 'BR',
      });
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const login = useCallback<AuthState['login']>(
    async (email, password) => {
      const res = await customerApi.login({ email, password });
      if (!res.ok) return { ok: false, error: res.error.message };
      setCustomerSession(res.data);
      await reload();
      return { ok: true };
    },
    [reload],
  );

  const register = useCallback<AuthState['register']>(
    async (data) => {
      const res = await customerApi.register(data);
      if (!res.ok) return { ok: false, error: res.error.message };
      setCustomerSession(res.data);
      await reload();
      return { ok: true };
    },
    [reload],
  );

  const logout = useCallback<AuthState['logout']>(async () => {
    await customerApi.logout();
    setCustomer(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ customer, loading, login, register, logout, reload }),
    [customer, loading, login, register, logout, reload],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth precisa estar dentro de <AuthProvider>.');
  return ctx;
}
