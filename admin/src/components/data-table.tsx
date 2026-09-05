'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Card, Spinner, cn } from '@ecom/ui';

export interface Column<T> {
  key: string;
  header: ReactNode;
  /** Conteúdo da célula. */
  cell: (row: T) => ReactNode;
  /** Esconde a coluna no cabeçalho da tabela desktop (ainda aparece no card mobile). */
  className?: string;
  /** Rótulo curto usado no card mobile (default = header se for string). */
  mobileLabel?: string;
  /** Não renderiza rótulo no card mobile (para a coluna "principal"). */
  primary?: boolean;
  /** Coluna com controle clicável (checkbox etc.) — a área da célula vira uma
   * "zona de segurança" que nunca deixa o clique vazar pro `onRowClick` da
   * linha/card, mesmo que o toque caia perto do controle e não exatamente nele. */
  stopRowClick?: boolean;
}

interface DataTableProps<T> {
  columns: Array<Column<T>>;
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  /** Ações renderizadas por linha (aparecem à direita no desktop, no rodapé do card no mobile). */
  rowActions?: (row: T) => ReactNode;
  /** Chave única da tabela — quando informada, a largura das colunas ajustada
   * pelo usuário (arrastando a divisória, estilo Excel) é lembrada entre
   * visitas (localStorage). Sem isso, o ajuste ainda funciona, só não persiste. */
  tableId?: string;
}

const MIN_COL_WIDTH = 60;

function loadWidths(tableId?: string): Record<string, number> {
  if (!tableId) return {};
  try {
    const raw = localStorage.getItem(`admin:col-widths:${tableId}`);
    return raw ? (JSON.parse(raw) as Record<string, number>) : {};
  } catch {
    return {};
  }
}

function saveWidths(tableId: string | undefined, widths: Record<string, number>): void {
  if (!tableId) return;
  try {
    localStorage.setItem(`admin:col-widths:${tableId}`, JSON.stringify(widths));
  } catch {
    /* privado/bloqueado: só não persiste */
  }
}

/**
 * Tabela responsiva: vira lista de cards no mobile (< sm) e tabela no desktop.
 * No desktop, a divisória entre colunas pode ser arrastada pra redimensionar
 * (estilo planilha) — segura o mouse na beirada direita do cabeçalho.
 * Estados de carregando / erro / vazio embutidos.
 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  error = null,
  emptyMessage = 'Nada por aqui ainda.',
  onRowClick,
  rowActions,
  tableId,
}: DataTableProps<T>) {
  const [widths, setWidths] = useState<Record<string, number>>({});
  const [resizingKey, setResizingKey] = useState<string | null>(null);
  const drag = useRef<{ key: string; startX: number; startWidth: number } | null>(null);

  useEffect(() => {
    setWidths(loadWidths(tableId));
  }, [tableId]);

  function startResize(key: string, thEl: HTMLElement, clientX: number) {
    const startWidth = widths[key] ?? thEl.getBoundingClientRect().width;
    drag.current = { key, startX: clientX, startWidth };
    setResizingKey(key);

    const onMove = (ev: MouseEvent) => {
      if (!drag.current) return;
      const w = Math.max(MIN_COL_WIDTH, Math.round(drag.current.startWidth + (ev.clientX - drag.current.startX)));
      setWidths((prev) => ({ ...prev, [drag.current!.key]: w }));
    };
    const onUp = () => {
      drag.current = null;
      setResizingKey(null);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      setWidths((prev) => {
        saveWidths(tableId, prev);
        return prev;
      });
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" label="Carregando…" />
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="outline" className="border-danger">
        <p className="text-sm text-danger">{error}</p>
      </Card>
    );
  }

  if (rows.length === 0) {
    return (
      <Card variant="outline" className="text-center text-sm text-text-muted">
        {emptyMessage}
      </Card>
    );
  }

  const hasCustomWidths = Object.keys(widths).length > 0;

  return (
    <>
      {/* Mobile: cards */}
      <ul className="flex flex-col gap-3 sm:hidden">
        {rows.map((row) => (
          <li key={rowKey(row)}>
            <Card
              variant="outline"
              className={cn(
                'group flex flex-col gap-2',
                onRowClick && 'cursor-pointer hover:bg-bg-subtle',
              )}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((col) => (
                <div
                  key={col.key}
                  className={cn('flex flex-col gap-0.5', col.stopRowClick && '-m-2 p-2')}
                  onClick={col.stopRowClick ? (e) => e.stopPropagation() : undefined}
                >
                  {!col.primary && (
                    <span className="text-xs font-medium uppercase tracking-wide text-text-muted">
                      {col.mobileLabel ?? (typeof col.header === 'string' ? col.header : '')}
                    </span>
                  )}
                  <span
                    className={cn(
                      'text-sm',
                      col.primary && 'font-semibold',
                      col.primary && onRowClick && 'group-hover:underline',
                    )}
                  >
                    {col.cell(row)}
                  </span>
                </div>
              ))}
              {rowActions && <div className="flex flex-wrap gap-2 pt-1">{rowActions(row)}</div>}
            </Card>
          </li>
        ))}
      </ul>

      {/* Desktop: tabela */}
      <div className="hidden overflow-x-auto rounded-card border border-surface-border sm:block">
        <table
          className={cn('border-collapse text-sm', !hasCustomWidths && 'w-full')}
          style={hasCustomWidths ? { tableLayout: 'fixed', width: 'max-content', minWidth: '100%' } : undefined}
        >
          {hasCustomWidths && (
            <colgroup>
              {columns.map((col) => (
                <col key={col.key} style={widths[col.key] ? { width: widths[col.key] } : undefined} />
              ))}
              {rowActions && <col />}
            </colgroup>
          )}
          <thead>
            <tr className="border-b border-surface-border bg-bg-subtle text-left">
              {columns.map((col, i) => (
                <th
                  key={col.key}
                  className={cn(
                    'relative px-3 py-2 font-medium text-text-muted',
                    col.className,
                  )}
                >
                  <span className="block truncate">{col.header}</span>
                  {i < columns.length - 1 + (rowActions ? 1 : 0) && (
                    <span
                      role="separator"
                      aria-orientation="vertical"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        startResize(col.key, e.currentTarget.parentElement as HTMLElement, e.clientX);
                      }}
                      className={cn(
                        'absolute -right-1 top-0 z-10 h-full w-2 cursor-col-resize select-none',
                        'hover:bg-primary/40',
                        resizingKey === col.key && 'bg-primary/60',
                      )}
                    />
                  )}
                </th>
              ))}
              {rowActions && <th className="px-3 py-2" />}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={rowKey(row)}
                className={cn(
                  'group border-b border-surface-border last:border-0',
                  onRowClick && 'cursor-pointer hover:bg-bg-subtle',
                )}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn('overflow-hidden px-3 py-2 align-middle', col.className)}
                    onClick={col.stopRowClick ? (e) => e.stopPropagation() : undefined}
                  >
                    {col.primary && onRowClick ? (
                      <span className="group-hover:underline">{col.cell(row)}</span>
                    ) : (
                      col.cell(row)
                    )}
                  </td>
                ))}
                {rowActions && (
                  <td className="px-3 py-2 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex justify-end gap-2">{rowActions(row)}</div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
