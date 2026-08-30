'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { ordersApi } from '@/modules/orders/api';
import { configApi, type ShippingConfig } from '@/modules/config/api';
import { appearanceApi } from '@/modules/appearance/api';
import type { OrderDetail } from '@/modules/orders/types';

interface Remetente {
  nome: string;
  cep: string;
}

function Etiqueta({ order, remetente }: { order: OrderDetail; remetente: Remetente }) {
  const a = order.shipping_address;
  const linha2 = [a?.district, a?.city, a?.state].filter(Boolean).join(' - ');
  return (
    <div className="etiqueta">
      <div className="et-topo">
        <strong>Pedido {order.number}</strong>
        <span>{order.shipping_service || order.shipping_method || 'Encomenda'}</span>
      </div>
      <div className="et-dest">
        <span className="et-rot">DESTINATÁRIO</span>
        <strong>{a?.recipient_name || order.email}</strong>
        <div>
          {a?.street}
          {a?.number ? `, ${a.number}` : ''}
          {a?.complement ? ` - ${a.complement}` : ''}
        </div>
        <div>{linha2}</div>
        <div>CEP {a?.zip || '—'}</div>
        {a?.phone ? <div>Tel: {a.phone}</div> : null}
      </div>
      <div className="et-rem">
        <span className="et-rot">REMETENTE</span>
        {remetente.nome} &middot; CEP {remetente.cep || '—'}
      </div>
    </div>
  );
}

function EtiquetasImpressao() {
  const params = useSearchParams();
  const ids = useMemo(
    () => (params.get('ids') ?? '').split(',').map((s) => s.trim()).filter(Boolean),
    [params],
  );
  const [orders, setOrders] = useState<OrderDetail[] | null>(null);
  const [remetente, setRemetente] = useState<Remetente>({ nome: 'Loja', cep: '' });
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (ids.length === 0) {
      setErro('Nenhum pedido selecionado.');
      return;
    }
    let cancelado = false;
    ordersApi.bulk(ids).then((res) => {
      if (cancelado) return;
      if (!res.ok) setErro(res.error.message);
      else setOrders(res.data);
    });
    Promise.all([configApi.getShipping(), appearanceApi.getSettings()]).then(([ship, appr]) => {
      if (cancelado) return;
      const s = ship.ok ? (ship.data as ShippingConfig) : null;
      setRemetente({
        nome: appr.ok ? appr.data.store_name || 'Loja' : 'Loja',
        cep: s?.origin_zip ?? '',
      });
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

  return (
    <>
      <style>{`
        @page { size: A4; margin: 0; }
        @media print {
          body * { visibility: hidden; }
          #print-root, #print-root * { visibility: visible; }
          #print-root { position: absolute; inset: 0; }
          .no-print { display: none !important; }
        }
        #print-root { font-family: Arial, Helvetica, sans-serif; color: #111; }
        .folha {
          display: grid;
          grid-template-columns: 1fr 1fr;
          grid-template-rows: 1fr 1fr;
          width: 210mm;
          height: 297mm;
          box-sizing: border-box;
          padding: 8mm;
          gap: 6mm;
          page-break-after: always;
        }
        .folha:last-child { page-break-after: auto; }
        .etiqueta {
          border: 1px dashed #999;
          border-radius: 4px;
          padding: 6mm;
          font-size: 12px;
          display: flex;
          flex-direction: column;
          gap: 4mm;
          overflow: hidden;
        }
        .et-topo { display: flex; justify-content: space-between; border-bottom: 2px solid #111; padding-bottom: 3mm; font-size: 13px; }
        .et-rot { display: block; font-size: 9px; letter-spacing: 1px; color: #666; margin-bottom: 1mm; }
        .et-dest strong { font-size: 15px; display: block; margin-bottom: 1mm; }
        .et-dest div { line-height: 1.4; }
        .et-rem { margin-top: auto; border-top: 1px solid #999; padding-top: 3mm; font-size: 11px; color: #333; }
        .vazia { border: 1px dashed #ddd; border-radius: 4px; }
      `}</style>
      <div id="print-root">
        <button
          type="button"
          className="no-print"
          onClick={() => window.print()}
          style={{ margin: 16, padding: '6px 12px', cursor: 'pointer' }}
        >
          Imprimir / Salvar PDF
        </button>
        {chunk(orders, 4).map((grupo, gi) => (
          <div className="folha" key={gi}>
            {grupo.map((o) => (
              <Etiqueta key={o.number} order={o} remetente={remetente} />
            ))}
            {Array.from({ length: 4 - grupo.length }).map((_, i) => (
              <div className="vazia" key={`v-${i}`} />
            ))}
          </div>
        ))}
      </div>
    </>
  );
}

function chunk<T>(arr: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

export default function EtiquetasPedidosPage() {
  return (
    <Suspense fallback={<p style={{ padding: 24 }}>Carregando…</p>}>
      <EtiquetasImpressao />
    </Suspense>
  );
}
