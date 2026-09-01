'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { Button, Drawer } from '@ecom/ui';
import { useCart } from '@/modules/cart/cart-context';
import { track, cartToTrackItems } from '@/modules/analytics';
import { resolveMediaUrl } from '@/lib/media';
import { formatBRL } from '@/lib/format';
import { FreeShippingProgress } from '@/components/layout/free-shipping-progress';

/** Mini-carrinho lateral (abre à direita ao adicionar um produto). */
export function MiniCartDrawer() {
  const router = useRouter();
  const { cart, miniCartOpen, closeMiniCart, updateItem, removeItem } = useCart();
  const [busy, setBusy] = useState<string | null>(null);

  // view_cart quando o drawer é REALMENTE exibido com itens (uma vez por abertura)
  const viewedOpen = useRef(false);
  useEffect(() => {
    if (!miniCartOpen) {
      viewedOpen.current = false;
      return;
    }
    if (viewedOpen.current || cart.items.length === 0) return;
    viewedOpen.current = true;
    track('view_cart', { items: cartToTrackItems(cart.items) });
  }, [miniCartOpen, cart.items]);

  /** item do carrinho com a QTD que mudou. */
  const trackItem = (id: string, quantity: number) => {
    const i = cart.items.find((x) => x.id === id);
    return i ? cartToTrackItems([{ ...i, quantity }]) : null;
  };

  async function change(id: string, qty: number, max: number) {
    if (qty < 1 || qty > max) return;
    const cur = cart.items.find((x) => x.id === id)?.quantity ?? qty;
    const delta = qty - cur;
    const items = trackItem(id, Math.abs(delta));
    setBusy(id);
    const res = await updateItem(id, qty);
    setBusy(null);
    if (res.ok && items && delta !== 0) {
      track(delta > 0 ? 'add_to_cart' : 'remove_from_cart', { items });
    }
  }
  async function remove(id: string) {
    const items = trackItem(id, cart.items.find((x) => x.id === id)?.quantity ?? 1);
    setBusy(id);
    const res = await removeItem(id);
    setBusy(null);
    if (res.ok && items) track('remove_from_cart', { items });
  }

  return (
    <Drawer
      open={miniCartOpen}
      onClose={closeMiniCart}
      side="right"
      title="Meu carrinho"
      labelledById="mini-cart-title"
    >
      <div className="flex h-full flex-col">
        {cart.items.length === 0 ? (
          <p className="py-10 text-center text-sm text-text-muted">Seu carrinho está vazio.</p>
        ) : (
          <ul className="flex-1 divide-y divide-surface-border overflow-y-auto">
            {cart.items.map((i) => {
              const img = resolveMediaUrl(i.image_url);
              return (
                <li key={i.id} className={`flex gap-3 py-3 ${busy === i.id ? 'opacity-50' : ''}`}>
                  <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-card bg-bg-subtle">
                    {img && <Image src={img} alt="" fill sizes="64px" className="object-cover" />}
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col gap-1">
                    <div className="flex items-start justify-between gap-2">
                      <span className="line-clamp-2 text-sm font-medium">{i.product_name}</span>
                      <button
                        type="button"
                        aria-label="Remover"
                        onClick={() => void remove(i.id)}
                        className="shrink-0 text-text-muted hover:text-danger"
                      >
                        🗑
                      </button>
                    </div>
                    {i.variant_label && (
                      <span className="text-xs text-text-muted">Tamanho: {i.variant_label}</span>
                    )}
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold">{formatBRL(i.line_total_cents)}</span>
                      <div className="flex items-center rounded-card border border-surface-border">
                        <button
                          type="button"
                          onClick={() => void change(i.id, i.quantity - 1, i.max_qty)}
                          disabled={i.quantity <= 1}
                          aria-label="Diminuir"
                          className="min-h-touch px-2.5 text-lg disabled:opacity-40"
                        >
                          −
                        </button>
                        <span className="w-7 text-center text-sm">{i.quantity}</span>
                        <button
                          type="button"
                          onClick={() => void change(i.id, i.quantity + 1, i.max_qty)}
                          disabled={i.quantity >= i.max_qty}
                          aria-label="Aumentar"
                          className="min-h-touch px-2.5 text-lg disabled:opacity-40"
                        >
                          +
                        </button>
                      </div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {cart.items.length > 0 && (
          <div className="mt-3 flex flex-col gap-2 border-t border-surface-border pt-3">
            <FreeShippingProgress variant="bar" className="mb-1 rounded-card bg-bg-subtle p-2.5" />
            <div className="flex justify-between text-sm">
              <span className="text-text-muted">Subtotal</span>
              <span>{formatBRL(cart.totals.items_total_cents)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-muted">Entrega</span>
              <span>{cart.selected_shipping ? formatBRL(cart.totals.shipping_cents) : 'A calcular'}</span>
            </div>
            <div className="flex justify-between border-t border-surface-border pt-2 text-base font-bold">
              <span>Total</span>
              <span>{formatBRL(cart.totals.grand_total_cents)}</span>
            </div>
            <Button
              block
              size="lg"
              className="mt-1 uppercase tracking-wide"
              onClick={() => {
                closeMiniCart();
                router.push('/checkout');
              }}
            >
              Ir para o checkout
            </Button>
            <button
              type="button"
              onClick={closeMiniCart}
              className="text-center text-sm font-semibold uppercase tracking-wide text-text underline"
            >
              Continuar comprando
            </button>
          </div>
        )}
      </div>
    </Drawer>
  );
}
