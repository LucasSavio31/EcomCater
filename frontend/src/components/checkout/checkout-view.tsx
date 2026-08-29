'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button, Card, Input, Spinner } from '@ecom/ui';
import { useCart } from '@/modules/cart/cart-context';
import { checkoutApi } from '@/modules/checkout/api';
import type { CardPayload, CheckoutPayload, PaymentMethods } from '@/modules/checkout/types';
import { ShippingPicker } from '@/components/cart/shipping-picker';
import { OrderTotals } from '@/components/cart/order-totals';
import { formatBRL } from '@/lib/format';
import { lookupCep } from '@/lib/viacep';

type Method = 'pix' | 'credit_card' | 'boleto';

interface AddressForm {
  recipient_name: string;
  zip: string;
  street: string;
  number: string;
  complement: string;
  district: string;
  city: string;
  state: string;
}

const EMPTY_ADDRESS: AddressForm = {
  recipient_name: '',
  zip: '',
  street: '',
  number: '',
  complement: '',
  district: '',
  city: '',
  state: '',
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const maskCep = (v: string) => {
  const d = v.replace(/\D/g, '').slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
};

export function CheckoutView() {
  const router = useRouter();
  const { cart, loading, refresh } = useCart();

  const [email, setEmail] = useState('');
  const [cpf, setCpf] = useState('');
  const [addr, setAddr] = useState<AddressForm>(EMPTY_ADDRESS);
  const [note, setNote] = useState('');

  const [methods, setMethods] = useState<PaymentMethods | null>(null);
  const [method, setMethod] = useState<Method>('pix');
  const [card, setCard] = useState({ number: '', holder_name: '', exp: '', cvv: '' });
  const [installments, setInstallments] = useState(1);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const idemRef = useRef<string>('');
  if (!idemRef.current && typeof crypto !== 'undefined') {
    idemRef.current = crypto.randomUUID();
  }

  useEffect(() => {
    void checkoutApi.paymentMethods().then((res) => {
      if (!res.ok) return;
      setMethods(res.data);
      const first: Method = res.data.pix
        ? 'pix'
        : res.data.credit_card
          ? 'credit_card'
          : 'boleto';
      setMethod(first);
    });
  }, []);

  const setField = (k: keyof AddressForm, v: string) => setAddr((p) => ({ ...p, [k]: v }));

  async function onCepBlur() {
    const found = await lookupCep(addr.zip);
    if (found) {
      setAddr((p) => ({
        ...p,
        street: found.street || p.street,
        district: found.district || p.district,
        city: found.city || p.city,
        state: found.state || p.state,
      }));
    }
  }

  const addressValid =
    addr.recipient_name.trim().length > 1 &&
    addr.zip.replace(/\D/g, '').length === 8 &&
    addr.street.trim() !== '' &&
    addr.number.trim() !== '' &&
    addr.district.trim() !== '' &&
    addr.city.trim() !== '' &&
    addr.state.trim().length === 2;

  const cardValid =
    method !== 'credit_card' ||
    (card.number.replace(/\D/g, '').length >= 13 &&
      card.holder_name.trim() !== '' &&
      /^\d{2}\/\d{2}$/.test(card.exp) &&
      card.cvv.length >= 3);

  const canSubmit =
    !submitting &&
    EMAIL_RE.test(email) &&
    addressValid &&
    !!cart.selected_shipping &&
    cardValid &&
    cart.items.length > 0;

  const maxInstallments = methods?.max_installments ?? 1;
  const installmentOptions = useMemo(
    () => Array.from({ length: Math.max(1, maxInstallments) }, (_, i) => i + 1),
    [maxInstallments],
  );

  function buildCard(): CardPayload | null {
    if (method !== 'credit_card') return null;
    const [mm, yy] = card.exp.split('/');
    return {
      number: card.number.replace(/\D/g, ''),
      holder_name: card.holder_name.trim(),
      exp_month: Number(mm),
      exp_year: 2000 + Number(yy),
      cvv: card.cvv,
      installments,
    };
  }

  async function submit() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);

    const payload: CheckoutPayload = {
      email: email.trim(),
      cpf: cpf.replace(/\D/g, '') || null,
      shipping_address: {
        recipient_name: addr.recipient_name.trim(),
        zip: addr.zip.replace(/\D/g, ''),
        street: addr.street.trim(),
        number: addr.number.trim(),
        complement: addr.complement.trim() || null,
        district: addr.district.trim(),
        city: addr.city.trim(),
        state: addr.state.trim().toUpperCase(),
        country: 'BR',
      },
      customer_note: note.trim() || null,
      shipping_service_id: cart.selected_shipping?.id ?? null,
      idempotency_key: idemRef.current || null,
    };

    const orderRes = await checkoutApi.placeOrder(payload);
    if (!orderRes.ok) {
      setSubmitting(false);
      setError(orderRes.error.message);
      return;
    }
    const order = orderRes.data;

    const chargeRes = await checkoutApi.charge({
      order_number: order.number,
      method,
      card: buildCard(),
    });

    if (!chargeRes.ok) {
      setSubmitting(false);
      setError(
        `Pedido ${order.number} criado, mas o pagamento não foi autorizado: ${chargeRes.error.message}. ` +
          'Revise os dados e tente novamente.',
      );
      return;
    }

    try {
      sessionStorage.setItem(`ecom:charge:${order.number}`, JSON.stringify(chargeRes.data));
    } catch {
      /* sem sessionStorage — a página de obrigado busca o status mesmo assim */
    }
    await refresh();
    router.push(`/checkout/obrigado?pedido=${order.number}&email=${encodeURIComponent(email.trim())}`);
  }

  if (loading) {
    return (
      <p className="flex items-center gap-2 py-16 text-text-muted">
        <Spinner /> Carregando…
      </p>
    );
  }

  if (cart.items.length === 0) {
    return (
      <Card variant="outline" className="flex flex-col items-center gap-4 py-16 text-center">
        <h2 className="text-lg font-semibold">Seu carrinho está vazio</h2>
        <p className="text-sm text-text-muted">Adicione produtos antes de finalizar a compra.</p>
        <Button onClick={() => router.push('/')}>Ir às compras</Button>
      </Card>
    );
  }

  const methodList: { id: Method; label: string; enabled: boolean }[] = [
    { id: 'pix', label: 'PIX', enabled: methods?.pix ?? false },
    { id: 'credit_card', label: 'Cartão de crédito', enabled: methods?.credit_card ?? false },
    { id: 'boleto', label: 'Boleto', enabled: methods?.boleto ?? false },
  ];

  return (
    <form
      className="grid gap-6 lg:grid-cols-[1fr_22rem]"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <div className="flex flex-col gap-4">
        {/* Contato */}
        <Card variant="outline" className="flex flex-col gap-3">
          <h2 className="text-base font-semibold">1. Contato</h2>
          <Input
            label="E-mail"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={email && !EMAIL_RE.test(email) ? 'E-mail inválido' : undefined}
          />
          <Input
            label="CPF (opcional)"
            inputMode="numeric"
            value={cpf}
            onChange={(e) => setCpf(e.target.value.replace(/\D/g, '').slice(0, 11))}
            hint="Recomendado para emissão de nota e antifraude."
          />
        </Card>

        {/* Entrega */}
        <Card variant="outline" className="flex flex-col gap-3">
          <h2 className="text-base font-semibold">2. Endereço de entrega</h2>
          <Input
            label="Nome de quem recebe"
            required
            value={addr.recipient_name}
            onChange={(e) => setField('recipient_name', e.target.value)}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="CEP"
              inputMode="numeric"
              required
              value={addr.zip}
              onChange={(e) => setField('zip', maskCep(e.target.value))}
              onBlur={() => void onCepBlur()}
              placeholder="00000-000"
            />
            <Input
              label="Número"
              required
              value={addr.number}
              onChange={(e) => setField('number', e.target.value)}
            />
          </div>
          <Input
            label="Rua / logradouro"
            required
            value={addr.street}
            onChange={(e) => setField('street', e.target.value)}
          />
          <Input
            label="Complemento (opcional)"
            value={addr.complement}
            onChange={(e) => setField('complement', e.target.value)}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Bairro"
              required
              value={addr.district}
              onChange={(e) => setField('district', e.target.value)}
            />
            <Input
              label="Cidade"
              required
              value={addr.city}
              onChange={(e) => setField('city', e.target.value)}
            />
          </div>
          <Input
            label="Estado (UF)"
            required
            maxLength={2}
            value={addr.state}
            onChange={(e) => setField('state', e.target.value.toUpperCase().slice(0, 2))}
            className="sm:w-32"
          />
        </Card>

        {/* Frete */}
        <Card variant="outline" className="flex flex-col gap-3">
          <h2 className="text-base font-semibold">3. Frete</h2>
          <ShippingPicker />
          {!cart.selected_shipping && (
            <p className="text-xs text-text-muted">Calcule e escolha uma opção de frete.</p>
          )}
        </Card>

        {/* Pagamento */}
        <Card variant="outline" className="flex flex-col gap-3">
          <h2 className="text-base font-semibold">4. Pagamento</h2>
          {!methods ? (
            <p className="flex items-center gap-2 text-sm text-text-muted">
              <Spinner /> Carregando formas de pagamento…
            </p>
          ) : (
            <>
              <div className="flex flex-wrap gap-2">
                {methodList
                  .filter((m) => m.enabled)
                  .map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setMethod(m.id)}
                      className={`min-h-touch rounded-card border px-4 text-sm font-medium transition ${
                        method === m.id
                          ? 'border-primary bg-primary/5'
                          : 'border-surface-border hover:border-primary'
                      }`}
                    >
                      {m.label}
                    </button>
                  ))}
              </div>

              {method === 'pix' && (
                <p className="text-sm text-text-muted">
                  Você receberá um código PIX na próxima tela. O pedido é confirmado assim que o
                  pagamento é compensado (geralmente em segundos).
                </p>
              )}
              {method === 'boleto' && (
                <p className="text-sm text-text-muted">
                  O boleto será gerado na próxima tela. A compensação leva de 1 a 2 dias úteis.
                </p>
              )}
              {method === 'credit_card' && (
                <div className="flex flex-col gap-3">
                  <Input
                    label="Número do cartão"
                    inputMode="numeric"
                    value={card.number}
                    onChange={(e) =>
                      setCard((c) => ({ ...c, number: e.target.value.replace(/[^\d ]/g, '').slice(0, 19) }))
                    }
                  />
                  <Input
                    label="Nome impresso no cartão"
                    value={card.holder_name}
                    onChange={(e) => setCard((c) => ({ ...c, holder_name: e.target.value }))}
                  />
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Input
                      label="Validade (MM/AA)"
                      placeholder="MM/AA"
                      value={card.exp}
                      onChange={(e) => {
                        const d = e.target.value.replace(/\D/g, '').slice(0, 4);
                        setCard((c) => ({ ...c, exp: d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d }));
                      }}
                    />
                    <Input
                      label="CVV"
                      inputMode="numeric"
                      value={card.cvv}
                      onChange={(e) => setCard((c) => ({ ...c, cvv: e.target.value.replace(/\D/g, '').slice(0, 4) }))}
                    />
                  </div>
                  {maxInstallments > 1 && (
                    <label className="flex flex-col gap-1 text-sm font-medium text-text">
                      Parcelas
                      <select
                        value={installments}
                        onChange={(e) => setInstallments(Number(e.target.value))}
                        className="min-h-touch rounded-card border border-surface-border bg-surface px-3 text-sm"
                      >
                        {installmentOptions.map((n) => (
                          <option key={n} value={n}>
                            {n}x de {formatBRL(Math.round(cart.totals.grand_total_cents / n))}
                            {n === 1 ? ' à vista' : ' sem juros'}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </div>
              )}
            </>
          )}
        </Card>

        <Card variant="outline" className="flex flex-col gap-2">
          <label htmlFor="note" className="text-sm font-medium">
            Observações do pedido (opcional)
          </label>
          <textarea
            id="note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
            className="rounded-card border border-surface-border bg-surface p-3 text-sm"
          />
        </Card>
      </div>

      {/* Resumo */}
      <aside className="flex flex-col gap-4 lg:sticky lg:top-24 lg:self-start">
        <Card variant="outline" className="flex flex-col gap-4">
          <h2 className="text-base font-semibold">Resumo do pedido</h2>
          <ul className="flex flex-col gap-2 text-sm">
            {cart.items.map((i) => (
              <li key={i.id} className="flex justify-between gap-2">
                <span className="min-w-0">
                  <span className="line-clamp-1">{i.product_name}</span>
                  <span className="text-xs text-text-muted">
                    {i.quantity}× {i.variant_label ? `· ${i.variant_label}` : ''}
                  </span>
                </span>
                <span className="shrink-0">{formatBRL(i.line_total_cents)}</span>
              </li>
            ))}
          </ul>
          <div className="border-t border-surface-border pt-3">
            <OrderTotals totals={cart.totals} hasShipping={!!cart.selected_shipping} />
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <Button type="submit" block loading={submitting} disabled={!canSubmit}>
            {method === 'pix'
              ? 'Gerar PIX'
              : method === 'boleto'
                ? 'Gerar boleto'
                : `Pagar ${formatBRL(cart.totals.grand_total_cents)}`}
          </Button>
          <p className="text-center text-xs text-text-muted">
            Ao finalizar você concorda com a{' '}
            <Link href="/pagina/politica-de-vendas" className="underline">
              política de vendas
            </Link>
            .
          </p>
        </Card>
      </aside>
    </form>
  );
}
