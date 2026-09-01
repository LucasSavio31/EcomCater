'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { identify } from '@/modules/analytics';

/**
 * Garante que os dados do cliente (e-mail/nome/geo persistidos) + `_fbp`/`_fbc`
 * + user-agent sejam re-emitidos no `dataLayer` a cada página — inclusive para
 * visitante anônimo (só cookies do pixel). Complementa os `identify()`
 * pontuais do login, checkout e captura de lead.
 */
export function AnalyticsIdentity() {
  const pathname = usePathname();
  useEffect(() => {
    try {
      if (!sessionStorage.getItem('ecom:landing')) {
        sessionStorage.setItem('ecom:landing', window.location.href);
      }
    } catch {
      /* noop */
    }
    identify();
  }, [pathname]);
  return null;
}
