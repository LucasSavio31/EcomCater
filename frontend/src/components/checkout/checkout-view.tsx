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
import { apiFetch } from '@/lib/api-client';
import { setCustomerSession } from '@/lib/customer-auth-storage';
import { formatBRL } from '@/lib/format';
import { isValidCpf } from '@/lib/cpf';
import { uuid } from '@/lib/uuid';
import { maskHouseNumber } from '@/lib/address';
import { lookupCep } from '@/lib/viacep';
import {
  track,
  identify,
  currentFbCookies,
  currentGaClientId,
  cartToTrackItems,
} from '@/modules/analytics';
import { CheckoutStepsTimeline, type CheckoutStepId } from './checkout-steps';
import { StepSection } from './step-section';
import { OrderSummary } from './order-summary';
import { AnimatedCard } from './animated-card';
import { PaymentIcon } from './payment-icons';
import { resolveMediaUrl } from '@/lib/media';

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
const maskPhone = (v: string) => {
  const d = onlyDigits(v).slice(0, 11);
  if (d.length === 0) return '';
  if (d.length <= 2) return `(${d}`;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
};
// "0000 0000 0000 0000" — grupos de 4 (até 19 dígitos p/ cobrir cartões maiores).
const maskCardNumber = (v: string) =>
  onlyDigits(v).slice(0, 19).replace(/(\d{4})(?=\d)/g, '$1 ');

const STEP_ORDER: CheckoutStepId[] = ['identify', 'profile', 'shipping', 'payment'];

export interface CheckoutSettings {
  emailFirst: boolean;
  /** Exigir o aceite "Li e concordo com as políticas". */
  requireTerms: boolean;
  showCoupon: boolean;
  itemsLayout: 'with_thumb' | 'simple';
  allowQtyChange: boolean;
  buttonColor: string;
  buttonTextColor: string;
  /** Borda do botão finalizar — igual ao fundo por padrão (some visualmente). */
  buttonBorderColor: string;
  /** Bolinha da etapa ativa (1,2,3,4) na linha do tempo. */
  stepActiveBg: string;
  stepActiveText: string;
  animatedCard: boolean;
  /** Ícones ao lado de PIX / Cartão / Boleto. */
  paymentIcons: boolean;
  /** Linha do tempo das etapas (1 2 3 4) no topo. */
  stepsTimeline: boolean;
  showReview: boolean;
  reviewPosition: 'side' | 'top';
  /** Caixa "Observações do pedido (opcional)". */
  orderNotes: boolean;
}

export interface OrderBumpProduct {
  slug: string;
  name: string;
  price_cents: number;
  image_url: string | null;
  variant_id: string | null;
}

const DEFAULT_SETTINGS: CheckoutSettings = {
  emailFirst: false,
  requireTerms: true,
  showCoupon: true,
  itemsLayout: 'with_thumb',
  allowQtyChange: true,
  buttonColor: '#111111',
  buttonTextColor: '#FFFFFF',
  buttonBorderColor: '#111111',
  stepActiveBg: '#111111',
  stepActiveText: '#FFFFFF',
  animatedCard: true,
  paymentIcons: true,
  stepsTimeline: true,
  showReview: true,
  reviewPosition: 'side',
  orderNotes: false,
};

