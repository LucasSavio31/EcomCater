'use client';

import { useEffect } from 'react';
import { registerServiceWorker } from '@/lib/sw-register';

/** Monta uma vez no cliente e registra o SW (no-op fora de produção). */
export function ServiceWorker() {
  useEffect(() => {
    registerServiceWorker();
  }, []);
  return null;
}
