'use client';

import { useState } from 'react';

interface SizeChartData {
  name: string;
  columns: string[];
  rows: string[][];
  note: string | null;
}

/** Link "Tabela de medidas" + popup com a tabela do produto. */
export function SizeChartButton({ chart }: { chart: SizeChartData }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-primary underline"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4">
          <path d="M4 15 15 4l5 5L9 20z" />
          <path d="M8 11l2 2M11 8l2 2M14 5l2 2" strokeLinecap="round" />
        </svg>
        Tabela de medidas
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-label={chart.name}
          onClick={() => setOpen(false)}
        >
          <div
            className="max-h-[85vh] w-full max-w-lg overflow-auto rounded-card bg-surface p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-start justify-between gap-4">
              <h2 className="text-lg font-semibold">{chart.name || 'Tabela de medidas'}</h2>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Fechar"
                className="text-2xl leading-none text-text-muted hover:text-text"
              >
                &times;
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[320px] border-collapse text-sm">
                <thead>
                  <tr>
                    {chart.columns.map((c, i) => (
                      <th
                        key={i}
                        className="border border-surface-border bg-bg-subtle px-3 py-2 text-left font-semibold"
                      >
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {chart.rows.map((r, ri) => (
                    <tr key={ri}>
                      {r.map((cell, ci) => (
                        <td key={ci} className="border border-surface-border px-3 py-2">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {chart.note && <p className="mt-3 text-xs text-text-muted">{chart.note}</p>}
          </div>
        </div>
      )}
    </>
  );
}
