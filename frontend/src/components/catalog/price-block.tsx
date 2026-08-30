import { cn } from '@ecom/ui';
import { formatBRL, installmentsText } from '@/lib/format';

interface PriceBlockProps {
  priceCents: number;
  compareAtCents?: number | null;
  installmentsMax?: number | null;
  discountPct?: number | null;
  /** `lg` para a PDP, `sm` para cards. */
  size?: 'sm' | 'lg';
  className?: string;
}

/** Preço à vista destacado + "de/por" + parcelamento. */
export function PriceBlock({
  priceCents,
  compareAtCents,
  installmentsMax,
  discountPct,
  size = 'sm',
  className,
}: PriceBlockProps) {
  const hasCompare = !!compareAtCents && compareAtCents > priceCents;
  const parcela = installmentsText(priceCents, installmentsMax);

  if (size === 'sm') {
    return (
      <div className={cn('flex flex-col gap-0.5', className)}>
        <span className="flex flex-wrap items-baseline gap-1.5">
          {hasCompare && (
            <span className="text-xs text-text-muted line-through">
              {formatBRL(compareAtCents ?? 0)}
            </span>
          )}
          <span className="text-base font-bold text-text">{formatBRL(priceCents)}</span>
          {typeof discountPct === 'number' && discountPct > 0 && (
            <span className="ecom-discount-badge text-xs font-semibold text-success">
              {discountPct}% OFF
            </span>
          )}
        </span>
        {parcela && <span className="text-xs text-text-muted">{parcela}</span>}
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col gap-0.5', className)}>
      {hasCompare && (
        <span className="text-xs text-text-muted line-through">{formatBRL(compareAtCents ?? 0)}</span>
      )}
      <span className="text-2xl font-semibold text-text sm:text-3xl">
        {formatBRL(priceCents)}
        {typeof discountPct === 'number' && discountPct > 0 && (
          <span className="ecom-discount-badge ml-2 align-middle text-xs font-semibold text-success">
            {discountPct}% OFF
          </span>
        )}
      </span>
      {parcela && <span className="text-sm text-text-muted">{parcela}</span>}
    </div>
  );
}
