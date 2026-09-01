'use client';

import { useEffect, useState } from 'react';

const KEY = 'ecom-cookie-consent';

interface Props {
  enabled: boolean;
  text: string;
}

/** Barra fixa de aviso de cookies de terceiros. Fecha e grava no localStorage.
 * Enquanto visível, reserva espaço no fim da página (padding no body) para não
 * cobrir o botão de compra / preço na PDP mobile. */
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

  useEffect(() => {
    if (!show) return;
    const prev = document.body.style.paddingBottom;
    document.body.style.paddingBottom = 'var(--cookie-bar-h, 6.5rem)';
    return () => {
      document.body.style.paddingBottom = prev;
    };
  }, [show]);

  if (!enabled || !show) return null;

  const close = (choice: 'accept' | 'reject') => {
    try {
      localStorage.setItem(KEY, `${choice}:${new Date().toISOString()}`);
    } catch {
      /* modo privado: só fecha */
    }
    setShow(false);
  };

  return (
    <div
      role="dialog"
      aria-label="Aviso de cookies"
      style={{ ['--cookie-bar-h' as string]: '6.5rem' }}
      className="fixed inset-x-0 bottom-0 z-[60] border-t border-surface-border bg-surface p-4 shadow-lg"
    >
      <div className="mx-auto flex max-w-3xl flex-col items-center gap-3 sm:flex-row">
        <p className="text-sm text-text">{text}</p>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => close('reject')}
            className="rounded-btn border border-surface-border px-4 py-2 text-sm font-medium text-text-muted hover:text-text"
          >
            Recusar
          </button>
          <button
            type="button"
            onClick={() => close('accept')}
            className="rounded-btn bg-primary px-4 py-2 text-sm font-semibold text-primary-fg"
          >
            Aceitar
          </button>
        </div>
      </div>
    </div>
  );
}
