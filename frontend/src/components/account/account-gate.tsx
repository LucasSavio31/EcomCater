'use client';

import type { ReactNode } from 'react';
import { Spinner } from '@ecom/ui';
import { useAuth } from '@/modules/customer/auth-context';
import { AuthForms } from './auth-forms';

/** Mostra o conteúdo só para clientes logados; senão, o formulário de acesso. */
export function AccountGate({ children, intro }: { children: ReactNode; intro?: string }) {
  const { customer, loading } = useAuth();

  if (loading) {
    return (
      <p className="flex items-center gap-2 py-16 text-text-muted">
        <Spinner /> Carregando…
      </p>
    );
  }

  if (!customer) {
    return (
      <div className="flex flex-col gap-4">
        {intro && <p className="text-sm text-text-muted">{intro}</p>}
        <AuthForms />
      </div>
    );
  }

  return <>{children}</>;
}
