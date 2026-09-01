'use client';

import { useId } from 'react';
import type { AbcPoint, SeriesPoint } from '@/modules/dashboard/api';

const W = 720;
const H = 240;
const PAD = { t: 18, r: 46, b: 28, l: 66 };

function niceMax(v: number): number {
  if (v <= 0) return 1;
  const mag = 10 ** Math.floor(Math.log10(v));
  const n = v / mag;
  const step = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return step * mag;
}

/* ------------------------------------------------------------------ série temporal */
export function SeriesChart({
  current,
  previous,
  fmt,
  labelCurrent = 'Período atual',
  labelPrevious = 'Período anterior',
}: {
  current: SeriesPoint[];
  previous: SeriesPoint[];
  fmt: (cents: number) => string;
  labelCurrent?: string;
  labelPrevious?: string;
}) {
  const gid = useId().replace(/[:]/g, '');
  const n = Math.max(current.length, previous.length, 2);
  const max = niceMax(
    Math.max(1, ...current.map((p) => p.cents), ...previous.map((p) => p.cents)),
  );
  const iw = W - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;
  const x = (i: number) => PAD.l + (n === 1 ? iw / 2 : (i / (n - 1)) * iw);
  const y = (c: number) => PAD.t + ih - (c / max) * ih;

  const line = (pts: SeriesPoint[]) =>
    pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(p.cents).toFixed(1)}`).join(' ');
  const area = (pts: SeriesPoint[]) =>
    `${line(pts)} L${x(pts.length - 1).toFixed(1)},${(PAD.t + ih).toFixed(1)} L${x(0).toFixed(1)},${(PAD.t + ih).toFixed(1)} Z`;

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * max);
  const everyN = Math.ceil(current.length / 8);

  return (
    <div className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Gráfico do período">
        <defs>
          <linearGradient id={`cur-${gid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2563eb" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#2563eb" stopOpacity="0.02" />
          </linearGradient>
          <linearGradient id={`prev-${gid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#94a3b8" stopOpacity="0.30" />
            <stop offset="100%" stopColor="#94a3b8" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={PAD.l} y1={y(t)} x2={W - PAD.r} y2={y(t)} stroke="#e5e7eb" strokeWidth={1} />
            <text x={PAD.l - 8} y={y(t) + 3} textAnchor="end" fontSize={10} fill="#6b7280">
              {fmt(t)}
            </text>
          </g>
        ))}

        {previous.length > 1 && (
          <>
            <path d={area(previous)} fill={`url(#prev-${gid})`} />
            <path d={line(previous)} fill="none" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="4 3" />
          </>
        )}
        {current.length > 1 && (
          <>
            <path d={area(current)} fill={`url(#cur-${gid})`} />
            <path d={line(current)} fill="none" stroke="#2563eb" strokeWidth={2} />
          </>
        )}

        {current.map((p, i) =>
          i % everyN === 0 || i === current.length - 1 ? (
            <text key={i} x={x(i)} y={H - 8} textAnchor="middle" fontSize={10} fill="#6b7280">
              {p.label}
            </text>
          ) : null,
        )}
      </svg>
      <div className="flex flex-wrap items-center gap-4 text-xs text-text-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-4 rounded-sm bg-[#2563eb]" /> {labelCurrent}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-4 rounded-sm bg-[#94a3b8]" /> {labelPrevious}
        </span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ curva ABC */
const ABC_COLOR: Record<AbcPoint['cls'], string> = { A: '#16a34a', B: '#d97706', C: '#94a3b8' };

export function AbcCurve({
  points,
  fmt,
}: {
  points: AbcPoint[];
  fmt: (cents: number) => string;
}) {
  if (points.length === 0) {
    return <p className="text-sm text-text-muted">Sem vendas no período para calcular a curva ABC.</p>;
  }
  const n = points.length;
  const max = niceMax(Math.max(1, ...points.map((p) => p.revenue_cents)));
  const iw = W - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;
  const bw = Math.max(2, (iw / n) * 0.7);
  const cx = (i: number) => PAD.l + (i + 0.5) * (iw / n);
  const yRev = (c: number) => PAD.t + ih - (c / max) * ih;
  const yPct = (p: number) => PAD.t + ih - (p / 100) * ih;
  const cumLine = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${cx(i).toFixed(1)},${yPct(p.cum_pct).toFixed(1)}`)
    .join(' ');
  const everyN = Math.ceil(n / 8);

  return (
    <div className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Curva ABC de produtos">
        {[0, 0.25, 0.5, 0.75, 1].map((f, i) => (
          <g key={i}>
            <line
              x1={PAD.l}
              y1={PAD.t + ih - f * ih}
              x2={W - PAD.r}
              y2={PAD.t + ih - f * ih}
              stroke="#e5e7eb"
              strokeWidth={1}
            />
            <text x={PAD.l - 8} y={PAD.t + ih - f * ih + 3} textAnchor="end" fontSize={10} fill="#6b7280">
              {fmt(f * max)}
            </text>
            <text x={W - PAD.r + 8} y={PAD.t + ih - f * ih + 3} fontSize={10} fill="#6b7280">
              {Math.round(f * 100)}%
            </text>
          </g>
        ))}

        {/* linha dos 80% (limite da classe A) */}
        <line
          x1={PAD.l}
          y1={yPct(80)}
          x2={W - PAD.r}
          y2={yPct(80)}
          stroke="#16a34a"
          strokeWidth={1}
          strokeDasharray="4 3"
        />

        {points.map((p, i) => {
          const yy = yRev(p.revenue_cents);
          return (
            <rect
              key={i}
              x={cx(i) - bw / 2}
              y={yy}
              width={bw}
              height={PAD.t + ih - yy}
              fill={ABC_COLOR[p.cls]}
              rx={1}
            >
              <title>{`${p.name}\n${fmt(p.revenue_cents)} · acumulado ${p.cum_pct}% · classe ${p.cls}`}</title>
            </rect>
          );
        })}

        <path d={cumLine} fill="none" stroke="#111827" strokeWidth={2} />
        {points.map((p, i) => (
          <circle key={i} cx={cx(i)} cy={yPct(p.cum_pct)} r={2.5} fill="#111827" />
        ))}

        {points.map((p, i) =>
          i % everyN === 0 || i === n - 1 ? (
            <text key={i} x={cx(i)} y={H - 8} textAnchor="middle" fontSize={9} fill="#6b7280">
              {p.name.length > 10 ? `${p.name.slice(0, 9)}…` : p.name}
            </text>
          ) : null,
        )}
      </svg>
      <div className="flex flex-wrap items-center gap-4 text-xs text-text-muted">
        {(['A', 'B', 'C'] as const).map((c) => (
          <span key={c} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: ABC_COLOR[c] }} />
            Classe {c} {c === 'A' ? '(até 80%)' : c === 'B' ? '(80–95%)' : '(95–100%)'}
          </span>
        ))}
      </div>
    </div>
  );
}
