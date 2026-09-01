'use client';

import type { ReactNode } from 'react';
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
}

/**
 * Tabela responsiva: vira lista de cards no mobile (< sm) e tabela no desktop.
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
}: DataTableProps<T>) {
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

  return (
    <>
      {/* Mobile: cards */}
      <ul className="flex flex-col gap-3 sm:hidden">
        {rows.map((row) => (
          <li key={rowKey(row)}>
            <Card
              variant="outline"
              className={cn('flex flex-col gap-2', onRowClick && 'cursor-pointer hover:bg-bg-subtle')}
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
                  <span className={cn('text-sm', col.primary && 'font-semibold')}>{col.cell(row)}</span>
                </div>
              ))}
              {rowActions && <div className="flex flex-wrap gap-2 pt-1">{rowActions(row)}</div>}
            </Card>
          </li>
        ))}
      </ul>

      {/* Desktop: tabela */}
      <div className="hidden overflow-x-auto rounded-card border border-surface-border sm:block">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-surface-border bg-bg-subtle text-left">
              {columns.map((col) => (
                <th key={col.key} className={cn('px-3 py-2 font-medium text-text-muted', col.className)}>
                  {col.header}
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
                  'border-b border-surface-border last:border-0',
                  onRowClick && 'cursor-pointer hover:bg-bg-subtle',
                )}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn('px-3 py-2 align-middle', col.className)}
                    onClick={col.stopRowClick ? (e) => e.stopPropagation() : undefined}
                  >
                    {col.cell(row)}
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
