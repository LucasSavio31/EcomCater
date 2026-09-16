'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

/**
 * Companheiro do ColorSiblings: ao navegar pra fora de /produto/ (voltou pra
 * home, categoria, carrinho etc.), limpa a memória de "ver mais cores"
 * aberto. Sem isso, o flag em sessionStorage só é revisto quando um
 * ColorSiblings monta de novo — e uma página sem PDP nunca monta um, então
 * o flag do produto anterior ficaria "preso" ligado.
 */
export function PdpContextGuard() {
  const pathname = usePathname();

  useEffect(() => {
    if (pathname.startsWith('/produto/')) return;
    try {
      sessionStorage.removeItem('cs-group');
      sessionStorage.removeItem('cs-expanded');
    } catch {
      /* sessionStorage indisponível */
    }
  }, [pathname]);

  return null;
}
