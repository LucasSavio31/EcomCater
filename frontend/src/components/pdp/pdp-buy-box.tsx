'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@ecom/ui';
import type { ProductDetail, ProductVariant } from '@/modules/catalog/types';
import { useCart } from '@/modules/cart/cart-context';
import { applyPixDiscount, formatBRL, installmentsText } from '@/lib/format';
import { HeartIcon } from '@/components/icons';
import { useWishlist } from '@/modules/wishlist/use-wishlist';
import { track, itemFromDetail } from '@/modules/analytics';
import { LeadPopup, type LeadPopupConfig } from '@/components/lead-popup';
import { SizeChartButton, type SizeChartColors } from '@/components/pdp/size-chart';

interface PdpBuyBoxProps {
  product: ProductDetail;
  /** Após adicionar ao carrinho, ir direto para /carrinho. */
  redirectAfterAdd?: boolean;
  /** Abrir o mini-carrinho lateral ao adicionar (tem precedência). */
  miniCart?: boolean;
  leadPopup?: LeadPopupConfig | null;
  showQty?: boolean;
  showWishlist?: boolean;
  sizeChartColors?: SizeChartColors;
}

export function PdpBuyBox({
  product,
  redirectAfterAdd = false,
  miniCart = false,
  leadPopup = null,
  showQty = true,
  showWishlist = true,
  sizeChartColors,
}: PdpBuyBoxProps) {
  const router = useRouter();
  const { addItem, openMiniCart } = useCart();
  const { has: isWished, toggle: toggleWish } = useWishlist();
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [leadOpen, setLeadOpen] = useState(false);
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [triedBuy, setTriedBuy] = useState(false);

  const hasVariants = product.option_types.length > 0 && product.variants.length > 0;

  const activeVariants = useMemo(
    () => product.variants.filter((v) => v.is_active),
    [product.variants],
  );

  const effectiveSelected = selected;

  const isValueAvailable = (optionTypeId: string, valueId: string): boolean => {
    const others = Object.entries(effectiveSelected).filter(([tid]) => tid !== optionTypeId);
    return activeVariants.some((v) => {
      if (!v.option_value_ids.includes(valueId)) return false;
      if (!v.in_stock) return false;
      return others.every(([, vid]) => v.option_value_ids.includes(vid));
    });
  };

  const selectedVariant: ProductVariant | null = useMemo(() => {
    if (!hasVariants) return null;
    if (Object.keys(effectiveSelected).length !== product.option_types.length) return null;
    const wanted = new Set(Object.values(effectiveSelected));
    return (
      activeVariants.find(
        (v) => v.option_value_ids.length === wanted.size && v.option_value_ids.every((id) => wanted.has(id)),
      ) ?? null
    );
  }, [hasVariants, effectiveSelected, product.option_types.length, activeVariants]);

  const priceCents = selectedVariant?.price_cents ?? product.price_cents;
  const compareAt = selectedVariant?.compare_at_price_cents ?? product.compare_at_price_cents;
  const pixCents = applyPixDiscount(priceCents, product.pix_discount_pct);
  const parcela = installmentsText(priceCents, product.installments_max);
  const onSale = !!compareAt && compareAt > priceCents;
  const discountPct = onSale ? Math.round((1 - priceCents / (compareAt as number)) * 100) : 0;

  const soloVariant = !hasVariants ? (activeVariants[0] ?? null) : null;
  const buyVariant = selectedVariant ?? soloVariant;

  const needsSelection = hasVariants && !selectedVariant;
  const outOfStock = hasVariants
    ? !!selectedVariant && !selectedVariant.in_stock
    : !soloVariant || !soloVariant.in_stock;
  const canBuy = !needsSelection && !outOfStock && !!buyVariant && !busy;

  const chooseValue = (typeId: string, valueId: string) => {
    setSelected((prev) => ({ ...prev, [typeId]: valueId }));
  };

  const onBuy = async () => {
    if (needsSelection) {
      setTriedBuy(true);
      document
        .querySelector<HTMLElement>('[data-variation-picker]')
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    if (!canBuy || !buyVariant) return;
    setBusy(true);
    setError(null);
    const res = await addItem(buyVariant.id, qty);
    setBusy(false);
    if (!res.ok) {
      setError(res.error ?? 'Não foi possível adicionar ao carrinho.');
      return;
    }
    // confirmado pela API (res.ok) → dispara com a variante e a qtd realmente adicionada
    track('add_to_cart', {
      items: [itemFromDetail(product, { variant: buyVariant, quantity: qty })],
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

  return (
    <div className="flex flex-col gap-5">
      {/* Preço */}
      <div className="flex flex-col gap-1.5">
        {onSale && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-muted line-through">{formatBRL(compareAt as number)}</span>
            <span className="ecom-discount-badge ecom-promo-pill ecom-promo-pill--pdp rounded-[4px] px-1.5 py-0.5 text-xs font-bold">
              -{discountPct}%
            </span>
          </div>
        )}
        <span className="text-3xl font-bold leading-tight sm:text-4xl">{formatBRL(priceCents)}</span>
        {product.pix_discount_pct ? (
          <p className="text-sm">
            <span className="font-semibold text-success">{formatBRL(pixCents)}</span>{' '}
            <span className="text-text-muted">
              à vista no PIX {Math.round(product.pix_discount_pct)}% OFF
            </span>
          </p>
        ) : null}
        {parcela && <p className="text-sm text-text-muted">{parcela.replace(/^ou /, 'Ou ')}</p>}
      </div>

      {/* Eixos de variação → caixinhas (numeração/tamanho etc.) */}
      {product.option_types.map((type) => {
        const missing = triedBuy && !effectiveSelected[type.id];
        return (
          <fieldset key={type.id} data-variation-picker className="flex flex-col gap-2">
            <legend className={`mb-1 flex w-full items-center justify-between text-sm font-semibold uppercase tracking-wide ${missing ? 'text-danger' : ''}`}>
              <span>
                {type.name}
                {effectiveSelected[type.id] && (
                  <span className="ml-1 font-normal normal-case text-text-muted">
                    · {type.values.find((v) => v.id === effectiveSelected[type.id])?.value}
                  </span>
                )}
              </span>
              {type.is_size && product.size_chart && (
                <SizeChartButton chart={product.size_chart} colors={sizeChartColors} />
              )}
            </legend>
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={type.name}>
              {type.values.map((value) => {
                const isSelected = effectiveSelected[type.id] === value.id;
                const available = isValueAvailable(type.id, value.id);
                return (
                  <button
                    key={value.id}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    aria-disabled={!available}
                    onClick={() => {
                      setTriedBuy(false);
                      chooseValue(type.id, value.id);
                    }}
                    style={{ borderRadius: 'var(--radius-var, 0.75rem)' }}
                    className={`relative flex h-11 min-w-[3rem] items-center justify-center border-2 px-3 text-sm font-medium transition ${
                      isSelected
                        ? 'border-var-border bg-var text-var-fg'
                        : missing
                          ? 'border-danger bg-surface'
                          : 'border-surface-border bg-surface hover:border-var-border'
                    } ${!available ? 'text-text-muted' : ''}`}
                  >
                    <span className={!available ? 'line-through decoration-2' : ''}>{value.value}</span>
                  </button>
                );
              })}
            </div>
            {missing && (
              <p className="text-xs font-medium text-danger">Escolha {type.name.toLowerCase()}.</p>
            )}
          </fieldset>
        );
      })}

      {needsSelection && !triedBuy && (
        <p className="text-xs text-text-muted">Selecione a numeração para continuar.</p>
      )}
      {outOfStock && <p className="text-sm font-medium text-danger">Combinação esgotada.</p>}

      {/* Quantidade + comprar */}
      <div className="flex flex-col gap-2">
        <div className="flex items-stretch gap-2">
          {showQty && (
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
          )}
          <Button
            block
            size="lg"
            onClick={() => void onBuy()}
            loading={busy}
            disabled={busy || outOfStock}
            className="flex-1 gap-2 text-lg font-extrabold uppercase tracking-wide"
          >
            {!busy && (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="9" cy="21" r="1" />
                <circle cx="20" cy="21" r="1" />
                <path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6" />
              </svg>
            )}
            {added ? 'Adicionado ✓' : 'Comprar'}
          </Button>
          {showWishlist && (
            <button
              type="button"
              onClick={() => {
                // favoritos é local (localStorage) → só dispara quando de fato ADICIONA
                if (!isWished(product.id)) {
                  track('add_to_wishlist', {
                    items: [itemFromDetail(product, { variant: selectedVariant })],
                  });
                }
                toggleWish(product.id);
              }}
              aria-pressed={isWished(product.id)}
              aria-label={isWished(product.id) ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
              className={`inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-card border-2 ${
                isWished(product.id) ? '' : 'border-surface-border text-text-muted hover:text-text'
              }`}
              style={
                isWished(product.id)
                  ? {
                      background: 'var(--color-wish-bg)',
                      borderColor: 'var(--color-wish-border)',
                      color: 'var(--color-wish-icon)',
                    }
                  : undefined
              }
            >
              <HeartIcon className="h-5 w-5" fill={isWished(product.id) ? 'currentColor' : 'none'} />
            </button>
          )}
        </div>
        {leadPopup?.enabled && (
          <button
            type="button"
            onClick={() => setLeadOpen(true)}
            className="w-fit text-xs font-medium text-primary underline"
          >
            Cadastre-se e ganhe promoções e cupons exclusivos
          </button>
        )}
      </div>

      {leadPopup?.enabled && (
        <LeadPopup open={leadOpen} onClose={() => setLeadOpen(false)} config={leadPopup} />
      )}

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
