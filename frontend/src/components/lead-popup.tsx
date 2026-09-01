'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { apiFetch } from '@/lib/api-client';
import { resolveMediaUrl } from '@/lib/media';
import { maskPhone } from '@/lib/phone';
import { track, identify } from '@/modules/analytics';

export interface LeadPopupConfig {
  enabled: boolean;
  title: string;
  subtitle: string;
  logoUrl: string | null;
  bg: string;
  text: string;
  btn: string;
  btnText: string;
}

/** Popup de captura de lead. Logo aparece metade "para fora" do topo. */
export function LeadPopup({
  open,
  onClose,
  config,
}: {
  open: boolean;
  onClose: () => void;
  config: LeadPopupConfig;
}) {
  const [form, setForm] = useState({ name: '', email: '', phone: '' });
  const [status, setStatus] = useState<'idle' | 'loading' | 'done'>('idle');
  const [coupon, setCoupon] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  if (!open) return null;
  const logo = resolveMediaUrl(config.logoUrl ?? undefined);
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!emailOk || status === 'loading') return;
    setStatus('loading');
    setErr(null);
    const res = await apiFetch<{ ok: boolean; coupon?: string | null }>('/api/newsletter/subscribe', {
      method: 'POST',
      body: { email: form.email.trim(), name: form.name.trim() || null, phone: form.phone.trim() || null, source: 'popup' },
    });
    if (res.ok) {
      identify({
        email: form.email.trim(),
        phone: form.phone.replace(/\D/g, '') || undefined,
        firstName: form.name.trim().split(/\s+/)[0] || undefined,
      });
      track('generate_lead', {});
      setCoupon(res.data.coupon ?? null);
      setStatus('done');
    } else {
      setStatus('idle');
      setErr('Não foi possível concluir o cadastro. Tente novamente.');
    }
  }

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={config.title}
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-sm rounded-2xl p-6 pt-14 shadow-xl"
        style={{ background: config.bg, color: config.text }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Logo: metade para fora do topo */}
        {logo && (
          <span className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2">
            <span className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-full bg-white shadow-md ring-4 ring-white">
              <Image src={logo} alt="" width={72} height={72} className="object-contain" />
            </span>
          </span>
        )}

        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar"
          className="absolute right-3 top-3 text-2xl leading-none opacity-60 hover:opacity-100"
          style={{ color: config.text }}
        >
          ×
        </button>

        {status === 'done' ? (
          <div className="flex flex-col gap-2 text-center">
            <p className="text-lg font-bold">Cadastro concluído! 🎉</p>
            {coupon ? (
              <>
                <p className="text-sm">Use o cupom na primeira compra:</p>
                <p className="rounded-lg border-2 border-dashed px-3 py-2 text-xl font-bold tracking-widest">
                  {coupon}
                </p>
                <p className="text-xs opacity-70">Enviamos também para o seu e-mail.</p>
              </>
            ) : (
              <p className="text-sm">Você receberá nossas novidades e promoções por e-mail.</p>
            )}
            <button
              type="button"
              onClick={onClose}
              className="mt-2 rounded-btn px-4 py-2 text-sm font-bold"
              style={{ background: config.btn, color: config.btnText }}
            >
              Continuar comprando
            </button>
          </div>
        ) : (
          <form onSubmit={submit} className="flex flex-col gap-3">
            <p className="text-center text-base font-bold leading-snug">{config.title}</p>
            {config.subtitle && (
              <p className="text-center text-sm opacity-80">{config.subtitle}</p>
            )}
            <input
              placeholder="Digite seu nome"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className="min-h-touch rounded-lg border-0 bg-black/5 px-3 text-sm outline-none"
            />
            <input
              type="email"
              required
              placeholder="Digite seu e-mail"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              className="min-h-touch rounded-lg border-0 bg-black/5 px-3 text-sm outline-none"
            />
            <input
              inputMode="numeric"
              placeholder="(11) 99999-9999"
              value={form.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: maskPhone(e.target.value) }))}
              className="min-h-touch rounded-lg border-0 bg-black/5 px-3 text-sm outline-none"
            />
            {err && <p className="text-xs text-danger">{err}</p>}
            <button
              type="submit"
              disabled={!emailOk || status === 'loading'}
              className="min-h-touch rounded-btn px-4 text-sm font-bold uppercase tracking-wide disabled:opacity-60"
              style={{ background: config.btn, color: config.btnText }}
            >
              {status === 'loading' ? 'Enviando…' : 'Cadastrar'}
            </button>
            <Link
              href="/pagina/politica-de-privacidade"
              className="text-center text-xs underline opacity-70"
            >
              Política de Privacidade
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}