export function CheckoutView({
  settings = DEFAULT_SETTINGS,
  orderBumps = [],
}: {
  settings?: CheckoutSettings;
  orderBumps?: OrderBumpProduct[];
}) {
  const router = useRouter();
  const { cart, loading, refresh, setZip, selectShipping } = useCart();
  const { customer, reload: reloadAuth } = useAuth();

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
  // CEP herdado da página do produto / carrinho (sessionStorage) — dispara a
  // cotação automática via o efeito de `addr.zip` abaixo.
  useEffect(() => {
    if (onlyDigits(addr.zip).length === 8) return;
    let stored = '';
    try {
      stored = window.sessionStorage.getItem('ecom:cep') || '';
    } catch {
      /* ignore */
    }
    if (onlyDigits(stored).length === 8) {
      setAddr((p) => ({ ...p, zip: maskCep(stored) }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [agree, setAgree] = useState(false);
  const [emailTouched, setEmailTouched] = useState(false);

  // ---- frete
  const [shipOptions, setShipOptions] = useState<ShippingOption[]>([]);
  const [shipLoading, setShipLoading] = useState(false);
  const [shipError, setShipError] = useState<string | null>(null);
  const [shipPickMsg, setShipPickMsg] = useState<string | null>(null);
  const lastQuotedZip = useRef('');

  // ---- pagamento
  const [methods, setMethods] = useState<PaymentMethods | null>(null);
  const [method, setMethod] = useState<Method>('pix');
  const [card, setCard] = useState({ number: '', holder_name: '', exp: '', cvv: '' });
  const [installments, setInstallments] = useState(1);

  const [cvvFocused, setCvvFocused] = useState(false);
  // ids de variante dos order bumps marcados
  const [bumpChecked, setBumpChecked] = useState<Set<string>>(new Set());

  const [submitting, setSubmitting] = useState(false);
  const [placed, setPlaced] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const idemRef = useRef<string>('');
  if (!idemRef.current) idemRef.current = uuid();

  // prefill do cliente logado
  useEffect(() => {
    if (!customer) return;
    setEmail((v) => v || customer.email);
    setCpf((v) => v || (customer.cpf ? maskCpf(customer.cpf) : ''));
    const parts = customer.full_name.trim().split(/\s+/);
    setFirstName((v) => v || parts[0] || '');
    setLastName((v) => v || parts.slice(1).join(' '));
    setPhone((v) => v || (customer.phone ? maskPhone(customer.phone) : ''));
    setFurthest((f) => (f === 'identify' ? 'profile' : f));
    setStep((s) => (s === 'identify' ? 'profile' : s));
  }, [customer]);

  // cliente logado: puxa o endereço padrão salvo (CEP + entrega completos) —
  // só entra se o formulário ainda estiver vazio (não sobrepõe um CEP que já
  // veio da página do produto nem o que o cliente já tenha digitado).
  useEffect(() => {
    if (!customer) return;
    let cancelled = false;
    void customerApi.listAddresses().then((res) => {
      if (cancelled || !res.ok || res.data.length === 0) return;
      const def = res.data.find((a) => a.is_default) ?? res.data[0];
      if (!def) return;
      setAddr((p) => {
        if (onlyDigits(p.zip).length === 8) return p;
        return {
          recipient_name: p.recipient_name || def.recipient_name || '',
          zip: maskCep(def.zip),
          street: def.street,
          number: def.number,
          complement: def.complement ?? '',
          district: def.district,
          city: def.city,
          state: def.state,
        };
      });
    });
    return () => {
      cancelled = true;
    };
  }, [customer]);

  useEffect(() => {
    void checkoutApi.paymentMethods().then((res) => {
      if (!res.ok) return;
      setMethods(res.data);
      setMethod(res.data.pix ? 'pix' : res.data.credit_card ? 'credit_card' : 'boleto');
    });
  }, []);

  // begin_checkout — 1x quando a 1ª etapa do checkout é exibida com itens
  const beginTracked = useRef(false);
  useEffect(() => {
    if (beginTracked.current || loading || cart.items.length === 0) return;
    beginTracked.current = true;
    track('begin_checkout', {
      coupon: cart.coupon_code ?? undefined,
      items: cartToTrackItems(cart.items),
    });
  }, [loading, cart]);

  // add_shipping_info — quando uma modalidade de frete válida é selecionada
  const shipTracked = useRef<string | null>(null);
  useEffect(() => {
    const sel = cart.selected_shipping;
    if (!sel || shipTracked.current === sel.id) return;
    shipTracked.current = sel.id;
    track('add_shipping_info', {
      shipping: cart.totals.shipping_cents / 100,
      coupon: cart.coupon_code ?? undefined,
      method: `${sel.carrier} ${sel.service}`,
      items: cartToTrackItems(cart.items),
    });
  }, [cart]);

  // add_payment_info — quando o usuário seleciona/confirma uma forma de pagamento
  const payTracked = useRef<string | null>(null);
  useEffect(() => {
    if (loading || cart.items.length === 0 || step !== 'payment') return;
    if (payTracked.current === method) return;
    payTracked.current = method;
    track('add_payment_info', {
      coupon: cart.coupon_code ?? undefined,
      shipping: cart.totals.shipping_cents / 100,
      method,
      items: cartToTrackItems(cart.items),
    });
  }, [method, step, loading, cart]);

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
        // opção única: já deixa selecionada (frete grátis ou não)
        const only = res.data.length === 1 ? res.data[0] : undefined;
        if (only && cart.selected_shipping?.id !== only.id) {
          setShipPickMsg(null);
          void selectShipping(only.id);
        }
      } else {
        setShipOptions([]);
        setShipError(res.error.message);
      }
    },
    [setZip, selectShipping, cart.selected_shipping?.id],
  );

  // dispara a cotação sempre que o CEP fica completo
  useEffect(() => {
    const digits = onlyDigits(addr.zip);
    if (digits.length === 8) void quoteShipping(digits);
  }, [addr.zip, quoteShipping]);

  // opção única de frete -> já vem selecionada como padrão no checkout
  useEffect(() => {
    if (shipOptions.length !== 1) return;
    const only = shipOptions[0];
    if (only && cart.selected_shipping?.id !== only.id) {
      setShipPickMsg(null);
      void selectShipping(only.id);
    }
  }, [shipOptions, cart.selected_shipping?.id, selectShipping]);

  // ---- validações por etapa
  const cpfOk = isValidCpf(cpf);
  const identifyValid = settings.emailFirst
    ? EMAIL_RE.test(email)
    : EMAIL_RE.test(email) && cpfOk;
  const profileValid =
    firstName.trim().length > 1 &&
    lastName.trim().length > 0 &&
    onlyDigits(phone).length >= 10 &&
    (!settings.emailFirst || cpfOk);
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
    (!settings.requireTerms || agree) &&
    cart.items.length > 0;

  // ---- campos que faltam por etapa: ao tentar avançar, destaca em vermelho
  //      SÓ os campos pendentes (o botão continua com a cor normal).
  const [missing, setMissing] = useState<Set<string>>(new Set());
  useEffect(() => {
    setMissing(new Set());
  }, [step]);

  // validade ATUAL de cada campo — recalculada a cada render, então a borda
  // vermelha some no instante em que o campo é preenchido certo.
  const fieldFilled: Record<string, boolean> = {
    email: EMAIL_RE.test(email),
    cpf: cpfOk,
    firstName: firstName.trim().length >= 2,
    lastName: lastName.trim() !== '',
    phone: onlyDigits(phone).length >= 10,
    zip: onlyDigits(addr.zip).length === 8,
    street: addr.street.trim() !== '',
    number: addr.number.trim() !== '',
    district: addr.district.trim() !== '',
    city: addr.city.trim() !== '',
    state: addr.state.trim().length === 2,
    shipping: !!cart.selected_shipping,
    card_number: onlyDigits(card.number).length >= 13,
    card_holder: card.holder_name.trim() !== '',
    card_exp: /^\d{2}\/\d{2}$/.test(card.exp),
    card_cvv: card.cvv.length >= 3,
    terms: agree,
  };
  const miss = (k: string): string | undefined =>
    missing.has(k) && !fieldFilled[k] ? 'Campo obrigatório' : undefined;
  const showMissingHint = [...missing].some((k) => !fieldFilled[k]);

  function missingIdentify(): string[] {
    const m: string[] = [];
    if (!EMAIL_RE.test(email)) m.push('email');
    if (!settings.emailFirst && !cpfOk) m.push('cpf');
    return m;
  }
  function missingProfile(): string[] {
    const m: string[] = [];
    if (firstName.trim().length < 2) m.push('firstName');
    if (!lastName.trim()) m.push('lastName');
    if (onlyDigits(phone).length < 10) m.push('phone');
    if (settings.emailFirst && !cpfOk) m.push('cpf');
    return m;
  }
  function missingShipping(): string[] {
    const m: string[] = [];
    if (onlyDigits(addr.zip).length !== 8) m.push('zip');
    if (!addr.street.trim()) m.push('street');
    if (!addr.number.trim()) m.push('number');
    if (!addr.district.trim()) m.push('district');
    if (!addr.city.trim()) m.push('city');
    if (addr.state.trim().length !== 2) m.push('state');
    if (!cart.selected_shipping) m.push('shipping');
    return m;
  }
  function missingPayment(): string[] {
    const m: string[] = [];
    if (method === 'credit_card') {
      if (onlyDigits(card.number).length < 13) m.push('card_number');
      if (!card.holder_name.trim()) m.push('card_holder');
      if (!/^\d{2}\/\d{2}$/.test(card.exp)) m.push('card_exp');
      if (card.cvv.length < 3) m.push('card_cvv');
    }
    if (settings.requireTerms && !agree) m.push('terms');
    return m;
  }

  const maxInstallments = methods?.max_installments ?? 1;
  const installmentOptions = useMemo(
    () => Array.from({ length: Math.max(1, maxInstallments) }, (_, i) => i + 1),
    [maxInstallments],
  );

  function stateOf(id: CheckoutStepId): 'active' | 'done' | 'locked' {
    if (step === id) return 'active';
    return STEP_ORDER.indexOf(id) < STEP_ORDER.indexOf(step) ? 'done' : 'locked';
  }

  /** Só mostra a etapa depois que a anterior foi concluída (visual mais limpo). */
  function stepVisible(id: CheckoutStepId): boolean {
    return STEP_ORDER.indexOf(id) <= STEP_ORDER.indexOf(furthest);
  }

  // ---- avançar etapas
  function tryInstantLogin() {
    if (!customer && EMAIL_RE.test(email) && cpfOk) {
      // "instant login": a senha do cliente é o CPF. Falhou? segue como convidado.
      void customerApi.login({ email: email.trim(), password: onlyDigits(cpf) });
    }
  }

  async function advanceIdentify() {
    if (!identifyValid) {
      setMissing(new Set(missingIdentify()));
      return;
    }
    setMissing(new Set());
    identify({ email: email.trim(), externalId: onlyDigits(cpf) || undefined });
    if (!settings.emailFirst) tryInstantLogin();
    // ao informar o e-mail: vira lead na hora + entra na recuperação de carrinho
    if (EMAIL_RE.test(email)) {
      void apiFetch('/api/newsletter/subscribe', {
        method: 'POST',
        body: { email: email.trim(), source: 'checkout' },
      });
      void apiFetch('/api/cart-recovery/capture', {
        method: 'POST',
        credentials: 'include',
        body: { email: email.trim() },
      });
    }
    goto('profile');
  }
  function advanceProfile() {
    if (!profileValid) {
      setMissing(new Set(missingProfile()));
      return;
    }
    setMissing(new Set());
    if (settings.emailFirst) tryInstantLogin();
    // atualiza o lead com nome/telefone agora que foram preenchidos
    if (EMAIL_RE.test(email)) {
      void apiFetch('/api/newsletter/subscribe', {
        method: 'POST',
        body: {
          email: email.trim(),
          name: `${firstName} ${lastName}`.trim() || null,
          phone: onlyDigits(phone) || null,
          source: 'checkout',
        },
      });
    }
    identify({
      firstName: firstName.trim(),
      lastName: lastName.trim(),
      phone: onlyDigits(phone),
      externalId: onlyDigits(cpf) || undefined,
    });
    setAddr((p) => ({ ...p, recipient_name: p.recipient_name || `${firstName} ${lastName}`.trim() }));
    goto('shipping');
  }
  function advanceShipping() {
    if (!shippingStepValid) {
      const m = missingShipping();
      setMissing(new Set(m));
      if (m.includes('shipping')) {
        setShipPickMsg('Selecione a forma de entrega para continuar.');
      }
      return;
    }
    setMissing(new Set());
    setShipPickMsg(null);
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
    if (!canPlaceOrder) {
      if (!submitting) {
        const m = missingPayment();
        setMissing(new Set(m));
        setError(
          m.length === 0
            ? 'Revise seus dados nas etapas anteriores para concluir.'
            : null,
        );
      }
      return;
    }
    setMissing(new Set());
    setSubmitting(true);
    setError(null);

    // order bumps: adiciona os produtos extras marcados ao carrinho antes de criar o pedido
    let bumpAdded = false;
    for (const b of orderBumps) {
      if (!b.variant_id || !bumpChecked.has(b.variant_id)) continue;
      if (cart.items.some((i) => i.variant_id === b.variant_id)) continue;
      const r = await cartApi.addItem(b.variant_id, 1);
      if (r.ok) bumpAdded = true;
    }
    if (bumpAdded) await refresh();
    // add_payment_info já foi disparado na SELEÇÃO da forma de pagamento (efeito acima)

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
        phone: onlyDigits(phone) || null,
      },
      customer_note: note.trim() || null,
      shipping_service_id: cart.selected_shipping?.id ?? null,
      idempotency_key: idemRef.current || null,
      // atribuição p/ Meta CAPI (cookies do pixel) + GA4 refund (client_id) + landing page
      ...currentFbCookies(),
      ga_client_id: currentGaClientId(),
      landing_url:
        (typeof window !== 'undefined' &&
          (sessionStorage.getItem('ecom:landing') || window.location.href)) ||
        undefined,
    };

    const orderRes = await checkoutApi.placeOrder(payload);
    if (!orderRes.ok) {
      setSubmitting(false);
      setError(orderRes.error.message);
      return;
    }
    const order = orderRes.data;
    setPlaced(true); // trava a tela de checkout — nada de "carrinho vazio" piscando

    // comprador já sai logado — pode ir direto para "minhas compras"
    if (order.auth) {
      setCustomerSession(order.auth);
      void reloadAuth();
    }

    const chargeRes = await checkoutApi.charge({
      order_number: order.number,
      method,
      card: buildCard(),
    });
    if (!chargeRes.ok) {
      setSubmitting(false);
      setPlaced(false); // volta o formulário para o cliente refazer o pagamento
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
    // navega ANTES de atualizar o carrinho — assim a tela de "obrigado" entra
    // direto, sem a tela de "carrinho vazio" aparecer no meio do caminho
    router.push(`/checkout/obrigado?pedido=${order.number}&email=${encodeURIComponent(email.trim())}`);
    void refresh();
  }

  if (loading) {
    return (
      <p className="flex items-center gap-2 py-16 text-text-muted">
        <Spinner /> Carregando…
      </p>
    );
  }
  if (placed) {
    return (
      <p className="flex items-center justify-center gap-2 py-24 text-text-muted">
        <Spinner /> Finalizando seu pedido…
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

  const reviewOnSide = settings.showReview && settings.reviewPosition === 'side';

  // Tela dedicada de e-mail (WC "custom screen"): só o e-mail, sem resumo do pedido.
  if (settings.emailFirst && !customer && step === 'identify' && furthest === 'identify') {
    const emailInvalid = emailTouched && (!email || !EMAIL_RE.test(email));
    return (
      <div className="mx-auto max-w-xl">
        <div className="flex flex-col gap-6">
          {settings.stepsTimeline && (
            <CheckoutStepsTimeline
              current="identify"
              furthest="identify"
              activeStyle={{ bg: settings.stepActiveBg, fg: settings.stepActiveText }}
            />
          )}
          <p className="text-lg text-text sm:text-xl">
            Para finalizar a compra, informe seu e-mail.{' '}
            <span className="whitespace-nowrap">Rápido, fácil e seguro.</span>
          </p>
          <form
            className="flex w-full flex-col gap-4 sm:flex-row sm:items-start sm:gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setEmailTouched(true);
              if (identifyValid) void advanceIdentify();
            }}
          >
            <div className="flex-1">
              <Input
                type="email"
                placeholder="seu@email.com"
                aria-label="E-mail"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => setEmailTouched(true)}
                error={emailInvalid ? (email ? 'E-mail inválido' : 'Informe seu e-mail') : undefined}
              />
            </div>
            <Button
              type="submit"
              size="lg"
              className="uppercase tracking-wide sm:w-40"
              style={{
                background: settings.buttonColor,
                color: settings.buttonTextColor,
                borderColor: settings.buttonBorderColor,
              }}
            >
              Continuar
            </Button>
          </form>

          <div className="text-left text-sm text-text-muted">
            <p className="mb-2 font-semibold text-accent">Usamos seu e-mail de forma 100% segura para:</p>
            <ul className="flex flex-col gap-1.5">
              {[
                'Identificar seu perfil',
                'Notificar sobre o andamento do seu pedido',
                'Gerenciar seu histórico de compras',
                'Acelerar o preenchimento de suas informações',
              ].map((t) => (
                <li key={t} className="flex items-center gap-2">
                  <span className="text-accent">✓</span> {t}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={
        reviewOnSide
          ? 'grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]'
          : 'flex flex-col gap-6'
      }
    >
      <div className="flex min-w-0 flex-col gap-4">
        {settings.stepsTimeline && (
          <CheckoutStepsTimeline
            current={step}
            furthest={furthest}
            onJump={goto}
            activeStyle={{ bg: settings.stepActiveBg, fg: settings.stepActiveText }}
          />
        )}

        {settings.showReview && settings.reviewPosition === 'top' && (
          <OrderSummary
            position="top"
            showCoupon={settings.showCoupon}
            layout={settings.itemsLayout}
            allowQtyChange={settings.allowQtyChange}
          />
        )}

        {/* 1 — Identificação */}
        <StepSection
          number={1}
          title="Identificação"
          state={stateOf('identify')}
          onEdit={() => goto('identify')}
          summary={
            <span>
              {email}
              {!settings.emailFirst && cpf ? ` · CPF ${maskCpf(cpf)}` : ''}
            </span>
          }
        >
          <p className="text-sm text-text-muted">
            {settings.emailFirst
              ? 'Informe seu e-mail para começar. Usamos ele para identificar a compra e enviar as atualizações do pedido.'
              : 'Informe seu e-mail e CPF. Usamos o e-mail para identificar a compra e enviar as atualizações; sua senha de acesso é o próprio CPF.'}
          </p>
          <Input
            label="E-mail"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={
              email && !EMAIL_RE.test(email) ? 'E-mail inválido' : miss('email')
            }
          />
          {!settings.emailFirst && (
            <Input
              label="CPF"
              inputMode="numeric"
              required
              value={cpf}
              onChange={(e) => setCpf(maskCpf(e.target.value))}
              error={
                cpf && onlyDigits(cpf).length === 11 && !cpfOk
                  ? 'CPF inválido'
                  : cpf && onlyDigits(cpf).length > 0 && onlyDigits(cpf).length < 11
                    ? 'CPF incompleto'
                    : miss('cpf')
              }
            />
          )}
          <Button
            block
            size="lg"
            onClick={() => void advanceIdentify()}
            className="font-bold"
          >
            Avançar
          </Button>
          {showMissingHint && (
            <p className="text-sm text-danger">Preencha os campos destacados.</p>
          )}
        </StepSection>

        {/* 2 — Dados pessoais */}
        {stepVisible('profile') && (
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
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Input
              label="Nome"
              required
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              error={miss('firstName')}
            />
            <Input
              label="Sobrenome"
              required
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              error={miss('lastName')}
            />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {settings.emailFirst && (
              <Input
                label="CPF"
                inputMode="numeric"
                required
                value={cpf}
                onChange={(e) => setCpf(maskCpf(e.target.value))}
                hint="Também é a sua senha de acesso à conta."
                error={
                  cpf && onlyDigits(cpf).length === 11 && !cpfOk
                    ? 'CPF inválido'
                    : cpf && onlyDigits(cpf).length > 0 && onlyDigits(cpf).length < 11
                      ? 'CPF incompleto'
                      : miss('cpf')
                }
              />
            )}
            <Input
              label="Telefone / WhatsApp"
              inputMode="numeric"
              required
              placeholder="(11) 99999-9999"
              value={maskPhone(phone)}
              onChange={(e) => setPhone(maskPhone(e.target.value))}
              error={
                phone && onlyDigits(phone).length < 10
                  ? 'Telefone incompleto'
                  : miss('phone')
              }
            />
          </div>
          <button type="button" onClick={() => goto('identify')} className="w-fit text-xs text-primary underline">
            {settings.emailFirst ? 'Trocar e-mail' : 'Trocar e-mail / CPF'}
          </button>
          <Button block size="lg" onClick={advanceProfile} className="font-bold">
            Avançar
          </Button>
          {showMissingHint && (
            <p className="text-sm text-danger">Preencha os campos destacados.</p>
          )}
        </StepSection>
        )}

        {/* 3 — Entrega */}
        {stepVisible('shipping') && (
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
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Input
              label="CEP"
              inputMode="numeric"
              required
              value={addr.zip}
              onChange={(e) => setAddrField('zip', maskCep(e.target.value))}
              placeholder="00000-000"
              hint="O frete é calculado automaticamente."
              error={miss('zip')}
            />
            <Input
              label="Número"
              required
              inputMode="numeric"
              placeholder="Nº ou S/N"
              hint="Sem número? Digite S/N."
              value={addr.number}
              onChange={(e) => setAddrField('number', maskHouseNumber(e.target.value))}
              error={miss('number')}
            />
          </div>
          <Input
            label="Rua / logradouro"
            required
            value={addr.street}
            onChange={(e) => setAddrField('street', e.target.value)}
            error={miss('street')}
          />
          <Input label="Complemento (opcional)" value={addr.complement} onChange={(e) => setAddrField('complement', e.target.value)} />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Input
              label="Bairro"
              required
              value={addr.district}
              onChange={(e) => setAddrField('district', e.target.value)}
              error={miss('district')}
            />
            <Input
              label="Cidade"
              required
              value={addr.city}
              onChange={(e) => setAddrField('city', e.target.value)}
              error={miss('city')}
            />
          </div>
          <Input
            label="Estado (UF)"
            required
            maxLength={2}
            value={addr.state}
            onChange={(e) => setAddrField('state', e.target.value.toUpperCase().slice(0, 2))}
            className="sm:w-32"
            error={miss('state')}
          />

          {/* Opções de frete */}
          <div
            className={`flex flex-col gap-2 rounded-card border-t pt-3 ${
              missing.has('shipping') && !fieldFilled.shipping
                ? 'border-danger border bg-danger/5 p-3'
                : 'border-surface-border'
            }`}
          >
            <p
              className={`text-sm font-medium ${
                missing.has('shipping') && !fieldFilled.shipping ? 'text-danger' : ''
              }`}
            >
              Selecione a forma de entrega...
            </p>
            {shipLoading && (
              <p className="flex items-center gap-2 text-sm text-text-muted">
                <Spinner /> Calculando o frete…
              </p>
            )}
            {shipError && <p className="text-xs text-danger">{shipError}</p>}
            {!shipLoading && shipOptions.length === 0 && !shipError && (
              <p className="text-xs text-text-muted">Digite o CEP para ver SEDEX, PAC e demais opções.</p>
            )}
            <ul className="flex flex-col gap-2">
              {shipOptions.map((opt) => {
                const selected = cart.selected_shipping?.id === opt.id;
                return (
                  <li
                    key={opt.id}
                    className={`rounded-card border ${selected ? 'border-primary bg-primary/5' : 'border-surface-border'}`}
                  >
                    <label className="flex cursor-pointer items-center gap-3 px-3 py-3 text-sm">
                      <input
                        type="radio"
                        name="shipping_option"
                        checked={selected}
                        onChange={() => {
                          setShipPickMsg(null);
                          void selectShipping(opt.id);
                        }}
                      />
                      <span className="flex-1">
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
                    </label>
                  </li>
                );
              })}
            </ul>
            {shipPickMsg && <p className="text-xs font-medium text-danger">{shipPickMsg}</p>}
          </div>

          <Button block size="lg" onClick={advanceShipping} className="font-bold">
            Avançar
          </Button>
          {showMissingHint && (
            <p className="text-sm text-danger">Preencha os campos destacados.</p>
          )}
        </StepSection>
        )}

        {/* 4 — Pagamento */}
        {stepVisible('payment') && (
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
                        {settings.paymentIcons && (
                          <span className="flex h-6 w-6 shrink-0 items-center justify-center text-text">
                            <PaymentIcon method={m.id} />
                          </span>
                        )}
                        <span>
                          <span className="text-sm font-medium">{m.label}</span>
                          <span className="block text-xs text-text-muted">{m.hint}</span>
                        </span>
                      </label>

                      {active && m.id === 'credit_card' && (
                        <div className="flex flex-col gap-3 border-t border-surface-border p-3">
                          {settings.animatedCard && (
                            <AnimatedCard
                              number={card.number}
                              name={card.holder_name}
                              expiry={card.exp}
                              cvv={card.cvv}
                              flipped={cvvFocused}
                            />
                          )}
                          <Input
                            label="Número do cartão"
                            inputMode="numeric"
                            autoComplete="cc-number"
                            placeholder="0000 0000 0000 0000"
                            value={card.number}
                            onChange={(e) =>
                              setCard((c) => ({ ...c, number: maskCardNumber(e.target.value) }))
                            }
                            error={miss('card_number')}
                          />
                          <Input
                            label="Nome impresso no cartão"
                            value={card.holder_name}
                            onChange={(e) => setCard((c) => ({ ...c, holder_name: e.target.value }))}
                            error={miss('card_holder')}
                          />
                          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                            <Input
                              label="Validade (MM/AA)"
                              placeholder="MM/AA"
                              inputMode="numeric"
                              pattern="[0-9/]*"
                              autoComplete="cc-exp"
                              value={card.exp}
                              onChange={(e) => {
                                const d = onlyDigits(e.target.value).slice(0, 4);
                                setCard((c) => ({ ...c, exp: d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d }));
                              }}
                              error={miss('card_exp')}
                            />
                            <Input
                              label="CVV"
                              inputMode="numeric"
                              value={card.cvv}
                              onFocus={() => setCvvFocused(true)}
                              onBlur={() => setCvvFocused(false)}
                              onChange={(e) => setCard((c) => ({ ...c, cvv: onlyDigits(e.target.value).slice(0, 4) }))}
                              error={miss('card_cvv')}
                            />
                          </div>
                          {maxInstallments > 1 && (
                            <label className="flex flex-col gap-1 text-sm font-medium text-text">
                              Parcelas
                              <select
                                value={installments}
                                onChange={(e) => setInstallments(Number(e.target.value))}
                                className="min-h-touch w-full rounded-card border border-surface-border bg-surface px-3 text-sm max-sm:h-12 max-sm:text-base"
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

          {orderBumps.length > 0 && (
            <div className="flex flex-col gap-2">
              {orderBumps.map((b, i) => {
                const id = b.variant_id ?? `bump-${i}`;
                const checked = b.variant_id ? bumpChecked.has(b.variant_id) : false;
                return (
                  <div
                    key={id}
                    className="flex items-center gap-3 rounded-card border-2 border-dashed border-accent/60 bg-accent/5 p-3"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={!b.variant_id}
                      onChange={(e) =>
                        setBumpChecked((prev) => {
                          const n = new Set(prev);
                          if (!b.variant_id) return n;
                          if (e.target.checked) n.add(b.variant_id);
                          else n.delete(b.variant_id);
                          return n;
                        })
                      }
                      className="h-5 w-5 shrink-0"
                      id={`orderbump-${i}`}
                    />
                    {b.image_url && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={resolveMediaUrl(b.image_url) ?? ''}
                        alt=""
                        className="h-14 w-14 shrink-0 rounded-card object-cover"
                      />
                    )}
                    <label htmlFor={`orderbump-${i}`} className="flex-1 cursor-pointer text-sm">
                      <span className="block font-semibold">Adicione também: {b.name}</span>
                      <span className="text-text-muted">
                        Aproveite e leve por {formatBRL(b.price_cents)}
                      </span>
                    </label>
                  </div>
                );
              })}
            </div>
          )}

          {settings.orderNotes && (
            <>
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
            </>
          )}

          {settings.requireTerms && (
            <label
              className={`flex items-start gap-2 text-sm ${
                missing.has('terms') && !fieldFilled.terms ? 'font-medium text-danger' : ''
              }`}
            >
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
          )}

          {error && <p className="text-sm text-danger">{error}</p>}

          <Button
            size="lg"
            block
            loading={submitting}
            onClick={() => void submit()}
            style={{
              background: settings.buttonColor,
              color: settings.buttonTextColor,
              borderColor: settings.buttonBorderColor,
            }}
          >
            {method === 'pix'
              ? 'Gerar PIX'
              : method === 'boleto'
                ? 'Gerar boleto'
                : `Pagar ${formatBRL(cart.totals.grand_total_cents)}`}
          </Button>
          {showMissingHint && (
            <p className="text-sm text-danger">Preencha os campos destacados.</p>
          )}
        </StepSection>
        )}
      </div>

      {reviewOnSide && (
        <div className="min-w-0">
          <OrderSummary
            position="side"
            showCoupon={settings.showCoupon}
            layout={settings.itemsLayout}
            allowQtyChange={settings.allowQtyChange}
          />
        </div>
      )}
    </div>
  );
}
