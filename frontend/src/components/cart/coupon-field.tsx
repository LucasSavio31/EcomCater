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
        <Button type="submit" variant="outline" loading={busy} disabled={!code.trim()}>
          Aplicar
        </Button>
      </form>
      {cart.coupon_error && <p className="text-xs text-danger">{cart.coupon_error}</p>}
    </div>
  );
}
