'use client';

import { useCallback, useMemo, useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { Select } from '@/components/form-controls';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatNumber } from '@/lib/format';
import { SeriesChart } from '@/components/dashboard-charts';
import { financialApi, type RevenueSeriesPoint } from '@/modules/financial/api';

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

type SeriesMetric = 'gross' | 'net' | 'refunded' | 'canceled' | 'orders';

const METRIC_OPTS: { value: SeriesMetric; label: string }[] = [
  { value: 'gross', label: 'Faturamento bruto' },
  { value: 'net', label: 'Faturamento líquido' },
  { value: 'refunded', label: 'Estornos' },
  { value: 'canceled', label: 'Cancelamentos' },
  { value: 'orders', label: 'Total de pedidos' },
];

const FIELD: Record<SeriesMetric, keyof RevenueSeriesPoint> = {
  gross: 'gross_cents',
  net: 'net_cents',
  refunded: 'refunded_cents',
  canceled: 'canceled_cents',
  orders: 'orders',
};

export default function FaturamentoPage() {
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [applied, setApplied] = useState<{ from: string; to: string }>({ from: '', to: '' });
  const [metric, setMetric] = useState<SeriesMetric>('gross');
  const ranged = applied.from !== '' || applied.to !== '';

  const fetcher = useCallback(
    () =>
      financialApi.summary({
        from: applied.from ? dayBoundISO(applied.from, false) : undefined,
        to: applied.to ? dayBoundISO(applied.to, true) : undefined,
      }),
    [applied.from, applied.to],
  );
  const { data, loading, error, reload } = useResource(fetcher, [applied.from, applied.to]);

  const isMoney = metric !== 'orders';
  const fmtMetric = (v: number) => (isMoney ? formatBRL(v) : formatNumber(v));

  const seriesCurrent = useMemo(
    () =>
      (data?.series ?? []).map((p) => ({
        label: p.label,
        cents: Number(p[FIELD[metric]] ?? 0),
      })),
    [data, metric],
  );

  const cards = data
    ? [
        { label: 'Faturamento bruto', value: formatBRL(data.gross_cents) },
        { label: 'Custo dos produtos', value: formatBRL(data.cost_cents) },
        { label: 'Faturamento líquido', value: formatBRL(data.net_cents) },
        { label: 'Margem de lucratividade', value: `${data.margin_pct.toFixed(1)}%` },
        {
          label: 'Estornos',
          value: `${formatBRL(data.refunded_cents)} · ${formatNumber(data.refunds_count)}`,
        },
        {
          label: 'Cancelamentos',
          value: `${formatBRL(data.canceled_cents)} · ${formatNumber(data.canceled_count)}`,
        },
        { label: 'Total de pedidos', value: formatNumber(data.orders_total) },
      ]
    : [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Faturamento"
        description="Livro-caixa da loja — valores cumulativos e persistentes (não mudam se um pedido for excluído). Mesmo filtro do painel; padrão: últimos 30 dias."
      />

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
          <b>Bruto</b> = soma dos pedidos pagos no período. <b>Líquido</b> = bruto − custo dos itens
          (campo “Custo” do produto). <b>Margem</b> = líquido ÷ bruto. Estornos e cancelamentos são
          contabilizados na data em que ocorreram.
        </p>
      </Card>

      {loading && (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
          {Array.from({ length: 7 }).map((_, i) => (
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
            {cards.map((card) => (
              <Card key={card.label} variant="elevated" className="flex flex-col gap-1">
                <span className="text-xs text-text-muted sm:text-sm">{card.label}</span>
                <span className="text-xl font-semibold sm:text-2xl">{card.value}</span>
              </Card>
            ))}
          </div>

          <Card variant="outline" className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">
                {METRIC_OPTS.find((m) => m.value === metric)?.label} — evolução no período
              </h2>
              <Select
                label=""
                value={metric}
                options={METRIC_OPTS}
                onChange={(e) => setMetric(e.target.value as SeriesMetric)}
              />
            </div>
            <SeriesChart current={seriesCurrent} previous={[]} fmt={fmtMetric} />
          </Card>
        </>
      )}
    </div>
  );
}
