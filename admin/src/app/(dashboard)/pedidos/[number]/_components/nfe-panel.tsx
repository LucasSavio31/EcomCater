'use client';

import { useEffect, useRef, useState } from 'react';
import { Badge, Button, Input, Modal } from '@ecom/ui';
import { Select, Textarea } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { formatDateTime } from '@/lib/format';
import { nfeApi, type NfeDocumentOut, type NfeDraft } from '@/modules/nfe/api';

const TPAG_LABELS: Record<string, string> = {
  '01': 'Dinheiro',
  '02': 'Cheque',
  '03': 'Cartão de crédito',
  '04': 'Cartão de débito',
  '15': 'Boleto bancário',
  '17': 'PIX',
  '90': 'Sem pagamento',
  '99': 'Outros',
};

function centsToStr(cents: number): string {
  return (cents / 100).toFixed(2).replace('.', ',');
}

function statusTone(status: NfeDocumentOut['status']): 'neutral' | 'warning' | 'success' | 'danger' {
  if (status === 'authorized') return 'success';
  if (status === 'processing' || status === 'pending') return 'warning';
  if (status === 'rejected' || status === 'error') return 'danger';
  return 'neutral';
}

function statusLabel(status: NfeDocumentOut['status']): string {
  return (
    {
      none: 'NF-e não emitida',
      pending: 'Preparando…',
      processing: 'Processando na SEFAZ…',
      authorized: 'Autorizada',
      rejected: 'Rejeitada',
      canceled: 'Cancelada',
      error: 'Erro',
    }[status] ?? status
  );
}

type ModalPhase = 'draft' | 'sending' | 'status';

