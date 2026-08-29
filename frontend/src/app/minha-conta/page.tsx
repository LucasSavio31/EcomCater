'use client';

import { useAuth } from '@/modules/customer/auth-context';
import { AccountDashboard } from '@/components/account/account-dashboard';
import { AuthForms } from '@/components/account/auth-forms';
import { Spinner } from '@ecom/ui';

export default function MinhaContaPage() {
  const { customer, loading } = useAuth();

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold sm:text-2xl">Minha conta</h1>
      {loading ? (
        <p className="flex items-center gap-2 py-16 text-text-muted">
          <Spinner /> Carregando…
        </p>
      ) : customer ? (
        <AccountDashboard />
      ) : (
        <AuthForms />
      )}
    </div>
  );
}
