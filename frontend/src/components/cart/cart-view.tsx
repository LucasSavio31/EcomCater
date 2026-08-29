'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { Button, Card, Spinner } from '@ecom/ui';
import { useCart } from '@/modules/cart/cart-context';
import type { CartItem } from '@/modules/cart/types';
import { resolveMediaUrl } from '@/lib/media';
import { formatBRL } from '@/lib/format';
import { BagIcon } from '@/components/icons';
import { CouponField } from './coupon-field';
import { ShippingPicker } from './shipping-picker';
import { OrderTotals } from './order-totals';

export function CartView() {
  const router = useRouter();
  const { cart, loading } = useCart();

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

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
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
          <h2 className="text-base font-semibold">Resumo</h2>
          <CouponField />
          <ShippingPicker />
          <OrderTotals totals={cart.totals} hasShipping={!!cart.selected_shipping} />
          {hasBlockingIssue && (
            <p className="text-xs text-danger">
              Remova ou ajuste os itens sem estoque para finalizar.
            </p>
          )}
          <Button block disabled={hasBlockingIssue} onClick={() => router.push('/checkout')}>
            Finalizar compra
          </Button>
          <p className="text-center text-xs text-text-muted">
            Frete e prazos são confirmados na etapa de pagamento.
          </p>
        </Card>
      </aside>
    </div>
  );
}

function CartRow({ item }: { item: CartItem }) {
  const { updateItem, removeItem } = useCart();
  const [busy, setBusy] = useState(false);
  const img = resolveMediaUrl(item.image_url);

  async function change(qty: number) {
    if (qty < 1 || qty > item.max_qty || qty === item.quantity) return;
    setBusy(true);
    await updateItem(item.id, qty);
    setBusy(false);
  }

  async function remove() {
    setBusy(true);
    await removeItem(item.id);
    setBusy(false);
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
            <div className="flex items-center rounded-card border border-surface-border">
              <button
                type="button"
                onClick={() => void change(item.quantity - 1)}
                disabled={busy || item.quantity <= 1}
                aria-label="Diminuir quantidade"
                className="min-h-touch min-w-touch px-3 text-lg disabled:opacity-40"
              >
                −
              </button>
              <span className="w-8 text-center text-sm">{item.quantity}</span>
              <button
                type="button"
                onClick={() => void change(item.quantity + 1)}
                disabled={busy || item.quantity >= item.max_qty}
                aria-label="Aumentar quantidade"
                className="min-h-touch min-w-touch px-3 text-lg disabled:opacity-40"
              >
                +
              </button>
            </div>
            <span className="text-sm font-semibold">{formatBRL(item.line_total_cents)}</span>
          </div>

          <button
            type="button"
            onClick={() => void remove()}
            disabled={busy}
            className="mt-1 w-fit text-xs text-text-muted underline hover:text-danger"
          >
            Remover
          </button>
        </div>
      </Card>
    </li>
  );
}
