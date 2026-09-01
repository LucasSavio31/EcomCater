'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { Button } from '@ecom/ui';

/**
 * Filtro de datas padrão do painel — De / Até + botão "Filtrar".
 * Só aplica quando o botão é clicado (nada de refazer a busca a cada tecla).
 * Use o mesmo componente em toda tela que filtra por período.
 */
export function DateRangeFilter({
  from,
  to,
  onApply,
  onClear,
  extra,
  className = '',
}: {
  from: string;
  to: string;
  onApply: (from: string, to: string) => void;
  onClear: () => void;
  extra?: ReactNode;
  className?: string;
}) {
  const [f, setF] = useState(from);
  const [t, setT] = useState(to);

  // mantém os campos em sincronia quando o período muda por fora (ex.: card do dashboard)
  useEffect(() => setF(from), [from]);
  useEffect(() => setT(to), [to]);

  const dirty = f !== from || t !== to;

  return (
    <form
      className={`flex flex-wrap items-end gap-3 ${className}`}
      onSubmit={(e) => {
        e.preventDefault();
        onApply(f, t);
      }}
    >
      <label className="flex flex-col gap-1 text-sm font-medium text-text">
        De
        <input
          type="date"
          value={f}
          max={t || undefined}
          onChange={(e) => setF(e.target.value)}
          className="min-h-touch rounded-card border border-surface-border bg-surface px-3 text-sm"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium text-text">
        Até
        <input
          type="date"
          value={t}
          min={f || undefined}
          onChange={(e) => setT(e.target.value)}
          className="min-h-touch rounded-card border border-surface-border bg-surface px-3 text-sm"
        />
      </label>
      <Button type="submit" variant={dirty ? 'primary' : 'outline'}>
        Filtrar
      </Button>
      {(from || to || f || t) && (
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            setF('');
            setT('');
            onClear();
          }}
        >
          Limpar
        </Button>
      )}
      {extra}
    </form>
  );
}

/** Opções padrão do seletor "itens por página": 10 (padrão), 20, 50, 100. */
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;
export const DEFAULT_PAGE_SIZE = 10;

export function PageSizeSelect({
  value,
  onChange,
  className = '',
}: {
  value: number;
  onChange: (n: number) => void;
  className?: string;
}) {
  return (
    <label className={`flex items-center gap-2 text-sm text-text-muted ${className}`}>
      Itens por página
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="min-h-touch rounded-card border border-surface-border bg-surface px-2 text-sm text-text"
      >
        {PAGE_SIZE_OPTIONS.map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    </label>
  );
}
