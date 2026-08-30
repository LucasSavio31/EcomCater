'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button, Card, Input, Spinner } from '@ecom/ui';
import { useCart } from '@/modules/cart/cart-context';
import { useAuth } from '@/modules/customer/auth-context';
import { customerApi } from '@/modules/customer/api';
import { checkoutApi } from '@/modules/checkout/api';
import type { CardPayload, CheckoutPayload, PaymentMethods } from '@/modules/checkout/types';
import type { ShippingOption } from '@/modules/cart/types';
import { cartApi } from '@/modules/cart/api';
import { formatBRL } from '@/lib/format';
import { lookupCep } from '@/lib/viacep';
import { track, identify, cartToTrackItems } from '@/modules/analytics';
import { CheckoutStepsTimeline, type CheckoutStepId } from './checkout-steps';
import { StepSection } from './step-section';
import { OrderSummary } from './order-summary';

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
const onlyDigits = (v: string) => v.replace(/\D/g, '');
const maskCep = (v: string) => {
  const d = onlyDigits(v).slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
};
const maskCpf = (v: string) => {
  const d = onlyDigits(v).slice(0, 11);
  return d
    .replace(/^(\d{3})(\d)/, '$1.$2')
    .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1-$2');
};

const STEP_ORDER: CheckoutStepId[] = ['identify', 'profile', 'shipping', 'payment'];

