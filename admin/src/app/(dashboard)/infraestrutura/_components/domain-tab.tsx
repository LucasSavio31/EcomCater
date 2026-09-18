'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import {
  domainsApi,
  type CachePageOption,
  type CredentialsTestResult,
  type DomainRecord,
  type DomainStatus,
} from '@/modules/domains/api';

function StatusPill({ status }: { status: DomainStatus }) {
  const map: Record<DomainStatus, string> = {
    active: 'border-success text-success',
    provisioning: 'border-warning text-warning',
    dns_pending: 'border-warning text-warning',
    awaiting_nameservers: 'border-warning text-warning',
    pending: 'border-text-muted text-text-muted',
    failed: 'border-danger text-danger',
  };
  const label: Record<DomainStatus, string> = {
    active: 'Ativo',
    provisioning: 'Configurando…',
    dns_pending: 'Pendente de DNS',
    awaiting_nameservers: 'Aguardando nameservers',
    pending: 'Pendente',
    failed: 'Erro',
  };
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${map[status]}`}>
      {label[status]}
    </span>
  );
}

function NameserverInstructions({ domain }: { domain: DomainRecord }) {
  const toast = useToast();
  const copy = (text: string) => {
    void navigator.clipboard.writeText(text);
    toast.success('Copiado.');
  };
  return (
    <div className="flex flex-col gap-2 rounded-card border border-warning bg-bg-subtle p-3 text-xs">
      <p className="text-text-muted">
        Domínio novo pra Cloudflare: crie a zona lá, mas falta apontar o{' '}
        <b>registrador</b> (onde você comprou o domínio) pra ela. Troque os nameservers do
        domínio nestes exatamente — isso substitui os nameservers atuais, não é um registro
        dentro do DNS:
      </p>
      <ul className="flex flex-col gap-1">
        {(domain.cloudflare_nameservers ?? []).map((ns) => (
          <li key={ns} className="flex items-center gap-2">
            <code className="rounded bg-surface px-1.5 py-0.5">{ns}</code>
            <button type="button" className="text-accent underline" onClick={() => copy(ns)}>
              copiar
            </button>
          </li>
        ))}
      </ul>
      <p className="text-text-muted">
        A propagação pode levar de minutos a algumas horas. Checamos sozinhos a cada 5 min e
        seguimos com SSL/proxy assim que confirmar — sem precisar voltar aqui.
      </p>
    </div>
  );
}

function DnsInstructions({ domain, serverIp }: { domain: DomainRecord; serverIp: string }) {
  const toast = useToast();
  const copy = (text: string) => {
    void navigator.clipboard.writeText(text);
    toast.success('Copiado.');
  };
  const rows: { type: string; name: string; content: string }[] = [
    { type: 'A', name: domain.hostname, content: serverIp || '(informe o IP da VPS em Credenciais)' },
    { type: 'CNAME', name: domain.admin_hostname, content: domain.hostname },
    { type: 'CNAME', name: domain.api_hostname, content: domain.hostname },
  ];
  return (
    <div className="flex flex-col gap-2 rounded-card border border-surface-border bg-bg-subtle p-3 text-xs">
      <p className="text-text-muted">
        Crie estes registros no DNS do domínio (Cloudflare ou outro provedor). O registro raiz
        precisa ser <b>A</b>, não CNAME — limitação de DNS.
      </p>
      <table className="w-full text-left">
        <thead>
          <tr className="text-text-muted">
            <th className="pr-3 font-medium">Tipo</th>
            <th className="pr-3 font-medium">Nome</th>
            <th className="pr-3 font-medium">Valor</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.name}>
              <td className="pr-3 py-0.5">{r.type}</td>
              <td className="pr-3 py-0.5">{r.name}</td>
              <td className="pr-3 py-0.5">{r.content}</td>
              <td className="py-0.5">
                <button
                  type="button"
                  className="text-accent underline"
                  onClick={() => copy(r.content)}
                >
                  copiar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SeoLinksSection({ hostname }: { hostname: string }) {
  const toast = useToast();
  const base = `https://${hostname}`;
  const links = [
    { label: 'Sitemap', href: `${base}/sitemap.xml` },
    { label: 'robots.txt', href: `${base}/robots.txt` },
    { label: 'llms.txt', href: `${base}/llms.txt` },
  ];
  const copy = (text: string) => {
    void navigator.clipboard.writeText(text);
    toast.success('Copiado.');
  };
  return (
    <div className="flex flex-col gap-2 rounded-card border border-surface-border p-3">
      <h3 className="text-sm font-semibold">URLs de SEO</h3>
      <p className="text-xs text-text-muted">
        Gerados sozinhos a partir do catálogo/tema/páginas atuais — nada fixo, atualiza junto com
        o site.
      </p>
      <ul className="flex flex-col gap-1 text-sm">
        {links.map((l) => (
          <li key={l.href} className="flex items-center gap-2">
            <a href={l.href} target="_blank" rel="noreferrer" className="text-accent underline">
              {l.href}
            </a>
            <button type="button" className="text-xs text-text-muted underline" onClick={() => copy(l.href)}>
              copiar
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

const ALWAYS_BYPASS_LABEL =
  'Carrinho, Checkout, Minha conta, Favoritos e recuperação de senha nunca são cacheados — regra fixa, não dá pra desmarcar.';

function CacheSection({
  domain,
  options,
  onSave,
  onPurge,
}: {
  domain: DomainRecord;
  options: CachePageOption[];
  onSave: (pages: string[]) => Promise<void>;
  onPurge: () => Promise<void>;
}) {
  const [draft, setDraft] = useState<string[]>(domain.cache_pages);
  const [saving, setSaving] = useState(false);
  const [purging, setPurging] = useState(false);
  const dirty = JSON.stringify([...draft].sort()) !== JSON.stringify([...domain.cache_pages].sort());

  const toggle = (key: string, checked: boolean) => {
    setDraft((cur) => (checked ? [...cur, key] : cur.filter((k) => k !== key)));
  };

  const save = async () => {
    setSaving(true);
    await onSave(draft);
    setSaving(false);
  };

  const purge = async () => {
    if (!confirm('Limpar todo o cache da Cloudflare pra este domínio? A próxima visita de cada página busca conteúdo fresco na origem (pode deixar o site um pouco mais lento por alguns minutos, até o cache se refazer).')) {
      return;
    }
    setPurging(true);
    await onPurge();
    setPurging(false);
  };

  return (
    <div className="flex flex-col gap-2 rounded-card border border-surface-border p-3">
      <h3 className="text-sm font-semibold">Cache na Cloudflare</h3>
      <p className="text-xs text-text-muted">{ALWAYS_BYPASS_LABEL}</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {options.map((opt) => (
          <Checkbox
            key={opt.key}
            label={`${opt.label} (${opt.ttl_seconds}s)`}
            hint={opt.description}
            checked={draft.includes(opt.key)}
            onChange={(v) => toggle(opt.key, v)}
          />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" loading={saving} disabled={!dirty} onClick={() => void save()}>
          Salvar cache
        </Button>
        <Button size="sm" variant="outline" loading={purging} onClick={() => void purge()}>
          Limpar cache agora
        </Button>
        {domain.cache_applied_at && (
          <span className="text-xs text-text-muted">
            Aplicado em {new Date(domain.cache_applied_at).toLocaleString('pt-BR')}
          </span>
        )}
      </div>
    </div>
  );
}

export function DomainTab() {
  const toast = useToast();
  const stateRes = useResource(() => domainsApi.getState());

  const [aapanelUrl, setAapanelUrl] = useState('');
  const [aapanelKey, setAapanelKey] = useState('');
  const [cloudflareToken, setCloudflareToken] = useState('');
  const [serverIp, setServerIp] = useState('');
  const [savingCreds, setSavingCreds] = useState(false);
  const [testingCreds, setTestingCreds] = useState(false);
  const [testResult, setTestResult] = useState<CredentialsTestResult | null>(null);

  const [newHostname, setNewHostname] = useState('');
  const [addingDomain, setAddingDomain] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const draftCreds = () => ({
    aapanel_url: aapanelUrl.trim() || undefined,
    aapanel_api_key: aapanelKey.trim() || undefined,
    cloudflare_api_token: cloudflareToken.trim() || undefined,
    server_ip: serverIp.trim() || undefined,
  });

  const testCredentials = async () => {
    setTestingCreds(true);
    setTestResult(null);
    const res = await domainsApi.testCredentials(draftCreds());
    setTestingCreds(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    setTestResult(res.data);
  };

  const saveCredentials = async () => {
    setSavingCreds(true);
    const res = await domainsApi.saveCredentials(draftCreds());
    setSavingCreds(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('Credenciais salvas.');
    setAapanelKey('');
    setCloudflareToken('');
    stateRes.setData(res.data);
  };

  const addDomain = async () => {
    const hostname = newHostname.trim().toLowerCase();
    if (!hostname) return;
    setAddingDomain(true);
    const res = await domainsApi.addOrUpdateDomain(hostname);
    setAddingDomain(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success(
      res.data.status === 'active' ? 'Domínio ativo!' : 'Domínio cadastrado — acompanhe o status abaixo.',
    );
    setNewHostname('');
    stateRes.reload();
  };

  const retry = async (id: string) => {
    setBusyId(id);
    const res = await domainsApi.retry(id);
    setBusyId(null);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success(res.data.status === 'active' ? 'Domínio ativo!' : 'Nova tentativa registrada.');
    stateRes.reload();
  };

  const setPrimary = async (id: string) => {
    if (
      !confirm(
        'Tornar este o domínio principal? A loja/admin/API passam a usar este domínio em até alguns minutos (o servidor troca as variáveis e rebuilda sozinho).',
      )
    ) {
      return;
    }
    setBusyId(id);
    const res = await domainsApi.setPrimary(id);
    setBusyId(null);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('Troca solicitada — aplicando no servidor em até alguns minutos.');
    stateRes.reload();
  };

  const saveCachePages = async (id: string, pages: string[]) => {
    const res = await domainsApi.saveCachePages(id, pages);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('Regras de cache aplicadas na Cloudflare.');
    stateRes.reload();
  };

  const purgeCache = async (id: string) => {
    const res = await domainsApi.purgeCache(id);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('Cache da Cloudflare limpo — próximas visitas buscam conteúdo fresco.');
  };

  const remove = async (d: DomainRecord) => {
    const msg = d.is_primary
      ? 'Remover o domínio PRINCIPAL? A loja/admin/API voltam a responder direto por IP:PORTA (sem TLS) em até alguns minutos, até você cadastrar outro domínio. Isso não desfaz o vhost/SSL já criados no aaPanel.'
      : 'Remover este domínio da lista? Isso não desfaz o vhost/SSL já criados no aaPanel.';
    if (!confirm(msg)) {
      return;
    }
    const id = d.id;
    setBusyId(id);
    const res = await domainsApi.remove(id);
    setBusyId(null);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    stateRes.reload();
  };

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary loading={stateRes.loading} error={stateRes.error} onRetry={stateRes.reload}>
        {stateRes.data && (
          <>
            <Card variant="outline" className="flex flex-col gap-4">
              <div>
                <h2 className="text-base font-semibold">Credenciais de automação</h2>
                <p className="text-sm text-text-muted">
                  Usadas pra criar o proxy reverso + SSL (aaPanel) e, opcionalmente, os registros
                  de DNS (Cloudflare) sozinho ao salvar um domínio abaixo. Sem a Cloudflare, o DNS
                  fica manual — a tela sempre mostra as instruções.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="URL do aaPanel"
                  value={aapanelUrl}
                  onChange={(e) => setAapanelUrl(e.target.value)}
                  placeholder={stateRes.data.aapanel_url || 'http://127.0.0.1:7800'}
                  hint="Painel → Configurações → API"
                />
                <Input
                  label="API key do aaPanel"
                  type="password"
                  value={aapanelKey}
                  onChange={(e) => setAapanelKey(e.target.value)}
                  placeholder={
                    stateRes.data.has_aapanel
                      ? '•••••••• configurada (deixe em branco p/ manter)'
                      : ''
                  }
                />
                <Input
                  label="Token da Cloudflare (opcional)"
                  type="password"
                  value={cloudflareToken}
                  onChange={(e) => setCloudflareToken(e.target.value)}
                  placeholder={
                    stateRes.data.has_cloudflare
                      ? '•••••••• configurado (deixe em branco p/ manter)'
                      : 'API Token com permissão Zone / DNS / Edit'
                  }
                />
                <Input
                  label="IP público da VPS"
                  value={serverIp}
                  onChange={(e) => setServerIp(e.target.value)}
                  placeholder={stateRes.data.server_ip || '167.86.92.107'}
                  hint="Usado nas instruções de DNS (registro A)"
                />
              </div>
              {testResult && (
                <div className="flex flex-col gap-1 text-sm">
                  <span className={testResult.aapanel_ok ? 'text-success' : 'text-danger'}>
                    aaPanel: {testResult.aapanel_message}
                  </span>
                  <span className={testResult.cloudflare_ok ? 'text-success' : 'text-text-muted'}>
                    Cloudflare: {testResult.cloudflare_message}
                  </span>
                </div>
              )}
              <div className="flex gap-3">
                <Button variant="outline" loading={testingCreds} onClick={() => void testCredentials()}>
                  Testar conexão
                </Button>
                <Button loading={savingCreds} onClick={() => void saveCredentials()}>
                  Salvar credenciais
                </Button>
              </div>
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-base font-semibold">Adicionar / trocar domínio</h2>
              <div className="flex flex-wrap items-end gap-3">
                <Input
                  label="Domínio raiz"
                  value={newHostname}
                  onChange={(e) => setNewHostname(e.target.value)}
                  placeholder="minhaloja.com.br"
                  hint="admin.minhaloja.com.br e api.minhaloja.com.br são criados junto, automaticamente"
                />
                <Button loading={addingDomain} onClick={() => void addDomain()}>
                  Salvar
                </Button>
              </div>
            </Card>

            <div className="flex flex-col gap-4">
              {stateRes.data.domains.length === 0 && (
                <p className="text-sm text-text-muted">Nenhum domínio cadastrado ainda.</p>
              )}
              {stateRes.data.domains.map((d) => (
                <Card key={d.id} variant="outline" className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{d.hostname}</span>
                      {d.is_primary && (
                        <span className="rounded-full border border-surface-border px-2 py-0.5 text-xs text-text-muted">
                          principal
                        </span>
                      )}
                      <StatusPill status={d.status} />
                    </div>
                    <div className="flex gap-2">
                      {(d.status === 'failed' ||
                        d.status === 'dns_pending' ||
                        d.status === 'awaiting_nameservers' ||
                        (d.status === 'active' && d.ssl_status === 'error')) && (
                        <Button
                          size="sm"
                          variant="outline"
                          loading={busyId === d.id}
                          onClick={() => void retry(d.id)}
                        >
                          Tentar novamente
                        </Button>
                      )}
                      {d.status === 'active' && !d.is_primary && (
                        <Button
                          size="sm"
                          variant="outline"
                          loading={busyId === d.id}
                          onClick={() => void setPrimary(d.id)}
                        >
                          Tornar principal
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-danger"
                        loading={busyId === d.id}
                        onClick={() => void remove(d)}
                      >
                        Remover
                      </Button>
                    </div>
                  </div>
                  <p className="text-sm text-text-muted">
                    Admin: {d.admin_hostname} · API: {d.api_hostname}
                  </p>
                  {d.switch_requested_at && (
                    <p className="text-xs text-text-muted">
                      Troca de domínio pedida em {new Date(d.switch_requested_at).toLocaleString('pt-BR')} — o
                      servidor aplica sozinho em até alguns minutos.
                    </p>
                  )}
                  {d.last_error && <p className="text-sm text-danger">{d.last_error}</p>}
                  {d.status === 'awaiting_nameservers' ? (
                    <NameserverInstructions domain={d} />
                  ) : d.dns_managed_by_cloudflare ? (
                    <p className="text-sm text-success">DNS criado automaticamente via Cloudflare ✓</p>
                  ) : (
                    <DnsInstructions domain={d} serverIp={stateRes.data!.server_ip} />
                  )}
                  {d.status === 'active' && <SeoLinksSection hostname={d.hostname} />}
                  {d.dns_confirmed && (
                    <CacheSection
                      domain={d}
                      options={stateRes.data!.cache_page_options}
                      onSave={(pages) => saveCachePages(d.id, pages)}
                      onPurge={() => purgeCache(d.id)}
                    />
                  )}
                </Card>
              ))}
            </div>
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
