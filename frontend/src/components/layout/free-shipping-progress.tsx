'use client';

import { useCart } from '@/modules/cart/cart-context';
import { formatBRL, freeShippingRemaining } from '@/lib/format';

interface FreeShippingProgressProps {
  /** Fallback quando o carrinho ainda não trouxe o valor. */
  thresholdCents?: number | null;
  /** `bar` mostra a barra de progresso; `text` só a frase. */
  variant?: 'bar' | 'text';
  className?: string;
}

/**
 * Progresso até o frete grátis. O valor mínimo e o quanto falta vêm do
 * carrinho (config em Frete, respeita cupom). Só aparece depois que há algo
 * no carrinho.
 */
export function FreeShippingProgress({
  thresholdCents,
  variant = 'text',
  className,
}: FreeShippingProgressProps) {
  const { subtotalCents, cart } = useCart();
  const threshold = cart.totals.free_shipping_threshold_cents ?? thresholdCents ?? 0;
  // só aparece depois que o cliente coloca algo no carrinho
  if (!threshold || threshold <= 0 || subtotalCents <= 0) return null;

  const remaining = cart.totals.free_shipping_remaining_cents ?? freeShippingRemaining(subtotalCents, threshold);
  const pct = Math.min(100, Math.round((subtotalCents / threshold) * 100));
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
