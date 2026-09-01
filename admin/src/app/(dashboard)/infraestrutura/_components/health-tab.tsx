'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Card } from '@ecom/ui';
import { useToast } from '@/components/toast';
import {
  systemApi,
  type HealthHistoryEntry,
  type HealthSample,
  type HealthService,
  type HealthStatus,
} from '@/modules/system/api';

/** A tela recarrega sozinha a cada 15 min — cada barra é uma janela de 15 min. */
const REFRESH_MS = 15 * 60 * 1000;
/** Um dia inteiro = 96 janelas de 15 min (00:00 … 23:45). */
const SLOTS_PER_DAY = 96;

const DOT: Record<HealthStatus, string> = {
  ok: 'bg-success',
  degraded: 'bg-warning',
  down: 'bg-danger',
};
const LABEL: Record<HealthStatus, string> = {
  ok: 'Operacional',
  degraded: 'Instável',
  down: 'Fora do ar',
};
const RANK: Record<HealthStatus, number> = { ok: 0, degraded: 1, down: 2 };

function dayISO(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dd}`;
}

function fmtDay(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  const s = d.toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function worstOf(list: { status: HealthStatus }[]): HealthStatus {
  if (list.some((s) => s.status === 'down')) return 'down';
  if (list.some((s) => s.status === 'degraded')) return 'degraded';
  return 'ok';
}

/** Índice da janela de 15 min (0..95) de um horário, no fuso local. */
function slotOf(date: Date): number {
  return date.getHours() * 4 + Math.floor(date.getMinutes() / 15);
}

/** Barra de um dia inteiro: 96 janelas fixas (00:00 → 23:45). Sem leitura = vão
 *  apagado; no dia de hoje, as janelas ainda no futuro ficam vazias. */
function DayBars({
  samples,
  isToday,
}: {
  samples: HealthSample[];
  isToday: boolean;
}) {
  const bySlot = useMemo(() => {
    const m = new Map<number, HealthSample>();
    for (const s of samples) {
      const i = slotOf(new Date(s.at));
      const cur = m.get(i);
      if (!cur || RANK[s.status] > RANK[cur.status]) m.set(i, s);
    }
    return m;
  }, [samples]);
  const nowSlot = isToday ? slotOf(new Date()) : SLOTS_PER_DAY;

  return (
    <div className="flex flex-col gap-1">
      {/* dia inteiro em uma faixa que ocupa toda a largura do card */}
      <div className="flex items-end gap-px">
        {Array.from({ length: SLOTS_PER_DAY }).map((_, i) => {
          const s = bySlot.get(i);
          const hh = String(Math.floor(i / 4)).padStart(2, '0');
          const mm = String((i % 4) * 15).padStart(2, '0');
          const future = isToday && i > nowSlot;
          const cls = s
            ? `${DOT[s.status]} h-6`
            : future
              ? 'bg-surface-border/25 h-3'
              : 'bg-surface-border h-3';
          return (
            <span
              key={i}
              title={
                s
                  ? `${LABEL[s.status]} · ${s.latency_ms} ms · ${hh}:${mm}`
                  : `${hh}:${mm} — ${future ? 'ainda não' : 'sem leitura'}`
              }
              className={`min-w-0 flex-1 rounded-[1px] ${cls}`}
            />
          );
        })}
      </div>
      <div className="flex justify-between text-[10px] leading-none text-text-muted">
        {['00h', '06h', '12h', '18h', '24h'].map((t) => (
          <span key={t}>{t}</span>
        ))}
      </div>
    </div>
  );
}

interface Row {
  key: string;
  label: string;
  status: HealthStatus;
  statusText: string;
  meta: string;
  detail: string;
  samples: HealthSample[];
}

export function HealthTab() {
  const toast = useToast();
  const [offset, setOffset] = useState(0); // 0 = hoje, -1 = ontem, ...
  const [live, setLive] = useState<HealthService[] | null>(null);
  const [dayHist, setDayHist] = useState<HealthHistoryEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const iso = dayISO(offset);
  const isToday = offset === 0;

  const refresh = useCallback(async () => {
    setLoading(true);
    const day = dayISO(offset);
    const [histRes, liveRes] = await Promise.all([
      systemApi.healthHistory(day, day),
      offset === 0 ? systemApi.health() : Promise.resolve(null),
    ]);
    setLoading(false);
    if (histRes.ok) {
      setDayHist(histRes.data);
      setError(null);
    } else {
      setError(histRes.error.message);
      toast.error(histRes.error.message);
    }
    if (liveRes && liveRes.ok) setLive(liveRes.data);
    if (!liveRes) setLive(null);
    setUpdatedAt(new Date());
  }, [offset, toast]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // atualização em tempo real: recarrega a visão atual a cada 15 min
  useEffect(() => {
    timer.current = setInterval(() => void refresh(), REFRESH_MS);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [refresh]);

  const rows: Row[] = useMemo(() => {
    const liveArr = live ?? [];
    const hist = dayHist ?? [];
    const liveByKey = new Map(liveArr.map((s) => [s.key, s]));
    // ordem: os checks ao vivo primeiro (ordem canônica); depois chaves que só
    // existem no histórico do dia (ex.: containers que já não rodam).
    const keys: string[] = [];
    const seen = new Set<string>();
    for (const k of [...liveArr.map((s) => s.key), ...hist.map((h) => h.key)]) {
      if (!seen.has(k)) {
        seen.add(k);
        keys.push(k);
      }
    }

    return keys.map((key) => {
      const h = hist.find((x) => x.key === key);
      const l = liveByKey.get(key);
      const samples = h?.samples ?? [];
      if (isToday && l) {
        return {
          key,
          label: l.label,
          status: l.status,
          statusText: LABEL[l.status],
          meta: `${l.latency_ms > 0 ? `${l.latency_ms} ms · ` : ''}${
            h ? `${h.uptime_pct}% ok no dia` : `${l.uptime_pct}% ok`
          }`,
          detail: l.detail,
          samples,
        };
      }
      const status = worstOf(samples.length ? samples : [{ status: 'ok' as HealthStatus }]);
      const parts = [`${h?.count ?? 0} leituras`, `${h?.uptime_pct ?? 100}% ok`];
      if (h && h.incidents > 0) parts.push(`${h.incidents} fora do ar`);
      return {
        key,
        label: h?.label ?? key,
        status,
        statusText: samples.length ? LABEL[status] : 'Sem leitura',
        meta: `${h && h.avg_latency_ms > 0 ? `~${h.avg_latency_ms} ms · ` : ''}${parts.join(' · ')}`,
        detail: samples.at(-1)?.detail ?? '',
        samples,
      };
    });
  }, [isToday, live, dayHist]);

  const worst = worstOf(rows.length ? rows : [{ status: 'ok' }]);
  const hasData = rows.length > 0;

  return (
    <Card variant="outline" className="flex flex-col gap-4">
      {/* cabeçalho: status geral + atualização */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={`h-3 w-3 rounded-full ${DOT[worst]}`} />
          <h2 className="text-base font-semibold">
            {!hasData
              ? 'Sem leituras neste dia'
              : worst === 'ok'
                ? isToday
                  ? 'Todos os serviços operacionais'
                  : 'Dia sem incidentes'
                : worst === 'degraded'
                  ? 'Alguns serviços instáveis'
                  : 'Há serviço fora do ar'}
          </h2>
        </div>
        <div className="flex items-center gap-3 text-xs text-text-muted">
          {updatedAt && <span>Atualizado {updatedAt.toLocaleTimeString('pt-BR')}</span>}
          <Button size="sm" variant="ghost" loading={loading} onClick={() => void refresh()}>
            Atualizar agora
          </Button>
        </div>
      </div>

      {/* navegação por dia — setas frente/trás pelo calendário */}
      <div className="flex items-center justify-between gap-2 rounded-card border border-surface-border px-3 py-2">
        <Button
          size="sm"
          variant="ghost"
          aria-label="Dia anterior"
          onClick={() => setOffset((o) => o - 1)}
        >
          ‹
        </Button>
        <div className="flex items-center gap-2 text-sm">
          <span className="font-medium">{fmtDay(iso)}</span>
          {isToday ? (
            <span className="rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success">
              hoje · em andamento
            </span>
          ) : (
            <button
              type="button"
              onClick={() => setOffset(0)}
              className="rounded-full border border-surface-border px-2 py-0.5 text-xs hover:border-primary"
            >
              Ir para hoje
            </button>
          )}
        </div>
        <Button
          size="sm"
          variant="ghost"
          aria-label="Próximo dia"
          disabled={offset >= 0}
          onClick={() => setOffset((o) => Math.min(0, o + 1))}
        >
          ›
        </Button>
      </div>

      <div className="flex flex-col gap-1 text-xs text-text-muted">
        <p>
          Cada linha de barras é um dia inteiro (00:00 → 23:45), uma barra a cada 15 min. Barra
          apagada = sem leitura naquela janela; no dia de hoje as janelas ainda por vir ficam
          vazias. A tela recarrega sozinha a cada 15 min; use as setas para ver outros dias.
        </p>
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="inline-flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-sm bg-success" /> OK
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-sm bg-warning" /> instável
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-sm bg-danger" /> fora do ar
          </span>
          <span>— 3 leituras instáveis seguidas viram “fora do ar”; volta ao normal com uma leitura OK.</span>
        </p>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}
      {!error && !hasData && !loading && (
        <p className="text-sm text-text-muted">Nenhuma leitura registrada neste dia.</p>
      )}

      <div className="flex flex-col divide-y divide-surface-border">
        {rows.map((r) => (
          <div key={r.key} className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className={`h-2.5 w-2.5 rounded-full ${DOT[r.status]}`} />
                <span className="font-medium">{r.label}</span>
                <span className="text-xs text-text-muted">{r.statusText}</span>
              </div>
              <span className="text-xs text-text-muted">{r.meta}</span>
            </div>
            <DayBars samples={r.samples} isToday={isToday} />
            {r.detail && <p className="text-xs text-text-muted">{r.detail}</p>}
          </div>
        ))}
      </div>
    </Card>
  );
}
