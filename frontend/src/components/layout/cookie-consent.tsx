'use client';

import { useEffect, useState } from 'react';

const KEY = 'ecom-cookie-consent';

interface Props {
  enabled: boolean;
  text: string;
}

/** Barra fixa de aviso de cookies de terceiros. Fecha e grava no localStorage. */
export function CookieConsent({ enabled, text }: Props) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    try {
      if (!localStorage.getItem(KEY)) setShow(true);
    } catch {
      setShow(true);
    }
  }, [enabled]);

  if (!enabled || !show) return null;

  const accept = () => {
    try {
      localStorage.setItem(KEY, new Date().toISOString());
    } catch {
      /* modo privado: só fecha */
    }
    setShow(false);
  };

  return (
    <div
      role="dialog"
      aria-label="Aviso de cookies"
      className="fixed inset-x-0 bottom-0 z-[60] border-t border-surface-border bg-surface/95 p-4 shadow-lg backdrop-blur"
    >
      <div className="mx-auto flex max-w-3xl flex-col items-center gap-3 sm:flex-row">
        <p className="text-sm text-text-muted">{text}</p>
        <button
          type="button"
          onClick={accept}
          className="shrink-0 rounded-btn bg-primary px-4 py-2 text-sm font-semibold text-primary-fg"
        >
          Aceitar
        </button>
      </div>
    </div>
  );
}
