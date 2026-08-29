'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Spinner } from '@ecom/ui';
import { useAdminAuth } from '@/modules/auth';

/**
 * Guarda de autenticação das rotas do painel.
 *  - Sem sessão → redireciona para /login.
 *  - `must_change_password` → força /change-password.
 * `basePath` (/administracao) é prefixado automaticamente pelo router do Next.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { status, user } = useAdminAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.replace('/login');
      return;
    }
    if (status === 'authenticated' && user?.must_change_password && pathname !== '/change-password') {
      router.replace('/change-password');
    }
  }, [status, user, pathname, router]);

  if (status !== 'authenticated') {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Spinner size="lg" label="Verificando sessão…" />
      </div>
    );
  }

  if (user?.must_change_password && pathname !== '/change-password') {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Spinner size="lg" label="Redirecionando…" />
      </div>
    );
  }

  return <>{children}</>;
}
