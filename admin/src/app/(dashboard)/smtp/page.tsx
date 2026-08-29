'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { smtpApi, type SmtpConfig } from '@/modules/smtp/api';

export default function SmtpPage() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => smtpApi.get());
  const [draft, setDraft] = useState<SmtpConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [testTo, setTestTo] = useState('');
  const [testing, setTesting] = useState(false);

  const cfg = draft ?? data;
  const set = <K extends keyof SmtpConfig>(k: K, v: SmtpConfig[K]): void => {
    if (!cfg) return;
    setDraft({ ...cfg, [k]: v });
  };

  async function save(): Promise<void> {
    if (!cfg) return;
    setSaving(true);
    const result = await smtpApi.put(cfg);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Configuração SMTP salva.');
    setData(result.data);
    setDraft(null);
  }

  async function sendTest(): Promise<void> {
    if (!testTo.trim()) return;
    setTesting(true);
    const result = await smtpApi.test(testTo.trim());
    setTesting(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success(`E-mail de teste enviado para ${testTo.trim()}.`);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="SMTP" description="Servidor de e-mail para mensagens transacionais." />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {cfg && (
          <Card variant="outline" className="flex flex-col gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label="Host" value={cfg.host} onChange={(e) => set('host', e.target.value)} />
              <Input
                label="Porta"
                inputMode="numeric"
                value={String(cfg.port)}
                onChange={(e) => set('port', Number(e.target.value) || 0)}
              />
              <Input label="Usuário" value={cfg.username} onChange={(e) => set('username', e.target.value)} />
              <Input
                label="Senha"
                type="password"
                value={cfg.password}
                onChange={(e) => set('password', e.target.value)}
              />
              <Input label="Remetente (e-mail)" value={cfg.from_email} onChange={(e) => set('from_email', e.target.value)} />
              <Input label="Remetente (nome)" value={cfg.from_name} onChange={(e) => set('from_name', e.target.value)} />
            </div>
            <div className="flex flex-wrap gap-4">
              <Checkbox label="Usar TLS" checked={cfg.use_tls} onChange={(v) => set('use_tls', v)} />
              <Checkbox label="Usar SSL" checked={cfg.use_ssl} onChange={(v) => set('use_ssl', v)} />
            </div>
            <Button loading={saving} onClick={() => void save()} className="self-start">
              Salvar configuração
            </Button>

            <div className="flex flex-col gap-2 border-t border-surface-border pt-4">
              <h2 className="text-sm font-semibold">Enviar e-mail de teste</h2>
              <div className="flex flex-wrap items-end gap-2">
                <Input
                  label="Destinatário"
                  type="email"
                  value={testTo}
                  onChange={(e) => setTestTo(e.target.value)}
                  className="flex-1"
                />
                <Button variant="outline" loading={testing} onClick={() => void sendTest()}>
                  Enviar teste
                </Button>
              </div>
            </div>
          </Card>
        )}
      </AsyncBoundary>
    </div>
  );
}
