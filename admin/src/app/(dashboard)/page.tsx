'use client';

import { useEffect, useState } from 'react';
import { Card, Spinner } from '@ecom/ui';
import { adminFetch } from '@/lib/admin-api-client';

interface DashboardData {
  orders_today: number;
  orders_pending: number;
  revenue_month_cents: number;
  low_stock_count: number;
  recent_orders: Array<Record<string, unknown>>;
}

function formatBRL(cents: number): string {
  return (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void (async () => {
      const result = await adminFetch<DashboardData>('/api/admin/dashboard');
      if (!active) return;
      if (result.ok) setData(result.data);
      else setError(result.error.message);
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, []);

  const cards: Array<{ label: string; value: string }> = data
    ? [
        { label: 'Pedidos hoje', value: String(data.orders_today) },
        { label: 'Pedidos pendentes', value: String(data.orders_pending) },
        { label: 'Faturamento do mês', value: formatBRL(data.revenue_month_cents) },
        { label: 'Estoque baixo', value: String(data.low_stock_count) },
      ]
    : [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-text-muted">
          Placeholder da fundação — os números vêm de <code>GET /api/admin/dashboard</code>.
        </p>
      </div>

      {loading && (
        <div className="flex justify-center py-12">
          <Spinner size="lg" label="Carregando indicadores…" />
        </div>
      )}

      {error && (
        <Card variant="outline" className="border-danger">
          <p className="text-sm text-danger">Falha ao carregar: {error}</p>
        </Card>
      )}

      {data && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {cards.map((card) => (
            <Card key={card.label} variant="elevated" className="flex flex-col gap-1">
              <span className="text-sm text-text-muted">{card.label}</span>
              <span className="text-2xl font-semibold">{card.value}</span>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
