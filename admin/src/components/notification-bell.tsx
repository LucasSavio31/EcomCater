'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { IconBell, IconTrash } from './nav-icons';
import { notificationsApi, type NotificationItem, type NotificationsList } from '@/modules/notifications/api';
import { playReturnSound, playSaleSound } from '@/lib/sounds';

const POLL_MS = 30_000;

function formatWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Sininho de notificações do header: novas vendas, pagamentos, envios e
 * devoluções entregues. Atualiza sozinho a cada 30s; clicar num item abre o
 * pedido e marca como lida; dá pra apagar 1 a 1 ou tudo de uma vez. Também
 * toca o som de venda/devolução (configurável em Aparência → Sons) quando
 * uma notificação nova desses tipos chega -- funciona em qualquer tela do
 * admin porque este componente vive no layout, não numa página específica. */
export function NotificationBell() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<NotificationsList | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  // Ids já vistos, pra tocar som só nas notificações que chegaram DEPOIS do
  // primeiro carregamento (nunca ao abrir o painel com itens antigos na fila).
  const seenIdsRef = useRef<Set<string> | null>(null);

  const refresh = useCallback(async () => {
    const res = await notificationsApi.list();
    if (!res.ok) return;
    setData(res.data);
    const seen = seenIdsRef.current;
    if (seen) {
      for (const item of res.data.items) {
        if (seen.has(item.id)) continue;
        if (item.type === 'order_paid' && res.data.sound_sale_enabled) playSaleSound();
        if (item.type === 'order_returned' && res.data.sound_return_enabled) playReturnSound();
      }
    }
    seenIdsRef.current = new Set(res.data.items.map((i) => i.id));
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [open]);

  async function openItem(item: NotificationItem): Promise<void> {
    setOpen(false);
    if (!item.read_at) {
      const res = await notificationsApi.markRead(item.id);
      if (res.ok) void refresh();
    }
    if (item.link_path) router.push(item.link_path);
  }

  async function markRead(id: string, e: React.MouseEvent): Promise<void> {
    e.stopPropagation();
    const res = await notificationsApi.markRead(id);
    if (res.ok) void refresh();
  }

  async function remove(id: string, e: React.MouseEvent): Promise<void> {
    e.stopPropagation();
    const res = await notificationsApi.remove(id);
    if (res.ok) void refresh();
  }

  async function removeAll(): Promise<void> {
    const res = await notificationsApi.removeAll();
    if (res.ok) void refresh();
  }

  const items = data?.items ?? [];
  const unread = data?.unread_count ?? 0;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label="Notificações"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="relative flex h-9 w-9 items-center justify-center rounded-full text-text-muted hover:bg-bg-subtle hover:text-text"
      >
        <IconBell className="h-5 w-5" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold leading-none text-white">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-11 z-50 flex w-80 flex-col rounded-card border border-surface-border bg-surface shadow-lg sm:w-96">
          <div className="flex items-center justify-between border-b border-surface-border px-3 py-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">
              Notificações
            </span>
            {items.length > 0 && (
              <button
                type="button"
                onClick={() => void removeAll()}
                className="text-xs text-danger underline"
              >
                Apagar todas
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {items.length === 0 && (
              <p className="px-3 py-6 text-center text-sm text-text-muted">Nenhuma notificação.</p>
            )}
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => void openItem(item)}
                className={`flex w-full flex-col gap-0.5 border-b border-surface-border px-3 py-2 text-left last:border-b-0 hover:bg-bg-subtle ${
                  item.read_at ? '' : 'bg-primary/5'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm font-medium">{item.title}</span>
                  <button
                    type="button"
                    aria-label="Apagar notificação"
                    onClick={(e) => void remove(item.id, e)}
                    className="shrink-0 rounded p-1 text-text-muted hover:bg-danger/10 hover:text-danger"
                  >
                    <IconTrash className="h-3.5 w-3.5" />
                  </button>
                </div>
                {item.message && <span className="text-xs text-text-muted">{item.message}</span>}
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-text-muted">{formatWhen(item.created_at)}</span>
                  {!item.read_at && (
                    <button
                      type="button"
                      onClick={(e) => void markRead(item.id, e)}
                      className="text-xs text-accent underline"
                    >
                      marcar como lida
                    </button>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
