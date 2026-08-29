'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Badge, Card } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { configApi, type ModuleInfo } from '@/modules/config/api';

export default function ModulosPage() {
  const toast = useToast();
  const { data, loading, error, reload } = useResource(() => configApi.listModules());
  const [busySlug, setBusySlug] = useState<string | null>(null);

  async function toggle(mod: ModuleInfo, enabled: boolean): Promise<void> {
    setBusySlug(mod.slug);
    const result = await configApi.patchModule(mod.slug, { enabled });
    setBusySlug(null);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success(`Módulo ${mod.label} ${enabled ? 'ativado' : 'desativado'}.`);
    reload();
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Módulos"
        description="Ative ou desative recursos da loja. Pagamento e frete têm telas próprias."
      />

      <div className="flex flex-wrap gap-3 text-sm">
        <Link href="/pagamento" className="rounded-card border border-surface-border px-3 py-1.5 hover:border-primary">
          → Configurar pagamento
        </Link>
        <Link href="/frete" className="rounded-card border border-surface-border px-3 py-1.5 hover:border-primary">
          → Configurar frete
        </Link>
        <Link href="/rastreamento" className="rounded-card border border-surface-border px-3 py-1.5 hover:border-primary">
          → Rastreamento e anúncios
        </Link>
      </div>

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        <div className="flex flex-col gap-3">
          {(data ?? []).map((mod) => (
            <Card key={mod.slug} variant="outline" className="flex items-center justify-between gap-3">
              <div className="flex flex-col gap-0.5">
                <span className="font-medium">
                  {mod.label} <span className="text-xs text-text-muted">({mod.slug})</span>
                </span>
                <span className="flex items-center gap-2 text-xs text-text-muted">
                  <Badge tone="neutral">{mod.kind}</Badge>
                  {!mod.toggleable && <span>sempre ativo</span>}
                </span>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={mod.enabled}
                  disabled={!mod.toggleable || busySlug === mod.slug}
                  onChange={(e) => void toggle(mod, e.target.checked)}
                  className="h-5 w-5"
                />
                {mod.enabled ? 'Ativo' : 'Inativo'}
              </label>
            </Card>
          ))}
        </div>
      </AsyncBoundary>
    </div>
  );
}
