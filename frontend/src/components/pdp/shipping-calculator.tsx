'use client';

import { useEffect, useState } from 'react';
import { Button } from '@ecom/ui';
import type { ProductDetail } from '@/modules/catalog/types';
import { quoteShipping, type ShippingRate } from '@/modules/shipping/api';
import { formatBRL } from '@/lib/format';

/** Máscara de CEP BR — 00000-000. */
function maskCep(v: string): string {
  const d = v.replace(/\D/g, '').slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}

/** Guarda o CEP p/ o carrinho herdar (sessionStorage). Só quando tem 8 dígitos. */
function stashCep(masked: string): void {
  const d = masked.replace(/\D/g, '');
  try {
    if (d.length === 8) window.sessionStorage.setItem('ecom:cep', d);
  } catch {
    /* ignore */
  }
}

/** Simulador de frete na PDP (CEP + Calcular → opções de entrega). */
export function ShippingCalculator({ product }: { product: ProductDetail }) {
  const [zip, setZip] = useState('');
  const [rates, setRates] = useState<ShippingRate[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Ao abrir a página do produto, zera o CEP herdado: o carrinho só recebe um
  // CEP se ele for digitado AQUI. Sem isso, um CEP de outro produto "vazava".
  useEffect(() => {
    try {
      window.sessionStorage.removeItem('ecom:cep');
    } catch {
      /* ignore */
    }
  }, []);

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
      <form onSubmit={onSubmit} className="flex items-center gap-2">
        <label className="min-w-0 flex-1">
          <span className="sr-only">CEP de entrega</span>
          <input
            type="text"
            inputMode="numeric"
            value={zip}
            onChange={(e) => {
              const m = maskCep(e.target.value);
              setZip(m);
              stashCep(m);
            }}
            placeholder="00000-000"
            maxLength={9}
            className="min-h-touch w-full rounded-card border border-surface-border bg-surface px-3 text-sm"
          />
        </label>
        <Button
          type="submit"
          variant="ghost"
          loading={loading}
          style={{
            borderRadius: 'var(--radius-freight, 0.75rem)',
            background: 'var(--color-freight-bg)',
            color: 'var(--color-freight-fg)',
            borderColor: 'var(--color-freight-border)',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-freight-hover)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--color-freight-bg)')}
          className="shrink-0 border-2"
        >
          Calcular
        </Button>
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
