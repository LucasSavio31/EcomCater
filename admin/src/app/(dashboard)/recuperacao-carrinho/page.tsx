'use client';

import { useMemo, useState } from 'react';
import { Badge, Button, Card, Input } from '@ecom/ui';
import { IconTrash } from '@/components/nav-icons';
import { PageHeader } from '@/components/page-header';
import { Checkbox } from '@/components/form-controls';
import { AsyncBoundary } from '@/components/async-boundary';
import { ConfirmDialog } from '@/components/confirm-dialog';
import {
  DateRangeFilter,
  PageSizeSelect,
  DEFAULT_PAGE_SIZE,
} from '@/components/date-range-filter';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime, formatNumber } from '@/lib/format';
import {
  cartRecoveryApi,
  type RecoveryMessage,
  type RecoveryMessageInput,
} from '@/modules/cart-recovery/api';

const STORE_URL =
  process.env.NEXT_PUBLIC_STORE_URL ?? process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000';
const TEST_CART_LINK = `${STORE_URL}/carrinho`;

const DEFAULT_DRAFT: RecoveryMessageInput = {
  position: 0,
  delay_minutes: 30,
  subject: '{nome}, você esqueceu produtos no seu carrinho',
  body:
    'Olá {nome}, notamos que você deixou alguns itens no carrinho.\n\n' +
    'Eles ainda estão reservados para você — mas por pouco tempo. Retome sua ' +
    'compra de onde parou: é rápido e 100% seguro.\n\n' +
    'Se tiver qualquer dúvida sobre pagamento, frete ou os produtos, é só ' +
    'responder este e-mail.',
  is_active: true,
};

