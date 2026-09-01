'use client';

import Image from 'next/image';
import { Card } from '@ecom/ui';
import { useCart } from '@/modules/cart/cart-context';
import { track, cartToTrackItems } from '@/modules/analytics';
import type { CartItem } from '@/modules/cart/types';
import { resolveMediaUrl } from '@/lib/media';
import { formatBRL } from '@/lib/format';
import { CollapsibleCoupon } from '@/components/cart/coupon-field';

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
  const { cart, updateItem, removeItem } = useCart();
  const t = cart.totals;

  async function changeQty(i: CartItem, qty: number) {
    if (qty === i.quantity) return;
    const delta = qty - i.quantity;
    const res = await updateItem(i.id, qty);
    if (!res.ok || delta === 0) return;
    track(delta > 0 ? 'add_to_cart' : 'remove_from_cart', {
      items: cartToTrackItems([{ ...i, quantity: Math.abs(delta) }]),
    });
  }
  async function removeLine(i: CartItem) {
    const res = await removeItem(i.id);
    if (res.ok) track('remove_from_cart', { items: cartToTrackItems([i]) });
  }
  const shipping = !cart.selected_shipping
    ? 'A calcular'
    : t.shipping_cents > 0
      ? formatBRL(t.shipping_cents)
      : 'Grátis';

  const body = (
    <div className="flex flex-col gap-4">
      {showCoupon && <CollapsibleCoupon />}

      <ul className="flex flex-col gap-3">
        {cart.items.map((i) => {
          const img = resolveMediaUrl(i.image_url);
          return (
            <li key={i.id} className="flex gap-3">
              {layout === 'with_thumb' && (
                <div className="relative h-14 w-14 shrink-0">
                  <div className="h-full w-full overflow-hidden rounded-card bg-bg-subtle">
                    {img && <Image src={img} alt="" fill sizes="56px" className="object-cover" />}
                  </div>
                  <span className="pointer-events-none absolute -right-2 -top-2 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-btn px-1 text-[10px] font-bold text-btn-fg shadow">
                    {i.quantity}
                  </span>
                </div>
              )}
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="line-clamp-2 text-sm">
                  {layout === 'simple' && <strong>{i.quantity}× </strong>}
                  {i.product_name}
                </span>
                {i.variant_label && (
                  <span className="text-xs text-text-muted">{i.variant_label}</span>
                )}
                {allowQtyChange && (
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                    {layout === 'with_thumb' && (
                      <div className="ecom-qty-stepper inline-flex w-fit items-center rounded-card border border-black/40 bg-white">
                        <button
                          type="button"
                          aria-label={`Diminuir quantidade de ${i.product_name}`}
                          onClick={() => void changeQty(i, Math.max(1, i.quantity - 1))}
                          disabled={i.quantity <= 1}
                          className="flex h-7 w-7 items-center justify-center text-sm disabled:opacity-40"
                        >
                          −
                        </button>
                        <input
                          type="text"
                          inputMode="numeric"
                          aria-label={`Quantidade de ${i.product_name}`}
                          value={i.quantity}
                          onChange={(e) => {
                            const n = Number(e.target.value.replace(/\D/g, ''));
                            if (n >= 1) void changeQty(i, Math.min(n, i.max_qty || 99));
                          }}
                          className="w-9 border-0 bg-transparent text-center text-xs font-medium outline-none"
                        />
                        <button
                          type="button"
                          aria-label={`Aumentar quantidade de ${i.product_name}`}
                          onClick={() => void changeQty(i, Math.min(i.max_qty || 99, i.quantity + 1))}
                          disabled={i.quantity >= (i.max_qty || 99)}
                          className="flex h-7 w-7 items-center justify-center text-sm disabled:opacity-40"
                        >
                          +
                        </button>
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => void removeLine(i)}
                      aria-label={`Remover ${i.product_name}`}
                      title="Remover"
                      className="text-text-muted transition hover:text-danger"
                    >
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.7"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <path d="M3 6h18" />
                        <path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" />
                        <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                        <path d="M10 11v6M14 11v6" />
                      </svg>
                    </button>
                  </div>
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
          <span>Revise Seu Pedido</span>
          <span className="font-bold">{formatBRL(t.grand_total_cents)}</span>
        </summary>
        <div className="border-t border-surface-border px-4 py-4">{body}</div>
      </details>
    );
  }

  return (
    <>
      <Card variant="outline" className="hidden lg:sticky lg:top-6 lg:flex lg:flex-col lg:gap-3 lg:self-start">
        <h2 className="text-xl font-bold">Revise Seu Pedido</h2>
        {/* painel translúcido sutil separando o título do conteúdo */}
        <div className="rounded-card bg-black/[0.04] p-3">{body}</div>
      </Card>

      <details className="rounded-card border border-surface-border bg-surface lg:hidden">
        <summary className="flex cursor-pointer items-center justify-between gap-2 px-4 py-3 text-sm font-semibold">
          <span>Resumo do pedido</span>
          <span className="font-bold">{formatBRL(t.grand_total_cents)}</span>
        </summary>
        <div className="border-t border-surface-border bg-black/[0.02] px-4 py-4">{body}</div>
      </details>
    </>
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
