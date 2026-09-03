'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { forgotPassword } from '@/modules/auth';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function AdminForgotPage() {
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function submit(): Promise<void> {
    if (!EMAIL_RE.test(email) || busy) return;
    setBusy(true);
    await forgotPassword(email.trim());
    setBusy(false);
    setDone(true);
  }

  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <Card variant="elevated" className="flex w-full max-w-sm flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-bold">Recuperar senha do painel</h1>
          <p className="text-sm text-text-muted">
            Enviamos um link de redefinição para o e-mail da conta de administrador.
          </p>
        </div>

        {done ? (
          <p className="text-sm">
            Se o e-mail estiver cadastrado, o link chega em instantes (vale por 30 minutos).
            Confira o spam.
          </p>
        ) : (
          <>
            <Input
              label="E-mail do administrador"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Button block loading={busy} disabled={!EMAIL_RE.test(email)} onClick={() => void submit()}>
              Enviar link
            </Button>
          </>
        )}
        <a href="login" className="text-center text-sm text-text-muted underline hover:text-text">
          Voltar para o login
        </a>
      </Card>
    </div>
  );
}
