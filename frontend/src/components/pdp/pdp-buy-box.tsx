'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@ecom/ui';
import type { ProductDetail, ProductVariant } from '@/modules/catalog/types';
import { useCart } from '@/modules/cart/cart-context';
import { applyPixDiscount, formatBRL, installmentsText } from '@/lib/format';
import { HeartIcon } from '@/components/icons';
import { useWishlist } from '@/modules/wishlist/use-wishlist';

interface PdpBuyBoxProps {
  product: ProductDetail;
}

export function PdpBuyBox({ product }: PdpBuyBoxProps) {
  const router = useRouter();
  const { addItem } = useCart();
  const { has: isWished, toggle: toggleWish } = useWishlist();
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasVariants = product.option_types.length > 0 && product.variants.length > 0;

  const activeVariants = useMemo(
    () => product.variants.filter((v) => v.is_active),
    [product.variants],
  );

  /** Um valor está disponível se há variante em estoque com ele + demais seleções. */
  const isValueAvailable = (optionTypeId: string, valueId: string): boolean => {
    const others = Object.entries(selected).filter(([tid]) => tid !== optionTypeId);
    return activeVariants.some((v) => {
      if (!v.option_value_ids.includes(valueId)) return false;
      if (!v.in_stock) return false;
      return others.every(([, vid]) => v.option_value_ids.includes(vid));
    });
  };

  const selectedVariant: ProductVariant | null = useMemo(() => {
    if (!hasVariants) return null;
    if (Object.keys(selected).length !== product.option_types.length) return null;
    const wanted = new Set(Object.values(selected));
    return (
      activeVariants.find(
        (v) => v.option_value_ids.length === wanted.size && v.option_value_ids.every((id) => wanted.has(id)),
      ) ?? null
    );
  }, [hasVariants, selected, product.option_types.length, activeVariants]);

  const priceCents = selectedVariant?.price_cents ?? product.price_cents;
  const compareAt = selectedVariant?.compare_at_price_cents ?? product.compare_at_price_cents;
  const pixCents = applyPixDiscount(priceCents, product.pix_discount_pct);
  const parcela = installmentsText(priceCents, product.installments_max);

  /** Produto simples: usa a variante única. Com opções: a combinação escolhida. */
  const soloVariant = !hasVariants ? (activeVariants[0] ?? null) : null;
  const buyVariant = selectedVariant ?? soloVariant;

  const needsSelection = hasVariants && !selectedVariant;
  const outOfStock = hasVariants
    ? !!selectedVariant && !selectedVariant.in_stock
    : !soloVariant || !soloVariant.in_stock;
  const canBuy = !needsSelection && !outOfStock && !!buyVariant && !busy;

  const onBuy = async () => {
    if (!canBuy || !buyVariant) return;
    setBusy(true);
    setError(null);
    const res = await addItem(buyVariant.id, qty);
    setBusy(false);
    if (!res.ok) {
      setError(res.error ?? 'Não foi possível adicionar ao carrinho.');
      return;
    }
    setAdded(true);
    window.setTimeout(() => setAdded(false), 2500);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Preço */}
      <div className="flex flex-col gap-1">
        {compareAt && compareAt > priceCents && (
          <span className="text-sm text-text-muted line-through">{formatBRL(compareAt)}</span>
        )}
        <span className="text-2xl font-semibold sm:text-3xl">{formatBRL(priceCents)}</span>
        {parcela && <span className="text-sm text-text-muted">{parcela}</span>}
        {product.pix_discount_pct ? (
          <span className="mt-1 inline-flex w-fit items-center gap-2 rounded-card bg-success/10 px-2 py-1 text-sm font-medium text-success">
            {Math.round(product.pix_discount_pct)}% NO PIX
            <span className="text-text-muted">{formatBRL(pixCents)}</span>
          </span>
        ) : null}
      </div>

      {/* Seletor de variação */}
      {product.option_types.map((type) => (
        <fieldset key={type.id} className="flex flex-col gap-2">
          <legend className="text-sm font-medium">
            {type.name}
            {type.is_size && (
              <a href="#guia-de-medidas" className="ml-2 text-xs font-normal text-primary underline">
                Guia de medidas
              </a>
            )}
          </legend>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={type.name}>
            {type.values.map((value) => {
              const isSelected = selected[type.id] === value.id;
              const available = isValueAvailable(type.id, value.id);
              return (
                <button
                  key={value.id}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  aria-disabled={!available}
                  onClick={() =>
                    setSelected((prev) => ({ ...prev, [type.id]: value.id }))
                  }
                  className={`relative min-h-touch min-w-touch rounded-card border px-3 text-sm transition ${
                    isSelected
                      ? 'border-primary bg-primary text-primary-fg'
                      : 'border-surface-border bg-surface hover:border-primary'
                  } ${!available ? 'text-text-muted' : ''}`}
                >
                  <span className={!available ? 'line-through decoration-2' : ''}>{value.value}</span>
                </button>
              );
            })}
          </div>
        </fieldset>
      ))}

      {needsSelection && (
        <p className="text-xs text-text-muted">Selecione as opções para continuar.</p>
      )}
      {outOfStock && (
        <p className="text-sm font-medium text-danger">Combinação esgotada.</p>
      )}

      {/* Quantidade + comprar */}
      <div className="flex items-stretch gap-2">
        <div className="flex items-center rounded-card border border-surface-border">
          <button
            type="button"
            onClick={() => setQty((q) => Math.max(1, q - 1))}
            aria-label="Diminuir quantidade"
            className="min-h-touch min-w-touch px-3 text-lg"
          >
            −
          </button>
          <span className="w-8 text-center text-sm" aria-live="polite">
            {qty}
          </span>
          <button
            type="button"
            onClick={() => setQty((q) => Math.min(99, q + 1))}
            aria-label="Aumentar quantidade"
            className="min-h-touch min-w-touch px-3 text-lg"
          >
            +
          </button>
        </div>
        <Button block onClick={() => void onBuy()} loading={busy} disabled={!canBuy} className="flex-1">
          {added ? 'Adicionado ✓' : 'COMPRAR'}
        </Button>
        <button
          type="button"
          onClick={() => toggleWish(product.id)}
          aria-pressed={isWished(product.id)}
          aria-label={isWished(product.id) ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
          className={`inline-flex min-h-touch min-w-touch items-center justify-center rounded-card border ${
            isWished(product.id)
              ? 'border-accent text-accent'
              : 'border-surface-border text-text-muted hover:text-text'
          }`}
        >
          <HeartIcon className="h-5 w-5" />
        </button>
      </div>

      {error && (
        <p className="text-sm text-danger" role="alert">
          {error}
        </p>
      )}

      {added && (
        <div className="flex flex-wrap items-center gap-3 rounded-card bg-success/10 px-3 py-2 text-sm">
          <span className="font-medium text-success" role="status">
            Produto adicionado ao carrinho.
          </span>
          <button
            type="button"
            onClick={() => router.push('/carrinho')}
            className="font-medium text-primary underline"
          >
            Ir para o carrinho
          </button>
        </div>
      )}
    </div>
  );
}