export function CheckoutView() {
  const router = useRouter();
  const { cart, loading, refresh, setZip, selectShipping } = useCart();
  const { customer } = useAuth();

  // ---- navegação entre etapas
  const [step, setStep] = useState<CheckoutStepId>('identify');
  const [furthest, setFurthest] = useState<CheckoutStepId>('identify');
  const goto = useCallback((id: CheckoutStepId) => {
    setStep(id);
    setFurthest((f) => (STEP_ORDER.indexOf(id) > STEP_ORDER.indexOf(f) ? id : f));
  }, []);

  // ---- dados
  const [email, setEmail] = useState('');
  const [cpf, setCpf] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [addr, setAddr] = useState<AddressForm>(EMPTY_ADDRESS);
  const [note, setNote] = useState('');
  const [agree, setAgree] = useState(false);

  // ---- frete
  const [shipOptions, setShipOptions] = useState<ShippingOption[]>([]);
  const [shipLoading, setShipLoading] = useState(false);
  const [shipError, setShipError] = useState<string | null>(null);
  const lastQuotedZip = useRef('');

  // ---- pagamento
  const [methods, setMethods] = useState<PaymentMethods | null>(null);
  const [method, setMethod] = useState<Method>('pix');
  const [card, setCard] = useState({ number: '', holder_name: '', exp: '', cvv: '' });
  const [installments, setInstallments] = useState(1);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const idemRef = useRef<string>('');
  if (!idemRef.current && typeof crypto !== 'undefined') idemRef.current = crypto.randomUUID();

  // prefill do cliente logado
  useEffect(() => {
    if (!customer) return;
    setEmail((v) => v || customer.email);
    setCpf((v) => v || (customer.cpf ? maskCpf(customer.cpf) : ''));
    const parts = customer.full_name.trim().split(/\s+/);
    setFirstName((v) => v || parts[0] || '');
    setLastName((v) => v || parts.slice(1).join(' '));
    setPhone((v) => v || customer.phone || '');
    setFurthest((f) => (f === 'identify' ? 'profile' : f));
    setStep((s) => (s === 'identify' ? 'profile' : s));
  }, [customer]);

  useEffect(() => {
    void checkoutApi.paymentMethods().then((res) => {
      if (!res.ok) return;
      setMethods(res.data);
      setMethod(res.data.pix ? 'pix' : res.data.credit_card ? 'credit_card' : 'boleto');
    });
  }, []);

  // begin_checkout
  const beginTracked = useRef(false);
  useEffect(() => {
    if (beginTracked.current || loading || cart.items.length === 0) return;
    beginTracked.current = true;
    track('begin_checkout', {
      value: cart.totals.items_total_cents / 100,
      coupon: cart.coupon_code ?? undefined,
      items: cartToTrackItems(cart.items),
    });
  }, [loading, cart]);

  // add_shipping_info
  const shipTracked = useRef<string | null>(null);
  useEffect(() => {
    const sel = cart.selected_shipping;
    if (!sel || shipTracked.current === sel.id) return;
    shipTracked.current = sel.id;
    track('add_shipping_info', {
      value: cart.totals.items_total_cents / 100,
      shipping: cart.totals.shipping_cents / 100,
      method: `${sel.carrier} ${sel.service}`,
      items: cartToTrackItems(cart.items),
    });
  }, [cart]);

  const setAddrField = (k: keyof AddressForm, v: string) => setAddr((p) => ({ ...p, [k]: v }));

  /** Cota o frete assim que o CEP tem 8 dígitos (sem precisar clicar em nada). */
  const quoteShipping = useCallback(
    async (rawZip: string) => {
      const digits = onlyDigits(rawZip);
      if (digits.length !== 8 || digits === lastQuotedZip.current) return;
      lastQuotedZip.current = digits;
      setShipLoading(true);
      setShipError(null);
      const found = await lookupCep(digits);
      if (found) {
        setAddr((p) => ({
          ...p,
          street: found.street || p.street,
          district: found.district || p.district,
          city: found.city || p.city,
          state: found.state || p.state,
        }));
      }
      await setZip(digits);
      const res = await cartApi.shippingOptions();
      setShipLoading(false);
      if (res.ok) {
        setShipOptions(res.data);
        if (res.data.length === 0) setShipError('Nenhuma opção de frete para este CEP.');
      } else {
        setShipOptions([]);
        setShipError(res.error.message);
      }
    },
    [setZip],
  );

  // dispara a cotação sempre que o CEP fica completo
  useEffect(() => {
    const digits = onlyDigits(addr.zip);
    if (digits.length === 8) void quoteShipping(digits);
  }, [addr.zip, quoteShipping]);

  // ---- validações por etapa
  const identifyValid = EMAIL_RE.test(email) && onlyDigits(cpf).length === 11;
  const profileValid =
    firstName.trim().length > 1 && lastName.trim().length > 0 && onlyDigits(phone).length >= 10;
  const addressValid =
    onlyDigits(addr.zip).length === 8 &&
    addr.street.trim() !== '' &&
    addr.number.trim() !== '' &&
    addr.district.trim() !== '' &&
    addr.city.trim() !== '' &&
    addr.state.trim().length === 2;
  const shippingStepValid = addressValid && !!cart.selected_shipping;
  const cardValid =
    method !== 'credit_card' ||
    (onlyDigits(card.number).length >= 13 &&
      card.holder_name.trim() !== '' &&
      /^\d{2}\/\d{2}$/.test(card.exp) &&
      card.cvv.length >= 3);

  const canPlaceOrder =
    !submitting &&
    identifyValid &&
    profileValid &&
    shippingStepValid &&
    cardValid &&
    agree &&
    cart.items.length > 0;

  const maxInstallments = methods?.max_installments ?? 1;
  const installmentOptions = useMemo(
    () => Array.from({ length: Math.max(1, maxInstallments) }, (_, i) => i + 1),
    [maxInstallments],
  );

  function stateOf(id: CheckoutStepId): 'active' | 'done' | 'locked' {
    if (step === id) return 'active';
    return STEP_ORDER.indexOf(id) < STEP_ORDER.indexOf(step) ? 'done' : 'locked';
  }

  // ---- avançar etapas
  async function advanceIdentify() {
    if (!identifyValid) return;
    identify({ email: email.trim(), externalId: onlyDigits(cpf) });
    if (!customer) {
      // "instant login": senha = CPF. Se falhar, segue como convidado.
      void customerApi.login({ email: email.trim(), password: onlyDigits(cpf) });
    }
    if (!addr.recipient_name) setAddr((p) => ({ ...p, recipient_name: `${firstName} ${lastName}`.trim() }));
    goto('profile');
  }
  function advanceProfile() {
    if (!profileValid) return;
    identify({ firstName: firstName.trim(), lastName: lastName.trim(), phone: onlyDigits(phone) });
    setAddr((p) => ({ ...p, recipient_name: p.recipient_name || `${firstName} ${lastName}`.trim() }));
    goto('shipping');
  }
  function advanceShipping() {
    if (!shippingStepValid) return;
    identify({
      street: `${addr.street}, ${addr.number}`,
      city: addr.city,
      state: addr.state,
      zip: onlyDigits(addr.zip),
      country: 'BR',
    });
    goto('payment');
  }

  function buildCard(): CardPayload | null {
    if (method !== 'credit_card') return null;
    const [mm, yy] = card.exp.split('/');
    return {
      number: onlyDigits(card.number),
      holder_name: card.holder_name.trim(),
      exp_month: Number(mm),
      exp_year: 2000 + Number(yy),
      cvv: card.cvv,
      installments,
    };
  }

  async function submit() {
    if (!canPlaceOrder) return;
    setSubmitting(true);
    setError(null);
    track('add_payment_info', {
      value: cart.totals.grand_total_cents / 100,
      coupon: cart.coupon_code ?? undefined,
      method,
      items: cartToTrackItems(cart.items),
    });

    const payload: CheckoutPayload = {
      email: email.trim(),
      cpf: onlyDigits(cpf) || null,
      shipping_address: {
        recipient_name: (addr.recipient_name || `${firstName} ${lastName}`).trim(),
        zip: onlyDigits(addr.zip),
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
        `Pedido ${order.number} criado, mas o pagamento não foi autorizado: ${chargeRes.error.message}. Revise os dados e tente novamente.`,
      );
      return;
    }

    try {
      sessionStorage.setItem(`ecom:charge:${order.number}`, JSON.stringify(chargeRes.data));
    } catch {
      /* segue mesmo sem sessionStorage */
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
      <Card variant="outline" className="mx-auto flex max-w-md flex-col items-center gap-4 py-16 text-center">
        <h2 className="text-lg font-semibold">Seu carrinho está vazio</h2>
        <p className="text-sm text-text-muted">Adicione produtos antes de finalizar a compra.</p>
        <Button onClick={() => router.push('/')}>Ir às compras</Button>
      </Card>
    );
  }

  const methodList: { id: Method; label: string; enabled: boolean; hint: string }[] = [
    { id: 'pix', label: 'PIX', enabled: methods?.pix ?? false, hint: 'Aprovação em segundos. Código na próxima tela.' },
    {
      id: 'credit_card',
      label: 'Cartão de crédito',
      enabled: methods?.credit_card ?? false,
      hint: 'Parcele sua compra.',
    },
    { id: 'boleto', label: 'Boleto bancário', enabled: methods?.boleto ?? false, hint: 'Compensa em 1–2 dias úteis.' },
  ];

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="flex flex-col gap-4">
        <CheckoutStepsTimeline current={step} furthest={furthest} onJump={goto} />

        {/* 1 — Identificação */}
        <StepSection
          number={1}
          title="Identificação"
          state={stateOf('identify')}
          onEdit={() => goto('identify')}
          summary={
            <span>
              {email} · CPF {maskCpf(cpf)}
            </span>
          }
        >
          <p className="text-sm text-text-muted">
            Informe seu e-mail e CPF. Usamos o e-mail para identificar a compra e enviar as
            atualizações do pedido; <strong>sua senha de acesso é o próprio CPF</strong>.
          </p>
          <Input
            label="E-mail"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={email && !EMAIL_RE.test(email) ? 'E-mail inválido' : undefined}
          />
          <Input
            label="CPF"
            inputMode="numeric"
            required
            value={cpf}
            onChange={(e) => setCpf(maskCpf(e.target.value))}
            error={cpf && onlyDigits(cpf).length !== 11 ? 'CPF incompleto' : undefined}
          />
          <Button onClick={() => void advanceIdentify()} disabled={!identifyValid} className="self-start">
            Avançar
          </Button>
        </StepSection>

        {/* 2 — Dados pessoais */}
        <StepSection
          number={2}
          title="Dados pessoais"
          state={stateOf('profile')}
          onEdit={() => goto('profile')}
          lockedHint="Confirme seu e-mail e CPF para continuar."
          summary={
            <span>
              {firstName} {lastName} · {phone}
            </span>
          }
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label="Nome" required value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            <Input label="Sobrenome" required value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </div>
          <Input
            label="Telefone / WhatsApp"
            inputMode="numeric"
            required
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            error={phone && onlyDigits(phone).length < 10 ? 'Telefone incompleto' : undefined}
          />
          <button type="button" onClick={() => goto('identify')} className="w-fit text-xs text-primary underline">
            Trocar e-mail / CPF
          </button>
          <Button onClick={advanceProfile} disabled={!profileValid} className="self-start">
            Avançar
          </Button>
        </StepSection>

        {/* 3 — Entrega */}
        <StepSection
          number={3}
          title="Entrega"
          state={stateOf('shipping')}
          onEdit={() => goto('shipping')}
          lockedHint="Finalize seus dados pessoais para informar a entrega."
          summary={
            <span>
              {addr.street}, {addr.number} — {addr.city}/{addr.state}
              {cart.selected_shipping
                ? ` · ${cart.selected_shipping.carrier} ${cart.selected_shipping.service} (${formatBRL(cart.totals.shipping_cents)})`
                : ''}
            </span>
          }
        >
          <Input
            label="Nome de quem recebe"
            required
            value={addr.recipient_name}
            onChange={(e) => setAddrField('recipient_name', e.target.value)}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="CEP"
              inputMode="numeric"
              required
              value={addr.zip}
              onChange={(e) => setAddrField('zip', maskCep(e.target.value))}
              placeholder="00000-000"
              hint="O frete é calculado automaticamente."
            />
            <Input label="Número" required value={addr.number} onChange={(e) => setAddrField('number', e.target.value)} />
          </div>
          <Input label="Rua / logradouro" required value={addr.street} onChange={(e) => setAddrField('street', e.target.value)} />
          <Input label="Complemento (opcional)" value={addr.complement} onChange={(e) => setAddrField('complement', e.target.value)} />
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label="Bairro" required value={addr.district} onChange={(e) => setAddrField('district', e.target.value)} />
            <Input label="Cidade" required value={addr.city} onChange={(e) => setAddrField('city', e.target.value)} />
          </div>
          <Input
            label="Estado (UF)"
            required
            maxLength={2}
            value={addr.state}
            onChange={(e) => setAddrField('state', e.target.value.toUpperCase().slice(0, 2))}
            className="sm:w-32"
          />

          {/* Opções de frete */}
          <div className="flex flex-col gap-2 border-t border-surface-border pt-3">
            <p className="text-sm font-medium">Forma de entrega</p>
            {shipLoading && (
              <p className="flex items-center gap-2 text-sm text-text-muted">
                <Spinner /> Calculando o frete…
              </p>
            )}
            {shipError && <p className="text-xs text-danger">{shipError}</p>}
            {!shipLoading && shipOptions.length === 0 && !shipError && (
              <p className="text-xs text-text-muted">Digite o CEP para ver SEDEX, PAC e demais opções.</p>
            )}
            <ul className="flex flex-col gap-2" role="radiogroup" aria-label="Opções de frete">
              {shipOptions.map((opt) => {
                const selected = cart.selected_shipping?.id === opt.id;
                return (
                  <li key={opt.id}>
                    <button
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      onClick={() => void selectShipping(opt.id)}
                      className={`flex w-full items-center justify-between gap-3 rounded-card border px-3 py-2 text-left text-sm transition ${
                        selected ? 'border-primary bg-primary/5' : 'border-surface-border hover:border-primary'
                      }`}
                    >
                      <span>
                        <span className="font-medium">
                          {opt.carrier} · {opt.service}
                        </span>
                        <span className="block text-xs text-text-muted">
                          {opt.delivery_days > 0
                            ? `em até ${opt.delivery_days} dia(s) útil(eis)`
                            : 'prazo a confirmar'}
                        </span>
                      </span>
                      <span className="shrink-0 font-semibold">
                        {opt.price_cents > 0 ? formatBRL(opt.price_cents) : 'Grátis'}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>

          <Button onClick={advanceShipping} disabled={!shippingStepValid} className="self-start">
            Avançar
          </Button>
        </StepSection>

        {/* 4 — Pagamento */}
        <StepSection
          number={4}
          title="Pagamento"
          state={stateOf('payment')}
          lockedHint="Finalize seu cadastro e endereço para escolher o pagamento."
        >
          {!methods ? (
            <p className="flex items-center gap-2 text-sm text-text-muted">
              <Spinner /> Carregando formas de pagamento…
            </p>
          ) : (
            <ul className="flex flex-col gap-2">
              {methodList
                .filter((m) => m.enabled)
                .map((m) => {
                  const active = method === m.id;
                  return (
                    <li
                      key={m.id}
                      className={`rounded-card border ${active ? 'border-primary' : 'border-surface-border'}`}
                    >
                      <label className="flex cursor-pointer items-center gap-3 px-3 py-3">
                        <input
                          type="radio"
                          name="payment_method"
                          checked={active}
                          onChange={() => setMethod(m.id)}
                        />
                        <span>
                          <span className="text-sm font-medium">{m.label}</span>
                          <span className="block text-xs text-text-muted">{m.hint}</span>
                        </span>
                      </label>

                      {active && m.id === 'credit_card' && (
                        <div className="flex flex-col gap-3 border-t border-surface-border p-3">
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
                                const d = onlyDigits(e.target.value).slice(0, 4);
                                setCard((c) => ({ ...c, exp: d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d }));
                              }}
                            />
                            <Input
                              label="CVV"
                              inputMode="numeric"
                              value={card.cvv}
                              onChange={(e) => setCard((c) => ({ ...c, cvv: onlyDigits(e.target.value).slice(0, 4) }))}
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
                      {active && m.id === 'pix' && (
                        <p className="border-t border-surface-border p-3 text-sm text-text-muted">
                          Você recebe o código PIX (copia e cola) na próxima tela.
                        </p>
                      )}
                      {active && m.id === 'boleto' && (
                        <p className="border-t border-surface-border p-3 text-sm text-text-muted">
                          O boleto é gerado na próxima tela.
                        </p>
                      )}
                    </li>
                  );
                })}
            </ul>
          )}

          <label htmlFor="note" className="mt-2 text-sm font-medium">
            Observações do pedido (opcional)
          </label>
          <textarea
            id="note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            className="rounded-card border border-surface-border bg-surface p-3 text-sm"
          />

          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} className="mt-0.5" />
            <span>
              Li e concordo com a{' '}
              <Link href="/pagina/politica-de-vendas" className="underline">
                política de vendas
              </Link>{' '}
              e a{' '}
              <Link href="/pagina/politica-de-privacidade" className="underline">
                política de privacidade
              </Link>
              .
            </span>
          </label>

          {error && <p className="text-sm text-danger">{error}</p>}

          <Button
            size="lg"
            block
            loading={submitting}
            disabled={!canPlaceOrder}
            onClick={() => void submit()}
          >
            {method === 'pix'
              ? 'Gerar PIX'
              : method === 'boleto'
                ? 'Gerar boleto'
                : `Pagar ${formatBRL(cart.totals.grand_total_cents)}`}
          </Button>
        </StepSection>
      </div>

      <OrderSummary />
    </div>
  );
}
