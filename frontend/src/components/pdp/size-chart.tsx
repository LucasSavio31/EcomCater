'use client';

import { useEffect, useState } from 'react';

export interface SizeChartData {
  name: string;
  columns: string[];
  rows: string[][];
  note: string | null;
}

export interface SizeChartColors {
  bg: string;
  headerBg: string;
  headerText: string;
  text: string;
}

const DEFAULT_COLORS: SizeChartColors = {
  bg: '#FFFFFF',
  headerBg: '#FFC400',
  headerText: '#111111',
  text: '#374151',
};

/** Gatilho "Tabela de medidas" + popup CENTRALIZADO (só aparece se houver tabela). */
export function SizeChartButton({
  chart,
  colors = DEFAULT_COLORS,
  className,
}: {
  chart: SizeChartData;
  colors?: SizeChartColors;
  className?: string;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          className ??
          'text-xs font-normal normal-case text-primary underline hover:no-underline'
        }
      >
        Tabela de medidas
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
        >
          <button
            type="button"
            aria-label="Fechar"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-black/50"
          />
          <div
            className="relative flex max-h-[85vh] w-full max-w-sm flex-col overflow-hidden rounded-lg shadow-2xl"
            style={{ backgroundColor: colors.bg, color: colors.text }}
          >
            {/* barra escura com FECHAR */}
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="flex shrink-0 items-center justify-end gap-2 bg-black px-4 py-2.5 text-xs font-semibold uppercase tracking-widest text-white"
            >
              Fechar
              <span aria-hidden className="text-lg leading-none">
                &times;
              </span>
            </button>

            {/* faixa de cabeçalho com título */}
            <div
              className="shrink-0 px-6 py-5 text-center"
              style={{ backgroundColor: colors.headerBg, color: colors.headerText }}
            >
              <h2 className="text-base font-extrabold uppercase tracking-[0.3em]">
                Tabela de medidas
              </h2>
              {chart.name && <p className="mt-1 text-sm font-medium opacity-80">{chart.name}</p>}
            </div>

            {/* tabela (rola aqui dentro se for grande) */}
            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-black/10 text-[10px] uppercase tracking-[0.25em] opacity-60">
                    {chart.columns.map((c, i) => (
                      <th key={i} className="py-2.5 text-left font-semibold">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {chart.rows.map((r, ri) => (
                    <tr key={ri} className="border-b border-dashed border-black/10">
                      {r.map((cell, ci) => (
                        <td key={ci} className="py-3.5">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {chart.note && <p className="mt-4 text-xs opacity-60">{chart.note}</p>}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
