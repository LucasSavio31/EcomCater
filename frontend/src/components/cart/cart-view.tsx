'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { Button, Card, Spinner } from '@ecom/ui';
import { useCart } from '@/modules/cart/cart-context';
import { track, cartToTrackItems } from '@/modules/analytics';
import type { CartItem } from '@/modules/cart/types';
import { resolveMediaUrl } from '@/lib/media';
import { formatBRL } from '@/lib/format';
import { BagIcon } from '@/components/icons';
import { CollapsibleCoupon } from './coupon-field';
import { ShippingPicker } from './shipping-picker';
import { OrderTotals } from './order-totals';
import { FreeShippingProgress } from '@/components/layout/free-shipping-progress';

export function CartView({ reassurance = null }: { reassurance?: string[] | null }) {
  const router = useRouter();
  const { cart, loading } = useCart();
  const viewTracked = useRef(false);

  useEffect(() => {
    if (viewTracked.current || loading || cart.items.length === 0) return;
    viewTracked.current = true;
    track('view_cart', {
      value: cart.totals.items_total_cents / 100,
      items: cartToTrackItems(cart.items),
    });
  }, [loading, cart]);

  if (loading) {
    return (
      <p className="flex items-center gap-2 py-16 text-text-muted">
        <Spinner /> Carregando seu carrinho…
      </p>
    );
  }

  if (cart.items.length === 0) {
    return (
      <Card variant="outline" className="flex flex-col items-center gap-4 py-16 text-center">
        <BagIcon className="h-10 w-10 text-text-muted" />
        <div>
          <h2 className="text-lg font-semibold">Seu carrinho está vazio</h2>
          <p className="text-sm text-text-muted">Explore a loja e adicione produtos por aqui.</p>
        </div>
        <Button onClick={() => router.push('/')}>Voltar às compras</Button>
      </Card>
    );
  }

  const hasBlockingIssue = cart.items.some((i) => !i.in_stock);
  // Pedido já qualifica para frete grátis → não mostra o cálculo de CEP.
  const freeShipping =
    cart.totals.free_shipping_threshold_cents != null &&
    (cart.totals.free_shipping_remaining_cents ?? 1) === 0;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_26rem]">
      <div className="flex flex-col gap-3">
        <ul className="flex flex-col gap-3">
          {cart.items.map((item) => (
            <CartRow key={item.id} item={item} />
          ))}
        </ul>
        <Link href="/" className="text-sm text-primary underline">
          ← Continuar comprando
        </Link>
      </div>

      <aside className="flex flex-col gap-4 lg:sticky lg:top-24 lg:self-start">
        <Card variant="outline" className="flex flex-col gap-4">
          <h2 className="text-xl font-bold">Resumo</h2>
          <FreeShippingProgress variant="bar" className="rounded-card bg-bg-subtle p-3" />
          <CollapsibleCoupon />
          {!freeShipping && <ShippingPicker />}
          <OrderTotals
            totals={cart.totals}
            hasShipping={!!cart.selected_shipping}
            freeShipping={freeShipping}
          />
          {hasBlockingIssue && (
            <p className="text-xs text-danger">
              Remova ou ajuste os itens sem estoque para finalizar.
            </p>
          )}
          <Button
            block
            size="lg"
            disabled={hasBlockingIssue}
            onClick={() => router.push('/checkout')}
            className="border text-base font-bold !min-h-[3.25rem] sm:!min-h-touch"
            style={{
              background: 'var(--color-cart-btn-bg)',
              color: 'var(--color-cart-btn-fg)',
              borderColor: 'var(--color-cart-btn-border)',
              borderRadius: 'var(--radius-cart-btn, 0.75rem)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-cart-btn-hover)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--color-cart-btn-bg)')}
          >
            Finalizar compra
          </Button>
          <p className="text-center text-xs text-text-muted">
            Frete e prazos são confirmados na etapa de pagamento.
          </p>
          {reassurance && reassurance.length > 0 && (
            <ul className="flex flex-col gap-1 border-t border-surface-border pt-3 text-xs text-text-muted">
              {reassurance.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          )}
        </Card>
      </aside>
    </div>
  );
}

