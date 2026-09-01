import { formatBRL } from '@/lib/format';
import type { CartTotals } from '@/modules/cart/types';

/** Quebra de valores (subtotal, desconto, frete, total) — usada no carrinho e no checkout. */
export function OrderTotals({
  totals,
  hasShipping = false,
  freeShipping = false,
}: {
  totals: CartTotals;
  /** Há uma opção de frete escolhida? Se não, o frete aparece como "a calcular". */
  hasShipping?: boolean;
  /** Pedido já qualifica para frete grátis — mostra "Grátis" mesmo sem opção escolhida. */
  freeShipping?: boolean;
}) {
  const shipping = freeShipping
    ? 'Grátis'
    : !hasShipping
      ? 'A calcular'
      : totals.shipping_cents > 0
        ? formatBRL(totals.shipping_cents)
        : 'Grátis';

  return (
    <dl className="flex flex-col gap-2 text-sm">
      <Row label="Subtotal" value={formatBRL(totals.items_total_cents)} />
      {totals.discount_cents > 0 && (
        <Row label="Desconto" value={`− ${formatBRL(totals.discount_cents)}`} accent />
      )}
      <Row label="Frete" value={shipping} />
      {totals.free_shipping_remaining_cents && totals.free_shipping_remaining_cents > 0 ? (
        <p className="text-xs text-text-muted">
          Faltam {formatBRL(totals.free_shipping_remaining_cents)} para o frete grátis.
        </p>
      ) : null}
      <div className="mt-1 border-t border-surface-border pt-2">
        <Row label="Total" value={formatBRL(totals.grand_total_cents)} strong />
      </div>
    </dl>
  );
}

function Row({
  label,
  value,
  strong,
  accent,
}: {
  label: string;
  value: string;
  strong?: boolean;
  accent?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className={strong ? 'text-base font-semibold' : 'text-text-muted'}>{label}</dt>
      <dd className={strong ? 'text-base font-semibold' : accent ? 'text-success' : 'text-text'}>
        {value}
      </dd>
    </div>
  );
}