export default function CartRecoveryPage() {
  const toast = useToast();
  const stats = useResource(() => cartRecoveryApi.stats());
  const carts = useResource(() => cartRecoveryApi.listCarts());
  const messages = useResource(() => cartRecoveryApi.listMessages());
  const [form, setForm] = useState<RecoveryMessageInput>(DEFAULT_DRAFT);
  const [openId, setOpenId] = useState<string | null>(null); // id da msg, 'new' ou null
  const [busy, setBusy] = useState(false);
  const [del, setDel] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmCarts, setConfirmCarts] = useState(false);
  const [cartFilter, setCartFilter] = useState<'' | 'recovered' | 'abandoned'>('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  const editing = openId && openId !== 'new' ? openId : null;
  const allCarts = carts.data ?? [];

  const cartRows = useMemo(() => {
    return allCarts.filter((c) => {
      if (cartFilter === 'recovered' && !c.recovered) return false;
      if (cartFilter === 'abandoned' && c.recovered) return false;
      const day = (c.created_at ?? '').slice(0, 10);
      if (dateFrom && (!day || day < dateFrom)) return false;
      if (dateTo && (!day || day > dateTo)) return false;
      return true;
    });
  }, [allCarts, cartFilter, dateFrom, dateTo]);

  const pageCount = Math.max(1, Math.ceil(cartRows.length / pageSize));
  const pagedCarts = useMemo(
    () => cartRows.slice((page - 1) * pageSize, page * pageSize),
    [cartRows, page, pageSize],
  );

  function applyCartFilter(f: 'recovered' | 'abandoned') {
    setPage(1);
    setCartFilter((cur) => (cur === f ? '' : f));
  }

  const allChecked = pagedCarts.length > 0 && pagedCarts.every((c) => selected.has(c.id));
  const toggle = (id: string) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  const toggleAll = () =>
    setSelected((s) => {
      const n = new Set(s);
      if (allChecked) pagedCarts.forEach((c) => n.delete(c.id));
      else pagedCarts.forEach((c) => n.add(c.id));
      return n;
    });

  async function deleteSelectedCarts() {
    setBusy(true);
    const res = await cartRecoveryApi.deleteCarts([...selected]);
    setBusy(false);
    setConfirmCarts(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success(`${res.data.deleted} carrinho(s) excluído(s).`);
    setSelected(new Set());
    carts.reload();
    stats.reload();
  }

  const set = <K extends keyof RecoveryMessageInput>(k: K, v: RecoveryMessageInput[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  function openPanel(id: string, m?: RecoveryMessage) {
    if (openId === id) {
      setOpenId(null);
      return;
    }
    setOpenId(id);
    setForm(
      m
        ? {
            position: m.position,
            delay_minutes: m.delay_minutes,
            subject: m.subject,
            body: m.body,
            is_active: m.is_active,
          }
        : { ...DEFAULT_DRAFT, position: (messages.data?.length ?? 0) },
    );
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
    setOpenId(null);
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
    setOpenId(null);
    messages.reload();
  }

  async function sendToSelected() {
    if (selected.size === 0) return;
    setBusy(true);
    const res = await cartRecoveryApi.sendToCarts([...selected]);
    setBusy(false);
    if (!res.ok) return toast.error(res.error.message);
    const { sent, skipped, reason } = res.data;
    if (reason) return toast.error(reason);
    toast.success(
      `${sent} e-mail(s) enviado(s)` + (skipped ? ` · ${skipped} pulado(s)` : '') + '.',
    );
    setSelected(new Set());
    carts.reload();
    stats.reload();
  }

  async function runNow() {
    setBusy(true);
    const res = await cartRecoveryApi.runNow();
    setBusy(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success(`Processado: ${res.data.sent} e-mail(s) enviado(s).`);
    carts.reload();
    stats.reload();
  }

  /** Formulário de mensagem — mesmo conteúdo para "nova" e para editar. */
  const messageForm = (
    <div className="flex flex-col gap-4 pt-2">
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
          <Checkbox label="Ativa" checked={form.is_active} onChange={(v) => set('is_active', v)} />
        </div>
      </div>
      <Input label="Assunto" value={form.subject} onChange={(e) => set('subject', e.target.value)} />
      <label className="flex flex-col gap-1 text-sm font-medium text-text">
        Conteúdo
        <textarea
          value={form.body}
          onChange={(e) => set('body', e.target.value)}
          rows={5}
          className="rounded-card border border-surface-border bg-surface px-3 py-2 text-sm"
        />
        <span className="text-xs text-text-muted">
          Variáveis: <code>{'{nome}'}</code> (nome do cliente), <code>{'{link}'}</code> (link que
          volta ao carrinho). Um botão “Voltar ao meu carrinho” já é adicionado automaticamente ao
          fim do e-mail.
        </span>
      </label>

      <div className="flex flex-col gap-2 rounded-card border border-surface-border bg-bg-subtle p-4">
        <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">
          Pré-visualização do e-mail
        </span>
        <p className="whitespace-pre-wrap text-sm text-text">
          {(form.body || DEFAULT_DRAFT.body)
            .replace(/\{nome\}/g, 'Maria')
            .replace(/\{link\}/g, TEST_CART_LINK)}
        </p>
        <a
          href={TEST_CART_LINK}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-flex w-fit items-center justify-center rounded-card bg-black px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90"
        >
          Voltar ao meu carrinho
        </a>
      </div>
      <div className="flex gap-2">
        <Button loading={busy} onClick={() => void save()}>
          {editing ? 'Salvar' : 'Adicionar'}
        </Button>
        <Button variant="outline" onClick={() => setOpenId(null)}>
          Fechar
        </Button>
        {editing && (
          <Button
            variant="ghost"
            className="ml-auto text-danger"
            onClick={() => setDel(editing)}
          >
            Excluir
          </Button>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Recuperação de carrinho"
        description="O e-mail é capturado no checkout e amarrado ao carrinho pelo cookie. Se a compra não acontecer, as mensagens abaixo são enviadas por SMTP; quando um pedido é feito com o mesmo e-mail, o carrinho é marcado como recuperado."
        actions={
          <Button variant="outline" loading={busy} onClick={() => void runNow()}>
            Processar agora
          </Button>
        }
      />

      {/* Métricas */}
      <AsyncBoundary loading={stats.loading} error={stats.error} onRetry={stats.reload}>
        {stats.data && (
          <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
            {[
              {
                label: 'Carrinhos recuperados',
                value: formatNumber(stats.data.recovered),
                filter: 'recovered' as const,
              },
              {
                label: 'Abandonados (sem conversão)',
                value: formatNumber(stats.data.abandoned),
                filter: 'abandoned' as const,
              },
              {
                label: 'Taxa de recuperação',
                value: `${stats.data.recovery_rate_pct}%`,
                hint: `${stats.data.recovered_after_email} após lembrete (${stats.data.email_recovery_rate_pct}% dos ${stats.data.reminded} lembrados)`,
                filter: null,
              },
              {
                label: 'Receita recuperada',
                value: formatBRL(stats.data.recovered_revenue_cents),
                filter: null,
              },
            ].map((c) => {
              const clickable = c.filter !== null;
              const active = clickable && cartFilter === c.filter;
              return (
                <Card
                  key={c.label}
                  variant="elevated"
                  as={clickable ? 'button' : 'div'}
                  onClick={clickable ? () => applyCartFilter(c.filter) : undefined}
                  className={`flex w-full flex-col gap-1 text-left transition ${
                    clickable ? 'cursor-pointer hover:border-primary' : ''
                  } ${active ? 'border-primary ring-1 ring-primary' : ''}`}
                >
                  <span className="text-xs text-text-muted sm:text-sm">{c.label}</span>
                  <span className="text-xl font-semibold sm:text-2xl">{c.value}</span>
                  {c.hint && <span className="text-[11px] text-text-muted">{c.hint}</span>}
                </Card>
              );
            })}
          </div>
        )}
      </AsyncBoundary>

      {/* Mensagens — sanfona */}
      <AsyncBoundary loading={messages.loading} error={messages.error} onRetry={messages.reload}>
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Mensagens de recuperação</h2>
            <Button
              size="sm"
              onClick={() => openPanel('new')}
              aria-expanded={openId === 'new'}
            >
              {openId === 'new' ? 'Fechar nova mensagem' : '+ Nova mensagem'}
            </Button>
          </div>

          {openId === 'new' && (
            <Card variant="outline" className="mb-1">
              <h3 className="text-sm font-semibold">Nova mensagem de recuperação</h3>
              {messageForm}
            </Card>
          )}

          <div className="divide-y divide-surface-border rounded-card border border-surface-border">
            {(messages.data ?? []).map((m) => {
              const open = openId === m.id;
              return (
                <div key={m.id}>
                  <div className="flex min-h-touch items-center gap-1 pr-2 hover:bg-bg-subtle">
                    <button
                      type="button"
                      aria-expanded={open}
                      onClick={() => openPanel(m.id, m)}
                      className="flex flex-1 flex-wrap items-center gap-3 px-4 py-3 text-left"
                    >
                      <span className="text-sm font-medium text-text-muted">#{m.position}</span>
                      <span className="min-w-0 flex-1 truncate text-sm font-medium">{m.subject}</span>
                      <Badge tone="neutral">após {m.delay_minutes} min</Badge>
                      {!m.is_active && <Badge tone="warning">inativa</Badge>}
                      <span aria-hidden className="text-text-muted">
                        {open ? '–' : '+'}
                      </span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setDel(m.id)}
                      aria-label={`Excluir a mensagem "${m.subject}"`}
                      title="Excluir esta mensagem"
                      className="shrink-0 rounded-card p-2 text-text-muted hover:bg-danger/10 hover:text-danger"
                    >
                      <IconTrash className="h-4 w-4" />
                    </button>
                  </div>
                  {open && <div className="px-4 pb-4">{messageForm}</div>}
                </div>
              );
            })}
            {(messages.data ?? []).length === 0 && (
              <p className="px-4 py-6 text-center text-sm text-text-muted">
                Nenhuma mensagem cadastrada. Use “+ Nova mensagem”.
              </p>
            )}
          </div>
        </div>
      </AsyncBoundary>

      {/* Carrinhos abandonados */}
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold">Carrinhos abandonados</h2>
        {cartFilter && (
          <Badge tone="neutral">
            {cartFilter === 'recovered' ? 'só recuperados' : 'só não recuperados'}
          </Badge>
        )}
        {selected.size > 0 && (
          <>
            <Button
              size="sm"
              variant="outline"
              loading={busy}
              onClick={() => void sendToSelected()}
            >
              Enviar recuperação p/ selecionados ({selected.size})
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="text-danger"
              onClick={() => setConfirmCarts(true)}
            >
              Excluir selecionados ({selected.size})
            </Button>
          </>
        )}
      </div>

      <Card variant="outline">
        <DateRangeFilter
          from={dateFrom}
          to={dateTo}
          onApply={(f, t) => {
            setPage(1);
            setDateFrom(f);
            setDateTo(t);
          }}
          onClear={() => {
            setPage(1);
            setDateFrom('');
            setDateTo('');
          }}
        />
      </Card>

      <AsyncBoundary loading={carts.loading} error={carts.error} onRetry={carts.reload}>
        <div className="overflow-x-auto rounded-card border border-surface-border">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="bg-bg-subtle text-left text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="w-10 px-3 py-2">
                  <input type="checkbox" checked={allChecked} onChange={toggleAll} aria-label="Selecionar todos" />
                </th>
                <th className="px-3 py-2">E-mail</th>
                <th className="px-3 py-2">Itens</th>
                <th className="px-3 py-2">Valor</th>
                <th className="px-3 py-2">Lembretes</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Capturado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {cartRows.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-8 text-center text-text-muted">
                    Nenhum carrinho abandonado.
                  </td>
                </tr>
              )}
              {pagedCarts.map((c) => (
                <tr key={c.id}>
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selected.has(c.id)}
                      onChange={() => toggle(c.id)}
                      aria-label={`Selecionar ${c.email}`}
                    />
                  </td>
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

      {cartRows.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <div className="flex items-center gap-4">
            <span className="text-text-muted">
              {cartRows.length} carrinho(s)
            </span>
            <PageSizeSelect
              value={pageSize}
              onChange={(n) => {
                setPage(1);
                setPageSize(n);
              }}
            />
          </div>
          {pageCount > 1 && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Anterior
              </Button>
              <span>
                Página {page} de {pageCount}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= pageCount}
                onClick={() => setPage((p) => p + 1)}
              >
                Próxima
              </Button>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        open={confirmCarts}
        title="Excluir carrinhos abandonados"
        description={`Excluir ${selected.size} carrinho(s)? Não afeta os pedidos já feitos.`}
        confirmLabel="Excluir"
        tone="danger"
        loading={busy}
        onConfirm={() => void deleteSelectedCarts()}
        onCancel={() => setConfirmCarts(false)}
      />

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
