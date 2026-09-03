'use client';

import { Suspense, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Button, Card, Input } from '@ecom/ui';
import { customerApi } from '@/modules/customer/api';

export default function RedefinirSenhaPage() {
  return (
    <Suspense fallback={null}>
      <ResetForm />
    </Suspense>
  );
}

function ResetForm() {
  const token = useSearchParams().get('token') ?? '';
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const valid = pw.length >= 6 && pw === pw2;

  async function submit() {
    if (!valid || busy) return;
    setBusy(true);
    setErr(null);
    const r = await customerApi.resetPassword({ token, new_password: pw });
    setBusy(false);
    if (r.ok) setDone(true);
    else setErr(r.error.message || 'Não foi possível redefinir. Peça um novo link.');
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-6 py-4">
      <h1 className="text-xl font-semibold sm:text-2xl">Criar nova senha</h1>

      {!token ? (
        <Card variant="outline" className="text-sm">
          Link inválido. Volte e peça um novo em{' '}
          <Link href="/esqueci-senha" className="text-primary hover:underline">
            Recuperar acesso
          </Link>
          .
        </Card>
      ) : done ? (
        <Card variant="outline" className="flex flex-col gap-3 text-sm">
          <p>Senha alterada com sucesso. ✅</p>
          <Link href="/minha-conta" className="text-primary hover:underline">
            Ir para o login
          </Link>
        </Card>
      ) : (
        <Card variant="outline" className="flex flex-col gap-4">
          <Input
            label="Nova senha"
            type="password"
            value={pw}
            onChange={(e) => setPw(e.target.value)}
            hint="Mínimo de 6 caracteres."
          />
          <Input
            label="Repita a nova senha"
            type="password"
            value={pw2}
            onChange={(e) => setPw2(e.target.value)}
            error={pw2 && pw !== pw2 ? 'As senhas não conferem' : undefined}
          />
          {err && <p className="text-sm text-danger">{err}</p>}
          <Button loading={busy} disabled={!valid} onClick={() => void submit()}>
            Salvar nova senha
          </Button>
        </Card>
      )}
    </div>
  );
}
