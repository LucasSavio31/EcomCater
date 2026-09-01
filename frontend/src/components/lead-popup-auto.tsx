'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { LeadPopup, type LeadPopupConfig } from '@/components/lead-popup';

const SEEN_KEY = 'ecom.lead_popup.seen_at';
const SUPPRESS_DAYS = 7;
const OPEN_DELAY_MS = 6000;

/**
 * Dispara o popup de captura de lead automaticamente na loja: uma vez por
 * visitante, ~6s após entrar, e não reaparece por 7 dias depois de fechado.
 * Não aparece no checkout nem se o popup estiver desligado no tema.
 */
export function LeadPopupAuto({ config }: { config: LeadPopupConfig }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const blockedRoute = pathname?.startsWith('/checkout') || pathname?.startsWith('/minha-conta');

  useEffect(() => {
    if (!config.enabled || blockedRoute) return;

    let recentlySeen = false;
    try {
      const raw = window.localStorage.getItem(SEEN_KEY);
      if (raw) {
        const seenAt = Number(raw);
        recentlySeen =
          Number.isFinite(seenAt) &&
          Date.now() - seenAt < SUPPRESS_DAYS * 24 * 60 * 60 * 1000;
      }
    } catch {
      /* modo privado / storage bloqueado — mostra mesmo assim */
    }
    if (recentlySeen) return;

    const t = setTimeout(() => setOpen(true), OPEN_DELAY_MS);
    return () => clearTimeout(t);
  }, [config.enabled, blockedRoute]);

  function close(): void {
    setOpen(false);
    try {
      window.localStorage.setItem(SEEN_KEY, String(Date.now()));
    } catch {
      /* ignore */
    }
  }

  if (!config.enabled) return null;
  return <LeadPopup open={open} onClose={close} config={config} />;
}