function CartRow({ item }: { item: CartItem }) {
  const { updateItem, removeItem } = useCart();
  const [busy, setBusy] = useState(false);
  const img = resolveMediaUrl(item.image_url);

  /** item do carrinho com a QTD que mudou (não a qtd total da linha). */
  const trackItem = (quantity: number) => cartToTrackItems([{ ...item, quantity }]);

  async function change(qty: number) {
    if (qty < 1 || qty > item.max_qty || qty === item.quantity) return;
    const delta = qty - item.quantity;
    setBusy(true);
    const res = await updateItem(item.id, qty);
    setBusy(false);
    if (!res.ok) return; // só mede a mudança confirmada pela store
    if (delta > 0) track('add_to_cart', { items: trackItem(delta) });
    else track('remove_from_cart', { items: trackItem(-delta) });
  }

  async function remove() {
    setBusy(true);
    const res = await removeItem(item.id);
    setBusy(false);
    if (!res.ok) return;
    track('remove_from_cart', { items: trackItem(item.quantity) });
  }

  return (
    <li>
      <Card variant="outline" className={`flex gap-3 ${busy ? 'opacity-60' : ''}`}>
        <Link
          href={`/produto/${item.product_slug}`}
          className="relative block h-20 w-20 shrink-0 overflow-hidden rounded-card bg-bg-subtle"
        >
          {img && (
            <Image src={img} alt={item.product_name} fill sizes="80px" className="object-cover" />
          )}
        </Link>

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <Link
            href={`/produto/${item.product_slug}`}
            className="line-clamp-2 text-sm font-medium hover:underline"
          >
            {item.product_name}
          </Link>
          {item.variant_label && (
            <span className="text-xs text-text-muted">{item.variant_label}</span>
          )}
          <span className="text-xs text-text-muted">{formatBRL(item.unit_price_cents)} / un.</span>

          {!item.in_stock && (
            <span className="text-xs font-medium text-danger">
              Sem estoque suficiente (máx. {item.max_qty}).
            </span>
          )}
          {item.in_stock && item.price_changed && (
            <span className="text-xs text-warning">O preço deste item foi atualizado.</span>
          )}

          <div className="mt-1 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
            <div
              className="ecom-qty-stepper flex items-center overflow-hidden rounded-card border border-black/40"
              style={{
                background: 'var(--color-cart-qty-bg)',
                color: 'var(--color-cart-qty-fg)',
                borderRadius: 'var(--radius-cart-qty, 0.75rem)',
              }}
            >
              <button
                type="button"
                onClick={() => void change(item.quantity - 1)}
                disabled={busy || item.quantity <= 1}
                aria-label="Diminuir quantidade"
                className="flex h-9 w-9 items-center justify-center text-lg disabled:opacity-40 sm:min-h-touch sm:min-w-touch"
              >
                −
              </button>
              <input
                type="text"
                inputMode="numeric"
                aria-label="Quantidade"
                value={item.quantity}
                onChange={(e) => {
                  const n = Number(e.target.value.replace(/\D/g, ''));
                  if (n >= 1) void change(Math.min(n, item.max_qty));
                }}
                className="w-9 border-0 bg-transparent text-center text-sm text-current outline-none"
              />
              <button
                type="button"
                onClick={() => void change(item.quantity + 1)}
                disabled={busy || item.quantity >= item.max_qty}
                aria-label="Aumentar quantidade"
                className="flex h-9 w-9 items-center justify-center text-lg disabled:opacity-40 sm:min-h-touch sm:min-w-touch"
              >
                +
              </button>
            </div>
              <button
                type="button"
                onClick={() => void remove()}
                disabled={busy}
                aria-label={`Remover ${item.product_name}`}
                title="Remover"
                className="p-1 text-text-muted transition hover:text-danger disabled:opacity-40"
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
            <span className="text-sm font-semibold">{formatBRL(item.line_total_cents)}</span>
          </div>
        </div>
      </Card>
    </li>
  );
}

