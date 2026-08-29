import { Card } from '@ecom/ui';

export function AdminStub({ title, phase }: { title: string; phase?: string }) {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">{title}</h1>
      <Card variant="outline" className="flex flex-col gap-1">
        <p className="font-medium">Em construção</p>
        <p className="text-sm text-text-muted">
          Tela stub da fundação (Fase 1).{phase ? ` Implementação na ${phase}.` : ''}
        </p>
      </Card>
    </div>
  );
}
