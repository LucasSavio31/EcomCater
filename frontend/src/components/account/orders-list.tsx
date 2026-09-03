'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Card, Spinner } from '@ecom/ui';
import { customerApi } from '@/modules/customer/api';
import type { Order, OrderEvent } from '@/modules/checkout/types';
import { formatBRL } from '@/lib/format';
import { resolveMediaUrl } from '@/lib/media';

const ORDER_STATUS_PT: Record<string, string> = {
  pending_payment: 'Aguardando pagamento',
  paid: 'Pago',
  processing: 'Em separação',
  tracking_available: 'Rastreio disponível',
  shipped: 'Enviado',
  delivered: 'Entregue',
  canceled: 'Cancelado',
  refunded: 'Reembolsado',
};
const PAYMENT_PT: Record<string, string> = {
  paid: 'Pago',
  pending: 'Aguardando pagamento',
  awaiting_payment: 'Aguardando pagamento',
  canceled: 'Cancelado',
  refunded: 'Estornado',
  failed: 'Não autorizado',
};

type Tone = 'neutral' | 'warning' | 'success' | 'danger' | 'accent' | 'info';

const ORDER_TONE: Record<string, Tone> = {
  pending_payment: 'warning',
  paid: 'success',
  processing: 'accent',
  tracking_available: 'info',
  shipped: 'accent',
  delivered: 'success',
  canceled: 'danger',
  refunded: 'danger',
};
const PAYMENT_TONE: Record<string, Tone> = {
  pending: 'warning',
  awaiting_payment: 'warning',
  authorized: 'accent',
  paid: 'success',
  failed: 'danger',
  refunded: 'danger',
  chargeback: 'danger',
  canceled: 'danger',
};
const FULFILL_PT: Record<string, string> = {
  pending: 'Em preparação',
  processing: 'Em preparação',
  posted: 'Postado',
  in_transit: 'Em trânsito',
  delivered: 'Entregue',
  POSTADO: 'Postado',
  EM_TRANSITO: 'Em trânsito',
  ENTREGUE: 'Entregue',
};
const ACTOR_PT: Record<string, string> = {
  system: 'sistema',
  admin: 'loja',
  customer: 'você',
};

