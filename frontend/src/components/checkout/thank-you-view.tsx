'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Button, Card, Spinner } from '@ecom/ui';
import { checkoutApi } from '@/modules/checkout/api';
import type { ChargeResult, Order } from '@/modules/checkout/types';
import { formatBRL } from '@/lib/format';

const PAYMENT_LABEL: Record<string, { text: string; tone: string }> = {
  paid: { text: 'Pagamento confirmado', tone: 'text-success' },
  pending: { text: 'Aguardando pagamento', tone: 'text-warning' },
  awaiting_payment: { text: 'Aguardando pagamento', tone: 'text-warning' },
  canceled: { text: 'Pagamento cancelado', tone: 'text-danger' },
  refunded: { text: 'Pagamento estornado', tone: 'text-danger' },
  failed: { text: 'Pagamento não autorizado', tone: 'text-danger' },
};

export function ThankYouView() {
  const params = useSearchParams();
  const number = params.get('pedido') ?? '';
  const email = params.get('email') ?? undefined;

  const [order, setOrder] = useState<Order | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [copied, setCopied] = useState(false);
  const charge = useRef<ChargeResult | null>(null);

  if (charge.current === null && number && typeof window !== 'undefined') {
    try {
      const raw = sessionStorage.getItem(`ecom:charge:${number}`);
      charge.current = raw ? (JSON.parse(raw) as ChargeResult) : null;
    } catch {
      charge.current = null;
    }
  }

  const load = useCallback(async () => {
    if (!number) {
      setNotFound(true);
      setLoading(false);
      return;
    }
    const [ordRes, statusRes] = await Promise.all([
      checkoutApi.getOrder(number, email),
      checkoutApi.paymentStatus(number),
    ]);
    if (ordRes.ok) setOrder(ordRes.data);
    else setNotFound(true);
    if (statusRes.ok) setPaymentStatus(statusRes.data.payment_status);
    else if (ordRes.ok) setPaymentStatus(ordRes.data.payment_status);
    setLoading(false);
  }, [number, email]);

  useEffect(() => {
    void load();
  }, [load]);

  // Enquanto pendente, refaz o polling do status por até ~2 min.
  useEffect(() => {
    if (!paymentStatus || paymentStatus === 'paid') return;
    let ticks = 0;
    const id = window.setInterval(async () => {
      ticks += 1;
      const res = await checkoutApi.paymentStatus(number);
      if (res.ok) setPaymentStatus(res.data.payment_status);
      if ((res.ok && res.data.payment_status === 'paid') || ticks >= 24) {
        window.clearInterval(id);
        if (res.ok && res.data.payment_status === 'paid') void load();
      }
    }, 5000);
    return () => window.clearInterval(id);
  }, [paymentStatus, number, load]);

  if (loading) {
    return (
      <p className="flex items-center gap-2 py-16 text-text-muted">
        <Spinner /> Carregando seu pedido…
      </p>
    );
  }

  if (notFound || !order) {
    return (
      <Card variant="outline" className="flex flex-col items-center gap-4 py-16 text-center">
        <h2 className="text-lg font-semibold">Não encontramos este pedido</h2>
        <p className="text-sm text-text-muted">
          Confira o link do e-mail de confirmação ou acesse sua conta.
        </p>
        <Button onClick={() => { window.location.href = '/minha-conta/pedidos'; }}>
          Meus pedidos
        </Button>
      </Card>
    );
  }

  const status = PAYMENT_LABEL[paymentStatus ?? order.payment_status] ?? {
    text: 'Pedido recebido',
    tone: 'text-text',
  };
  const pixCode = charge.current?.pix_qr_code ?? null;
  const boletoUrl = charge.current?.boleto_url ?? null;
  const boletoBarcode = charge.current?.boleto_barcode ?? null;
  const isPaid = (paymentStatus ?? order.payment_status) === 'paid';

  function copyPix() {
    if (!pixCode) return;
    void navigator.clipboard.writeText(pixCode).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <Card variant="outline" className="flex flex-col gap-2">
        <span className="text-sm text-text-muted">Pedido</span>
        <span className="text-2xl font-semibold">#{order.number}</span>
        <span className={`text-sm font-medium ${status.tone}`}>{status.text}</span>
        {!isPaid && (
          <span className="text-xs text-text-muted">
            Esta página atualiza sozinha quando o pagamento for confirmado.
          </span>
        )}
      </Card>

      {/* Instruções de pagamento */}
      {!isPaid && pixCode && (
        <Card variant="outline" className="flex flex-col gap-3">
          <h2 className="text-base font-semibold">Pague com PIX</h2>
          <p className="text-sm text-text-muted">
            Copie o código abaixo e cole no app do seu banco, na opção PIX Copia e Cola.
          </p>
          <code className="block break-all rounded-card bg-bg-subtle p-3 text-xs">{pixCode}</code>
          <Button variant="outline" onClick={copyPix}>
            {copied ? 'Código copiado ✓' : 'Copiar código PIX'}
          </Button>
        </Card>
      )}

      {!isPaid && (boletoUrl || boletoBarcode) && (
        <Card variant="outline" className="flex flex-col gap-3">
          <h2 className="text-base font-semibold">Boleto bancário</h2>
          {boletoBarcode && (
            <code className="block break-all rounded-card bg-bg-subtle p-3 text-xs">
              {boletoBarcode}
            </code>
          )}
          {boletoUrl && (
            <a
              href={boletoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-h-touch items-center justify-center rounded-card border border-surface-border px-4 text-sm font-medium hover:border-primary"
            >
              Abrir boleto
            </a>
          )}
        </Card>
      )}

      {/* Resumo */}
      <Card variant="outline" className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">Itens</h2>
        <ul className="flex flex-col gap-2 text-sm">
          {order.items.map((i) => (
            <li key={i.sku} className="flex justify-between gap-2">
              <span>
                {i.quantity}× {i.name}
                {i.variant_label ? ` · ${i.variant_label}` : ''}
              </span>
              <span className="shrink-0">{formatBRL(i.total_cents)}</span>
            </li>
          ))}
        </ul>
        <dl className="flex flex-col gap-1 border-t border-surface-border pt-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-text-muted">Subtotal</dt>
            <dd>{formatBRL(order.items_total_cents)}</dd>
          </div>
          {order.discount_cents > 0 && (
            <div className="flex justify-between">
              <dt className="text-text-muted">Desconto</dt>
              <dd className="text-success">− {formatBRL(order.discount_cents)}</dd>
            </div>
          )}
          <div className="flex justify-between">
            <dt className="text-text-muted">Frete{order.shipping_method ? ` (${order.shipping_method})` : ''}</dt>
            <dd>{order.shipping_cents > 0 ? formatBRL(order.shipping_cents) : 'Grátis'}</dd>
          </div>
          <div className="flex justify-between border-t border-surface-border pt-1 font-semibold">
            <dt>Total</dt>
            <dd>{formatBRL(order.grand_total_cents)}</dd>
          </div>
        </dl>
      </Card>

      <Card variant="outline" className="flex flex-col gap-1 text-sm">
        <h2 className="text-base font-semibold">Entrega</h2>
        <p>{order.shipping_address.recipient_name}</p>
        <p className="text-text-muted">
          {order.shipping_address.street}, {order.shipping_address.number}
          {order.shipping_address.complement ? ` — ${order.shipping_address.complement}` : ''}
        </p>
        <p className="text-text-muted">
          {order.shipping_address.district} · {order.shipping_address.city}/
          {order.shipping_address.state} · CEP {order.shipping_address.zip}
        </p>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Link
          href="/minha-conta/pedidos"
          className="inline-flex min-h-touch items-center rounded-card border border-surface-border px-4 text-sm font-medium hover:border-primary"
        >
          Acompanhar meus pedidos
        </Link>
        <Link
          href="/"
          className="inline-flex min-h-touch items-center rounded-card bg-btn px-4 text-sm font-medium text-btn-fg hover:bg-btn-hover"
        >
          Continuar comprando
        </Link>
      </div>
    </div>
  );
}
