'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button, Card, Input } from '@ecom/ui';
import { customerApi } from '@/modules/customer/api';
import { maskCpf, onlyDigits } from '@/lib/cpf';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function EsqueciSenhaPage() {
  const [tab, setTab] = useState<'senha' | 'email'>('senha');

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-6 py-4">
      <h1 className="text-xl font-semibold sm:text-2xl">Recuperar acesso</h1>

      <div className="flex gap-2 rounded-card border border-surface-border p-1">
        {(['senha', 'email'] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium ${
              tab === t ? 'bg-primary text-primary-fg' : 'text-text-muted'
            }`}
          >
            {t === 'senha' ? 'Esqueci a senha' : 'Esqueci o e-mail'}
          </button>
        ))}
      </div>

      {tab === 'senha' ? <ForgotPassword /> : <RecoverEmail />}

      <p className="text-center text-sm text-text-muted">
        <Link href="/minha-conta" className="text-primary hover:underline">
          Voltar para o login
        </Link>
      </p>
    </div>
  );
}

function ForgotPassword() {
  const [by, setBy] = useState<'email' | 'cpf'>('email');
  const [email, setEmail] = useState('');
  const [cpf, setCpf] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const valid = by === 'email' ? EMAIL_RE.test(email) : onlyDigits(cpf).length === 11;

  async function submit() {
    if (!valid || busy) return;
    setBusy(true);
    await customerApi.forgotPassword(
      by === 'email' ? { email: email.trim() } : { cpf: onlyDigits(cpf) },
    );
    setBusy(false);
    setDone(true);
  }

  if (done) {
    return (
      <Card variant="outline" className="text-sm">
        Se existir uma conta com esse dado, enviamos um <b>link de redefinição</b> para o e-mail
        cadastrado. O link vale por 30 minutos. Confira também o spam.
      </Card>
    );
  }

  return (
    <Card variant="outline" className="flex flex-col gap-4">
      <p className="text-sm text-text-muted">
        Enviamos um link para você criar uma nova senha.
      </p>
      <div className="flex gap-3 text-sm">
        <label className="flex items-center gap-1">
          <input type="radio" checked={by === 'email'} onChange={() => setBy('email')} /> por e-mail
        </label>
        <label className="flex items-center gap-1">
          <input type="radio" checked={by === 'cpf'} onChange={() => setBy('cpf')} /> por CPF
        </label>
      </div>
      {by === 'email' ? (
        <Input
          label="E-mail cadastrado"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      ) : (
        <Input
          label="CPF"
          inputMode="numeric"
          value={cpf}
          onChange={(e) => setCpf(maskCpf(e.target.value))}
        />
      )}
      <Button loading={busy} disabled={!valid} onClick={() => void submit()}>
        Enviar link
      </Button>
    </Card>
  );
}

function RecoverEmail() {
  const [cpf, setCpf] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ found: boolean; email_masked?: string } | null>(null);

  async function submit() {
    if (onlyDigits(cpf).length !== 11 || busy) return;
    setBusy(true);
    const r = await customerApi.recoverEmail(onlyDigits(cpf));
    setBusy(false);
    setResult(r.ok ? r.data : { found: false });
  }

  return (
    <Card variant="outline" className="flex flex-col gap-4">
      <p className="text-sm text-text-muted">
        Informe seu CPF e mostramos o e-mail (parcialmente oculto) da conta.
      </p>
      <Input
        label="CPF"
        inputMode="numeric"
        value={cpf}
        onChange={(e) => setCpf(maskCpf(e.target.value))}
      />
      <Button loading={busy} disabled={onlyDigits(cpf).length !== 11} onClick={() => void submit()}>
        Mostrar e-mail
      </Button>
      {result &&
        (result.found ? (
          <p className="rounded-card border border-surface-border bg-surface p-3 text-sm">
            E-mail da conta: <b>{result.email_masked}</b>
          </p>
        ) : (
          <p className="text-sm text-text-muted">Nenhuma conta encontrada com esse CPF.</p>
        ))}
    </Card>
  );
}
