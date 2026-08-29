import type { ReactNode } from 'react';
import { Card } from '@ecom/ui';

export interface UnderConstructionProps {
  title: string;
  /** Fase do plano de execução em que a tela é implementada. */
  phase?: string;
  children?: ReactNode;
}

/** Placeholder tipado para rotas ainda não implementadas (Fase 1). */
export function UnderConstruction({ title, phase, children }: UnderConstructionProps) {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">{title}</h1>
      <Card variant="outline" className="flex flex-col gap-2">
        <p className="font-medium">Em construção</p>
        <p className="text-sm text-text-muted">
          Esta rota é um stub da fundação (Fase 1).
          {phase ? ` Implementação prevista para a ${phase}.` : ''}
        </p>
        {children}
      </Card>
    </div>
  );
}
