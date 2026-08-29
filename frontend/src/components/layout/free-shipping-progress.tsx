'use client';

import { useCart } from '@/modules/cart/cart-context';
import { formatBRL, freeShippingRemaining } from '@/lib/format';

interface FreeShippingProgressProps {
  thresholdCents?: number | null;
  /** `bar` mostra a barra de progresso; `text` só a frase. */
  variant?: 'bar' | 'text';
  className?: string;
}

/**
 * Progresso até o frete grátis. Lê o subtotal do contexto de carrinho
 * (placeholder na Fase 3; a Fase 4 alimenta com dados reais).
 */
export function FreeShippingProgress({
  thresholdCents,
  variant = 'text',
  className,
}: FreeShippingProgressProps) {
  const { subtotalCents } = useCart();
  if (!thresholdCents || thresholdCents <= 0) return null;

  const remaining = freeShippingRemaining(subtotalCents, thresholdCents);
  const pct = Math.min(100, Math.round((subtotalCents / thresholdCents) * 100));
  const reached = remaining === 0;

  return (
    <div className={className} aria-live="polite">
      <p className="text-xs">
        {reached ? (
          <span className="font-medium text-success">Você ganhou frete grátis! 🎉</span>
        ) : (
          <>
            Faltam <strong>{formatBRL(remaining)}</strong> para o frete grátis
          </>
        )}
      </p>
      {variant === 'bar' && (
        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-card bg-bg-subtle">
          <div
            className="h-full rounded-card bg-primary transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}
