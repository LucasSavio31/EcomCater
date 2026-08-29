'use client';

import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Card, Input } from '@ecom/ui';
import { fetchMe, login } from '@/modules/auth';
import { hasSession } from '@/lib/auth-storage';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (hasSession()) router.replace('/');
  }, [router]);

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

    const me = await fetchMe();
    if (me.ok && me.data.must_change_password) {
      router.replace('/change-password');
      return;
    }
    router.replace('/');
  }

  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <Card variant="elevated" className="w-full max-w-sm">
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
          <Input
            label="Senha"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}

          <Button type="submit" block loading={submitting}>
            Entrar
          </Button>
        </form>
      </Card>
    </div>
  );
}
