'use client';

import { useEffect } from 'react';
import { Button, Card } from '@ecom/ui';

export default function GlobalError({
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
    <Card variant="outline" className="mx-auto flex max-w-md flex-col items-start gap-3">
      <h1 className="text-lg font-semibold">Algo deu errado</h1>
      <p className="text-sm text-text-muted">Tente recarregar a página em instantes.</p>
      <Button variant="outline" onClick={reset}>
        Tentar de novo
      </Button>
    </Card>
  );
}
