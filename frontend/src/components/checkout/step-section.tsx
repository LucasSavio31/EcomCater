'use client';

import type { ReactNode } from 'react';
import { Card } from '@ecom/ui';

type State = 'active' | 'done' | 'locked';

/**
 * Bloco de etapa do checkout (padrão smart checkout):
 *  - `active`: expandido, com os campos
 *  - `done`: recolhido, mostra um resumo + "Alterar"
 *  - `locked`: desabilitado, mostra a instrução do que falta
 */
export function StepSection({
  number,
  title,
  state,
  summary,
  lockedHint,
  onEdit,
  children,
}: {
  number: number;
  title: string;
  state: State;
  summary?: ReactNode;
  lockedHint?: string;
  onEdit?: () => void;
  children: ReactNode;
}) {
  return (
    <Card
      variant="outline"
      className={`flex flex-col gap-3 ${state === 'locked' ? 'opacity-60' : ''}`}
    >
      <div className="flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-base font-semibold">
          <span
            className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
              state === 'done' ? 'bg-success text-white' : ''
            }`}
            style={
              state === 'done'
                ? undefined
                : { background: 'var(--color-step-active-bg)', color: 'var(--color-step-active-fg)' }
            }
          >
            {state === 'done' ? '✓' : number}
          </span>
          {title}
        </h2>
        {state === 'done' && onEdit && (
          <button type="button" onClick={onEdit} className="text-sm text-primary underline">
            Alterar
          </button>
        )}
      </div>

      {state === 'active' && children}

      {state === 'done' && summary && (
        <div className="text-sm text-text-muted">{summary}</div>
      )}

      {state === 'locked' && lockedHint && (
        <p className="text-sm text-text-muted">{lockedHint}</p>
      )}
    </Card>
  );
}
