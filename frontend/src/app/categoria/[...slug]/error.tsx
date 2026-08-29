'use client';

import { useEffect } from 'react';
import { Button, Card } from '@ecom/ui';

export default function CategoriaError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Card variant="outline" className="flex flex-col items-start gap-3">
      <h2 className="text-lg font-semibold">Não foi possível carregar a categoria</h2>
      <p className="text-sm text-text-muted">Tente novamente em instantes.</p>
      <Button variant="outline" onClick={reset}>
        Tentar de novo
      </Button>
    </Card>
  );
}
