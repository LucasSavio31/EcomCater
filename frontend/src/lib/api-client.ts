/**
 * Cliente HTTP tipado da loja.
 *
 * - Base: `NEXT_PUBLIC_API_URL` (default http://localhost:8000).
 * - Isomórfico: funciona em server e client components.
 * - Erros no formato da API (`{ error: { code, message, details } }`) viram um
 *   `ApiError` estruturado; a função nunca "explode" — retorna um `ApiResult`.
 * - Suporta `next: { tags, revalidate }` para cache/revalidação por tag no SSR.
 */

export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  /** HTTP status; 0 quando a requisição sequer completou (rede/timeout). */
  status: number;
}

export type ApiResult<T> =
  | { ok: true; data: T; status: number }
  | { ok: false; error: ApiError };

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  /** Serializado como JSON automaticamente (a menos que já seja string/FormData). */
  body?: unknown;
  /** Token Bearer explícito (o admin usa; a loja normalmente não). */
  token?: string | null;
  /** Querystring. Valores `undefined`/`null` são omitidos. */
  query?: Record<string, string | number | boolean | undefined | null>;
  /** Opções de cache do Next (App Router). */
  next?: { tags?: string[]; revalidate?: number | false };
  /** `include` para enviar/receber cookies (carrinho de convidado via `cart_token`). */
  credentials?: RequestCredentials;
}

function buildUrl(path: string, query?: ApiRequestOptions['query']): string {
  const url = new URL(path.startsWith('http') ? path : `${API_BASE_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

interface RawErrorEnvelope {
  error?: { code?: string; message?: string; details?: Record<string, unknown> };
  detail?: unknown;
}

export async function apiFetch<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<ApiResult<T>> {
  const { body, token, query, next, headers, credentials, ...rest } = options;

  const finalHeaders = new Headers(headers);
  let finalBody: BodyInit | undefined;
  if (body !== undefined) {
    if (typeof body === 'string' || body instanceof FormData) {
      finalBody = body;
    } else {
      finalHeaders.set('content-type', 'application/json');
      finalBody = JSON.stringify(body);
    }
  }
  if (token) finalHeaders.set('authorization', `Bearer ${token}`);
  finalHeaders.set('accept', 'application/json');

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      ...rest,
      headers: finalHeaders,
      body: finalBody,
      ...(credentials ? { credentials } : {}),
      ...(next ? { next } : {}),
    });
  } catch (cause) {
    return {
      ok: false,
      error: {
        code: 'network_error',
        message: cause instanceof Error ? cause.message : 'Falha de rede',
        status: 0,
      },
    };
  }

  if (response.status === 204) {
    return { ok: true, data: undefined as T, status: 204 };
  }

  const text = await response.text();
  const parsed: unknown = text ? safeJson(text) : null;

  if (!response.ok) {
    const envelope = (parsed ?? {}) as RawErrorEnvelope;
    return {
      ok: false,
      error: {
        code: envelope.error?.code ?? 'http_error',
        message:
          envelope.error?.message ??
          (typeof envelope.detail === 'string' ? envelope.detail : response.statusText) ??
          'Erro na requisição',
        details: envelope.error?.details,
        status: response.status,
      },
    };
  }

  return { ok: true, data: parsed as T, status: response.status };
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/** Igual a `apiFetch`, mas lança `ApiError` — conveniente em Server Components. */
export async function apiGet<T>(path: string, options?: ApiRequestOptions): Promise<T> {
  const result = await apiFetch<T>(path, { ...options, method: 'GET' });
  if (!result.ok) throw Object.assign(new Error(result.error.message), result.error);
  return result.data;
}
