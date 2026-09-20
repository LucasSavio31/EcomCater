'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Button, Card } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { useToast } from '@/components/toast';
import { nfeApi } from '@/modules/nfe/api';

export default function NfeXmlPage() {
  const toast = useToast();
  const now = new Date();
  const [exportMonth, setExportMonth] = useState(
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
  );
  const [busy, setBusy] = useState(false);

  async function doExportMonth(): Promise<void> {
    const [y, m] = exportMonth.split('-').map(Number);
    if (!y || !m) {
      toast.error('Selecione um mês.');
      return;
    }
    setBusy(true);
    const res = await nfeApi.downloadExportMonth(y, m);
    setBusy(false);
    if (!res.ok) toast.error(res.message);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="XML para o contador"
        description="Baixa o XML de todas as NF-e autorizadas de um mês, num único .zip."
        actions={
          <Link href="/nfe" className="text-sm text-accent hover:underline">
            → Configuração de emissão
          </Link>
        }
      />

      <Card variant="outline" className="flex max-w-3xl flex-col gap-4">
        <p className="text-sm text-text-muted">
          Baixa um .zip com o XML de todas as NF-e autorizadas do mês escolhido (um arquivo por nota,
          nome = chave de acesso). O XML já fica guardado no sistema desde a emissão — isso só agrupa
          por mês pra facilitar o envio pro contador.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium" htmlFor="nfe-export-month">
              Mês
            </label>
            <input
              id="nfe-export-month"
              type="month"
              value={exportMonth}
              onChange={(e) => setExportMonth(e.target.value)}
              className="min-h-touch rounded-card border border-surface-border bg-surface px-3 text-sm"
            />
          </div>
          <Button size="sm" loading={busy} onClick={() => void doExportMonth()}>
            Baixar XML do mês (.zip)
          </Button>
        </div>
      </Card>
    </div>
  );
}
