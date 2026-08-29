/** Helpers de formatação de preço/valores (pt-BR, dinheiro em centavos). */

const BRL = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
});

/** Centavos → `R$ 1.234,56`. */
export function formatBRL(cents: number): string {
  return BRL.format((Number.isFinite(cents) ? cents : 0) / 100);
}

/** Percentual de desconto entre preço atual e preço "de". `null` se não houver. */
export function discountPct(priceCents: number, compareAtCents?: number | null): number | null {
  if (!compareAtCents || compareAtCents <= priceCents) return null;
  return Math.round((1 - priceCents / compareAtCents) * 100);
}

/**
 * Texto de parcelamento à vista: "ou 6x de R$ 20,00 sem juros".
 * `null` quando não há parcelamento configurado.
 */
export function installmentsText(priceCents: number, installmentsMax?: number | null): string | null {
  if (!installmentsMax || installmentsMax < 2) return null;
  const per = priceCents / installmentsMax;
  return `ou ${installmentsMax}x de ${formatBRL(per)} sem juros`;
}

/** Aplica desconto Pix percentual sobre um valor em centavos. */
export function applyPixDiscount(priceCents: number, pixPct?: number | null): number {
  if (!pixPct || pixPct <= 0) return priceCents;
  return Math.round(priceCents * (1 - pixPct / 100));
}

/** Quanto falta (em centavos) para o frete grátis; 0 quando já atingiu. */
export function freeShippingRemaining(
  subtotalCents: number,
  thresholdCents?: number | null,
): number {
  if (!thresholdCents || thresholdCents <= 0) return 0;
  return Math.max(0, thresholdCents - subtotalCents);
}
