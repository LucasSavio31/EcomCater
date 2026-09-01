'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { ordersApi } from '@/modules/orders/api';
import { appearanceApi, type StoreSettings } from '@/modules/appearance/api';
import { formatBRL, formatDateTime } from '@/lib/format';
import type { OrderDetail } from '@/modules/orders/types';

const money = (c: number | null | undefined) => formatBRL(c ?? 0);

const PAYMENT_STATUS_PT: Record<string, string> = {
  pending: 'Pendente',
  authorized: 'Autorizado',
  paid: 'Pago',
  failed: 'Não autorizado',
  refunded: 'Estornado',
  chargeback: 'Chargeback',
  canceled: 'Cancelado',
};

function maskCnpjCpf(v: string | null | undefined): string {
  const d = (v ?? '').replace(/\D/g, '');
  if (d.length === 14)
    return d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
  if (d.length === 11) return d.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4');
  return v ?? '—';
}

function addrLine(a: Record<string, string> | null | undefined): string {
  if (!a) return '—';
  const p = [
    [a.street, a.number].filter(Boolean).join(', '),
    a.complement,
    a.district,
  ].filter(Boolean);
  return p.join(' — ') || '—';
}

function FaturaDoc() {
  const params = useSearchParams();
  const number = (params.get('id') ?? params.get('ids') ?? '').split(',')[0]?.trim() ?? '';
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [store, setStore] = useState<StoreSettings | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!number) {
      setErro('Nenhum pedido informado.');
      return;
    }
    let cancel = false;
    void Promise.all([ordersApi.get(number), appearanceApi.getSettings()]).then(
      ([ordRes, stRes]) => {
        if (cancel) return;
        if (!ordRes.ok) return setErro(ordRes.error.message);
        setOrder(ordRes.data);
        if (stRes.ok) setStore(stRes.data);
      },
    );
    return () => {
      cancel = true;
    };
  }, [number]);

  // Título da aba / cabeçalho de impressão do navegador — "Fatura ..." em vez
  // do "Painel" da app.
  useEffect(() => {
    const prev = document.title;
    document.title = order ? `Fatura ${order.number}` : 'Fatura';
    return () => {
      document.title = prev;
    };
  }, [order]);

  useEffect(() => {
    if (!order) return;
    // Folha X/Y: A4 útil ≈ 277mm ≈ 1047px @96dpi (margem 10mm).
    const setFolha = () => {
      const el = document.getElementById('fat');
      const out = document.getElementById('folha');
      if (!el || !out) return;
      const pages = Math.max(1, Math.ceil(el.scrollHeight / 1047));
      out.innerHTML = `<b>Folha:</b> 1/${pages}`;
    };
    const t = setTimeout(() => {
      setFolha();
      window.print();
    }, 500);
    window.addEventListener('beforeprint', setFolha);
    return () => {
      clearTimeout(t);
      window.removeEventListener('beforeprint', setFolha);
    };
  }, [order]);

  if (erro) return <p style={{ padding: 24 }}>{erro}</p>;
  if (!order) return <p style={{ padding: 24 }}>Carregando…</p>;

  const a = order.shipping_address ?? {};
  const emit = order.placed_at ? formatDateTime(order.placed_at) : '—';
  const lojaNome = store?.legal_name || store?.store_name || 'Loja';
  const pay = order.payment;
  const tracking = order.shipping_service?.tracking_code ?? null;

  // Descrição explícita da forma de pagamento
  const parcelas = pay?.installments && pay.installments > 1 ? pay.installments : 1;
  const juros = pay ? Math.max(0, pay.amount_cents - order.grand_total_cents) : 0;
  const pagamentoDesc = (() => {
    if (!pay) return '—';
    if (pay.method === 'credit_card')
      return parcelas > 1
        ? `Cartão de crédito — ${parcelas}x de ${money(Math.round(pay.amount_cents / parcelas))}`
        : 'Cartão de crédito — à vista';
    if (pay.method === 'boleto') return 'Boleto bancário — à vista';
    if (pay.method === 'pix') return 'PIX — à vista';
    return pay.method;
  })();

  // Cupom + % de redução sobre os produtos
  const cupomPct =
    order.coupon_code && order.items_total_cents > 0
      ? Math.round((order.discount_cents / order.items_total_cents) * 100)
      : 0;

  // Status do envio (com data/hora do evento que levou o pedido a esse status)
  const envioLabel =
    order.status === 'delivered'
      ? 'Recebido'
      : order.status === 'shipped'
        ? 'Enviado'
        : order.status === 'canceled'
          ? 'Cancelado'
          : order.status === 'refunded'
            ? 'Estornado'
            : 'Pendente';
  const envioEvent = [...order.events]
    .filter((e) => e.to_status === order.status)
    .sort((x, y) => new Date(y.created_at).getTime() - new Date(x.created_at).getTime())[0];
  const envioAt = envioEvent ? formatDateTime(envioEvent.created_at) : null;

  return (
    <>
      <style>{`
        /* margin: 0 esconde a data/URL que o navegador imprime na borda */
        @page { size: A4; margin: 0; }
        @media print {
          body * { visibility: hidden; }
          #fat, #fat * { visibility: visible; }
          #fat { position: absolute; inset: 0; padding: 10mm !important; }
          .no-print { display: none !important; }
        }
        #fat { font-family: Arial, Helvetica, sans-serif; color: #000; font-size: 11px; line-height: 1.35; }
        #fat .box { border: 1px solid #000; }
        #fat .row { display: flex; }
        #fat .cell { border-right: 1px solid #000; padding: 3px 6px; flex: 1; }
        #fat .cell:last-child { border-right: 0; }
        #fat .lbl { font-size: 8px; text-transform: uppercase; color: #000; letter-spacing: .3px; }
        #fat .val { font-size: 11px; }
        #fat .sec { border: 1px solid #000; border-top: 0; }
        #fat .sec-h { background: #eee; font-weight: bold; font-size: 9px; text-transform: uppercase; padding: 2px 6px; border-bottom: 1px solid #000; }
        #fat h1 { font-size: 15px; margin: 0; text-align: center; letter-spacing: 1px; }
        #fat table { width: 100%; border-collapse: collapse; }
        #fat th, #fat td { border: 1px solid #000; padding: 3px 5px; text-align: left; vertical-align: top; }
        #fat th { background: #eee; font-size: 8px; text-transform: uppercase; }
        #fat .r { text-align: right; }
        #fat .c { text-align: center; }
        #fat .mt { margin-top: 6px; }
      `}</style>

      <div id="fat" style={{ padding: 16 }}>
        <button
          type="button"
          className="no-print"
          onClick={() => window.print()}
          style={{ float: 'right', padding: '6px 12px', cursor: 'pointer' }}
        >
          Imprimir / Salvar PDF
        </button>

        {/* Recibo */}
        <div className="box">
          <div className="cell" style={{ borderRight: 0 }}>
            <div className="val">
              Recebemos de <b>{lojaNome}</b> os produtos constantes da fatura indicada ao lado.
            </div>
            <div className="row mt" style={{ borderTop: '1px solid #000' }}>
              <div className="cell">
                <div className="lbl">Data do recebimento</div>
                <div className="val">&nbsp;</div>
              </div>
              <div className="cell" style={{ flex: 2 }}>
                <div className="lbl">Identificação e assinatura do recebedor</div>
                <div className="val">&nbsp;</div>
              </div>
              <div
                className="cell c"
                style={{ flex: '0 0 150px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}
              >
                <div style={{ fontWeight: 'bold', fontSize: 13 }}>FATURA</div>
                <div className="val">Nº {order.number}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Cabeçalho: emitente | bloco DFAT-e | QR */}
        <div className="row box mt">
          <div className="cell" style={{ flex: 2 }}>
            <div style={{ fontWeight: 'bold', fontSize: 12 }}>{lojaNome}</div>
            <div className="val">{addrLine(store?.address_json)}</div>
            <div className="val">
              {[store?.address_json?.city, store?.address_json?.state].filter(Boolean).join(' - ')}
              {store?.address_json?.zip ? ` — CEP ${store.address_json.zip}` : ''}
            </div>
            <div className="val">CNPJ: {maskCnpjCpf(store?.cnpj)}</div>
            {store?.contact_phone && <div className="val">Tel: {store.contact_phone}</div>}
          </div>

          {/* Bloco central estilo DANFE */}
          <div className="cell c" style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div style={{ fontWeight: 'bold', fontSize: 15, letterSpacing: 1 }}>DFAT-e</div>
            <div className="val">Documento de Fatura Eletrônica</div>
            <div
              className="row"
              style={{ border: '1px solid #000', marginTop: 3, alignItems: 'stretch' }}
            >
              <div style={{ flex: 1, textAlign: 'left', padding: '2px 6px' }}>
                <div>0 - Entrada</div>
                <div>1 - Saída</div>
              </div>
              <div
                style={{
                  borderLeft: '1px solid #000',
                  width: 34,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 'bold',
                  fontSize: 18,
                }}
              >
                1
              </div>
            </div>
            <div className="val" style={{ marginTop: 2 }}>
              <b>Nº:</b> {order.number}
            </div>
            <div className="val">
              <b>Série:</b> 0
            </div>
            <div className="val" id="folha">
              <b>Folha:</b> 1/1
            </div>
            <div className="lbl" style={{ marginTop: 2 }}>Emissão: {emit}</div>
          </div>

          <div
            className="cell c"
            style={{ flex: '0 0 140px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}
          >
            {order.qr_data_uri && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={order.qr_data_uri}
                alt={`Código ${order.number}`}
                style={{ width: 108, height: 108 }}
              />
            )}
            <div className="val" style={{ fontFamily: 'monospace' }}>{order.number}</div>
          </div>
        </div>

        {/* Destinatário */}
        <div className="sec">
          <div className="sec-h">Destinatário</div>
          <div className="row">
            <div className="cell" style={{ flex: 2 }}>
              <div className="lbl">Nome / Razão social</div>
              <div className="val">{a.recipient_name || order.email}</div>
            </div>
            <div className="cell">
              <div className="lbl">CNPJ / CPF</div>
              <div className="val">{maskCnpjCpf(order.cpf)}</div>
            </div>
            <div className="cell">
              <div className="lbl">Data de emissão</div>
              <div className="val">{emit}</div>
            </div>
          </div>
          <div className="row" style={{ borderTop: '1px solid #000' }}>
            <div className="cell" style={{ flex: 2 }}>
              <div className="lbl">Endereço</div>
              <div className="val">{addrLine(a as Record<string, string>)}</div>
            </div>
            <div className="cell">
              <div className="lbl">Bairro</div>
              <div className="val">{a.district || '—'}</div>
            </div>
            <div className="cell">
              <div className="lbl">CEP</div>
              <div className="val">{a.zip || '—'}</div>
            </div>
          </div>
          <div className="row" style={{ borderTop: '1px solid #000' }}>
            <div className="cell">
              <div className="lbl">Município</div>
              <div className="val">{a.city || '—'}</div>
            </div>
            <div className="cell" style={{ flex: '0 0 60px' }}>
              <div className="lbl">UF</div>
              <div className="val">{a.state || '—'}</div>
            </div>
            <div className="cell">
              <div className="lbl">Telefone</div>
              <div className="val">{a.phone || '—'}</div>
            </div>
            <div className="cell" style={{ flex: 2 }}>
              <div className="lbl">E-mail</div>
              <div className="val">{order.email}</div>
            </div>
          </div>
        </div>

        {/* Rastreio da entrega */}
        <div className="sec">
          <div className="sec-h">Transporte / entrega</div>
          <div className="row">
            <div className="cell">
              <div className="lbl">Transportadora / serviço</div>
              <div className="val">
                {order.shipping_service?.carrier || 'Correios'}
                {order.shipping_method ? ` · ${order.shipping_method}` : ''}
              </div>
            </div>
            <div className="cell" style={{ flex: 2 }}>
              <div className="lbl">Código de rastreio</div>
              <div className="val" style={{ fontFamily: 'monospace' }}>{tracking || '—'}</div>
            </div>
          </div>
          <div className="row" style={{ borderTop: '1px solid #000' }}>
            <div className="cell">
              <div className="lbl">Status do envio</div>
              <div className="val">{envioLabel}</div>
            </div>
            <div className="cell" style={{ flex: 2 }}>
              <div className="lbl">Data/hora do status</div>
              <div className="val">{envioAt ?? '—'}</div>
            </div>
          </div>
        </div>

        {/* Cálculo dos valores */}
        <div className="sec">
          <div className="sec-h">Cálculo dos valores</div>
          <div className="row">
            <div className="cell">
              <div className="lbl">Valor dos produtos</div>
              <div className="val r">{money(order.items_total_cents)}</div>
            </div>
            <div className="cell">
              <div className="lbl">
                Desconto{cupomPct > 0 ? ` (cupom ${order.coupon_code} · −${cupomPct}%)` : ''}
              </div>
              <div className="val r">{order.discount_cents > 0 ? `− ${money(order.discount_cents)}` : money(0)}</div>
            </div>
            <div className="cell">
              <div className="lbl">Valor do frete{order.shipping_method ? ` (${order.shipping_method})` : ''}</div>
              <div className="val r">{money(order.shipping_cents)}</div>
            </div>
            {juros > 0 && (
              <div className="cell">
                <div className="lbl">Juros do parcelamento</div>
                <div className="val r">{money(juros)}</div>
              </div>
            )}
            <div className="cell">
              <div className="lbl">Valor total da fatura</div>
              <div className="val r" style={{ fontWeight: 'bold' }}>
                {money(juros > 0 && pay ? pay.amount_cents : order.grand_total_cents)}
              </div>
            </div>
          </div>
        </div>

        {/* Produtos */}
        <div className="sec">
          <div className="sec-h">Dados dos produtos / serviços</div>
          <table>
            <thead>
              <tr>
                <th style={{ width: '16%' }}>Código</th>
                <th>Descrição do produto / serviço</th>
                <th style={{ width: '16%' }}>Variação</th>
                <th style={{ width: '7%' }} className="c">Qtd</th>
                <th style={{ width: '13%' }} className="r">Valor unit.</th>
                <th style={{ width: '13%' }} className="r">Valor total</th>
              </tr>
            </thead>
            <tbody>
              {order.items.map((it, i) => (
                <tr key={`${it.sku}-${i}`}>
                  <td>{it.sku}</td>
                  <td>{it.name}</td>
                  <td>{it.variant_label || '—'}</td>
                  <td className="c">{it.quantity}</td>
                  <td className="r">{money(it.unit_price_cents)}</td>
                  <td className="r">{money(it.total_cents)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagamento */}
        <div className="sec">
          <div className="sec-h">Pagamento</div>
          <div className="row">
            <div className="cell" style={{ flex: 2 }}>
              <div className="lbl">Forma de pagamento</div>
              <div className="val">{pagamentoDesc}</div>
            </div>
            <div className="cell">
              <div className="lbl">Juros</div>
              <div className="val r">{juros > 0 ? money(juros) : 'Sem juros'}</div>
            </div>
            <div className="cell">
              <div className="lbl">Situação</div>
              <div className="val">{pay ? (PAYMENT_STATUS_PT[pay.status] ?? pay.status) : '—'}</div>
            </div>
          </div>
          {order.coupon_code && (
            <div className="row" style={{ borderTop: '1px solid #000' }}>
              <div className="cell">
                <div className="lbl">Cupom usado</div>
                <div className="val" style={{ fontFamily: 'monospace' }}>{order.coupon_code}</div>
              </div>
              <div className="cell">
                <div className="lbl">Redução</div>
                <div className="val r">
                  {cupomPct > 0 ? `−${cupomPct}%` : '—'} ({money(order.discount_cents)})
                </div>
              </div>
              <div className="cell" style={{ flex: 2 }} />
            </div>
          )}
        </div>

        {/* Dados adicionais */}
        <div className="sec">
          <div className="sec-h">Dados adicionais</div>
          <div className="row">
            <div className="cell">
              <div className="lbl">Informações complementares</div>
              <div className="val">{order.customer_note || '—'}</div>
            </div>
          </div>
        </div>

        <p className="mt" style={{ fontSize: 9 }}>
          Documento não fiscal, gerado para conferência do pedido. Impresso em{' '}
          {formatDateTime(new Date().toISOString())}.
        </p>
      </div>
    </>
  );
}

export default function FaturaPage() {
  return (
    <Suspense fallback={<p style={{ padding: 24 }}>Carregando…</p>}>
      <FaturaDoc />
    </Suspense>
  );
}
