'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Card, Spinner } from '@ecom/ui';
import { customerApi } from '@/modules/customer/api';
import type { Order, OrderEvent } from '@/modules/checkout/types';
import { formatBRL } from '@/lib/format';

const ORDER_STATUS_PT: Record<string, string> = {
  pending_payment: 'Aguardando pagamento',
  paid: 'Pago',
  processing: 'Em separação',
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
          <li key={o.id}>
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
                  <Tag>{ORDER_STATUS_PT[o.status] ?? PAYMENT_PT[o.payment_status] ?? o.status}</Tag>
                  <Tag>{FULFILL_PT[o.fulfillment_status] ?? o.fulfillment_status}</Tag>
                  <span className="font-semibold">{formatBRL(o.grand_total_cents)}</span>
                </span>
              </button>

              {open && (
                <div className="flex flex-col gap-4 border-t border-surface-border pt-3">
                  <ul className="flex flex-col gap-3">
                    {o.items.map((i) => (
                      <li key={i.sku} className="flex items-center gap-3">
                        <span className="h-14 w-14 shrink-0 overflow-hidden rounded-card bg-bg-subtle">
                          {i.image_url && (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={i.image_url}
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
                    ))}
                  </ul>

                  <div className="text-sm text-text-muted">
                    Entrega: {o.shipping_address.recipient_name} — {o.shipping_address.street},{' '}
                    {o.shipping_address.number}, {o.shipping_address.city}/{o.shipping_address.state}
                  </div>

                  {o.payment && (
                    <div className="flex flex-col gap-1">
                      <h3 className="text-sm font-semibold">Pagamento</h3>
                      <dl className="flex flex-col gap-1 text-sm">
                        <div className="flex justify-between gap-2">
                          <dt className="text-text-muted">Método</dt>
                          <dd>{PAYMENT_METHOD_PT[o.payment.method] ?? o.payment.method}</dd>
                        </div>
                        <div className="flex justify-between gap-2">
                          <dt className="text-text-muted">Situação</dt>
                          <dd>{PAYMENT_STATUS_PT[o.payment.status] ?? o.payment.status}</dd>
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

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-card bg-bg-subtle px-2 py-0.5 text-xs font-medium">{children}</span>
  );
}
