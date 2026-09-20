'use client';

import { adminFetch } from '@/lib/admin-api-client';

export type NotificationType = 'order_created' | 'order_shipped' | 'order_paid' | 'order_returned';

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  message: string | null;
  link_path: string | null;
  read_at: string | null;
  created_at: string;
}

export interface NotificationsList {
  items: NotificationItem[];
  unread_count: number;
  /** Sons do painel (menu Aparência → Sons) -- vêm junto pra não exigir outra chamada. */
  sound_sale_enabled: boolean;
  sound_return_enabled: boolean;
}

export const notificationsApi = {
  list: () => adminFetch<NotificationsList>('/api/admin/notifications'),
  markRead: (id: string) =>
    adminFetch<NotificationItem>(`/api/admin/notifications/${id}/read`, { method: 'POST' }),
  markAllRead: () => adminFetch<{ ok: boolean }>('/api/admin/notifications/read-all', { method: 'POST' }),
  remove: (id: string) => adminFetch<{ ok: boolean }>(`/api/admin/notifications/${id}`, { method: 'DELETE' }),
  removeAll: () => adminFetch<{ ok: boolean }>('/api/admin/notifications', { method: 'DELETE' }),
};
