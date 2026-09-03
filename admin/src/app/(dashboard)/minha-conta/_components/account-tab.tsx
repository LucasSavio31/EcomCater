'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { useToast } from '@/components/toast';
import { formatDateTime } from '@/lib/format';
import { changePassword, useAdminAuth } from '@/modules/auth';
import { accountApi, type TwoFaSetup } from '@/modules/account/api';

export function AccountTab() {
  const toast = useToast();
  const { user, reload } = useAdminAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);

  const [setup, setSetup] = useState<TwoFaSetup | null>(null);
  const [otpCode, setOtpCode] = useState('');
  const [busy2fa, setBusy2fa] = useState(false);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [disablePwd, setDisablePwd] = useState('');

  const [curPw, setCurPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [newPw2, setNewPw2] = useState('');
  const [savingPw, setSavingPw] = useState(false);

  if (!user) return null;

  const pwValid = curPw.length >= 1 && newPw.length >= 8 && newPw === newPw2;

  async function savePassword(): Promise<void> {
    setSavingPw(true);
    const result = await changePassword(curPw, newPw);
    setSavingPw(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    setCurPw('');
    setNewPw('');
    setNewPw2('');
    toast.success('Senha alterada.');
  }

  const currentName = name || user.name;
  const currentEmail = email || user.email;
  const profileDirty = currentName.trim() !== user.name || currentEmail.trim() !== user.email;

  async function saveProfile(): Promise<void> {
    setSavingProfile(true);
    const result = await accountApi.updateProfile({
      name: currentName.trim(),
      email: currentEmail.trim(),
    });
    setSavingProfile(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Dados atualizados.');
    setName('');
    setEmail('');
    await reload();
  }

  async function start2fa(): Promise<void> {
    setBusy2fa(true);
    const result = await accountApi.start2fa();
    setBusy2fa(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    setSetup(result.data);
    setRecoveryCodes(null);
  }

  async function confirm2fa(): Promise<void> {
    setBusy2fa(true);
    const result = await accountApi.confirm2fa(otpCode.trim());
    setBusy2fa(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    setRecoveryCodes(result.data.recovery_codes);
    setSetup(null);
    setOtpCode('');
    toast.success('Verificação em duas etapas ativada.');
    await reload();
  }

  async function disable2fa(): Promise<void> {
    setBusy2fa(true);
    const result = await accountApi.disable2fa(disablePwd);
    setBusy2fa(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    setDisablePwd('');
    setRecoveryCodes(null);
    toast.success('Verificação em duas etapas desativada.');
    await reload();
  }

  return (
    <div className="flex flex-col gap-6">
      <Card variant="outline" className="flex flex-col gap-4">
        <h2 className="text-base font-semibold">Dados pessoais</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Nome" value={currentName} onChange={(e) => setName(e.target.value)} />
          <Input
            label="E-mail"
            type="email"
            value={currentEmail}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-text-muted">
          <span>
            Papel: <strong className="text-text">{user.role}</strong>
          </span>
          <span>·</span>
          <span>Último acesso: {formatDateTime(user.last_login_at)}</span>
        </div>
        <div>
          <Button onClick={saveProfile} loading={savingProfile} disabled={!profileDirty}>
            Salvar dados
          </Button>
        </div>
      </Card>

      <Card variant="outline" className="flex flex-col gap-4">
        <h2 className="text-base font-semibold">Alterar senha</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <Input
            label="Senha atual"
            type="password"
            autoComplete="current-password"
            value={curPw}
            onChange={(e) => setCurPw(e.target.value)}
          />
          <Input
            label="Nova senha"
            type="password"
            autoComplete="new-password"
            value={newPw}
            onChange={(e) => setNewPw(e.target.value)}
            hint="Mínimo de 8 caracteres."
          />
          <Input
            label="Repita a nova senha"
            type="password"
            autoComplete="new-password"
            value={newPw2}
            onChange={(e) => setNewPw2(e.target.value)}
            error={newPw2 && newPw !== newPw2 ? 'As senhas não conferem' : undefined}
          />
        </div>
        <div>
          <Button onClick={savePassword} loading={savingPw} disabled={!pwValid}>
            Alterar senha
          </Button>
        </div>
      </Card>

      <Card variant="outline" className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold">Verificação em duas etapas (2FA)</h2>
          <span
            className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${
              user.totp_enabled
                ? 'border-success text-success'
                : 'border-surface-border bg-bg-subtle text-text-muted'
            }`}
          >
            {user.totp_enabled ? 'Ativa' : 'Inativa'}
          </span>
        </div>
        <p className="text-sm text-text-muted">
          Use um app como Google Authenticator, Authy ou 1Password. A cada login será pedido um
          código de 6 dígitos além da senha.
        </p>

        {user.totp_enabled && !recoveryCodes && (
          <div className="flex flex-col gap-3 rounded-card border border-surface-border p-3">
            <p className="text-sm">Para desativar, confirme sua senha.</p>
            <div className="flex flex-wrap items-end gap-3">
              <Input
                label="Senha atual"
                type="password"
                autoComplete="current-password"
                value={disablePwd}
                onChange={(e) => setDisablePwd(e.target.value)}
              />
              <Button variant="danger" onClick={disable2fa} loading={busy2fa} disabled={!disablePwd}>
                Desativar 2FA
              </Button>
            </div>
          </div>
        )}

        {!user.totp_enabled && !setup && (
          <div>
            <Button onClick={start2fa} loading={busy2fa}>
              Ativar 2FA
            </Button>
          </div>
        )}

        {setup && (
          <div className="flex flex-col gap-4 rounded-card border border-surface-border p-4 sm:flex-row sm:items-start">
            <div
              className="mx-auto h-44 w-44 shrink-0 [&>svg]:h-full [&>svg]:w-full"
              // eslint-disable-next-line react/no-danger
              dangerouslySetInnerHTML={{ __html: setup.qr_svg }}
            />
            <div className="flex flex-1 flex-col gap-3">
              <p className="text-sm">
                1. Escaneie o QR code no app autenticador. Se não conseguir escanear, use a chave
                manual:
              </p>
              <code className="select-all break-all rounded bg-bg-subtle px-2 py-1 text-sm">
                {setup.secret}
              </code>
              <p className="text-sm">2. Digite o código de 6 dígitos gerado pelo app:</p>
              <div className="flex flex-wrap items-end gap-3">
                <Input
                  label="Código"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                />
                <Button onClick={confirm2fa} loading={busy2fa} disabled={otpCode.trim().length < 6}>
                  Confirmar e ativar
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setSetup(null);
                    setOtpCode('');
                  }}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          </div>
        )}

        {recoveryCodes && (
          <div className="flex flex-col gap-3 rounded-card border border-warning bg-bg-subtle p-4">
            <p className="text-sm font-medium">
              Guarde estes códigos de recuperação num lugar seguro. Cada um funciona uma única vez e
              permite entrar se você perder o app autenticador.
            </p>
            <ul className="grid grid-cols-2 gap-1.5 font-mono text-sm sm:grid-cols-4">
              {recoveryCodes.map((c) => (
                <li key={c} className="select-all rounded bg-bg px-2 py-1 text-center">
                  {c}
                </li>
              ))}
            </ul>
            <div>
              <Button
                variant="secondary"
                onClick={() => {
                  void navigator.clipboard?.writeText(recoveryCodes.join('\n'));
                  toast.success('Códigos copiados.');
                }}
              >
                Copiar códigos
              </Button>
            </div>
            <button
              type="button"
              className="self-start text-sm text-text-muted underline"
              onClick={() => setRecoveryCodes(null)}
            >
              Já guardei, fechar
            </button>
          </div>
        )}
      </Card>
    </div>
  );
}
