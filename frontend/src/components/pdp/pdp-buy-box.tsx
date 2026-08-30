'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@ecom/ui';
import type { ProductDetail, ProductVariant } from '@/modules/catalog/types';
import { useCart } from '@/modules/cart/cart-context';
import { applyPixDiscount, formatBRL, installmentsText } from '@/lib/format';
import { HeartIcon } from '@/components/icons';
import { useWishlist } from '@/modules/wishlist/use-wishlist';
import { track, type TrackItem } from '@/modules/analytics';

interface PdpBuyBoxProps {
  product: ProductDetail;
  /** Após adicionar ao carrinho, ir direto para /carrinho. */
  redirectAfterAdd?: boolean;
  /** Abrir o mini-carrinho lateral ao adicionar (tem precedência). */
  miniCart?: boolean;
}

export function PdpBuyBox({ product, redirectAfterAdd = false, miniCart = false }: PdpBuyBoxProps) {
  const router = useRouter();
  const { addItem, openMiniCart } = useCart();
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
  const onSale = !!compareAt && compareAt > priceCents;
  const discountPct = onSale ? Math.round((1 - priceCents / (compareAt as number)) * 100) : 0;

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
    track('add_to_cart', {
      value: (priceCents / 100) * qty,
      items: [{ ...baseTrackItem(), price: priceCents / 100, quantity: qty }],
    });
    if (miniCart) {
      openMiniCart();
      return;
    }
    if (redirectAfterAdd) {
      router.push('/carrinho');
      return;
    }
    setAdded(true);
    window.setTimeout(() => setAdded(false), 2500);
  };

  function baseTrackItem(): TrackItem {
    return {
      id: selectedVariant?.sku ?? product.sku_root ?? product.id,
      name: product.name,
      price: priceCents / 100,
      brand: product.brand ?? undefined,
      category: product.category?.name ?? undefined,
      variant: selectedVariant?.option_labels?.join(' / ') || undefined,
    };
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Preço */}
      <div className="flex flex-col gap-1.5">
        {onSale && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-muted line-through">{formatBRL(compareAt as number)}</span>
            <span className="rounded-[4px] bg-accent px-1.5 py-0.5 text-xs font-bold text-white">
              -{discountPct}%
            </span>
          </div>
        )}
        <span className="text-3xl font-bold leading-tight sm:text-4xl">{formatBRL(priceCents)}</span>
        {product.pix_discount_pct ? (
          <p className="text-sm text-text">
            <span className="font-semibold text-success">
              À vista no PIX {Math.round(product.pix_discount_pct)}% OFF
            </span>{' '}
            <span className="text-text-muted">— {formatBRL(pixCents)}</span>
          </p>
        ) : null}
        {parcela && <p className="text-sm text-text-muted">{parcela.replace(/^ou /, 'Ou ')}</p>}
      </div>

      {/* Seletor de variação */}
      {product.option_types.map((type) => (
        <fieldset key={type.id} className="flex flex-col gap-2">
          <legend className="mb-1 flex w-full items-center justify-between text-sm font-semibold">
            <span>
              {type.name}
              {selected[type.id] && (
                <span className="ml-1 font-normal text-text-muted">
                  · {type.values.find((v) => v.id === selected[type.id])?.value}
                </span>
              )}
            </span>
            {type.is_size && (
              <a href="#specs" className="text-xs font-normal text-primary underline">
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
                  className={`relative flex h-11 min-w-[3rem] items-center justify-center rounded-card border-2 px-3 text-sm font-medium transition ${
                    isSelected
                      ? 'border-var-border bg-var text-var-fg'
                      : 'border-surface-border bg-surface hover:border-var-border'
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

      {/* Quantidade + adicionar ao carrinho */}
      <div className="flex flex-col gap-2">
        <div className="flex items-stretch gap-2">
          <div className="flex items-center rounded-card border border-surface-border">
            <button
              type="button"
              onClick={() => setQty((q) => Math.max(1, q - 1))}
              aria-label="Diminuir quantidade"
              className="flex h-12 w-11 items-center justify-center text-lg"
            >
              −
            </button>
            <span className="w-8 text-center text-sm font-medium" aria-live="polite">
              {qty}
            </span>
            <button
              type="button"
              onClick={() => setQty((q) => Math.min(99, q + 1))}
              aria-label="Aumentar quantidade"
              className="flex h-12 w-11 items-center justify-center text-lg"
            >
              +
            </button>
          </div>
          <Button
            block
            size="lg"
            onClick={() => void onBuy()}
            loading={busy}
            disabled={!canBuy}
            className="flex-1 text-sm font-semibold uppercase tracking-wide"
          >
            {added ? 'Adicionado ✓' : 'Adicionar ao carrinho'}
          </Button>
          <button
            type="button"
            onClick={() => {
              if (!isWished(product.id)) {
                track('add_to_wishlist', {
                  value: priceCents / 100,
                  items: [{ ...baseTrackItem(), price: priceCents / 100 }],
                });
              }
              toggleWish(product.id);
            }}
            aria-pressed={isWished(product.id)}
            aria-label={isWished(product.id) ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
            className={`inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-card border ${
              isWished(product.id)
                ? 'border-accent text-accent'
                : 'border-surface-border text-text-muted hover:text-text'
            }`}
          >
            <HeartIcon className="h-5 w-5" />
          </button>
        </div>
        <button
          type="button"
          onClick={() => router.push('/minha-conta')}
          className="w-fit text-xs font-medium text-primary underline"
        >
          Cadastre-se e ganhe 10% OFF na primeira compra
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
