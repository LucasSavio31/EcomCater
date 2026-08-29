'use client';

import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Card, Input } from '@ecom/ui';
import { changePassword } from '@/modules/auth';
import { hasSession } from '@/lib/auth-storage';

export default function ChangePasswordPage() {
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!hasSession()) router.replace('/login');
  }, [router]);

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);

    if (newPassword.length < 8) {
      setError('A nova senha precisa ter ao menos 8 caracteres.');
      return;
    }
    if (newPassword !== confirm) {
      setError('A confirmação não confere.');
      return;
    }

    setSubmitting(true);
    const result = await changePassword(currentPassword, newPassword);
    if (!result.ok) {
      setError(result.error.message);
      setSubmitting(false);
      return;
    }
    router.replace('/');
  }

  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <Card variant="elevated" className="w-full max-w-sm">
        <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-bold">Trocar senha</h1>
            <p className="text-sm text-text-muted">
              Obrigatório no primeiro acesso. Defina uma nova senha para continuar.
            </p>
          </div>

          <Input
            label="Senha atual"
            type="password"
            autoComplete="current-password"
            required
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
          <Input
            label="Nova senha"
            type="password"
            autoComplete="new-password"
            required
            hint="Mínimo de 8 caracteres."
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <Input
            label="Confirmar nova senha"
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />

          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}

          <Button type="submit" block loading={submitting}>
            Salvar nova senha
          </Button>
        </form>
      </Card>
    </div>
  );
}
