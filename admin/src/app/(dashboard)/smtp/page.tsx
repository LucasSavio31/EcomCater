'use client';

import { useState } from 'react';
import { Accordion, Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { smtpApi, type SmtpConfig, type SmtpDomain } from '@/modules/smtp/api';

// Mostrado no campo Senha sempre que já existe uma senha salva no servidor.
// Nunca é enviado de volta como senha nova.
const SAVED_MASK = '••••••••••••';

const EMPTY: SmtpConfig = {
  host: '',
  port: 587,
  username: '',
  password: '',
  use_tls: true,
  use_ssl: false,
  from_email: '',
  from_name: '',
  order_bcc: null,
};

/**
 * E-mail (SMTP) por domínio (multi-domínio): uma venda feita no domínio X
 * manda os e-mails pelo SMTP vinculado a X. O domínio principal usa o SMTP
 * de sempre — que também é o reserva de qualquer domínio sem SMTP próprio.
 */
export default function SmtpPage() {
  const { data, loading, error, reload } = useResource(() => smtpApi.domains());
  const [adding, setAdding] = useState('');
  // domínios com o formulário de SMTP próprio aberto (recém "adicionados")
  const [linking, setLinking] = useState<string[]>([]);

  const unlinked = (data ?? []).filter((d) => !d.is_primary && d.uses_primary);

  function addSmtp(): void {
    if (!adding) return;
    setLinking((l) => (l.includes(adding) ? l : [...l, adding]));
    setAdding('');
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="E-mail (SMTP)"
        description="Servidor de e-mail de cada domínio. Os e-mails de uma venda (pedido recebido, pago, enviado…) e de recuperação de senha saem pelo SMTP do domínio onde o cliente comprou."
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {data && (
          <div className="flex max-w-3xl flex-col gap-4">
            <Card variant="outline" className="flex flex-col gap-2">
              <div className="flex flex-wrap items-end gap-3">
                <Select
                  label="Adicionar SMTP para o domínio"
                  placeholder={unlinked.length ? 'Escolha o domínio' : 'Nenhum domínio sem SMTP'}
                  options={unlinked.map((d) => ({ value: d.hostname, label: d.hostname }))}
                  value={adding}
                  onChange={(e) => setAdding(e.target.value)}
                  disabled={unlinked.length === 0}
                  className="min-w-64 flex-1"
                />
                <Button variant="outline" onClick={addSmtp} disabled={!adding}>
                  Adicionar SMTP
                </Button>
              </div>
              <p className="text-xs text-text-muted">
                {unlinked.length
                  ? 'Escolha o domínio e preencha o SMTP dele — as vendas feitas nesse domínio passam a mandar e-mail por ele.'
                  : 'Para adicionar outro SMTP, conecte primeiro o domínio em Infraestrutura → Domínios; ele aparece aqui para você vincular o SMTP.'}
              </p>
            </Card>

            <Accordion
              key={linking.join(',')}
              multiple
              defaultOpen={[
                ...(data.length === 1 && data[0] ? [data[0].hostname] : []),
                ...linking,
              ]}
              items={data.map((d) => ({
                id: d.hostname,
                title: (
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{d.hostname}</span>
                    {d.is_primary && (
                      <span className="rounded-full bg-blue-600/10 px-2 py-0.5 text-xs font-medium text-blue-600">
                        principal
                      </span>
                    )}
                    <span className="text-xs font-normal text-text-muted">
                      {d.uses_primary
                        ? 'usando o SMTP principal'
                        : d.smtp.configured
                          ? `${d.smtp.from_email || d.smtp.host}`
                          : 'SMTP não configurado'}
                    </span>
                  </span>
                ),
                content:
                  d.uses_primary && !linking.includes(d.hostname) ? (
                    <div className="flex flex-col items-start gap-3 pt-2 text-text">
                      <p className="text-sm text-text-muted">
                        Este domínio ainda não tem SMTP próprio — os e-mails das vendas feitas nele
                        saem pelo SMTP do domínio principal.
                      </p>
                      <Button
                        variant="outline"
                        onClick={() => setLinking((l) => [...l, d.hostname])}
                      >
                        Vincular um SMTP a este domínio
                      </Button>
                    </div>
                  ) : (
                    <SmtpForm
                      domain={d}
                      onSaved={async () => {
                        setLinking((l) => l.filter((h) => h !== d.hostname));
                        await reload();
                      }}
                    />
                  ),
              }))}
            />
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}

function SmtpForm({ domain, onSaved }: { domain: SmtpDomain; onSaved: () => Promise<void> }) {
  const toast = useToast();
  const initial: SmtpConfig = {
    ...EMPTY,
    ...Object.fromEntries(Object.entries(domain.smtp).filter(([, v]) => v !== null && v !== undefined)),
    password: domain.smtp.password_set ? SAVED_MASK : '',
  } as SmtpConfig;
  const [draft, setDraft] = useState<SmtpConfig | null>(null);
  const cfg = draft ?? initial;
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [testTo, setTestTo] = useState('');
  const [testing, setTesting] = useState(false);

  const set = <K extends keyof SmtpConfig>(k: K, v: SmtpConfig[K]): void => setDraft({ ...cfg, [k]: v });

  async function save(): Promise<void> {
    setSaving(true);
    // só manda a senha se o usuário realmente digitou outra (não o mascarão)
    const body: Partial<SmtpConfig> = { ...cfg };
    if (body.password === SAVED_MASK || !body.password) delete body.password;
    const result = domain.is_primary
      ? await smtpApi.put(body)
      : await smtpApi.putDomain(domain.hostname, body);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success(`SMTP de ${domain.hostname} salvo.`);
    setDraft(null);
    await onSaved();
  }

  async function remove(): Promise<void> {
    if (!window.confirm(`Desvincular o SMTP de ${domain.hostname}? Os e-mails dele voltam a sair pelo SMTP principal.`)) {
      return;
    }
    setRemoving(true);
    const result = await smtpApi.removeDomain(domain.hostname);
    setRemoving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success(`${domain.hostname} voltou a usar o SMTP principal.`);
    await onSaved();
  }

  async function sendTest(): Promise<void> {
    if (!testTo.trim()) return;
    setTesting(true);
    const result = await smtpApi.test(testTo.trim(), domain.is_primary ? undefined : domain.hostname);
    setTesting(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success(`E-mail de teste enviado para ${testTo.trim()} pelo SMTP de ${domain.hostname}.`);
  }

  return (
    <div className="flex flex-col gap-4 pt-2 text-text">
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label="Host" value={cfg.host} onChange={(e) => set('host', e.target.value)} />
        <Input
          label="Porta"
          inputMode="numeric"
          value={String(cfg.port)}
          onChange={(e) => set('port', Number(e.target.value) || 0)}
        />
        <Input label="Usuário" value={cfg.username} onChange={(e) => set('username', e.target.value)} />
        <Input
          label="Senha"
          type="password"
          value={cfg.password}
          onFocus={(e) => {
            if (e.target.value === SAVED_MASK) set('password', '');
          }}
          onChange={(e) => set('password', e.target.value)}
          hint={
            domain.smtp.password_set
              ? 'Há uma senha salva. Deixe o mascarão para mantê-la; digite outra para trocar.'
              : 'Para Gmail use uma Senha de app de 16 caracteres (não a senha da conta).'
          }
        />
        <Input
          label="Remetente (e-mail)"
          value={cfg.from_email}
          onChange={(e) => set('from_email', e.target.value)}
          hint={domain.is_primary ? undefined : `Ideal: um endereço @${domain.hostname}.`}
        />
        <Input label="Remetente (nome)" value={cfg.from_name} onChange={(e) => set('from_name', e.target.value)} />
      </div>
      <Input
        label="Cópia oculta dos e-mails de pedido (Bcc)"
        type="email"
        placeholder="copia@empresa.com"
        value={cfg.order_bcc ?? ''}
        onChange={(e) => set('order_bcc', e.target.value)}
        hint="Recebe uma cópia de TODOS os e-mails de pedido que o cliente deste domínio recebe. Não recebe os e-mails de conta/acesso. Deixe em branco para desligar."
      />
      <div className="flex flex-wrap gap-4">
        <Checkbox label="Usar TLS (porta 587 / STARTTLS)" checked={cfg.use_tls} onChange={(v) => set('use_tls', v)} />
        <Checkbox label="Usar SSL (porta 465 / TLS implícito)" checked={cfg.use_ssl} onChange={(v) => set('use_ssl', v)} />
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button loading={saving} onClick={() => void save()}>
          Salvar SMTP de {domain.hostname}
        </Button>
        {!domain.is_primary && !domain.uses_primary && (
          <Button variant="outline" loading={removing} onClick={() => void remove()}>
            Desvincular (usar o principal)
          </Button>
        )}
      </div>

      <div className="flex flex-col gap-2 border-t border-surface-border pt-4">
        <h2 className="text-sm font-semibold">Enviar e-mail de teste por este SMTP</h2>
        <div className="flex flex-wrap items-end gap-2">
          <Input
            label="Destinatário"
            type="email"
            value={testTo}
            onChange={(e) => setTestTo(e.target.value)}
            className="flex-1"
          />
          <Button variant="outline" loading={testing} onClick={() => void sendTest()}>
            Enviar teste
          </Button>
        </div>
        <p className="text-xs text-text-muted">
          Salve antes de testar. Se falhar, a mensagem exata do servidor SMTP aparece no aviso de erro.
        </p>
      </div>
    </div>
  );
}
