'use client';

import { useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';
import { apiFetch } from '@/lib/api-client';

const HEARTBEAT_MS = 25_000;

/**
 * Heartbeat de presença pro "visitantes ao vivo" do admin. Sempre silencioso:
 * se o módulo estiver desligado (404) ou der qualquer erro de rede, só para
 * de tentar pelo resto da sessão da aba — nunca aparece pro cliente da loja.
 */
export function PresenceBeacon() {
  const pathname = usePathname();
  const disabledRef = useRef(false);

  useEffect(() => {
    if (disabledRef.current) return;
    void apiFetch('/api/presence/heartbeat', {
      method: 'POST',
      body: { path: pathname || '/' },
      credentials: 'include',
      cache: 'no-store',
    }).then((res) => {
      if (!res.ok && res.error.status === 404) disabledRef.current = true;
    });
  }, [pathname]);

  useEffect(() => {
    const tick = (): void => {
      if (disabledRef.current || document.visibilityState !== 'visible') return;
      void apiFetch('/api/presence/heartbeat', {
        method: 'POST',
        body: { path: pathname || '/' },
        credentials: 'include',
        cache: 'no-store',
      }).then((res) => {
        if (!res.ok && res.error.status === 404) disabledRef.current = true;
      });
    };
    const id = window.setInterval(tick, HEARTBEAT_MS);
    document.addEventListener('visibilitychange', tick);
    return () => {
      window.clearInterval(id);
      document.removeEventListener('visibilitychange', tick);
    };
  }, [pathname]);

  return null;
}
