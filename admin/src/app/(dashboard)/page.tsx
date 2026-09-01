'use client';

import { useCallback, useMemo, useState } from 'react';
import Link from 'next/link';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatNumber } from '@/lib/format';
import { SeriesChart, AbcCurve } from '@/components/dashboard-charts';
import { dashboardApi, type DashboardMetric } from '@/modules/dashboard/api';
import { productsApi } from '@/modules/catalog/api';
import type { ProductListItem } from '@/modules/catalog/types';

function todayISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function daysAgoISO(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function dayBoundISO(ymd: string, end: boolean): string {
  const [y, m, d] = ymd.split('-').map(Number);
  const dt = end
    ? new Date(y || 1970, (m || 1) - 1, d || 1, 23, 59, 59, 999)
    : new Date(y || 1970, (m || 1) - 1, d || 1, 0, 0, 0, 0);
  return dt.toISOString();
}

const METRIC_OPTS: { value: DashboardMetric; label: string }[] = [
  { value: 'revenue', label: 'Faturamento' },
  { value: 'canceled', label: 'Cancelados' },
  { value: 'refunded', label: 'Estornados' },
];

export default function DashboardPage() {
  const toast = useToast();
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [applied, setApplied] = useState<{ from: string; to: string }>({ from: '', to: '' });
  const [metric, setMetric] = useState<DashboardMetric>('revenue');
  const ranged = applied.from !== '' || applied.to !== '';

  const fetcher = useCallback(
    () =>
      dashboardApi.get({
        from: applied.from ? dayBoundISO(applied.from, false) : undefined,
        to: applied.to ? dayBoundISO(applied.to, true) : undefined,
        metric,
      }),
    [applied.from, applied.to, metric],
  );
  const { data, loading, error, reload } = useResource(fetcher, [applied.from, applied.to, metric]);

  // link para /pedidos respeitando o período aplicado (ou 30 dias)
  const rangeQS = ranged
    ? `from=${applied.from || daysAgoISO(30)}&to=${applied.to || todayISO()}`
    : `from=${daysAgoISO(30)}&to=${todayISO()}`;

  const fmtMetric = (v: number) => (metric === 'revenue' ? formatBRL(v) : formatNumber(v));

  const cards = data
    ? [
        {
          label: `Pedidos (${data.window_days}d)`,
          value: formatNumber(data.orders_period),
          href: `/pedidos?${rangeQS}`,
        },
        {
          label: 'Aguardando pagamento',
          value: formatNumber(data.orders_pending),
          href: '/pedidos?status=pending_payment',
        },
        {
          label: 'Pendentes de envio',
          value: formatNumber(data.orders_to_ship),
          href: '/pedidos?bucket=to_ship',
        },
        {
          label: 'Atrasados (+2 dias)',
          value: formatNumber(data.orders_late),
          href: '/pedidos?bucket=late',
          alert: data.orders_late > 0,
        },
        {
          label: `Faturamento (${data.window_days}d)`,
          value: formatBRL(data.revenue_period_cents),
          href: undefined as string | undefined,
        },
        {
          label: `Cancelados (${data.window_days}d)`,
          value: formatNumber(data.orders_canceled),
          href: `/pedidos?status=canceled&${rangeQS}`,
        },
        {
          label: `Estornados (${data.window_days}d)`,
          value: formatNumber(data.orders_refunded),
          href: `/pedidos?status=refunded&${rangeQS}`,
        },
        {
          label: 'Total de pedidos (histórico)',
          value: formatNumber(data.total_orders_all_time),
          href: '/pedidos',
        },
      ]
    : [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Dashboard" description="Visão geral da loja — padrão: últimos 30 dias." />

      <Card variant="outline" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <Input type="date" label="De" value={from} max={to || undefined} onChange={(e) => setFrom(e.target.value)} />
          <Input type="date" label="Até" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} />
          <Button onClick={() => setApplied({ from, to })}>Aplicar</Button>
          <Button
            variant="outline"
            onClick={() => {
              const f = daysAgoISO(30);
              const t = todayISO();
              setFrom(f);
              setTo(t);
              setApplied({ from: f, to: t });
            }}
          >
            Últimos 30 dias
          </Button>
          {ranged && (
            <Button
              variant="ghost"
              onClick={() => {
                setFrom('');
                setTo('');
                setApplied({ from: '', to: '' });
              }}
            >
              Limpar
            </Button>
          )}
        </div>
        <p className="text-xs text-text-muted">
          Sem filtro, tudo considera os <b>últimos 30 dias</b>. “Aguardando pagamento”, “Pendentes de
          envio” e “Atrasados” são sempre a foto atual. O <b>total histórico</b> nunca zera (conta
          pedidos excluídos e cancelados).
        </p>
      </Card>

      {loading && (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i} variant="elevated" className="h-24 animate-pulse bg-bg-subtle" />
          ))}
        </div>
      )}

      {error && (
        <Card variant="outline" className="border-danger">
          <p className="text-sm text-danger">Falha ao carregar: {error}</p>
          <button type="button" onClick={reload} className="mt-2 text-sm text-accent hover:underline">
            Tentar de novo
          </button>
        </Card>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
            {cards.map((card) => {
              const body = (
                <>
                  <span className="text-xs text-text-muted sm:text-sm">{card.label}</span>
                  <span
                    className={`text-xl font-semibold sm:text-2xl ${'alert' in card && card.alert ? 'text-danger' : ''}`}
                  >
                    {card.value}
                  </span>
                </>
              );
              return card.href ? (
                <Link
                  key={card.label}
                  href={card.href}
                  className="flex flex-col gap-1 rounded-card border border-surface-border bg-surface p-4 shadow-sm transition hover:border-primary"
                >
                  {body}
                </Link>
              ) : (
                <Card key={card.label} variant="elevated" className="flex flex-col gap-1">
                  {body}
                </Card>
              );
            })}
          </div>

          {/* Série temporal: período atual x anterior */}
          <Card variant="outline" className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">
                {METRIC_OPTS.find((m) => m.value === metric)?.label} — atual x período anterior
              </h2>
              <Select
                label=""
                value={metric}
                options={METRIC_OPTS}
                onChange={(e) => setMetric(e.target.value as DashboardMetric)}
              />
            </div>
            <SeriesChart current={data.series_current} previous={data.series_previous} fmt={fmtMetric} />
          </Card>

          {/* Curva ABC de produtos */}
          <Card variant="outline" className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold">Curva ABC dos produtos</h2>
            <p className="text-xs text-text-muted">
              Produtos ordenados por faturamento no período; a linha mostra o acumulado (Pareto).
            </p>
            <AbcCurve points={data.abc_curve} fmt={formatBRL} />
          </Card>

          {/* Top 10 + promoção rápida lado a lado */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card variant="outline" className="flex flex-col gap-3">
              <h2 className="text-lg font-semibold">10 modelos mais vendidos</h2>
              {data.top_products.length === 0 ? (
                <p className="text-sm text-text-muted">Sem vendas no período.</p>
              ) : (
                <ol className="flex flex-col divide-y divide-surface-border">
                  {data.top_products.map((p, i) => (
                    <li key={p.sku || p.name} className="flex items-center gap-3 py-2 first:pt-0 last:pb-0">
                      <span className="w-5 shrink-0 text-right text-sm font-semibold text-text-muted">
                        {i + 1}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">{p.name}</span>
                        <span className="text-xs text-text-muted">{p.sku}</span>
                      </span>
                      <span className="shrink-0 text-right">
                        <span className="block text-sm font-semibold">{formatBRL(p.revenue_cents)}</span>
                        <span className="text-xs text-text-muted">{p.units} un.</span>
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </Card>

            <QuickPromo onDone={() => toast.success('Preços atualizados.')} />
          </div>
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------- promoção rápida */
function QuickPromo({ onDone }: { onDone: () => void }) {
  const toast = useToast();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<ProductListItem[]>([]);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [percent, setPercent] = useState(10);
  const [busy, setBusy] = useState(false);
  const [searching, setSearching] = useState(false);

  const pickedList = useMemo(() => [...picked], [picked]);

  async function search() {
    setSearching(true);
    const res = await productsApi.list({ q, page: 1, page_size: 20 });
    setSearching(false);
    if (res.ok) setResults(res.data.items);
    else toast.error(res.error.message);
  }

  async function apply(pct: number) {
    if (pickedList.length === 0) return;
    setBusy(true);
    const res = await productsApi.bulkDiscount(pickedList, pct);
    setBusy(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    onDone();
    setPicked(new Set());
    void search();
  }

  return (
    <Card variant="outline" className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">Promoção rápida</h2>
      <p className="text-xs text-text-muted">
        Busque os produtos, marque quais entram e aplique um % de desconto (o preço atual vira o
        “de”). “Remover” volta ao preço cheio.
      </p>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void search();
        }}
      >
        <Input label="" placeholder="Buscar produto…" value={q} onChange={(e) => setQ(e.target.value)} className="flex-1" />
        <Button type="submit" variant="outline" loading={searching}>
          Buscar
        </Button>
      </form>

      {results.length > 0 && (
        <ul className="flex max-h-64 flex-col divide-y divide-surface-border overflow-y-auto rounded-card border border-surface-border">
          {results.map((p) => {
            const on = picked.has(p.id);
            const promo = p.compare_at_price_cents && p.compare_at_price_cents > p.price_cents;
            return (
              <li key={p.id}>
                <label className="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm">
                  <input
                    type="checkbox"
                    checked={on}
                    onChange={() =>
                      setPicked((prev) => {
                        const n = new Set(prev);
                        if (on) n.delete(p.id);
                        else n.add(p.id);
                        return n;
                      })
                    }
                  />
                  <span className="min-w-0 flex-1 truncate">{p.name}</span>
                  <span className="shrink-0 text-xs">
                    {promo && (
                      <span className="mr-1 text-text-muted line-through">
                        {formatBRL(p.compare_at_price_cents ?? 0)}
                      </span>
                    )}
                    <span className={promo ? 'font-semibold text-success' : ''}>
                      {formatBRL(p.price_cents)}
                    </span>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      )}

      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Desconto (%)
          <input
            type="number"
            min={1}
            max={90}
            value={percent}
            onChange={(e) => setPercent(Math.max(1, Math.min(90, Number(e.target.value) || 0)))}
            className="min-h-touch w-24 rounded-card border border-surface-border bg-surface px-3 text-sm"
          />
        </label>
        <Button disabled={pickedList.length === 0} loading={busy} onClick={() => void apply(percent)}>
          Aplicar em {pickedList.length}
        </Button>
        <Button
          variant="ghost"
          disabled={pickedList.length === 0}
          loading={busy}
          onClick={() => void apply(0)}
        >
          Remover promoção
        </Button>
      </div>
    </Card>
  );
}
