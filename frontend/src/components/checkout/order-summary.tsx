'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Card } from '@ecom/ui';
import { useCart } from '@/modules/cart/cart-context';
import { resolveMediaUrl } from '@/lib/media';
import { formatBRL } from '@/lib/format';
import { CouponField } from '@/components/cart/coupon-field';

interface Props {
  showCoupon?: boolean;
  layout?: 'with_thumb' | 'simple';
  allowQtyChange?: boolean;
  /** `side` = card fixo à direita (+ recolhível no mobile); `top` = dropdown em todas as telas. */
  position?: 'side' | 'top';
}

/** "Revise seu pedido": cupom recolhido + itens + totais. */
export function OrderSummary({
  showCoupon = true,
  layout = 'with_thumb',
  allowQtyChange = true,
  position = 'side',
}: Props) {
  const { cart, updateItem } = useCart();
  const t = cart.totals;
  const shipping = !cart.selected_shipping
    ? 'A calcular'
    : t.shipping_cents > 0
      ? formatBRL(t.shipping_cents)
      : 'Grátis';

  const body = (
    <div className="flex flex-col gap-4">
      {showCoupon && <Coupon />}

      <ul className="flex flex-col gap-3">
        {cart.items.map((i) => {
          const img = resolveMediaUrl(i.image_url);
          return (
            <li key={i.id} className="flex gap-3">
              {layout === 'with_thumb' && (
                <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-card bg-bg-subtle">
                  {img && <Image src={img} alt="" fill sizes="56px" className="object-cover" />}
                  <span className="absolute -right-1.5 -top-1.5 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-btn px-1 text-[10px] font-bold text-btn-fg">
                    {i.quantity}
                  </span>
                </div>
              )}
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="line-clamp-2 text-sm">
                  {layout === 'simple' && <strong>{i.quantity}× </strong>}
                  {i.product_name}
                </span>
                {i.variant_label && (
                  <span className="text-xs text-text-muted">{i.variant_label}</span>
                )}
                {layout === 'with_thumb' && allowQtyChange && i.max_qty > 1 && (
                  <select
                    value={i.quantity}
                    onChange={(e) => void updateItem(i.id, Number(e.target.value))}
                    className="mt-1 w-16 rounded-card border border-surface-border bg-surface px-1 text-xs"
                    aria-label={`Quantidade de ${i.product_name}`}
                  >
                    {Array.from({ length: Math.min(i.max_qty, 10) }, (_, n) => n + 1).map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <span className="shrink-0 text-sm font-medium">{formatBRL(i.line_total_cents)}</span>
            </li>
          );
        })}
      </ul>

      <dl className="flex flex-col gap-1.5 border-t border-surface-border pt-3 text-sm">
        <Row label="Subtotal" value={formatBRL(t.items_total_cents)} />
        {t.discount_cents > 0 && (
          <Row label="Desconto" value={`− ${formatBRL(t.discount_cents)}`} accent />
        )}
        <Row label="Envio" value={shipping} />
        {t.free_shipping_remaining_cents && t.free_shipping_remaining_cents > 0 ? (
          <p className="text-xs text-text-muted">
            Faltam {formatBRL(t.free_shipping_remaining_cents)} para o frete grátis.
          </p>
        ) : null}
        <div className="mt-1 flex items-baseline justify-between border-t border-surface-border pt-2">
          <dt className="text-base font-semibold">Total</dt>
          <dd className="text-lg font-bold">{formatBRL(t.grand_total_cents)}</dd>
        </div>
      </dl>
    </div>
  );

  if (position === 'top') {
    return (
      <details className="rounded-card border border-surface-border bg-surface">
        <summary className="flex cursor-pointer items-center justify-between gap-2 px-4 py-3 text-sm font-semibold">
          <span>Revise seu pedido</span>
          <span className="font-bold">{formatBRL(t.grand_total_cents)}</span>
        </summary>
        <div className="border-t border-surface-border px-4 py-4">{body}</div>
      </details>
    );
  }

  return (
    <>
      <Card variant="outline" className="hidden lg:sticky lg:top-6 lg:flex lg:flex-col lg:gap-4 lg:self-start">
        <h2 className="text-base font-semibold">Revise seu pedido</h2>
        {body}
      </Card>

      <details className="rounded-card border border-surface-border bg-surface lg:hidden">
        <summary className="flex cursor-pointer items-center justify-between gap-2 px-4 py-3 text-sm font-semibold">
          <span>Resumo do pedido</span>
          <span className="font-bold">{formatBRL(t.grand_total_cents)}</span>
        </summary>
        <div className="border-t border-surface-border px-4 py-4">{body}</div>
      </details>
    </>
  );
}

function Coupon() {
  const [open, setOpen] = useState(false);
  const { cart } = useCart();
  if (cart.coupon_code) return <CouponField />;
  return open ? (
    <CouponField />
  ) : (
    <button
      type="button"
      onClick={() => setOpen(true)}
      className="flex w-fit items-center gap-1 text-sm font-medium text-primary underline"
    >
      Tenho um cupom de desconto
    </button>
  );
}

function Row({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-text-muted">{label}</dt>
      <dd className={accent ? 'text-success' : 'text-text'}>{value}</dd>
    </div>
  );
}
