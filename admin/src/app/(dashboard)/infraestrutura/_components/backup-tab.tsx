'use client';

import { useCallback, useRef, useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { formatDateTime } from '@/lib/format';
import { useResource } from '@/lib/use-resource';
import { getSession } from '@/lib/auth-storage';
import { systemApi, type BackupRecord, type BackupSettings } from '@/modules/system/api';

function StatusPill({ status }: { status: BackupRecord['status'] }) {
  const map = {
    ok: 'border-success text-success',
    error: 'border-danger text-danger',
    running: 'border-warning text-warning',
  } as const;
  const label = { ok: 'OK', error: 'Erro', running: 'Rodando' }[status];
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${map[status]}`}>
      {label}
    </span>
  );
}

export function BackupTab() {
  const toast = useToast();
  const settingsRes = useResource(() => systemApi.getBackupSettings());
  const listRes = useResource(() => systemApi.listBackups());

  const [draft, setDraft] = useState<BackupSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const cfg = draft ?? settingsRes.data ?? null;
  const set = <K extends keyof BackupSettings>(k: K, v: BackupSettings[K]): void => {
    if (!cfg) return;
    setDraft({ ...cfg, [k]: v });
  };
  const setSftp = (patch: Partial<BackupSettings['sftp']>): void => {
    if (!cfg) return;
    setDraft({ ...cfg, sftp: { ...cfg.sftp, ...patch } });
  };
  const setGdrive = (patch: Partial<BackupSettings['gdrive']>): void => {
    if (!cfg) return;
    setDraft({ ...cfg, gdrive: { ...cfg.gdrive, ...patch } });
  };

  const saveSettings = useCallback(async () => {
    if (!cfg) return;
    setSaving(true);
    const res = await systemApi.saveBackupSettings(cfg);
    setSaving(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('Configuração de backup salva.');
    setDraft(null);
    settingsRes.setData(res.data);
  }, [cfg, settingsRes, toast]);

  const runNow = useCallback(async () => {
    setRunning(true);
    const res = await systemApi.runBackup();
    setRunning(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('Backup criado.');
    listRes.reload();
  }, [listRes, toast]);

  const doRestore = useCallback(async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) {
      toast.error('Escolha um arquivo de backup.');
      return;
    }
    if (confirmText.trim().toUpperCase() !== 'RESTAURAR') {
      toast.error('Digite RESTAURAR para confirmar.');
      return;
    }
    setRestoring(true);
    const form = new FormData();
    form.append('file', file);
    form.append('confirm', 'RESTAURAR');
    const session = getSession();
    try {
      const res = await fetch(systemApi.restoreUrl, {
        method: 'POST',
        headers: session ? { authorization: `Bearer ${session.accessToken}` } : undefined,
        body: form,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast.error(data?.error?.message ?? `Falha na restauração (${res.status}).`);
      } else {
        toast.success('Banco restaurado. Um backup de segurança foi criado antes.');
        setConfirmText('');
        if (fileRef.current) fileRef.current.value = '';
        listRes.reload();
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Falha de rede na restauração.');
    } finally {
      setRestoring(false);
    }
  }, [confirmText, listRes, toast]);

  return (
    <div className="flex flex-col gap-6">
      {/* ---------------------------------------------------------- configuração */}
      <AsyncBoundary loading={settingsRes.loading} error={settingsRes.error} onRetry={settingsRes.reload}>
        {cfg && (
          <Card variant="outline" className="flex flex-col gap-4">
            <h2 className="text-base font-semibold">Backup automático</h2>
            <Checkbox
              label="Fazer backup automaticamente"
              hint="O agendador roda dentro da API e verifica a cada 10 min. Não depende de cron do sistema."
              checked={cfg.auto_enabled}
              onChange={(v) => set('auto_enabled', v)}
            />
            <div className="grid gap-4 sm:grid-cols-3">
              <Select
                label="Frequência"
                value={cfg.frequency}
                onChange={(e) => set('frequency', e.target.value as BackupSettings['frequency'])}
                options={[
                  { value: 'diario', label: 'Diário' },
                  { value: 'semanal', label: 'Semanal' },
                  { value: 'mensal', label: 'Mensal' },
                ]}
              />
              <Input
                label="Hora (0–23)"
                type="number"
                min={0}
                max={23}
                hint="Fuso da loja (America/Sao_Paulo)"
                value={String(cfg.hour)}
                onChange={(e) => set('hour', Number(e.target.value))}
              />
              <Input
                label="Manter últimos N"
                type="number"
                min={1}
                max={60}
                value={String(cfg.keep)}
                onChange={(e) => set('keep', Number(e.target.value))}
              />
            </div>
            <Checkbox
              label="Incluir os arquivos de mídia (imagens) no backup"
              checked={cfg.include_media}
              onChange={(v) => set('include_media', v)}
            />

            <div className="h-px bg-surface-border" />
            <h3 className="text-sm font-semibold">Cópia redundante</h3>
            <Input
              label="Pasta no servidor (opcional)"
              placeholder="/mnt/backups ou D:\\backups"
              value={cfg.folder_path ?? ''}
              onChange={(e) => set('folder_path', e.target.value || null)}
              hint="Cada backup é copiado para esta pasta (disco local ou unidade de rede montada)."
            />

            <div className="rounded-card border border-surface-border p-3">
              <Checkbox
                label="Enviar cópia por SFTP para um servidor remoto"
                checked={!!cfg.sftp.enabled}
                onChange={(v) => setSftp({ enabled: v })}
              />
              {cfg.sftp.enabled && (
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <Input label="Host" value={cfg.sftp.host ?? ''} onChange={(e) => setSftp({ host: e.target.value })} />
                  <Input label="Porta" type="number" value={String(cfg.sftp.port ?? 22)} onChange={(e) => setSftp({ port: Number(e.target.value) })} />
                  <Input label="Usuário" value={cfg.sftp.user ?? ''} onChange={(e) => setSftp({ user: e.target.value })} />
                  <Input label="Senha" type="password" placeholder="(mantida se em branco)" value={cfg.sftp.password ?? ''} onChange={(e) => setSftp({ password: e.target.value })} />
                  <Input label="Caminho da chave privada (opcional)" value={cfg.sftp.key_path ?? ''} onChange={(e) => setSftp({ key_path: e.target.value })} />
                  <Input label="Pasta remota" value={cfg.sftp.remote_dir ?? ''} onChange={(e) => setSftp({ remote_dir: e.target.value })} />
                </div>
              )}
            </div>

            <div className="rounded-card border border-surface-border p-3">
              <Checkbox
                label="Enviar cópia para uma pasta do Google Drive"
                checked={!!cfg.gdrive.enabled}
                onChange={(v) => setGdrive({ enabled: v })}
              />
              {cfg.gdrive.enabled && (
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <Input label="ID da pasta do Drive" value={cfg.gdrive.folder_id ?? ''} onChange={(e) => setGdrive({ folder_id: e.target.value })} />
                  <Input
                    label="Caminho do JSON da conta de serviço"
                    value={cfg.gdrive.service_account_json_path ?? ''}
                    onChange={(e) => setGdrive({ service_account_json_path: e.target.value })}
                    hint="Crie uma conta de serviço no Google Cloud, compartilhe a pasta do Drive com o e-mail dela e informe o caminho do arquivo .json no servidor."
                  />
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={saveSettings} loading={saving} disabled={!draft}>
                Salvar configuração
              </Button>
              {cfg.last_run_at && (
                <span className="text-xs text-text-muted">
                  Último backup: {formatDateTime(cfg.last_run_at)} ({cfg.last_status})
                </span>
              )}
            </div>
          </Card>
        )}
      </AsyncBoundary>

      {/* ---------------------------------------------------------- executar + lista */}
      <Card variant="outline" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold">Backups</h2>
          <Button onClick={runNow} loading={running}>
            Fazer backup agora
          </Button>
        </div>

        <AsyncBoundary loading={listRes.loading} error={listRes.error} onRetry={listRes.reload}>
          {listRes.data && listRes.data.length === 0 && (
            <p className="text-sm text-text-muted">Nenhum backup ainda.</p>
          )}
          {listRes.data && listRes.data.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-text-muted">
                    <th className="py-2 pr-3">Data</th>
                    <th className="py-2 pr-3">Origem</th>
                    <th className="py-2 pr-3">Tamanho</th>
                    <th className="py-2 pr-3">Mídia</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Destinos</th>
                    <th className="py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {listRes.data.map((b) => (
                    <tr key={b.id}>
                      <td className="py-2 pr-3 whitespace-nowrap">{formatDateTime(b.created_at)}</td>
                      <td className="py-2 pr-3">{b.triggered_by}</td>
                      <td className="py-2 pr-3 whitespace-nowrap">{b.size_mb} MB</td>
                      <td className="py-2 pr-3">{b.includes_media ? 'sim' : 'não'}</td>
                      <td className="py-2 pr-3">
                        <StatusPill status={b.status} />
                        {b.error_message && (
                          <span className="ml-2 text-xs text-danger">{b.error_message}</span>
                        )}
                      </td>
                      <td className="py-2 pr-3 text-xs text-text-muted">
                        {b.destinations.length === 0
                          ? '—'
                          : b.destinations
                              .map((d) => `${d.type}: ${d.ok ? 'ok' : 'falhou'}`)
                              .join(' · ')}
                      </td>
                      <td className="py-2">
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={b.status !== 'ok'}
                            onClick={async () => {
                              const r = await systemApi.downloadBackup(b.id, b.filename);
                              if (!r.ok) toast.error(r.error);
                            }}
                          >
                            Baixar
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={async () => {
                              if (!confirm(`Excluir o backup de ${formatDateTime(b.created_at)}?`)) return;
                              const r = await systemApi.deleteBackup(b.id);
                              if (!r.ok) toast.error(r.error.message);
                              else listRes.reload();
                            }}
                          >
                            Excluir
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </AsyncBoundary>
      </Card>

      {/* ---------------------------------------------------------- restauração */}
      <Card variant="outline" className="flex flex-col gap-3 border-danger">
        <h2 className="text-base font-semibold text-danger">Restaurar um backup</h2>
        <p className="text-sm text-text-muted">
          Substitui <strong>todo</strong> o banco de dados atual pelo conteúdo do arquivo enviado
          (aceita o <code>.tar.gz</code> gerado aqui ou um <code>.dump</code> do PostgreSQL). Um
          backup de segurança é criado automaticamente antes. Esta ação não pode ser desfeita.
        </p>
        <input
          ref={fileRef}
          type="file"
          accept=".gz,.tgz,.tar.gz,.dump,.backup"
          className="text-sm"
        />
        <Input
          label='Digite "RESTAURAR" para confirmar'
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
        />
        <div>
          <Button
            variant="danger"
            loading={restoring}
            disabled={confirmText.trim().toUpperCase() !== 'RESTAURAR'}
            onClick={doRestore}
          >
            Restaurar agora
          </Button>
        </div>
      </Card>
    </div>
  );
}
