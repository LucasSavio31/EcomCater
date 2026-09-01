'use client';

import { ADMIN_API_BASE_URL, adminFetch, type ApiResult } from '@/lib/admin-api-client';
import { getSession } from '@/lib/auth-storage';

export type HealthStatus = 'ok' | 'degraded' | 'down';

export interface HealthSample {
  status: HealthStatus;
  latency_ms: number;
  at: string;
}

export interface HealthService {
  key: string;
  label: string;
  status: HealthStatus;
  latency_ms: number;
  detail: string;
  uptime_pct: number;
  history: HealthSample[];
  checked_at: string;
}

export interface HealthHistoryEntry {
  key: string;
  label: string;
  samples: (HealthSample & { detail: string | null })[];
  count: number;
  uptime_pct: number;
  incidents: number;
  avg_latency_ms: number;
  first_at: string | null;
  last_at: string | null;
}

export interface SftpConfig {
  enabled?: boolean;
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  key_path?: string;
  remote_dir?: string;
}

export interface GDriveConfig {
  enabled?: boolean;
  folder_id?: string;
  service_account_json_path?: string;
  account_email?: string;
}

export interface BackupSettings {
  auto_enabled: boolean;
  frequency: 'diario' | 'semanal' | 'mensal';
  hour: number;
  keep: number;
  include_media: boolean;
  folder_path: string | null;
  sftp: SftpConfig;
  gdrive: GDriveConfig;
  last_run_at: string | null;
  last_status: string | null;
}

export interface BackupRecord {
  id: string;
  filename: string;
  size_bytes: number;
  size_mb: number;
  status: 'ok' | 'error' | 'running';
  error_message: string | null;
  triggered_by: string;
  includes_media: boolean;
  destinations: { type: string; ok: boolean; detail: string }[];
  created_at: string | null;
}

export const systemApi = {
  health: (): Promise<ApiResult<HealthService[]>> =>
    adminFetch<HealthService[]>('/api/admin/system/health'),

  healthHistory: (
    fromDate: string,
    toDate: string,
    key?: string,
  ): Promise<ApiResult<HealthHistoryEntry[]>> => {
    // converte AAAA-MM-DD (dia local) para limites ISO com fuso, para o servidor
    // não cortar leituras por diferença de timezone.
    const from = new Date(`${fromDate}T00:00:00`).toISOString();
    const to = new Date(`${toDate}T23:59:59.999`).toISOString();
    return adminFetch<HealthHistoryEntry[]>('/api/admin/system/health/history', {
      query: key ? { from, to, key } : { from, to },
    });
  },

  getBackupSettings: (): Promise<ApiResult<BackupSettings>> =>
    adminFetch<BackupSettings>('/api/admin/system/backup/settings'),

  saveBackupSettings: (body: Partial<BackupSettings>): Promise<ApiResult<BackupSettings>> =>
    adminFetch<BackupSettings>('/api/admin/system/backup/settings', { method: 'PATCH', body }),

  listBackups: (): Promise<ApiResult<BackupRecord[]>> =>
    adminFetch<BackupRecord[]>('/api/admin/system/backup'),

  runBackup: (includeMedia?: boolean): Promise<ApiResult<BackupRecord>> =>
    adminFetch<BackupRecord>('/api/admin/system/backup/run', {
      method: 'POST',
      query: includeMedia === undefined ? undefined : { include_media: includeMedia },
    }),

  deleteBackup: (id: string): Promise<ApiResult<void>> =>
    adminFetch<void>(`/api/admin/system/backup/${id}`, { method: 'DELETE' }),

  /** Baixa o arquivo com o Bearer no header e dispara o "salvar como" do navegador. */
  async downloadBackup(id: string, filename: string): Promise<{ ok: true } | { ok: false; error: string }> {
    const session = getSession();
    if (!session) return { ok: false, error: 'Sessão expirada.' };
    const res = await fetch(`${ADMIN_API_BASE_URL}/api/admin/system/backup/${id}/download`, {
      headers: { authorization: `Bearer ${session.accessToken}` },
    });
    if (!res.ok) return { ok: false, error: `Falha ao baixar (${res.status}).` };
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    return { ok: true };
  },

  restoreUrl: `${ADMIN_API_BASE_URL}/api/admin/system/backup/restore`,
};
