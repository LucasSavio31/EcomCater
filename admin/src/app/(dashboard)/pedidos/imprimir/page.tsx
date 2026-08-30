'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { ordersApi } from '@/modules/orders/api';
import { formatBRL, formatDateTime } from '@/lib/format';
import type { OrderDetail } from '@/modules/orders/types';

const SEM_FORNECEDOR = 'Sem fornecedor';

interface Linha {
  pedido: string;
  data: string;
  cliente: string;
  item: string;
  variacao: string | null;
  sku: string;
  qtd: number;
  total_cents: number;
}

function agruparPorFornecedor(orders: OrderDetail[]): Map<string, Linha[]> {
  const grupos = new Map<string, Linha[]>();
  for (const o of orders) {
    for (const it of o.items) {
      const forn = it.supplier?.trim() || SEM_FORNECEDOR;
      const linha: Linha = {
        pedido: o.number,
        data: o.placed_at,
        cliente: o.shipping_address?.recipient_name || o.email,
        item: it.name,
        variacao: it.variant_label,
        sku: it.sku,
        qtd: it.quantity,
        total_cents: it.total_cents,
      };
      const atual = grupos.get(forn);
      if (atual) atual.push(linha);
      else grupos.set(forn, [linha]);
    }
  }
  return grupos;
}

function ResumoImpressao() {
  const params = useSearchParams();
  const ids = useMemo(
    () => (params.get('ids') ?? '').split(',').map((s) => s.trim()).filter(Boolean),
    [params],
  );
  const [orders, setOrders] = useState<OrderDetail[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (ids.length === 0) {
      setErro('Nenhum pedido selecionado.');
      return;
    }
    let cancelado = false;
    ordersApi.bulk(ids).then((res) => {
      if (cancelado) return;
      if (!res.ok) {
        setErro(res.error.message);
        return;
      }
      setOrders(res.data);
    });
    return () => {
      cancelado = true;
    };
  }, [ids]);

  useEffect(() => {
    if (orders && orders.length > 0) {
      const t = setTimeout(() => window.print(), 400);
      return () => clearTimeout(t);
    }
  }, [orders]);

  if (erro) return <p style={{ padding: 24 }}>{erro}</p>;
  if (!orders) return <p style={{ padding: 24 }}>Carregando…</p>;

  const grupos = agruparPorFornecedor(orders);
  const fornecedores = [...grupos.keys()].sort((a, b) =>
    a === SEM_FORNECEDOR ? 1 : b === SEM_FORNECEDOR ? -1 : a.localeCompare(b),
  );

  return (
    <>
      <style>{`
        @page { size: A4; margin: 14mm; }
        @media print {
          body * { visibility: hidden; }
          #print-root, #print-root * { visibility: visible; }
          #print-root { position: absolute; inset: 0; }
          .no-print { display: none !important; }
        }
        #print-root { font-family: Arial, Helvetica, sans-serif; color: #111; font-size: 12px; }
        #print-root h1 { font-size: 18px; margin: 0 0 4px; }
        #print-root h2 { font-size: 14px; margin: 18px 0 6px; padding-bottom: 3px; border-bottom: 2px solid #111; page-break-after: avoid; }
        #print-root table { width: 100%; border-collapse: collapse; margin-bottom: 6px; }
        #print-root th, #print-root td { border: 1px solid #999; padding: 4px 6px; text-align: left; vertical-align: top; }
        #print-root th { background: #f0f0f0; }
        #print-root tr { page-break-inside: avoid; }
        #print-root .sub { color: #555; font-size: 11px; }
        #print-root .grp-tot { font-weight: bold; text-align: right; }
      `}</style>
      <div id="print-root" style={{ padding: 24 }}>
        <button
          type="button"
          className="no-print"
          onClick={() => window.print()}
          style={{ float: 'right', padding: '6px 12px', cursor: 'pointer' }}
        >
          Imprimir / Salvar PDF
        </button>
        <h1>Resumo de pedidos por fornecedor</h1>
        <p className="sub">
          {orders.length} pedido(s) &middot; gerado em {formatDateTime(new Date().toISOString())}
        </p>

        {fornecedores.map((forn) => {
          const linhas = grupos.get(forn)!;
          const totQtd = linhas.reduce((s, l) => s + l.qtd, 0);
          const totCents = linhas.reduce((s, l) => s + l.total_cents, 0);
          return (
            <section key={forn}>
              <h2>{forn}</h2>
              <table>
                <thead>
                  <tr>
                    <th style={{ width: '14%' }}>Pedido</th>
                    <th style={{ width: '20%' }}>Cliente</th>
                    <th>Produto</th>
                    <th style={{ width: '16%' }}>Variação</th>
                    <th style={{ width: '12%' }}>SKU</th>
                    <th style={{ width: '6%' }}>Qtd</th>
                    <th style={{ width: '12%' }}>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {linhas.map((l, i) => (
                    <tr key={`${l.pedido}-${l.sku}-${i}`}>
                      <td>
                        {l.pedido}
                        <div className="sub">{formatDateTime(l.data)}</div>
                      </td>
                      <td>{l.cliente}</td>
                      <td>{l.item}</td>
                      <td>{l.variacao ?? '—'}</td>
                      <td>{l.sku}</td>
                      <td>{l.qtd}</td>
                      <td>{formatBRL(l.total_cents)}</td>
                    </tr>
                  ))}
                  <tr>
                    <td colSpan={5} className="grp-tot">
                      Subtotal {forn}
                    </td>
                    <td>{totQtd}</td>
                    <td>{formatBRL(totCents)}</td>
                  </tr>
                </tbody>
              </table>
            </section>
          );
        })}
      </div>
    </>
  );
}

export default function ImprimirPedidosPage() {
  return (
    <Suspense fallback={<p style={{ padding: 24 }}>Carregando…</p>}>
      <ResumoImpressao />
    </Suspense>
  );
}
