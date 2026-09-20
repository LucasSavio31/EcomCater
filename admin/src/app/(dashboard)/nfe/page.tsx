'use client';

import Link from 'next/link';
import { useRef, useState } from 'react';
import { Badge, Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { appearanceApi, type StoreSettings } from '@/modules/appearance/api';
import {
  nfeApi,
  nfeStatusLabel,
  nfeStatusTone,
  type NfeConfig,
  type NfeConnectionTest,
  type NfeDocumentOut,
} from '@/modules/nfe/api';
import { maskCep, maskCnpj, maskDigits } from '@/lib/br-masks';

const ADDR_FIELDS: Array<[keyof NonNullable<StoreSettings['address_json']>, string]> = [
  ['street', 'Rua'],
  ['number', 'Número'],
  ['complement', 'Complemento'],
  ['district', 'Bairro'],
  ['city', 'Cidade'],
  ['state', 'UF'],
  ['zip', 'CEP'],
];

export default function NfePage() {
  const toast = useToast();
  const storeRes = useResource(() => appearanceApi.getSettings());
  const cfgRes = useResource(() => nfeApi.getConfig());

  const [storeDraft, setStoreDraft] = useState<StoreSettings | null>(null);
  const [cfgDraft, setCfgDraft] = useState<NfeConfig | null>(null);
  const [savingStore, setSavingStore] = useState(false);
  const [savingCfg, setSavingCfg] = useState(false);
  const [certFile, setCertFile] = useState<File | null>(null);
  const [certSenha, setCertSenha] = useState('');
  const [certBusy, setCertBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const [testingConn, setTestingConn] = useState(false);
  const [connResult, setConnResult] = useState<NfeConnectionTest | null>(null);

  const [testOrderNumber, setTestOrderNumber] = useState('');
  const [testEmitBusy, setTestEmitBusy] = useState(false);
  const [testEmitResult, setTestEmitResult] = useState<NfeDocumentOut | null>(null);

  const store = storeDraft ?? storeRes.data;
  const cfg = cfgDraft ?? cfgRes.data;

  const setStore = <K extends keyof StoreSettings>(k: K, v: StoreSettings[K]): void => {
    if (!store) return;
    setStoreDraft({ ...store, [k]: v });
  };
  const setAddr = (k: string, v: string): void => {
    if (!store) return;
    setStoreDraft({ ...store, address_json: { ...(store.address_json ?? {}), [k]: v } });
  };
  const setCfg = <K extends keyof NfeConfig>(k: K, v: NfeConfig[K]): void => {
    if (!cfg) return;
    setCfgDraft({ ...cfg, [k]: v });
  };

  async function saveStore(): Promise<void> {
    if (!store) return;
    setSavingStore(true);
    const res = await appearanceApi.putSettings(store);
    setSavingStore(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success('Dados fiscais da empresa salvos.');
    storeRes.setData(res.data);
    setStoreDraft(null);
  }

  async function saveCfg(): Promise<void> {
    if (!cfg) return;
    setSavingCfg(true);
    const res = await nfeApi.putConfig(cfg);
    setSavingCfg(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success('Configuração de emissão salva.');
    cfgRes.setData(res.data);
    setCfgDraft(null);
  }

  async function uploadCert(): Promise<void> {
    if (!certFile || !certSenha) {
      toast.error('Selecione o arquivo .pfx e informe a senha.');
      return;
    }
    setCertBusy(true);
    const res = await nfeApi.uploadCertificate(certFile, certSenha);
    setCertBusy(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success('Certificado validado e salvo.');
    cfgRes.setData(res.data);
    setCfgDraft(null);
    setCertFile(null);
    setCertSenha('');
    if (fileRef.current) fileRef.current.value = '';
  }

  async function doTestConnection(): Promise<void> {
    setTestingConn(true);
    setConnResult(null);
    const res = await nfeApi.testConnection();
    setTestingConn(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    setConnResult(res.data);
    if (res.data.ok) toast.success('Conexão com a SEFAZ OK.');
    else toast.error(res.data.motivo || 'A SEFAZ recusou a consulta.');
  }

  async function doTestEmit(): Promise<void> {
    const number = testOrderNumber.trim();
    if (!number) {
      toast.error('Informe o número de um pedido existente.');
      return;
    }
    setTestEmitBusy(true);
    setTestEmitResult(null);
    const draftRes = await nfeApi.getDraft(number);
    if (!draftRes.ok) {
      setTestEmitBusy(false);
      toast.error(draftRes.error.message);
      return;
    }
    const res = await nfeApi.emit(number, draftRes.data);
    setTestEmitBusy(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    setTestEmitResult(res.data);
    if (res.data.status === 'authorized' || res.data.status === 'processing') {
      toast.success('NF-e de teste enviada com sucesso.');
    } else {
      toast.error(res.data.status_message || 'A SEFAZ recusou a NF-e de teste.');
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="NF-e"
        description="Configuração de emissão — dados fiscais, certificado digital e ambiente. Configure tudo aqui antes de emitir a primeira nota, sempre testando em homologação primeiro."
        actions={
          <div className="flex gap-4 text-sm">
            <Link href="/nfe/xml" className="text-accent hover:underline">
              → XML para o contador
            </Link>
            <Link href="/nfe/notas" className="text-accent hover:underline">
              → Notas emitidas
            </Link>
          </div>
        }
      />

      <AsyncBoundary loading={storeRes.loading} error={storeRes.error} onRetry={storeRes.reload}>
        {store && (
          <Card variant="outline" className="flex max-w-3xl flex-col gap-4">
            <h3 className="text-sm font-semibold">Dados fiscais da empresa (emitente)</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label="Razão social" value={store.legal_name ?? ''} onChange={(e) => setStore('legal_name', e.target.value)} />
              <Input label="CNPJ" value={maskCnpj(store.cnpj ?? '')} onChange={(e) => setStore('cnpj', maskCnpj(e.target.value))} />
              <Input label="Inscrição Estadual" value={store.ie ?? ''} onChange={(e) => setStore('ie', e.target.value)} />
              <Select
                label="Regime tributário"
                value={store.regime_tributario ?? '1'}
                options={[
                  { value: '1', label: 'Simples Nacional' },
                  { value: '2', label: 'Simples Nacional — excesso de sublimite' },
                  { value: '3', label: 'Regime Normal (Lucro Presumido/Real)' },
                ]}
                onChange={(e) => setStore('regime_tributario', e.target.value)}
              />
              <Input
                label="CNAE fiscal"
                value={maskDigits(store.cnae_fiscal ?? '', 7)}
                onChange={(e) => setStore('cnae_fiscal', maskDigits(e.target.value, 7))}
              />
              <Input
                label="Código IBGE do município (opcional)"
                hint="Deixe em branco para detectar automaticamente pela cidade/UF do endereço."
                value={maskDigits(store.municipio_ibge ?? '', 7)}
                onChange={(e) => setStore('municipio_ibge', maskDigits(e.target.value, 7))}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              {ADDR_FIELDS.map(([key, label]) => (
                <Input
                  key={key}
                  label={label}
                  value={key === 'zip' ? maskCep(store.address_json?.[key] ?? '') : (store.address_json?.[key] ?? '')}
                  onChange={(e) => setAddr(key, key === 'zip' ? maskCep(e.target.value) : e.target.value)}
                />
              ))}
            </div>
            {store.regime_tributario === '3' && (
              <p className="text-xs text-warning">
                Regime Normal ainda não é totalmente coberto pelo cálculo de imposto desta primeira
                versão (foco em Simples Nacional/CSOSN) — confirme com o contador antes de emitir em produção.
              </p>
            )}
            <Button size="sm" loading={savingStore} onClick={() => void saveStore()} className="self-start">
              Salvar dados da empresa
            </Button>
          </Card>
        )}
      </AsyncBoundary>

      <AsyncBoundary loading={cfgRes.loading} error={cfgRes.error} onRetry={cfgRes.reload}>
        {cfg && (
          <>
            <Card variant="outline" className="flex max-w-3xl flex-col gap-4">
              <h3 className="text-sm font-semibold">Configuração de emissão</h3>
              <Select
                label="Ambiente"
                value={cfg.ambiente}
                options={[
                  { value: 'homologacao', label: '🟡 Homologação — notas de teste, sem valor fiscal' },
                  { value: 'producao', label: '🔴 Produção — notas reais' },
                ]}
                onChange={(e) => setCfg('ambiente', e.target.value as NfeConfig['ambiente'])}
              />
              {cfg.ambiente === 'homologacao' ? (
                <p className="text-xs text-text-muted">
                  Modo de testes: as notas emitidas aqui vão pra SEFAZ de verdade, mas saem marcadas
                  &quot;SEM VALOR FISCAL&quot; — use pra validar o fluxo completo antes de ligar produção.
                </p>
              ) : (
                <p className="text-xs text-danger">Produção: as notas emitidas aqui têm valor fiscal real.</p>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Série"
                  inputMode="numeric"
                  value={String(cfg.serie_nfe)}
                  onChange={(e) => setCfg('serie_nfe', Number(e.target.value) || 1)}
                />
                <Input
                  label="Próximo número"
                  inputMode="numeric"
                  value={String(cfg.proximo_numero)}
                  onChange={(e) => setCfg('proximo_numero', Number(e.target.value) || 1)}
                />
                <Input
                  label="CFOP padrão — venda dentro do estado"
                  value={cfg.cfop_padrao_dentro_uf}
                  onChange={(e) => setCfg('cfop_padrao_dentro_uf', e.target.value)}
                />
                <Input
                  label="CFOP padrão — venda fora do estado"
                  value={cfg.cfop_padrao_fora_uf}
                  onChange={(e) => setCfg('cfop_padrao_fora_uf', e.target.value)}
                />
              </div>
              <Input
                label="Natureza da operação"
                value={cfg.natureza_operacao}
                onChange={(e) => setCfg('natureza_operacao', e.target.value)}
              />
              <Button size="sm" loading={savingCfg} onClick={() => void saveCfg()} className="self-start">
                Salvar configuração
              </Button>
            </Card>

            <Card variant="outline" className="flex max-w-3xl flex-col gap-4">
              <h3 className="text-sm font-semibold">Certificado digital (e-CNPJ, modelo A1)</h3>
              {cfg.certificado_configurado ? (
                <p className="text-sm text-success">
                  Certificado configurado — titular: {cfg.certificado_titular}. Validade: {cfg.certificado_validade}.
                </p>
              ) : (
                <p className="text-sm text-text-muted">Nenhum certificado cadastrado ainda.</p>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-1">
                  <label className="text-sm font-medium">Arquivo .pfx</label>
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".pfx,.p12"
                    onChange={(e) => setCertFile(e.target.files?.[0] ?? null)}
                    className="rounded-card border border-surface-border px-3 py-2 text-sm"
                  />
                </div>
                <Input
                  label="Senha do certificado"
                  type="password"
                  value={certSenha}
                  onChange={(e) => setCertSenha(e.target.value)}
                />
              </div>
              <Button size="sm" loading={certBusy} onClick={() => void uploadCert()} className="self-start">
                Enviar certificado
              </Button>
              <p className="text-xs text-text-muted">
                Só é aceito certificado modelo A1 (arquivo .pfx/.p12) — o modelo A3 (token/cartão físico)
                não funciona num servidor.
              </p>
            </Card>

            <Card variant="outline" className="flex max-w-3xl flex-col gap-4">
              <h3 className="text-sm font-semibold">Teste de conexão</h3>
              <p className="text-sm text-text-muted">
                Consulta o status do serviço na SEFAZ (sem emitir nada) — confirma que o certificado é
                válido e o webservice da UF está no ar antes de emitir a primeira nota de verdade.
              </p>
              <Button size="sm" variant="outline" loading={testingConn} onClick={() => void doTestConnection()} className="self-start">
                Testar conexão
              </Button>
              {connResult && (
                <p className={`text-sm ${connResult.ok ? 'text-success' : 'text-danger'}`}>
                  {connResult.ok ? '✅' : '⚠️'} [{connResult.codigo_status ?? '—'}] {connResult.motivo}
                </p>
              )}
            </Card>

            {cfg.ambiente === 'homologacao' && (
              <Card variant="outline" className="flex max-w-3xl flex-col gap-4">
                <h3 className="text-sm font-semibold">Emitir NF de teste (sandbox)</h3>
                <p className="text-sm text-text-muted">
                  Emite a NF-e de um pedido real contra o ambiente de homologação da SEFAZ (marcada
                  &quot;SEM VALOR FISCAL&quot;) — pra validar o fluxo completo (certificado, dados
                  fiscais, itens) sem sair do ambiente de testes.
                </p>
                <div className="flex flex-wrap items-end gap-3">
                  <Input
                    label="Número do pedido"
                    placeholder="Ex.: 2026-000123"
                    value={testOrderNumber}
                    onChange={(e) => setTestOrderNumber(e.target.value)}
                  />
                  <Button size="sm" loading={testEmitBusy} onClick={() => void doTestEmit()}>
                    Emitir NF de teste
                  </Button>
                </div>
                {testEmitResult && (
                  <div className="flex flex-col gap-1">
                    <Badge tone={nfeStatusTone(testEmitResult.status)} className="self-start">
                      {nfeStatusLabel(testEmitResult.status)}
                    </Badge>
                    {(testEmitResult.status === 'rejected' || testEmitResult.status === 'error') &&
                      testEmitResult.status_message && (
                        <p className="text-sm text-danger">{testEmitResult.status_message}</p>
                      )}
                  </div>
                )}
              </Card>
            )}
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
