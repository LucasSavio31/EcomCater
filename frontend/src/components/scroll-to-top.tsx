'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

/**
 * Sempre que a rota (pathname) muda — clique num menu, num produto, num link —
 * a página volta ao topo. Não dispara em mudança só de query string (filtros /
 * ordenação da vitrine), para não "pular" a tela enquanto o cliente filtra.
 */
export function ScrollToTop() {
  const pathname = usePathname();

  useEffect(() => {
    // instant: ignora qualquer scroll-behavior: smooth herdado
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior });
  }, [pathname]);

  return null;
}
