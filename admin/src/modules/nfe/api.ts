'use client';

import { ADMIN_API_BASE_URL, adminFetch, type ApiResult } from '@/lib/admin-api-client';
import { getSession } from '@/lib/auth-storage';

export interface NfeConfig {
  ambiente: 'homologacao' | 'producao';
  serie_nfe: number;
  proximo_numero: number;
  cfop_padrao_dentro_uf: string;
  cfop_padrao_fora_uf: string;
  natureza_operacao: string;
  certificado_storage_key: string;
  certificado_senha: string; // vem mascarado ("•••• configurado") do GET
  certificado_validade: string;
  certificado_titular: string;
  certificado_configurado: boolean;
}

export interface NfeEndereco {
  logradouro: string;
  numero: string;
  complemento: string;
  bairro: string;
  municipio: string;
  codigo_municipio: string;
  uf: string;
  cep: string;
  telefone: string;
}

export interface NfeItemDraft {
  n_item: number;
  sku: string;
  descricao: string;
  ncm: string;
  cfop: string;
  cest: string;
  csosn_cst: string;
  origem: string;
  unidade: string;
  quantidade: number;
  valor_unitario_cents: number;
  valor_total_cents: number;
}

export interface NfeDraft {
  ambiente: string;
  natureza_operacao: string;
  serie: number;
  numero: number;
  emitente: {
    cnpj: string;
    razao_social: string;
    nome_fantasia: string;
    ie: string;
    cnae: string;
    regime_tributario: string;
    endereco: NfeEndereco;
    telefone: string;
  };
  destinatario: {
    nome: string;
    cpf: string;
    cnpj: string;
    email: string;
    endereco: NfeEndereco;
  };
  itens: NfeItemDraft[];
  totais: {
    valor_produtos_cents: number;
    valor_desconto_cents: number;
    valor_frete_cents: number;
    valor_total_cents: number;
  };
  pagamento: { forma: string; valor_cents: number };
  informacoes_complementares: string;
}

export interface NfeDocumentOut {
  id?: string;
  order_number?: string;
  status: 'none' | 'pending' | 'processing' | 'authorized' | 'rejected' | 'canceled' | 'error';
  status_message?: string | null;
  ambiente?: string;
  numero?: number | null;
  serie?: number | null;
  chave_acesso?: string | null;
  protocolo_autorizacao?: string | null;
  has_xml?: boolean;
  has_danfe?: boolean;
  requested_at?: string | null;
  authorized_at?: string | null;
  canceled_at?: string | null;
}

/** Versão maior de `NfeDocumentOut`, usada na listagem/detalhe de "Notas emitidas". */
export interface NfeDocumentFull extends NfeDocumentOut {
  id: string;
  order_number: string;
  total_cents: number;
  natureza_operacao: string | null;
  destinatario_nome: string | null;
  cancel_justificativa: string | null;
  created_at: string;
}

export interface NfeDocumentsList {
  items: NfeDocumentFull[];
  total: number;
  page: number;
  page_size: number;
}

export interface NfeConnectionTest {
  ok: boolean;
  codigo_status: string | null;
  motivo: string | null;
  ambiente?: string;
  uf?: string;
}

export function nfeStatusTone(status: NfeDocumentOut['status']): 'neutral' | 'warning' | 'success' | 'danger' {
  if (status === 'authorized') return 'success';
  if (status === 'processing' || status === 'pending') return 'warning';
  if (status === 'rejected' || status === 'error') return 'danger';
  return 'neutral';
}

export function nfeStatusLabel(status: NfeDocumentOut['status']): string {
  return (
    {
      none: 'Não emitida',
      pending: 'Preparando…',
      processing: 'Processando…',
      authorized: 'Autorizada',
      rejected: 'Rejeitada',
      canceled: 'Cancelada',
      error: 'Erro',
    }[status] ?? status
  );
}

