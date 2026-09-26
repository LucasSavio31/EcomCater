import Link from 'next/link';
import { Card } from '@ecom/ui';

export default function NotFound() {
  return (
    <Card variant="outline" className="mx-auto flex max-w-md flex-col items-start gap-3">
      <h1 className="text-2xl font-bold">Página não encontrada</h1>
      <p className="text-sm text-text-muted">
        O endereço acessado não existe ou foi movido.
      </p>
      <Link
        href="/"
        className="inline-flex min-h-touch items-center justify-center rounded-card bg-primary px-4 text-sm font-medium text-primary-fg transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
      >
        Voltar para a home
      </Link>
    </Card>
  );
}
