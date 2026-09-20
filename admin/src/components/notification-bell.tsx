'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { IconBell, IconTrash } from './nav-icons';
import { notificationsApi, type NotificationItem, type NotificationsList } from '@/modules/notifications/api';
import { playReturnSound, playSaleSound } from '@/lib/sounds';
import { ADMIN_API_BASE_URL } from '@/lib/admin-api-client';
import { getSession } from '@/lib/auth-storage';

// Rede de segurança: o WebSocket cobre o tempo real; o poll continua existindo
// pra sincronizar caso a conexão caia (fila, reconexão de wifi, etc).
const POLL_MS = 30_000;
const WS_RETRY_MS = 5_000;

function wsUrl(): string | null {
  const session = getSession();
  if (!session) return null;
  const base = ADMIN_API_BASE_URL.replace(/^http/, 'ws');
  return `${base}/api/admin/notifications/stream?token=${encodeURIComponent(session.accessToken)}`;
}

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
  // primeiro carregamento (nunca ao abrir o painel com itens antigos na fila) --
  // compartilhado entre o poll e o WebSocket pra nunca tocar 2x a mesma.
  const seenIdsRef = useRef<Set<string> | null>(null);
  const soundFlagsRef = useRef({ sale: true, return: true });

  const playIfNew = useCallback((item: NotificationItem) => {
    const seen = seenIdsRef.current;
    if (!seen || seen.has(item.id)) return;
    seen.add(item.id);
    if (item.type === 'order_paid' && soundFlagsRef.current.sale) playSaleSound();
    if (item.type === 'order_returned' && soundFlagsRef.current.return) playReturnSound();
  }, []);

  const refresh = useCallback(async () => {
    const res = await notificationsApi.list();
    if (!res.ok) return;
    setData(res.data);
    soundFlagsRef.current = {
      sale: res.data.sound_sale_enabled,
      return: res.data.sound_return_enabled,
    };
    if (seenIdsRef.current === null) {
      // Primeiro carregamento: só registra os ids existentes -- nunca toca
      // som pra notificação que já estava na fila antes de abrir o painel.
      seenIdsRef.current = new Set(res.data.items.map((i) => i.id));
      return;
    }
    for (const item of res.data.items) playIfNew(item);
  }, [playIfNew]);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  // Push em tempo real: assim que uma venda é paga ou uma devolução é
  // entregue, o backend manda na hora -- não importa a página do admin em
  // que o usuário está, porque este componente vive no layout. Reconecta
  // sozinho se a conexão cair (wifi, servidor reiniciando, etc).
  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof window.setTimeout> | null = null;
    let stopped = false;

    function connect(): void {
      if (stopped) return;
      const url = wsUrl();
      if (!url) {
        retryTimer = setTimeout(connect, WS_RETRY_MS);
        return;
      }
      socket = new WebSocket(url);
      socket.onmessage = (ev: MessageEvent<string>) => {
        let item: NotificationItem;
        try {
          item = JSON.parse(ev.data) as NotificationItem;
        } catch {
          return;
        }
        setData((prev) =>
          prev
            ? {
                ...prev,
                items: [item, ...prev.items.filter((i) => i.id !== item.id)],
                unread_count: prev.unread_count + (item.read_at ? 0 : 1),
              }
            : prev,
        );
        playIfNew(item);
      };
      socket.onclose = () => {
        if (stopped) return;
        retryTimer = setTimeout(connect, WS_RETRY_MS);
      };
      socket.onerror = () => socket?.close();
    }

    connect();
    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, [playIfNew]);

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
