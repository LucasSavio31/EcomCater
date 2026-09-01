'use client';

import Link from 'next/link';
import { Button, Card } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';

/**
 * A configuração do popup / bloco de newsletter foi centralizada em
 * Aparência → Popups. Os inscritos e as campanhas ficam em Marketing → Leads.
 */
export default function NewsletterPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Newsletter e popup"
        description="Esta configuração agora fica junto das demais aparências."
      />
      <Card variant="outline" className="flex flex-col gap-4">
        <p className="text-sm">
          Para editar o <strong>popup de captura de leads</strong>, o <strong>bloco de newsletter da
          home</strong> e o <strong>aviso de cookies</strong>, use a aba <strong>Popups</strong> em
          Aparência.
        </p>
        <p className="text-sm">
          Para ver os <strong>inscritos</strong> e disparar <strong>campanhas por e-mail</strong>,
          use a tela de <strong>Leads</strong>.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/aparencia">
            <Button>Ir para Aparência → Popups</Button>
          </Link>
          <Link href="/leads">
            <Button variant="outline">Ir para Leads</Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}
