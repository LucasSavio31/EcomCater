'use client';

import { useState } from 'react';
import { Button } from '@ecom/ui';
import type { ProductDetail } from '@/modules/catalog/types';
import { quoteShipping, type ShippingRate } from '@/modules/shipping/api';
import { formatBRL } from '@/lib/format';

/** Simulador de frete na PDP (CEP + Calcular → opções de entrega). */
export function ShippingCalculator({ product }: { product: ProductDetail }) {
  const [zip, setZip] = useState('');
  const [rates, setRates] = useState<ShippingRate[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const dims = product.dimensions_mm;

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError('');
    setRates(null);
    const result = await quoteShipping(zip, [
      {
        weight_grams: product.weight_grams || 300,
        length_mm: dims.length ?? 200,
        width_mm: dims.width ?? 150,
        height_mm: dims.height ?? 100,
        price_cents: product.price_cents,
        quantity: 1,
      },
    ]);
    setLoading(false);
    if (result.ok) setRates(result.rates);
    else setError(result.message);
  }

  return (
    <div className="rounded-card border border-surface-border p-4">
      <p className="mb-2 text-sm font-medium">Calcular frete e prazo</p>
      <form onSubmit={onSubmit} className="flex flex-wrap items-center gap-2">
        <label className="flex-1">
          <span className="sr-only">CEP de entrega</span>
          <input
            type="text"
            inputMode="numeric"
            value={zip}
            onChange={(e) => setZip(e.target.value)}
            placeholder="00000-000"
            maxLength={9}
            className="min-h-touch w-full rounded-card border border-surface-border bg-surface px-3 text-sm"
          />
        </label>
        <Button type="submit" loading={loading}>
          Calcular
        </Button>
        <a
          href="https://buscacepinter.correios.com.br/app/endereco/index.php"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-primary underline"
        >
          Não sei meu CEP
        </a>
      </form>

      {error && (
        <p className="mt-2 text-sm text-danger" role="alert">
          {error}
        </p>
      )}

      {rates && rates.length === 0 && (
        <p className="mt-2 text-sm text-text-muted">Nenhuma opção de entrega para este CEP.</p>
      )}

      {rates && rates.length > 0 && (
        <ul className="mt-3 flex flex-col divide-y divide-surface-border">
          {rates.map((rate) => (
            <li key={rate.id} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span>
                <span className="font-medium">{rate.carrier}</span> · {rate.service}
                <span className="block text-xs text-text-muted">
                  até {rate.delivery_days} {rate.delivery_days === 1 ? 'dia útil' : 'dias úteis'}
                </span>
              </span>
              <span className="font-semibold">
                {rate.price_cents === 0 ? 'Grátis' : formatBRL(rate.price_cents)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