async function uploadMultipart<T>(path: string, form: FormData): Promise<ApiResult<T>> {
  const session = getSession();
  try {
    const res = await fetch(`${ADMIN_API_BASE_URL}${path}`, {
      method: 'POST',
      headers: session ? { authorization: `Bearer ${session.accessToken}` } : undefined,
      body: form,
    });
    const text = await res.text();
    const parsed: unknown = text ? JSON.parse(text) : null;
    if (!res.ok) {
      const env = (parsed ?? {}) as { error?: { message?: string }; detail?: string };
      return {
        ok: false,
        error: { code: 'upload_error', message: env.error?.message ?? env.detail ?? 'Falha no upload', status: res.status },
      };
    }
    return { ok: true, data: parsed as T, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: { code: 'network_error', message: err instanceof Error ? err.message : 'Falha de rede', status: 0 },
    };
  }
}

async function downloadFile(
  path: string,
): Promise<{ ok: true; blob: Blob; headers: Headers } | { ok: false; message: string }> {
  const session = getSession();
  try {
    const r = await fetch(`${ADMIN_API_BASE_URL}${path}`, {
      headers: session ? { authorization: `Bearer ${session.accessToken}` } : undefined,
    });
    if (!r.ok) {
      let msg = 'Falha ao baixar o arquivo.';
      try {
        const j = await r.json();
        msg = j?.error?.message ?? j?.detail ?? msg;
      } catch {
        /* corpo não-JSON */
      }
      return { ok: false, message: msg };
    }
    return { ok: true, blob: await r.blob(), headers: r.headers };
  } catch {
    return { ok: false, message: 'Falha de rede.' };
  }
}

