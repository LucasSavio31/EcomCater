'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spinner } from '@ecom/ui';
import { useAuth } from '@/modules/customer/auth-context';
import { FavoritesView } from '@/components/wishlist/favorites-view';

/**
 * Favoritos do visitante não logado — a lista vem do cache do navegador
 * (`localStorage`). Se o cliente estiver logado, vai para `/minha-conta/favoritos`.
 */
export default function FavoritosPublicPage() {
  const router = useRouter();
  const { customer, loading } = useAuth();

  useEffect(() => {
    if (!loading && customer) router.replace('/minha-conta/favoritos');
  }, [loading, customer, router]);

  if (loading || customer) {
    return (
      <p className="flex items-center gap-2 py-16 text-text-muted">
        <Spinner /> Carregando…
      </p>
    );
  }

  return <FavoritesView />;
}
