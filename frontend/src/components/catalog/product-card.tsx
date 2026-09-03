'use client';

import Link from 'next/link';
import Image from 'next/image';
import { Badge } from '@ecom/ui';
import type { ProductListItem } from '@/modules/catalog/types';
import { resolveMediaUrl } from '@/lib/media';
import { track, itemFromListItem } from '@/modules/analytics';
import { PriceBlock } from './price-block';
import { Stars } from './stars';

interface ProductCardProps {
  product: ProductListItem;
  /** Prioriza o LCP (primeiros itens da primeira dobra). */
  priority?: boolean;
  className?: string;
  /** Rótulo do botão "Comprar" abaixo do card. Vazio/omitido = sem botão. */
  buyButtonLabel?: string;
  /** Lista de origem do clique (GA4 `select_item` / Meta `SelectItem`). */
  listId?: string;
  listName?: string;
  /** Posição do item na lista (0-based). */
  index?: number;
}

const CARD_SIZES =
  '(min-width: 1024px) 25vw, (min-width: 768px) 33vw, 50vw';

/**
 * Card de produto reutilizado em vitrine, PLP, busca e relacionados.
 * Imagem com troca no hover (CSS `group-hover`), badge de desconto, preço à
 * vista + parcelamento. Sempre `rounded-card`.
 */
export function ProductCard({
  product,
  priority = false,
  className,
  buyButtonLabel,
  listId,
  listName,
  index,
}: ProductCardProps) {
  const primary = resolveMediaUrl(product.primary_image_url);
  const hover = resolveMediaUrl(product.hover_image_url);
  const href = `/produto/${product.slug}`;

  const onSelect = () =>
    track('select_item', {
      item_list_id: listId,
      item_list_name: listName,
      items: [itemFromListItem(product, { index, list: { id: listId, name: listName } })],
    });

  return (
    <article
      className={`group relative flex flex-col overflow-hidden rounded-card bg-surface transition ${className ?? ''}`}
    >
      <Link
        href={href}
        onClick={onSelect}
        className="relative block aspect-square overflow-hidden rounded-card bg-white"
      >
        {primary ? (
          <>
            <Image
              src={primary}
              alt={product.name}
              fill
              sizes={CARD_SIZES}
              priority={priority}
              className={`ecom-card-img object-contain transition-opacity duration-300 ${hover ? 'group-hover:opacity-0' : ''}`}
            />
            {hover && (
              <Image
                src={hover}
                alt=""
                aria-hidden="true"
                fill
                sizes={CARD_SIZES}
                className="ecom-card-img object-contain opacity-0 transition-opacity duration-300 group-hover:opacity-100"
              />
            )}
          </>
        ) : (
          <span className="flex h-full w-full items-center justify-center text-xs text-text-muted">
            sem imagem
          </span>
        )}

        {typeof product.discount_pct === 'number' && product.discount_pct > 0 && (
          <Badge tone="accent" className="ecom-discount-badge ecom-promo-pill ecom-promo-pill--card absolute left-2 top-2">
            -{product.discount_pct}%
          </Badge>
        )}
        {!product.in_stock && (
          <Badge tone="neutral" className="absolute right-2 top-2 bg-bg/90">
            Esgotado
          </Badge>
        )}
      </Link>

      <div className="flex flex-1 flex-col gap-1 p-3 pl-0">
        <h3 className="line-clamp-2 text-sm font-bold uppercase leading-snug text-text">
          <Link href={href} className="hover:underline focus-visible:outline-none focus-visible:underline">
            {product.name}
          </Link>
        </h3>
        {product.rating_count > 0 && (
          <Stars value={product.rating_avg} count={product.rating_count} />
        )}
        <PriceBlock
          className="mt-auto pt-0.5"
          priceCents={product.price_cents}
          compareAtCents={product.compare_at_price_cents}
          pixDiscountPct={product.pix_discount_pct}
          installmentsMax={product.installments_max}
        />
        {buyButtonLabel && (
          <Link
            href={href}
            className="mt-2 inline-flex min-h-touch items-center justify-center rounded-btn bg-btn px-4 text-sm font-black uppercase tracking-wide text-black hover:opacity-90"
          >
            {buyButtonLabel}
          </Link>
        )}
      </div>
    </article>
  );
}