function orderStatusLabel(value: string | null): string {
  if (!value) return '';
  return ORDER_STATUS_PT[value] ?? value;
}
function fmtDate(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
}
function fmtDateTime(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Link de rastreamento no site dos Correios. */
function correiosTrackingUrl(code: string): string {
  return `https://rastreamento.correios.com.br/app/index.php?objeto=${encodeURIComponent(code.trim())}`;
}

/** Mesmo visual da linha do tempo do painel: bolinha + fio + rótulo do status. */
function Timeline({ events }: { events: OrderEvent[] }) {
  if (!events || events.length === 0) {
    return <p className="text-sm text-text-muted">Sem eventos.</p>;
  }
  const sorted = [...events].sort(
    (a, b) => new Date(a.created_at ?? 0).getTime() - new Date(b.created_at ?? 0).getTime(),
  );
  return (
    <ol className="flex flex-col gap-0">
      {sorted.map((ev, i) => (
        <li key={i} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-primary" />
            {i < sorted.length - 1 && <span className="w-px flex-1 bg-surface-border" />}
          </div>
          <div className="flex flex-col gap-0.5 pb-4">
            <span className="text-sm font-medium">
              {ev.type === 'note'
                ? 'Nota interna'
                : ev.to_status
                  ? `Status: ${orderStatusLabel(ev.to_status)}`
                  : ev.message ?? ev.type}
            </span>
            {ev.message && ev.to_status && (
              <span className="text-sm text-text-muted">{ev.message}</span>
            )}
            <span className="text-xs text-text-muted">
              {fmtDateTime(ev.created_at)}
              {ev.actor_type ? ` · ${ACTOR_PT[ev.actor_type] ?? ev.actor_type}` : ''}
            </span>
          </div>
        </li>
      ))}
    </ol>
  );
}

const PAYMENT_METHOD_PT: Record<string, string> = {
  pix: 'PIX',
  credit_card: 'Cartão de crédito',
  boleto: 'Boleto bancário',
};
const PAYMENT_STATUS_PT: Record<string, string> = {
  pending: 'Aguardando pagamento',
  authorized: 'Autorizado',
  paid: 'Pago',
  failed: 'Não autorizado',
  refunded: 'Estornado',
  chargeback: 'Chargeback',
  canceled: 'Cancelado',
};

/** Poll completo lento (rede de segurança) + poll leve rápido no pedido aberto. */
const SLOW_POLL_MS = 30_000;
const FAST_PULSE_MS = 4_000;

export function OrdersList() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const loadedOnce = useRef(false);

  const load = useCallback(async (silent: boolean) => {
    const res = await customerApi.myOrders();
    if (res.ok) {
      setOrders(res.data);
      setError(null);
      loadedOnce.current = true;
    } else if (!silent && !loadedOnce.current) {
      setError(res.error.message);
    }
  }, []);

  useEffect(() => {
    void load(false);
    const id = window.setInterval(() => {
      if (document.visibilityState === 'visible') void load(true);
    }, SLOW_POLL_MS);
    const onFocus = () => void load(true);
    window.addEventListener('focus', onFocus);
    return () => {
      window.clearInterval(id);
      window.removeEventListener('focus', onFocus);
    };
  }, [load]);

  // deep-link ?pedido=2026-000123 (QR da fatura): abre e rola até o pedido
  const deepLinked = useRef(false);
  useEffect(() => {
    if (deepLinked.current || !orders) return;
    const want = new URLSearchParams(window.location.search).get('pedido');
    if (!want) return;
    const target = orders.find((o) => o.number === want.trim());
    if (!target) return;
    deepLinked.current = true;
    setOpenId(target.id);
    window.setTimeout(
      () =>
        document
          .getElementById(`pedido-${target.number}`)
          ?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      120,
    );
  }, [orders]);

  // pedido aberto: bate um "pulse" leve a cada 4s e só refaz o GET quando muda
  const openNumber = orders?.find((o) => o.id === openId)?.number ?? null;
  const lastPulse = useRef<string>('');
  useEffect(() => {
    if (!openNumber) return;
    lastPulse.current = '';
    const tick = async () => {
      if (document.visibilityState !== 'visible') return;
      const res = await customerApi.orderPulse(openNumber);
      if (!res.ok) return;
      const sig = `${res.data.status}|${res.data.payment_status}|${res.data.fulfillment_status}|${res.data.event_count}|${res.data.last_change_at}`;
      if (lastPulse.current && lastPulse.current !== sig) void load(true);
      lastPulse.current = sig;
    };
    void tick();
    const id = window.setInterval(() => void tick(), FAST_PULSE_MS);
    return () => window.clearInterval(id);
  }, [openNumber, load]);

  if (error) return <p className="text-sm text-danger">{error}</p>;
  if (!orders) {
    return (
      <p className="flex items-center gap-2 py-16 text-text-muted">
        <Spinner /> Carregando pedidos…
      </p>
    );
  }
  if (orders.length === 0) {
    return (
      <Card variant="outline" className="flex flex-col items-center gap-3 py-16 text-center">
        <p className="text-sm text-text-muted">Você ainda não fez nenhum pedido.</p>
        <Link href="/" className="text-sm text-primary underline">
          Começar a comprar
        </Link>
      </Card>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {orders.map((o) => {
        const open = openId === o.id;
        return (
          <li key={o.id} id={`pedido-${o.number}`} className="scroll-mt-4">
            <Card variant="outline" className="flex flex-col gap-3">
              <button
                type="button"
                onClick={() => setOpenId(open ? null : o.id)}
                className="flex flex-wrap items-center justify-between gap-2 text-left"
                aria-expanded={open}
              >
                <span>
                  <span className="font-semibold">#{o.number}</span>
                  <span className="ml-2 text-xs text-text-muted">{fmtDate(o.placed_at)}</span>
                </span>
                <span className="flex flex-wrap items-center gap-2">
                  <Tag tone={ORDER_TONE[o.status] ?? 'neutral'}>
                    {ORDER_STATUS_PT[o.status] ?? PAYMENT_PT[o.payment_status] ?? o.status}
                  </Tag>
                  {FULFILL_PT[o.fulfillment_status] && (
                    <Tag>{FULFILL_PT[o.fulfillment_status]}</Tag>
                  )}
                  {o.processing_error && <Tag tone="danger">Pendência no processamento</Tag>}
                  <span className="font-semibold">{formatBRL(o.grand_total_cents)}</span>
                </span>
              </button>

              {open && (
                <div className="flex flex-col gap-4 border-t border-surface-border pt-3">
                  {o.processing_error && (
                    <p className="rounded-card border border-danger/40 bg-danger/5 p-3 text-xs text-danger">
                      Alguns passos pós-pedido não concluíram e nossa equipe foi avisada:{' '}
                      <span className="text-text-muted">{o.processing_error}</span>
                    </p>
                  )}
                  <ul className="flex flex-col gap-3">
                    {o.items.map((i) => {
                      const img = resolveMediaUrl(i.image_url);
                      return (
                      <li key={i.sku} className="flex items-center gap-3">
                        <span className="h-14 w-14 shrink-0 overflow-hidden rounded-card border border-surface-border bg-bg-subtle">
                          {img && (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={img}
                              alt=""
                              className="h-full w-full object-cover"
                              loading="lazy"
                            />
                          )}
                        </span>
                        <span className="flex flex-1 flex-col text-sm">
                          <span className="font-medium">{i.name}</span>
                          <span className="text-xs text-text-muted">
                            {i.quantity}× {formatBRL(i.unit_price_cents)}
                            {i.variant_label ? ` · ${i.variant_label}` : ''}
                          </span>
                        </span>
                        <span className="shrink-0 text-sm font-medium">
                          {formatBRL(i.total_cents)}
                        </span>
                      </li>
                      );
                    })}
                  </ul>

                  <div className="text-sm text-text-muted">
                    Entrega: {o.shipping_address.recipient_name} — {o.shipping_address.street},{' '}
                    {o.shipping_address.number}, {o.shipping_address.city}/{o.shipping_address.state}
                  </div>

                  {typeof o.shipping_service?.tracking_code === 'string' &&
                    o.shipping_service.tracking_code && (
                      <div className="text-sm">
                        <span className="text-text-muted">Rastreio: </span>
                        <a
                          href={correiosTrackingUrl(o.shipping_service.tracking_code)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-primary underline"
                        >
                          {o.shipping_service.tracking_code}
                        </a>
                      </div>
                    )}

                  {o.payment && (
                    <div className="flex flex-col gap-1">
                      <h3 className="text-sm font-semibold">Pagamento</h3>
                      <dl className="flex flex-col gap-1 text-sm">
                        <div className="flex justify-between gap-2">
                          <dt className="text-text-muted">Método</dt>
                          <dd>{PAYMENT_METHOD_PT[o.payment.method] ?? o.payment.method}</dd>
                        </div>
                        <div className="flex items-center justify-between gap-2">
                          <dt className="text-text-muted">Situação</dt>
                          <dd>
                            <Tag tone={PAYMENT_TONE[o.payment.status] ?? 'neutral'}>
                              {PAYMENT_STATUS_PT[o.payment.status] ?? o.payment.status}
                            </Tag>
                          </dd>
                        </div>
                        {o.payment.installments && o.payment.installments > 1 && (
                          <div className="flex justify-between gap-2">
                            <dt className="text-text-muted">Parcelas</dt>
                            <dd>{o.payment.installments}x</dd>
                          </div>
                        )}
                        <div className="flex justify-between gap-2">
                          <dt className="text-text-muted">Valor</dt>
                          <dd>{formatBRL(o.payment.amount_cents)}</dd>
                        </div>
                      </dl>
                    </div>
                  )}

                  <div className="flex flex-col gap-2">
                    <h3 className="text-sm font-semibold">Linha do tempo</h3>
                    <Timeline events={o.events} />
                  </div>
                </div>
              )}
            </Card>
          </li>
        );
      })}
    </ul>
  );
}

const TAG_TONE_CLASS: Record<Tone, string> = {
  neutral: 'bg-bg-subtle text-text',
  warning: 'bg-warning/10 text-warning',
  success: 'bg-success/10 text-success',
  danger: 'bg-danger/10 text-danger',
  accent: 'bg-accent/10 text-accent',
  info: 'bg-blue-600/10 text-blue-600',
};

function Tag({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: Tone }) {
  return (
    <span className={`rounded-card px-2 py-0.5 text-xs font-medium ${TAG_TONE_CLASS[tone]}`}>
      {children}
    </span>
  );
}
