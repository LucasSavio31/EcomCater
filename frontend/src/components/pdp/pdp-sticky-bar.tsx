'use client';

import { useEffect, useState } from 'react';
import { formatBRL } from '@/lib/format';

/**
 * Barra fixa no rodapé (só mobile) com preço + "Comprar", que aparece quando o
 * botão de compra principal sai da tela. "Comprar" rola até o buy-box.
 */
export function PdpStickyBar({
  priceCents,
  pixCents,
  buyBoxId = 'pdp-buybox',
}: {
  priceCents: number;
  pixCents?: number | null;
  buyBoxId?: string;
}) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const target = document.getElementById(buyBoxId);
    if (!target) return;
    const io = new IntersectionObserver(
      (entries) => setShow(!(entries[0]?.isIntersecting ?? true)),
      { rootMargin: '-64px 0px 0px 0px' },
    );
    io.observe(target);
    return () => io.disconnect();
  }, [buyBoxId]);

  return (
    <div
      className={`fixed inset-x-0 bottom-0 z-40 border-t border-surface-border bg-surface px-4 py-2.5 shadow-[0_-4px_16px_rgba(0,0,0,0.08)] transition-transform md:hidden ${
        show ? 'translate-y-0' : 'translate-y-full'
      }`}
    >
      <div className="mx-auto flex max-w-header items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-base font-bold leading-none">{formatBRL(priceCents)}</p>
          {pixCents ? (
            <p className="text-xs text-success">{formatBRL(pixCents)} no PIX</p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() =>
            document.getElementById(buyBoxId)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
          className="rounded-btn bg-btn px-6 py-3 text-base font-extrabold uppercase tracking-wide text-btn-fg"
        >
          Comprar
        </button>
      </div>
    </div>
  );
}
