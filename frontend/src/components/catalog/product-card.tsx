import Link from 'next/link';
import Image from 'next/image';
import { Badge } from '@ecom/ui';
import type { ProductListItem } from '@/modules/catalog/types';
import { resolveMediaUrl } from '@/lib/media';
import { PriceBlock } from './price-block';
import { Stars } from './stars';

interface ProductCardProps {
  product: ProductListItem;
  /** Prioriza o LCP (primeiros itens da primeira dobra). */
  priority?: boolean;
  className?: string;
}

const CARD_SIZES =
  '(min-width: 1024px) 25vw, (min-width: 768px) 33vw, 50vw';

/**
 * Card de produto reutilizado em vitrine, PLP, busca e relacionados.
 * Imagem com troca no hover (CSS `group-hover`), badge de desconto, preço à
 * vista + parcelamento. Sempre `rounded-card`.
 */
export function ProductCard({ product, priority = false, className }: ProductCardProps) {
  const primary = resolveMediaUrl(product.primary_image_url);
  const hover = resolveMediaUrl(product.hover_image_url);
  const href = `/produto/${product.slug}`;

  return (
    <article
      className={`group relative flex flex-col overflow-hidden rounded-card border border-surface-border bg-surface transition hover:shadow-sm ${className ?? ''}`}
    >
      <Link href={href} className="relative block aspect-[3/4] overflow-hidden bg-bg-subtle">
        {primary ? (
          <>
            <Image
              src={primary}
              alt={product.name}
              fill
              sizes={CARD_SIZES}
              priority={priority}
              className={`object-cover transition-opacity duration-300 ${hover ? 'group-hover:opacity-0' : ''}`}
            />
            {hover && (
              <Image
                src={hover}
                alt=""
                aria-hidden="true"
                fill
                sizes={CARD_SIZES}
                className="object-cover opacity-0 transition-opacity duration-300 group-hover:opacity-100"
              />
            )}
          </>
        ) : (
          <span className="flex h-full w-full items-center justify-center text-xs text-text-muted">
            sem imagem
          </span>
        )}

        {typeof product.discount_pct === 'number' && product.discount_pct > 0 && (
          <Badge tone="accent" className="ecom-discount-badge absolute left-2 top-2">
            -{product.discount_pct}%
          </Badge>
        )}
        {!product.in_stock && (
          <Badge tone="neutral" className="absolute right-2 top-2 bg-bg/90">
            Esgotado
          </Badge>
        )}
      </Link>

      <div className="flex flex-1 flex-col gap-1.5 p-3">
        {product.brand && (
          <span className="text-[11px] uppercase tracking-wide text-text-muted">{product.brand}</span>
        )}
        <h3 className="line-clamp-2 text-sm text-text">
          <Link href={href} className="hover:underline focus-visible:outline-none focus-visible:underline">
            {product.name}
          </Link>
        </h3>
        {product.rating_count > 0 && (
          <Stars value={product.rating_avg} count={product.rating_count} />
        )}
        <PriceBlock
          className="mt-auto pt-1"
          priceCents={product.price_cents}
          compareAtCents={product.compare_at_price_cents}
          installmentsMax={product.installments_max}
        />
      </div>
    </article>
  );
}
