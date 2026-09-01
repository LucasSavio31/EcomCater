'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Input, Spinner } from '@ecom/ui';
import { useCart } from '@/modules/cart/cart-context';
import { cartApi } from '@/modules/cart/api';
import type { ShippingOption } from '@/modules/cart/types';
import { formatBRL } from '@/lib/format';

const CEP_KEY = 'ecom:cep';

function maskCep(v: string): string {
  const d = v.replace(/\D/g, '').slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}

function deliveryText(days: number): string {
  if (!days || days <= 0) return 'prazo a confirmar';
  return days === 1 ? 'em 1 dia útil' : `em até ${days} dias úteis`;
}

function readSessionCep(): string {
  try {
    return maskCep(window.sessionStorage.getItem(CEP_KEY) ?? '');
  } catch {
    return '';
  }
}

/** CEP + opções de frete. O CEP não é "lembrado" do carrinho salvo — vem em
 *  branco, ou herda o CEP digitado na página do produto (sessionStorage). */
export function ShippingPicker() {
  const { cart, setZip, selectShipping } = useCart();
  const [cep, setCep] = useState('');
  const [options, setOptions] = useState<ShippingOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastQuoted = useRef('');
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  const calcular = useCallback(
    async (raw: string) => {
      const digits = raw.replace(/\D/g, '');
      if (digits.length !== 8) {
        setError(digits.length ? 'Digite um CEP válido (8 dígitos).' : null);
        return;
      }
      if (digits === lastQuoted.current) return;
      lastQuoted.current = digits;
      setLoading(true);
      try {
        window.sessionStorage.setItem(CEP_KEY, digits);
      } catch {
        /* ignore */
      }
      await setZip(digits);
      await fetchOptions();
    },
    [setZip, fetchOptions],
  );

  // Ao montar: se veio um CEP da página do produto, já calcula. Senão, e o
  // carrinho salvo tinha um frete de uma sessão/CEP anterior, limpa — do
  // contrário o total mostrava um frete "fantasma" sem CEP nenhum na tela.
  const handledInherit = useRef(false);
  useEffect(() => {
    if (handledInherit.current) return;
    const fromPdp = readSessionCep();
    if (fromPdp) {
      handledInherit.current = true;
      setCep(fromPdp);
      void calcular(fromPdp);
      return;
    }
    if (cart.shipping_zip || cart.selected_shipping) {
      handledInherit.current = true;
      void setZip('');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cart.shipping_zip, cart.selected_shipping]);

  useEffect(
    () => () => {
      if (debounce.current) clearTimeout(debounce.current);
    },
    [],
  );

  // SEDEX vem selecionado por padrão (sem sobrescrever escolha manual do cliente).
  useEffect(() => {
    if (options.length === 0) return;
    const chosen = cart.selected_shipping?.id;
    if (chosen && options.some((o) => o.id === chosen)) return;
    const pref = options.find((o) => /sedex/i.test(o.service)) ?? options[0];
    if (pref) void selectShipping(pref.id);
  }, [options, cart.selected_shipping, selectShipping]);

  function onCepChange(v: string): void {
    const masked = maskCep(v);
    setCep(masked);
    if (debounce.current) clearTimeout(debounce.current);
    // calcula sozinho assim que o CEP fica completo
    if (masked.replace(/\D/g, '').length === 8) {
      debounce.current = setTimeout(() => void calcular(masked), 350);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void calcular(cep);
        }}
      >
        <Input
          label="CEP de entrega"
          inputMode="numeric"
          value={cep}
          onChange={(e) => onCepChange(e.target.value)}
          placeholder="00000-000"
          className="flex-1"
        />
        <Button
          type="submit"
          variant="ghost"
          loading={loading}
          className="shrink-0 border-2"
          style={{
            background: 'var(--color-cart-freight-bg)',
            color: 'var(--color-cart-freight-fg)',
            borderColor: 'var(--color-cart-freight-border)',
            borderRadius: 'var(--radius-cart-freight, 0.75rem)',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-cart-freight-hover)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--color-cart-freight-bg)')}
        >
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
