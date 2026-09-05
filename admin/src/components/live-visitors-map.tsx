'use client';

import { useEffect, useRef, useState } from 'react';
import { Card } from '@ecom/ui';
import { presenceApi, type LiveVisitorsData } from '@/modules/presence/api';

const POLL_MS = 5_000;
const W = 1000;
const H = 500;

// Elipses estilizadas (fidelidade "ambiente", não cartográfica) — mesmo
// espírito 100%-sem-lib do resto do dashboard (dashboard-charts.tsx).
const CONTINENTS = [
  { cx: 260, cy: 165, rx: 150, ry: 95 }, // América do Norte
  { cx: 300, cy: 260, rx: 35, ry: 30 }, // América Central
  { cx: 330, cy: 350, rx: 75, ry: 110 }, // América do Sul
  { cx: 500, cy: 195, rx: 60, ry: 50 }, // Europa
  { cx: 530, cy: 300, rx: 90, ry: 125 }, // África
  { cx: 700, cy: 190, rx: 200, ry: 105 }, // Ásia
  { cx: 760, cy: 320, rx: 45, ry: 30 }, // Sudeste asiático
  { cx: 850, cy: 380, rx: 60, ry: 40 }, // Oceania
];

function project(lon: number, lat: number): { x: number; y: number } {
  return { x: ((lon + 180) / 360) * W, y: ((90 - lat) / 180) * H };
}

function fmtAgo(seconds: number): string {
  if (seconds < 60) return `há ${seconds}s`;
  const m = Math.floor(seconds / 60);
  return `há ${m} min`;
}

export function LiveVisitorsMap() {
  const [data, setData] = useState<LiveVisitorsData | null>(null);
  const [hidden, setHidden] = useState(false);
  const loaded = useRef(false);

  useEffect(() => {
    let alive = true;
    const tick = async (): Promise<void> => {
      if (document.visibilityState !== 'visible' && loaded.current) return;
      const res = await presenceApi.live();
      if (!alive) return;
      if (!res.ok) {
        if (res.error.code === 'module_disabled') setHidden(true);
        return;
      }
      loaded.current = true;
      setData(res.data);
    };
    void tick();
    const id = window.setInterval(() => void tick(), POLL_MS);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  if (hidden || !data) return null;

  const dots = data.visitors.filter((v) => v.lat != null && v.lon != null);

  return (
    <Card variant="outline" className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Visitantes ao vivo</h2>
        <span className="flex items-center gap-2 text-sm font-medium text-text-muted">
          <span className="h-2 w-2 rounded-full bg-success" />
          {data.total} agora
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="overflow-hidden rounded-card lg:col-span-2" style={{ background: '#0b2545' }}>
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Mapa de visitantes ao vivo">
            <style>{`
              @keyframes presence-ping {
                0% { transform: scale(1); opacity: 0.6; }
                100% { transform: scale(2.8); opacity: 0; }
              }
              .presence-ring { transform-box: fill-box; transform-origin: center; animation: presence-ping 1.8s ease-out infinite; }
            `}</style>
            {CONTINENTS.map((c, i) => (
              <ellipse key={i} cx={c.cx} cy={c.cy} rx={c.rx} ry={c.ry} fill="#173d6b" />
            ))}
            {dots.map((v, i) => {
              const { x, y } = project(v.lon as number, v.lat as number);
              return (
                <g key={i}>
                  <circle cx={x} cy={y} r={5} fill="#38bdf8" className="presence-ring" />
                  <circle cx={x} cy={y} r={3} fill="#e0f2fe" />
                </g>
              );
            })}
          </svg>
        </div>

        <div className="flex max-h-72 flex-col gap-2 overflow-y-auto">
          {data.visitors.length === 0 ? (
            <p className="text-sm text-text-muted">Ninguém navegando agora.</p>
          ) : (
            data.visitors.map((v, i) => (
              <div key={i} className="flex flex-col gap-0.5 rounded-card border border-surface-border px-3 py-2 text-sm">
                <span className="flex items-center gap-1.5 font-medium">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-success" />
                  {v.city ? `${v.city}, ` : ''}
                  {v.region || v.country || 'Local desconhecido'}
                </span>
                <span className="truncate text-xs text-text-muted">
                  {v.page_label} · {fmtAgo(v.since_seconds)}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {data.top_states.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-text-muted">Top 10 estados</h3>
          <ol className="flex flex-col divide-y divide-surface-border">
            {data.top_states.map((s, i) => (
              <li key={s.region} className="flex items-center gap-3 py-1.5 first:pt-0 last:pb-0 text-sm">
                <span className="w-5 shrink-0 text-right text-text-muted">{i + 1}</span>
                <span className="min-w-0 flex-1 truncate">{s.region}</span>
                <span className="font-semibold">{s.count}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </Card>
  );
}
