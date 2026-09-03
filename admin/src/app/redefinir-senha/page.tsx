'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button, Card, Input } from '@ecom/ui';
import { resetPassword } from '@/modules/auth';

export default function AdminResetPage() {
  return (
    <Suspense fallback={null}>
      <ResetForm />
    </Suspense>
  );
}

function ResetForm() {
  const router = useRouter();
  const token = useSearchParams().get('token') ?? '';
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const valid = pw.length >= 8 && pw === pw2;

  async function submit(): Promise<void> {
    if (!valid || busy) return;
    setBusy(true);
    setErr(null);
    const r = await resetPassword(token, pw);
    setBusy(false);
    if (r.ok) setDone(true);
    else setErr(r.error.message || 'Link inválido ou expirado. Peça um novo.');
  }

  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <Card variant="elevated" className="flex w-full max-w-sm flex-col gap-4">
        <h1 className="text-xl font-bold">Criar nova senha do painel</h1>

        {!token ? (
          <p className="text-sm">
            Link inválido. Peça um novo em <a href="esqueci-senha" className="underline">Recuperar senha</a>.
          </p>
        ) : done ? (
          <>
            <p className="text-sm">Senha alterada com sucesso. ✅</p>
            <Button block onClick={() => router.replace('/login')}>
              Ir para o login
            </Button>
          </>
        ) : (
          <>
            <Input
              label="Nova senha"
              type="password"
              autoComplete="new-password"
              value={pw}
              onChange={(e) => setPw(e.target.value)}
              hint="Mínimo de 8 caracteres."
            />
            <Input
              label="Repita a nova senha"
              type="password"
              autoComplete="new-password"
              value={pw2}
              onChange={(e) => setPw2(e.target.value)}
              error={pw2 && pw !== pw2 ? 'As senhas não conferem' : undefined}
            />
            {err && <p className="text-sm text-danger">{err}</p>}
            <Button block loading={busy} disabled={!valid} onClick={() => void submit()}>
              Salvar nova senha
            </Button>
          </>
        )}
      </Card>
    </div>
  );
}