export function NfePanel({ orderNumber }: { orderNumber: string }) {
  const toast = useToast();
  const [status, setStatus] = useState<NfeDocumentOut | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [phase, setPhase] = useState<ModalPhase>('draft');
  const [draft, setDraft] = useState<NfeDraft | null>(null);
  const [draftLoading, setDraftLoading] = useState(false);
  // motivo da rejeição/erro anterior, mostrado ao reabrir o popup pra corrigir
  const [lastFailure, setLastFailure] = useState<string | null>(null);

  const [cancelOpen, setCancelOpen] = useState(false);
  const [justificativa, setJustificativa] = useState('');
  const [cancelBusy, setCancelBusy] = useState(false);
  const [xmlBusy, setXmlBusy] = useState(false);
  const [danfeBusy, setDanfeBusy] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function loadStatus(): Promise<NfeDocumentOut | null> {
    const res = await nfeApi.getStatus(orderNumber);
    if (res.ok) {
      setStatus(res.data);
      return res.data;
    }
    return null;
  }

  useEffect(() => {
    void loadStatus();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderNumber]);

  useEffect(() => {
    if (status?.status === 'processing' && !pollRef.current) {
      pollRef.current = setInterval(() => void loadStatus(), 6000);
    } else if (status?.status !== 'processing' && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status?.status]);

  // popup aberto + em processamento na SEFAZ: consulta mais rápido, pra
  // "validar -> enviar -> autorizar -> imprimir" acontecer sem fechar a tela
  useEffect(() => {
    if (!(modalOpen && phase === 'status' && status?.status === 'processing')) return;
    const t = setInterval(() => void loadStatus(), 3000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modalOpen, phase, status?.status]);

  async function openEmitPopup(): Promise<void> {
    setPhase('draft');
    setModalOpen(true);
    setLastFailure(
      status && (status.status === 'rejected' || status.status === 'error') ? status.status_message ?? null : null,
    );
    setDraftLoading(true);
    const res = await nfeApi.getDraft(orderNumber);
    setDraftLoading(false);
    if (!res.ok) {
      toast.error(res.error.message);
      setModalOpen(false);
      return;
    }
    setDraft(res.data);
  }

  function setItem(idx: number, patch: Partial<NfeDraft['itens'][number]>): void {
    setDraft((d) => {
      if (!d) return d;
      const itens = [...d.itens];
      itens[idx] = { ...itens[idx], ...patch } as NfeDraft['itens'][number];
      return { ...d, itens };
    });
  }

  async function confirmEmit(): Promise<void> {
    if (!draft) return;
    setPhase('sending');
    const res = await nfeApi.emit(orderNumber, draft);
    if (!res.ok) {
      toast.error(res.error.message);
      setPhase('draft');
      return;
    }
    setStatus(res.data);
    setPhase('status');
  }

  async function doCancel(): Promise<void> {
    if (justificativa.trim().length < 15) {
      toast.error('Justificativa precisa ter pelo menos 15 caracteres.');
      return;
    }
    setCancelBusy(true);
    const res = await nfeApi.cancel(orderNumber, justificativa.trim());
    setCancelBusy(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('NF-e cancelada.');
    setCancelOpen(false);
    setJustificativa('');
    setStatus(res.data);
  }

  async function doDownloadXml(): Promise<void> {
    setXmlBusy(true);
    const res = await nfeApi.downloadXml(orderNumber);
    setXmlBusy(false);
    if (!res.ok) toast.error(res.message);
  }

  async function doOpenDanfe(): Promise<void> {
    setDanfeBusy(true);
    const res = await nfeApi.openDanfe(orderNumber);
    setDanfeBusy(false);
    if (!res.ok) toast.error(res.message);
  }

  function closeModal(): void {
    setModalOpen(false);
    setDraft(null);
  }

  const canEmit = !status || ['none', 'rejected', 'error', 'canceled'].includes(status.status);

  return (
    <>
      <div className="inline-flex flex-wrap items-center gap-2">
        {status && status.status !== 'none' && (
          <Badge tone={statusTone(status.status)}>{statusLabel(status.status)}</Badge>
        )}
        {canEmit && (
          <Button size="sm" variant="outline" onClick={() => void openEmitPopup()}>
            {status && status.status !== 'none' ? 'Reemitir NF-e' : 'Emitir NF-e'}
          </Button>
        )}
        {status?.status === 'processing' && (
          <Button size="sm" variant="outline" onClick={() => setModalOpen(true)}>
            Acompanhar
          </Button>
        )}
        {status?.status === 'authorized' && (
          <>
            <Button size="sm" variant="outline" loading={xmlBusy} onClick={() => void doDownloadXml()}>
              Baixar XML
            </Button>
            <Button size="sm" variant="outline" loading={danfeBusy} onClick={() => void doOpenDanfe()}>
              Baixar DANFE
            </Button>
            <Button size="sm" variant="ghost" className="text-danger" onClick={() => setCancelOpen(true)}>
              Cancelar NF-e
            </Button>
          </>
        )}
        {status?.status === 'rejected' && status.status_message && (
          <span className="text-xs text-danger">{status.status_message}</span>
        )}
      </div>

      {/* Um popup só: revisar/validar -> enviar pra SEFAZ -> acompanhar -> imprimir, sem trocar de tela */}
      <Modal
        open={modalOpen}
        onClose={closeModal}
        title={phase === 'draft' ? 'Revisar antes de emitir' : 'Emissão da NF-e'}
        description={
          phase === 'draft'
            ? 'Confira/corrija os dados antes de enviar pra SEFAZ — todos os campos são editáveis.'
            : undefined
        }
        size="lg"
        footer={
          phase === 'draft' ? (
            <>
              <Button variant="ghost" onClick={closeModal}>
                Cancelar
              </Button>
              <Button onClick={() => void confirmEmit()} loading={draftLoading} disabled={!draft}>
                Confirmar e emitir
              </Button>
            </>
          ) : (
            <Button variant="ghost" onClick={closeModal}>
              Fechar
            </Button>
          )
        }
      >
        {phase === 'draft' && draft && (
          <div className="flex flex-col gap-5">
            {lastFailure && (
              <p className="rounded-card bg-danger/10 p-2 text-sm text-danger">
                A tentativa anterior foi recusada: <strong>{lastFailure}</strong> — corrija o que for
                preciso abaixo antes de reenviar.
              </p>
            )}
            {draft.ambiente === 'homologacao' ? (
              <p className="rounded-card bg-warning/10 p-2 text-xs text-warning">
                🟡 Ambiente de homologação — esta nota sai marcada &quot;SEM VALOR FISCAL&quot;.
              </p>
            ) : (
              <p className="rounded-card bg-danger/10 p-2 text-xs text-danger">
                🔴 Ambiente de produção — esta nota terá valor fiscal real.
              </p>
            )}

            <div>
              <h4 className="mb-2 text-sm font-semibold">Destinatário</h4>
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  label="Nome / Razão social"
                  value={draft.destinatario.nome}
                  onChange={(e) => setDraft({ ...draft, destinatario: { ...draft.destinatario, nome: e.target.value } })}
                />
                <Input
                  label="CPF"
                  value={draft.destinatario.cpf}
                  onChange={(e) => setDraft({ ...draft, destinatario: { ...draft.destinatario, cpf: e.target.value } })}
                />
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                {(
                  [
                    ['logradouro', 'Rua'],
                    ['numero', 'Número'],
                    ['complemento', 'Complemento'],
                    ['bairro', 'Bairro'],
                    ['municipio', 'Cidade'],
                    ['uf', 'UF'],
                    ['cep', 'CEP'],
                    ['codigo_municipio', 'Código IBGE do município'],
                  ] as const
                ).map(([key, label]) => (
                  <Input
                    key={key}
                    label={label}
                    value={draft.destinatario.endereco[key]}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        destinatario: {
                          ...draft.destinatario,
                          endereco: { ...draft.destinatario.endereco, [key]: e.target.value },
                        },
                      })
                    }
                  />
                ))}
              </div>
            </div>

            <div>
              <h4 className="mb-2 text-sm font-semibold">Itens</h4>
              <div className="flex flex-col gap-3">
                {draft.itens.map((item, idx) => (
                  <div key={idx} className="rounded-card border border-surface-border p-3">
                    <p className="mb-2 text-sm font-medium">{item.descricao}</p>
                    <div className="grid gap-3 sm:grid-cols-3">
                      <Input label="NCM" value={item.ncm} onChange={(e) => setItem(idx, { ncm: e.target.value })} />
                      <Input label="CFOP" value={item.cfop} onChange={(e) => setItem(idx, { cfop: e.target.value })} />
                      <Input label="CEST" value={item.cest} onChange={(e) => setItem(idx, { cest: e.target.value })} />
                      <Input
                        label="CSOSN/CST"
                        value={item.csosn_cst}
                        onChange={(e) => setItem(idx, { csosn_cst: e.target.value })}
                      />
                      <Input label="Unidade" value={item.unidade} onChange={(e) => setItem(idx, { unidade: e.target.value })} />
                      <Input
                        label="Origem"
                        value={item.origem}
                        onChange={(e) => setItem(idx, { origem: e.target.value })}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="mb-2 text-sm font-semibold">Pagamento e observações</h4>
              <div className="grid gap-3 sm:grid-cols-2">
                <Select
                  label="Forma de pagamento"
                  value={draft.pagamento.forma}
                  options={Object.entries(TPAG_LABELS).map(([value, label]) => ({ value, label }))}
                  onChange={(e) => setDraft({ ...draft, pagamento: { ...draft.pagamento, forma: e.target.value } })}
                />
                <Input
                  label="Natureza da operação"
                  value={draft.natureza_operacao}
                  onChange={(e) => setDraft({ ...draft, natureza_operacao: e.target.value })}
                />
              </div>
              <Textarea
                label="Informações complementares"
                value={draft.informacoes_complementares}
                onChange={(e) => setDraft({ ...draft, informacoes_complementares: e.target.value })}
                rows={2}
                className="mt-3"
              />
              <p className="mt-2 text-sm text-text-muted">
                Total: R$ {centsToStr(draft.totais.valor_total_cents)} (produtos R${' '}
                {centsToStr(draft.totais.valor_produtos_cents)} + frete R${' '}
                {centsToStr(draft.totais.valor_frete_cents)} − desconto R${' '}
                {centsToStr(draft.totais.valor_desconto_cents)})
              </p>
            </div>
          </div>
        )}

        {phase === 'sending' && (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <span className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            <p className="text-sm text-text-muted">Assinando e enviando pra SEFAZ…</p>
          </div>
        )}

        {phase === 'status' && status && (
          <div className="flex flex-col items-center gap-4 py-6 text-center">
            <Badge tone={statusTone(status.status)} className="text-sm">
              {statusLabel(status.status)}
            </Badge>
            {status.status === 'processing' && (
              <>
                <span className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
                <p className="text-sm text-text-muted">
                  A SEFAZ processa em fila — isso normalmente leva alguns segundos. Pode deixar essa
                  tela aberta ou fechar e voltar depois; o status fica salvo no pedido.
                </p>
              </>
            )}
            {status.status === 'authorized' && (
              <>
                <p className="text-sm text-text-muted">
                  Chave de acesso: <span className="font-mono">{status.chave_acesso}</span>
                  <br />
                  Protocolo: {status.protocolo_autorizacao}
                </p>
                <div className="flex gap-2">
                  <Button loading={danfeBusy} onClick={() => void doOpenDanfe()}>
                    Imprimir DANFE
                  </Button>
                  <Button variant="outline" loading={xmlBusy} onClick={() => void doDownloadXml()}>
                    Baixar XML
                  </Button>
                </div>
              </>
            )}
            {(status.status === 'rejected' || status.status === 'error') && (
              <p className="text-sm text-danger">{status.status_message}</p>
            )}
          </div>
        )}
      </Modal>

      <Modal
        open={cancelOpen}
        onClose={() => setCancelOpen(false)}
        title="Cancelar NF-e"
        description="A SEFAZ exige uma justificativa com pelo menos 15 caracteres. Só é possível cancelar dentro do prazo legal (normalmente 24h após a autorização)."
        footer={
          <>
            <Button variant="ghost" onClick={() => setCancelOpen(false)} disabled={cancelBusy}>
              Voltar
            </Button>
            <Button variant="danger" onClick={() => void doCancel()} loading={cancelBusy}>
              Cancelar nota
            </Button>
          </>
        }
      >
        <Textarea
          label="Justificativa"
          value={justificativa}
          onChange={(e) => setJustificativa(e.target.value)}
          rows={3}
        />
        {status?.chave_acesso && (
          <p className="mt-2 text-xs text-text-muted">
            Chave: {status.chave_acesso} — autorizada em {formatDateTime(status.authorized_at ?? '')}
          </p>
        )}
      </Modal>
    </>
  );
}
