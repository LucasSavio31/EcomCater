'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, Spinner } from '@ecom/ui';
import { customerApi } from '@/modules/customer/api';
import type { Order } from '@/modules/checkout/types';
import { formatBRL } from '@/lib/format';

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

function fmtDate(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function OrdersList() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    void customerApi.myOrders().then((res) => {
      if (res.ok) setOrders(res.data);
      else setError(res.error.message);
    });
  }, []);

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
                  <Tag>{PAYMENT_PT[o.payment_status] ?? o.payment_status}</Tag>
                  <Tag>{FULFILL_PT[o.fulfillment_status] ?? o.fulfillment_status}</Tag>
                  <span className="font-semibold">{formatBRL(o.grand_total_cents)}</span>
                </span>
              </button>

              {open && (
                <div className="flex flex-col gap-3 border-t border-surface-border pt-3">
                  <ul className="flex flex-col gap-1 text-sm">
                    {o.items.map((i) => (
                      <li key={i.sku} className="flex justify-between gap-2">
                        <span>
                          {i.quantity}× {i.name}
                          {i.variant_label ? ` · ${i.variant_label}` : ''}
                        </span>
                        <span className="shrink-0">{formatBRL(i.total_cents)}</span>
                      </li>
                    ))}
                  </ul>

                  <div className="text-sm text-text-muted">
                    Entrega: {o.shipping_address.recipient_name} — {o.shipping_address.street},{' '}
                    {o.shipping_address.number}, {o.shipping_address.city}/{o.shipping_address.state}
                  </div>

                  {o.events.length > 0 && (
                    <ol className="flex flex-col gap-1 border-l-2 border-surface-border pl-3 text-xs text-text-muted">
                      {o.events
                        .slice()
                        .reverse()
                        .map((ev, idx) => (
                          <li key={idx}>
                            <span className="text-text">{ev.message ?? ev.to_status ?? ev.type}</span>
                            {ev.created_at ? ` · ${fmtDate(ev.created_at)}` : ''}
                          </li>
                        ))}
                    </ol>
                  )}
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
