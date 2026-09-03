'use client';

import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Card, Input } from '@ecom/ui';
import { fetchMe, login, verifyMfa } from '@/modules/auth';
import { hasSession } from '@/lib/auth-storage';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [code, setCode] = useState('');

  useEffect(() => {
    if (hasSession()) router.replace('/');
  }, [router]);

  async function finish(): Promise<void> {
    const me = await fetchMe();
    if (me.ok && me.data.must_change_password) {
      router.replace('/change-password');
      return;
    }
    router.replace('/');
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    const result = await login(email.trim(), password);
    if (!result.ok) {
      setError(result.error.message);
      setSubmitting(false);
      return;
    }
    if (result.mfaRequired) {
      setMfaToken(result.mfaToken);
      setSubmitting(false);
      return;
    }
    await finish();
  }

  async function onVerify(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!mfaToken) return;
    setError(null);
    setSubmitting(true);

    const result = await verifyMfa(mfaToken, code.trim());
    if (!result.ok) {
      setError(result.error.message);
      setSubmitting(false);
      return;
    }
    await finish();
  }

  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <Card variant="elevated" className="w-full max-w-sm">
        {mfaToken ? (
          <form onSubmit={onVerify} className="flex flex-col gap-4" noValidate>
            <div className="flex flex-col gap-1">
              <h1 className="text-xl font-bold">Verificação em duas etapas</h1>
              <p className="text-sm text-text-muted">
                Digite o código de 6 dígitos do app autenticador (ou um código de recuperação).
              </p>
            </div>

            <Input
              label="Código"
              inputMode="text"
              autoComplete="one-time-code"
              autoFocus
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />

            {error && (
              <p role="alert" className="text-sm text-danger">
                {error}
              </p>
            )}

            <Button type="submit" block loading={submitting}>
              Verificar
            </Button>
            <button
              type="button"
              className="text-sm text-text-muted underline"
              onClick={() => {
                setMfaToken(null);
                setCode('');
                setError(null);
              }}
            >
              Voltar
            </button>
          </form>
        ) : (
          <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
            <div className="flex flex-col gap-1">
              <h1 className="text-xl font-bold">Entrar no painel</h1>
              <p className="text-sm text-text-muted">Use suas credenciais de administrador.</p>
            </div>

            <Input
              label="E-mail"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <div className="relative">
              <Input
                label="Senha"
                type={showPw ? 'text' : 'password'}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-3 top-[34px] text-xs font-medium text-text-muted hover:text-text"
              >
                {showPw ? 'Ocultar' : 'Mostrar'}
              </button>
            </div>

            {error && (
              <p role="alert" className="text-sm text-danger">
                {error}
              </p>
            )}

            <Button type="submit" block loading={submitting}>
              Entrar
            </Button>
            <a
              href="esqueci-senha"
              className="text-center text-sm text-text-muted underline hover:text-text"
            >
              Esqueci minha senha
            </a>
          </form>
        )}
      </Card>
    </div>
  );
}
