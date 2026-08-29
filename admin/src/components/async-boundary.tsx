'use client';

import type { ReactNode } from 'react';
import { Button, Card, Spinner } from '@ecom/ui';

interface AsyncBoundaryProps {
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
  /** Considerado "vazio" quando true e não está carregando/erro. */
  empty?: boolean;
  emptyMessage?: string;
  children: ReactNode;
}

export function AsyncBoundary({
  loading,
  error,
  onRetry,
  empty = false,
  emptyMessage = 'Nada por aqui ainda.',
  children,
}: AsyncBoundaryProps) {
  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" label="Carregando…" />
      </div>
    );
  }
  if (error) {
    return (
      <Card variant="outline" className="flex flex-col items-start gap-3 border-danger">
        <p className="text-sm text-danger">{error}</p>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            Tentar de novo
          </Button>
        )}
      </Card>
    );
  }
  if (empty) {
    return (
      <Card variant="outline" className="text-center text-sm text-text-muted">
        {emptyMessage}
      </Card>
    );
  }
  return <>{children}</>;
}
