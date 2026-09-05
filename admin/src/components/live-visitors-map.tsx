'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Card } from '@ecom/ui';
import { presenceApi, type LiveVisitor, type LiveVisitorsData } from '@/modules/presence/api';
import { BRAZIL_STATES, BRAZIL_VIEWBOX } from './brazil-states';

const POLL_MS = 5_000;

// Nome (como o serviço de geoip devolve, sem acento/minúsculo) -> sigla do estado.
const STATE_NAME_TO_UF: Record<string, string> = {
  acre: 'ac',
  alagoas: 'al',
  amapa: 'ap',
  amazonas: 'am',
  bahia: 'ba',
  ceara: 'ce',
  'distrito federal': 'df',
  'espirito santo': 'es',
  goias: 'go',
  maranhao: 'ma',
  'mato grosso': 'mt',
  'mato grosso do sul': 'ms',
  'minas gerais': 'mg',
  para: 'pa',
  paraiba: 'pb',
  parana: 'pr',
  pernambuco: 'pe',
  piaui: 'pi',
  'rio de janeiro': 'rj',
  'rio grande do norte': 'rn',
  'rio grande do sul': 'rs',
  rondonia: 'ro',
  roraima: 'rr',
  'santa catarina': 'sc',
  'sao paulo': 'sp',
  sergipe: 'se',
  tocantins: 'to',
};

function normalize(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();
}

function ufFor(region: string | null): string | null {
  if (!region) return null;
  return STATE_NAME_TO_UF[normalize(region)] ?? null;
}

// Espalha visitantes do mesmo estado ao redor do centroide, sem sobrepor
// perfeitamente (determinístico — não "pula" a cada poll).
function jitter(seed: number): { dx: number; dy: number } {
  const a = (seed * 12.9898) % 1;
  const b = (seed * 78.233) % 1;
  const r = 2200;
  return { dx: (a - 0.5) * r, dy: (b - 0.5) * r };
}

function fmtAgo(seconds: number): string {
  if (seconds < 60) return `há ${seconds}s`;
  const m = Math.floor(seconds / 60);
  return `há ${m} min`;
}

function deviceIcon(device: string | null): string {
  switch (device) {
    case 'iPhone':
    case 'Android':
      return '📱';
    case 'iPad':
      return '📱';
    case 'Mac':
    case 'PC':
    case 'Linux':
      return '💻';
    default:
      return '🖥️';
  }
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

  const dots = useMemo(() => {
    if (!data) return [];
    return data.visitors
      .map((v: LiveVisitor, i: number) => {
        const uf = ufFor(v.region);
        if (!uf) return null;
        const geo = BRAZIL_STATES[uf];
        if (!geo) return null;
        const { dx, dy } = jitter(i + 1);
        return { key: i, x: geo.cx + dx, y: geo.cy + dy };
      })
      .filter((d): d is { key: number; x: number; y: number } => d !== null);
  }, [data]);

  if (hidden || !data) return null;

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
          <svg viewBox={BRAZIL_VIEWBOX} className="w-full" role="img" aria-label="Mapa de visitantes ao vivo por estado">
            <style>{`
              @keyframes presence-ping {
                0% { transform: scale(1); opacity: 0.6; }
                100% { transform: scale(2.8); opacity: 0; }
              }
              .presence-ring { transform-box: fill-box; transform-origin: center; animation: presence-ping 1.8s ease-out infinite; }
            `}</style>
            {Object.entries(BRAZIL_STATES).map(([uf, s]) => (
              <path key={uf} d={s.d} fill="#173d6b" stroke="#0b2545" strokeWidth={400} />
            ))}
            {dots.map((d) => (
              <g key={d.key}>
                <circle cx={d.x} cy={d.y} r={2600} fill="#38bdf8" className="presence-ring" />
                <circle cx={d.x} cy={d.y} r={1500} fill="#e0f2fe" />
              </g>
            ))}
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
                <span className="flex items-center gap-1 truncate text-xs text-text-muted">
                  <span aria-hidden>{deviceIcon(v.device)}</span>
                  {v.device || 'Dispositivo desconhecido'}
                  {v.ip ? ` · ${v.ip}` : ''}
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
