'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spinner } from '@ecom/ui';
import { useAuth } from '@/modules/customer/auth-context';
import { FavoritesView } from '@/components/wishlist/favorites-view';

/** Favoritos do cliente logado. Sem login, a rota pública é `/favoritos`. */
export default function FavoritosContaPage() {
  const router = useRouter();
  const { customer, loading } = useAuth();

  useEffect(() => {
    if (!loading && !customer) router.replace('/favoritos');
  }, [loading, customer, router]);

  if (loading || !customer) {
    return (
      <p className="flex items-center gap-2 py-16 text-text-muted">
        <Spinner /> Carregando…
      </p>
    );
  }

  return <FavoritesView showAccountLink />;
}
