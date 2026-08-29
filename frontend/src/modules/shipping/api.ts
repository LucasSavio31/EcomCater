import { apiFetch } from '@/lib/api-client';

export interface ShippingQuoteItem {
  weight_grams: number;
  length_mm: number;
  width_mm: number;
  height_mm: number;
  price_cents: number;
  quantity: number;
}

export interface ShippingRate {
  id: string;
  service: string;
  carrier: string;
  price_cents: number;
  delivery_days: number;
}

export type ShippingQuoteResult =
  | { ok: true; rates: ShippingRate[] }
  | { ok: false; message: string };

/** `POST /api/shipping/quote` — usado como simulador na PDP. */
export async function quoteShipping(
  destZip: string,
  items: ShippingQuoteItem[],
): Promise<ShippingQuoteResult> {
  const zip = destZip.replace(/\D/g, '');
  if (zip.length !== 8) return { ok: false, message: 'Informe um CEP válido (8 dígitos).' };

  const res = await apiFetch<ShippingRate[]>('/api/shipping/quote', {
    method: 'POST',
    body: { dest_zip: zip, items },
  });
  if (!res.ok) {
    return {
      ok: false,
      message:
        res.error.status === 429
          ? 'Muitas consultas. Aguarde um instante.'
          : 'Não foi possível calcular o frete agora.',
    };
  }
  return { ok: true, rates: res.data };
}
