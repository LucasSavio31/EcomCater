'use client';

import { adminFetch } from '@/lib/admin-api-client';
import type { AdminRole } from '@/modules/auth';

export interface AdminUserRow {
  id: string;
  email: string;
  name: string;
  role: AdminRole;
  is_active: boolean;
  last_login_at: string | null;
  must_change_password?: boolean;
}

export interface CreateUserInput {
  email: string;
  name: string;
  password: string;
  role: AdminRole;
}

export interface UpdateUserInput {
  name?: string;
  role?: AdminRole;
  is_active?: boolean;
  password?: string;
}

export const usersApi = {
  list: () => adminFetch<AdminUserRow[]>('/api/admin/users'),
  create: (body: CreateUserInput) => adminFetch<AdminUserRow>('/api/admin/users', { method: 'POST', body }),
  update: (id: string, body: UpdateUserInput) =>
    adminFetch<AdminUserRow>(`/api/admin/users/${id}`, { method: 'PATCH', body }),
};
