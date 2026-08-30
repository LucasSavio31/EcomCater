'use client';

import { useState } from 'react';
import { Badge, Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { Checkbox } from '@/components/form-controls';
import { AsyncBoundary } from '@/components/async-boundary';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime } from '@/lib/format';
import {
  cartRecoveryApi,
  type RecoveryMessage,
  type RecoveryMessageInput,
} from '@/modules/cart-recovery/api';

const EMPTY: RecoveryMessageInput = {
  position: 0,
  delay_minutes: 60,
  subject: '',
  body: '',
  is_active: true,
};

export default function CartRecoveryPage() {
  const toast = useToast();
  const carts = useResource(() => cartRecoveryApi.listCarts());
  const messages = useResource(() => cartRecoveryApi.listMessages());
  const [form, setForm] = useState<RecoveryMessageInput>(EMPTY);
  const [editing, setEditing] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [del, setDel] = useState<string | null>(null);

  const set = <K extends keyof RecoveryMessageInput>(k: K, v: RecoveryMessageInput[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  function edit(m: RecoveryMessage) {
    setEditing(m.id);
    setForm({
      position: m.position,
      delay_minutes: m.delay_minutes,
      subject: m.subject,
      body: m.body,
      is_active: m.is_active,
    });
  }

  async function save() {
    if (!form.subject.trim()) return toast.error('Informe o assunto.');
    setBusy(true);
    const res = editing
      ? await cartRecoveryApi.updateMessage(editing, form)
      : await cartRecoveryApi.createMessage(form);
    setBusy(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success('Mensagem salva.');
    setForm(EMPTY);
    setEditing(null);
    messages.reload();
  }

  async function remove() {
    if (!del) return;
    setBusy(true);
    const res = await cartRecoveryApi.deleteMessage(del);
    setBusy(false);
    setDel(null);
    if (!res.ok) return toast.error(res.error.message);
    toast.success('Mensagem removida.');
    messages.reload();
  }

  async function runNow() {
    setBusy(true);
    const res = await cartRecoveryApi.runNow();
    setBusy(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success(`Processado: ${res.data.sent} e-mail(s) enviado(s).`);
    carts.reload();
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Recuperação de carrinho"
        description="O e-mail é capturado no checkout. Se a compra não acontecer, as mensagens abaixo são enviadas por SMTP com um link que volta direto ao checkout com os produtos."
        actions={
          <Button variant="outline" loading={busy} onClick={() => void runNow()}>
            Processar agora
          </Button>
        }
      />

      <Card variant="outline" className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">
          {editing ? 'Editar mensagem' : 'Nova mensagem de recuperação'}
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <Input
            label="Ordem"
            inputMode="numeric"
            value={String(form.position)}
            onChange={(e) => set('position', Number(e.target.value) || 0)}
          />
          <Input
            label="Enviar após (minutos da captura)"
            inputMode="numeric"
            value={String(form.delay_minutes)}
            onChange={(e) => set('delay_minutes', Number(e.target.value) || 0)}
          />
          <div className="flex items-end">
            <Checkbox
              label="Ativa"
              checked={form.is_active}
              onChange={(v) => set('is_active', v)}
            />
          </div>
        </div>
        <Input
          label="Assunto"
          value={form.subject}
          onChange={(e) => set('subject', e.target.value)}
        />
        <label className="flex flex-col gap-1 text-sm font-medium text-text">
          Conteúdo
          <textarea
            value={form.body}
            onChange={(e) => set('body', e.target.value)}
            rows={5}
            className="rounded-card border border-surface-border bg-surface px-3 py-2 text-sm"
          />
          <span className="text-xs text-text-muted">
            Variáveis: <code>{'{nome}'}</code> (nome do cliente),{' '}
            <code>{'{link}'}</code> (link que volta ao carrinho). Um botão “Voltar ao meu
            carrinho” já é adicionado automaticamente ao fim do e-mail.
          </span>
        </label>
        <div className="flex gap-2">
          <Button loading={busy} onClick={() => void save()}>
            {editing ? 'Salvar' : 'Adicionar'}
          </Button>
          {editing && (
            <Button
              variant="outline"
              onClick={() => {
                setEditing(null);
                setForm(EMPTY);
              }}
            >
              Cancelar
            </Button>
          )}
        </div>
      </Card>

      <AsyncBoundary loading={messages.loading} error={messages.error} onRetry={messages.reload}>
        <div className="flex flex-col gap-2">
          {(messages.data ?? []).map((m) => (
            <Card key={m.id} variant="outline" className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium">#{m.position}</span>
              <span className="text-sm">{m.subject}</span>
              <Badge tone="neutral">após {m.delay_minutes} min</Badge>
              {!m.is_active && <Badge tone="warning">inativa</Badge>}
              <div className="ml-auto flex gap-2">
                <Button size="sm" variant="outline" onClick={() => edit(m)}>
                  Editar
                </Button>
                <Button size="sm" variant="ghost" className="text-danger" onClick={() => setDel(m.id)}>
                  Excluir
                </Button>
              </div>
            </Card>
          ))}
          {(messages.data ?? []).length === 0 && (
            <p className="text-sm text-text-muted">Nenhuma mensagem cadastrada.</p>
          )}
        </div>
      </AsyncBoundary>

      <h2 className="text-lg font-semibold">Carrinhos abandonados</h2>
      <AsyncBoundary loading={carts.loading} error={carts.error} onRetry={carts.reload}>
        <div className="overflow-x-auto rounded-card border border-surface-border">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="bg-bg-subtle text-left text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="px-3 py-2">E-mail</th>
                <th className="px-3 py-2">Itens</th>
                <th className="px-3 py-2">Valor</th>
                <th className="px-3 py-2">Lembretes</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Capturado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {(carts.data ?? []).length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-text-muted">
                    Nenhum carrinho abandonado.
                  </td>
                </tr>
              )}
              {(carts.data ?? []).map((c) => (
                <tr key={c.id}>
                  <td className="px-3 py-2">{c.email}</td>
                  <td className="px-3 py-2">{c.items_count}</td>
                  <td className="px-3 py-2">{formatBRL(c.total_cents)}</td>
                  <td className="px-3 py-2">{c.reminders_sent}</td>
                  <td className="px-3 py-2">
                    {c.recovered ? (
                      <Badge tone="success">Recuperado</Badge>
                    ) : (
                      <Badge tone="warning">Pendente</Badge>
                    )}
                  </td>
                  <td className="px-3 py-2 text-text-muted">
                    {c.created_at ? formatDateTime(c.created_at) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AsyncBoundary>

      <ConfirmDialog
        open={del !== null}
        title="Excluir mensagem"
        description="Remover esta mensagem de recuperação?"
        confirmLabel="Excluir"
        tone="danger"
        loading={busy}
        onConfirm={() => void remove()}
        onCancel={() => setDel(null)}
      />
    </div>
  );
}
