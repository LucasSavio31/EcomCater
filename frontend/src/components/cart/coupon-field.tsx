'use client';

import { useState } from 'react';
import { Button, Input } from '@ecom/ui';
import { useCart } from '@/modules/cart/cart-context';

/** Campo de cupom — aplica/remove via contexto de carrinho. */
export function CouponField() {
  const { cart, applyCoupon, removeCoupon } = useCart();
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!code.trim()) return;
    setBusy(true);
    await applyCoupon(code.trim());
    setBusy(false);
    setCode('');
  }

  if (cart.coupon_code) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-card bg-success/10 px-3 py-2 text-sm">
        <span>
          Cupom <strong>{cart.coupon_code}</strong> aplicado.
        </span>
        <button
          type="button"
          onClick={() => void removeCoupon()}
          className="font-medium text-text-muted underline hover:text-text"
        >
          Remover
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <Input
          label="Cupom de desconto"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="Ex.: BEMVINDO10"
          className="flex-1"
        />
        <Button
          type="submit"
          variant="outline"
          loading={busy}
          disabled={!code.trim()}
          className="border-2"
          style={{
            background: 'var(--color-cart-coupon-bg)',
            color: 'var(--color-cart-coupon-fg)',
            borderColor: 'var(--color-cart-coupon-border)',
            borderRadius: 'var(--radius-cart-coupon, 0.75rem)',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-cart-coupon-hover)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--color-cart-coupon-bg)')}
        >
          Aplicar
        </Button>
      </form>
      {cart.coupon_error && <p className="text-xs text-danger">{cart.coupon_error}</p>}
    </div>
  );
}

/**
 * Cupom em sanfona: "Tenho um cupom de desconto" abre e fecha o campo.
 * Se já houver um cupom aplicado, mostra o campo direto (para poder remover).
 */
export function CollapsibleCoupon() {
  const { cart } = useCart();
  if (cart.coupon_code) return <CouponField />;
  return (
    <details className="group">
      <summary className="flex w-fit cursor-pointer list-none items-center gap-1.5 text-sm font-medium text-primary [&::-webkit-details-marker]:hidden">
        <span className="underline">Tenho um cupom de desconto</span>
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
          className="h-4 w-4 transition-transform group-open:rotate-180"
        >
          <path d="M5 7l5 6 5-6z" />
        </svg>
      </summary>
      <div className="pt-2">
        <CouponField />
      </div>
    </details>
  );
}
