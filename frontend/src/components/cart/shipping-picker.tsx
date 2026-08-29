'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Input, Spinner } from '@ecom/ui';
import { useCart } from '@/modules/cart/cart-context';
import { cartApi } from '@/modules/cart/api';
import type { ShippingOption } from '@/modules/cart/types';
import { formatBRL } from '@/lib/format';

function maskCep(v: string): string {
  const d = v.replace(/\D/g, '').slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}

function deliveryText(days: number): string {
  if (!days || days <= 0) return 'prazo a confirmar';
  return days === 1 ? 'em 1 dia útil' : `em até ${days} dias úteis`;
}

/** CEP + opções de frete. Compartilhado entre carrinho e checkout. */
export function ShippingPicker() {
  const { cart, setZip, selectShipping } = useCart();
  const [cep, setCep] = useState(maskCep(cart.shipping_zip ?? ''));
  const [options, setOptions] = useState<ShippingOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoDone = useRef(false);

  const fetchOptions = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await cartApi.shippingOptions();
    setLoading(false);
    if (res.ok) {
      setOptions(res.data);
      if (res.data.length === 0) setError('Nenhuma opção de frete para este CEP.');
    } else {
      setOptions([]);
      setError(res.error.message);
    }
  }, []);

  // Se o carrinho já tem CEP, busca as opções uma vez ao montar.
  useEffect(() => {
    if (autoDone.current) return;
    autoDone.current = true;
    if (cart.shipping_zip) void fetchOptions();
  }, [cart.shipping_zip, fetchOptions]);

  async function calcular() {
    const digits = cep.replace(/\D/g, '');
    if (digits.length !== 8) {
      setError('Digite um CEP válido (8 dígitos).');
      return;
    }
    setLoading(true);
    await setZip(digits);
    await fetchOptions();
  }

  return (
    <div className="flex flex-col gap-3">
      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void calcular();
        }}
      >
        <Input
          label="CEP de entrega"
          inputMode="numeric"
          value={cep}
          onChange={(e) => setCep(maskCep(e.target.value))}
          placeholder="00000-000"
          className="flex-1"
        />
        <Button type="submit" variant="outline" loading={loading}>
          Calcular
        </Button>
      </form>

      {error && <p className="text-xs text-danger">{error}</p>}

      {loading && options.length === 0 && (
        <p className="flex items-center gap-2 text-sm text-text-muted">
          <Spinner /> Consultando transportadoras…
        </p>
      )}

      {options.length > 0 && (
        <ul className="flex flex-col gap-2" role="radiogroup" aria-label="Opções de frete">
          {options.map((opt) => {
            const selected = cart.selected_shipping?.id === opt.id;
            return (
              <li key={opt.id}>
                <button
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => void selectShipping(opt.id)}
                  className={`flex w-full items-center justify-between gap-3 rounded-card border px-3 py-2 text-left text-sm transition ${
                    selected
                      ? 'border-primary bg-primary/5'
                      : 'border-surface-border hover:border-primary'
                  }`}
                >
                  <span>
                    <span className="font-medium">
                      {opt.carrier} · {opt.service}
                    </span>
                    <span className="block text-xs text-text-muted">{deliveryText(opt.delivery_days)}</span>
                  </span>
                  <span className="shrink-0 font-semibold">
                    {opt.price_cents > 0 ? formatBRL(opt.price_cents) : 'Grátis'}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