export const nfeApi = {
  getConfig: (): Promise<ApiResult<NfeConfig>> => adminFetch<NfeConfig>('/api/admin/nfe/config'),

  putConfig: (body: Partial<NfeConfig>): Promise<ApiResult<NfeConfig>> =>
    adminFetch<NfeConfig>('/api/admin/nfe/config', { method: 'PUT', body }),

  uploadCertificate: (file: File, senha: string): Promise<ApiResult<NfeConfig>> => {
    const form = new FormData();
    form.append('file', file);
    form.append('senha', senha);
    return uploadMultipart<NfeConfig>('/api/admin/nfe/config/certificate', form);
  },

  getDraft: (orderNumber: string): Promise<ApiResult<NfeDraft>> =>
    adminFetch<NfeDraft>(`/api/admin/nfe/orders/${orderNumber}/draft`),

  getStatus: (orderNumber: string): Promise<ApiResult<NfeDocumentOut>> =>
    adminFetch<NfeDocumentOut>(`/api/admin/nfe/orders/${orderNumber}`),

  emit: (orderNumber: string, payload: NfeDraft): Promise<ApiResult<NfeDocumentOut>> =>
    adminFetch<NfeDocumentOut>(`/api/admin/nfe/orders/${orderNumber}`, { method: 'POST', body: payload }),

  cancel: (orderNumber: string, justificativa: string): Promise<ApiResult<NfeDocumentOut>> =>
    adminFetch<NfeDocumentOut>(`/api/admin/nfe/orders/${orderNumber}/cancel`, {
      method: 'POST',
      body: { justificativa },
    }),

  downloadXml: async (orderNumber: string): Promise<{ ok: true } | { ok: false; message: string }> => {
    const res = await downloadFile(`/api/admin/nfe/orders/${orderNumber}/xml`);
    if (!res.ok) return res;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(res.blob);
    a.download = `nfe-${orderNumber}.xml`;
    a.click();
    URL.revokeObjectURL(a.href);
    return { ok: true };
  },

  /** .zip com o XML de todas as NF-e autorizadas do mês — pra mandar pro contador. */
  downloadExportMonth: async (
    year: number,
    month: number,
  ): Promise<{ ok: true } | { ok: false; message: string }> => {
    const res = await downloadFile(`/api/admin/nfe/export-month?year=${year}&month=${month}`);
    if (!res.ok) return res;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(res.blob);
    a.download = `nfe-${year}-${String(month).padStart(2, '0')}.zip`;
    a.click();
    URL.revokeObjectURL(a.href);
    return { ok: true };
  },

  openDanfe: async (orderNumber: string): Promise<{ ok: true } | { ok: false; message: string }> => {
    const res = await downloadFile(`/api/admin/nfe/orders/${orderNumber}/danfe`);
    if (!res.ok) return res;
    const url = URL.createObjectURL(res.blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
    return { ok: true };
  },

  /** DANFE Simplificado – Etiqueta (NT 2020.004), 10x15 — pra imprimir na
   * térmica junto com a etiqueta de envio, igual Mercado Livre/Shopee. */
  openMiniDanfe: async (orderNumber: string): Promise<{ ok: true } | { ok: false; message: string }> => {
    const res = await downloadFile(`/api/admin/nfe/orders/${orderNumber}/mini-danfe`);
    if (!res.ok) return res;
    const url = URL.createObjectURL(res.blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
    return { ok: true };
  },

  // --------------------------------- lote (seleção múltipla na listagem)

  statusMap: (numbers: string[]): Promise<ApiResult<{ results: NfeDocumentOut[] }>> =>
    adminFetch<{ results: NfeDocumentOut[] }>('/api/admin/nfe/status-map', {
      method: 'POST',
      body: { numbers },
    }),

  bulkEmit: (
    numbers: string[],
  ): Promise<ApiResult<{ results: Array<{ number: string; ok: boolean; status?: string; message?: string | null }> }>> =>
    adminFetch('/api/admin/nfe/bulk-emit', { method: 'POST', body: { numbers } }),

  openBulkDanfe: async (
    numbers: string[],
    mini = false,
  ): Promise<{ ok: true; skipped: string[] } | { ok: false; message: string }> => {
    const qs = `numbers=${encodeURIComponent(numbers.join(','))}${mini ? '&mini=true' : ''}`;
    const res = await downloadFile(`/api/admin/nfe/bulk-danfe?${qs}`);
    if (!res.ok) return res;
    const url = URL.createObjectURL(res.blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
    const skippedHeader = res.headers.get('X-Nfe-Skipped');
    return { ok: true, skipped: skippedHeader ? skippedHeader.split(',') : [] };
  },

  // --------------------------------------------------------- teste de conexão

  testConnection: (): Promise<ApiResult<NfeConnectionTest>> =>
    adminFetch<NfeConnectionTest>('/api/admin/nfe/test-connection'),

  // --------------------------------------------------------- notas emitidas (listagem)

  listDocuments: (params: {
    page: number;
    pageSize: number;
    status?: string;
  }): Promise<ApiResult<NfeDocumentsList>> =>
    adminFetch<NfeDocumentsList>('/api/admin/nfe/documents', {
      query: { page: params.page, page_size: params.pageSize, status: params.status || undefined },
    }),

  getDocument: (id: string): Promise<ApiResult<NfeDocumentFull>> =>
    adminFetch<NfeDocumentFull>(`/api/admin/nfe/documents/${id}`),

  cancelDocument: (id: string, justificativa: string): Promise<ApiResult<NfeDocumentFull>> =>
    adminFetch<NfeDocumentFull>(`/api/admin/nfe/documents/${id}/cancel`, {
      method: 'POST',
      body: { justificativa },
    }),

  deleteDocument: (id: string): Promise<ApiResult<{ ok: boolean }>> =>
    adminFetch<{ ok: boolean }>(`/api/admin/nfe/documents/${id}`, { method: 'DELETE' }),

  emailDocument: (id: string, to: string, mini = false): Promise<ApiResult<{ ok: boolean }>> =>
    adminFetch<{ ok: boolean }>(`/api/admin/nfe/documents/${id}/email`, {
      method: 'POST',
      body: { to, mini },
    }),

  downloadDocumentXml: async (id: string): Promise<{ ok: true } | { ok: false; message: string }> => {
    const res = await downloadFile(`/api/admin/nfe/documents/${id}/xml`);
    if (!res.ok) return res;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(res.blob);
    a.download = `nfe-${id}.xml`;
    a.click();
    URL.revokeObjectURL(a.href);
    return { ok: true };
  },

  openDocumentDanfe: async (id: string): Promise<{ ok: true } | { ok: false; message: string }> => {
    const res = await downloadFile(`/api/admin/nfe/documents/${id}/danfe`);
    if (!res.ok) return res;
    const url = URL.createObjectURL(res.blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
    return { ok: true };
  },

  openDocumentMiniDanfe: async (id: string): Promise<{ ok: true } | { ok: false; message: string }> => {
    const res = await downloadFile(`/api/admin/nfe/documents/${id}/mini-danfe`);
    if (!res.ok) return res;
    const url = URL.createObjectURL(res.blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
    return { ok: true };
  },
};
