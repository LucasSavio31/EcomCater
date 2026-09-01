'use client';

import type { TrackEvent, TrackItem, TrackPromotion } from './types';
import { logEvent } from './debug';

/**
 * Dispara eventos para todos os canais ativos, com o máximo de dados possível
 * e no formato padrão de cada plataforma:
 *  - Google (GA4 / Google Ads) via `gtag('event', ...)` + Enhanced Conversions
 *  - Google Tag Manager via `dataLayer.push({ event, ecommerce, user_data })`
 *  - Meta Pixel via `fbq('track' | 'trackCustom', ...)` + Advanced Matching
 *
 * Canal não carregado (integração desligada no admin) é ignorado — nunca lança.
 */

/* ------------------------------------------------------------------ tipos */

interface TrackPayload {
  items?: TrackItem[];
  value?: number; // em reais
  currency?: string;
  transaction_id?: string;
  coupon?: string;
  discount?: number;
  shipping?: number;
  tax?: number;
  search_term?: string;
  item_list_id?: string;
  item_list_name?: string;
  method?: string;
  affiliation?: string;
  /** share: 'whatsapp' | 'facebook' | 'copy_link' | 'email' */
  share_method?: string;
  content_type?: string;
  item_id?: string;
  /** id compartilhado com a Conversions API para deduplicação (purchase). */
  event_id?: string;
}

export interface IdentifyData {
  email?: string | null;
  phone?: string | null;
  firstName?: string | null;
  lastName?: string | null;
  street?: string | null;
  city?: string | null;
  state?: string | null;
  zip?: string | null;
  country?: string | null;
  externalId?: string | null;
}

interface W {
  gtag?: (...args: unknown[]) => void;
  dataLayer?: unknown[];
  fbq?: ((...args: unknown[]) => void) & { callMethod?: unknown };
  __ECOM_ANALYTICS__?: {
    ga4: string | null;
    ads: string | null;
    adsPurchaseLabel: string | null;
    pixel: string | null;
    gtm: string | null;
  };
  __ECOM_IDENTITY__?: IdentifyData;
}

/* --------------------------------------------------------------- mapeamentos */

const META_NAME: Record<TrackEvent, string> = {
  page_view: 'PageView',
  view_promotion: 'ViewPromotion',
  select_promotion: 'SelectPromotion',
  view_item: 'ViewContent',
  view_item_list: 'ViewItemList',
  select_item: 'SelectItem',
  search: 'Search',
  view_search_results: 'ViewSearchResults',
  add_to_cart: 'AddToCart',
  remove_from_cart: 'RemoveFromCart',
  view_cart: 'ViewCart',
  begin_checkout: 'InitiateCheckout',
  add_shipping_info: 'AddShippingInfo',
  add_payment_info: 'AddPaymentInfo',
  purchase: 'Purchase',
  refund: 'Refund',
  add_to_wishlist: 'AddToWishlist',
  login: 'Login',
  sign_up: 'CompleteRegistration',
  share: 'Share',
  generate_lead: 'Lead',
};

const META_STANDARD = new Set([
  'ViewContent',
  'Search',
  'AddToCart',
  'InitiateCheckout',
  'AddPaymentInfo',
  'Purchase',
  'AddToWishlist',
  'CompleteRegistration',
  'Lead',
]);

/* ----------------------------------------------------------------- helpers */

const round = (n: number) => Math.round((Number.isFinite(n) ? n : 0) * 100) / 100;
/** Remove undefined / null / '' — nunca vaza `undefined` no dataLayer. */
function prune<T extends Record<string, unknown>>(o: T): T {
  return Object.fromEntries(
    Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== ''),
  ) as T;
}
const norm = (v?: string | null) => (v ?? '').trim().toLowerCase() || undefined;
const digits = (v?: string | null) => (v ?? '').replace(/\D/g, '') || undefined;

/* ------------------------------------------------- cookies / identidade ------ */

function getCookie(name: string): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const esc = name.replace(/[.$?*|{}()[\]\\/+^]/g, '\\$&');
  const m = document.cookie.match(new RegExp(`(?:^|; )${esc}=([^;]*)`));
  return m ? decodeURIComponent(m[1] ?? '') : undefined;
}

/**
 * `_fbp` e `_fbc` (cookies do Meta Pixel). Se não houver `_fbc` mas a URL
 * trouxer `fbclid`, sintetiza `fb.1.<ts>.<fbclid>` (formato oficial da Meta)
 * e grava o cookie para as próximas páginas.
 */
function fbCookies(): { fbp?: string; fbc?: string } {
  const fbp = getCookie('_fbp');
  let fbc = getCookie('_fbc');
  try {
    const fbclid = new URLSearchParams(window.location.search).get('fbclid');
    if (!fbc && fbclid) {
      fbc = `fb.1.${Date.now()}.${fbclid}`;
      document.cookie = `_fbc=${fbc}; path=/; max-age=${60 * 60 * 24 * 90}; samesite=lax`;
    }
  } catch {
    /* noop */
  }
  return { fbp: fbp || undefined, fbc: fbc || undefined };
}

const IDENTITY_KEY = 'ecom:identity';

function loadIdentity(): IdentifyData {
  try {
    const raw = localStorage.getItem(IDENTITY_KEY);
    return raw ? (JSON.parse(raw) as IdentifyData) : {};
  } catch {
    return {};
  }
}
function saveIdentity(d: IdentifyData): void {
  try {
    localStorage.setItem(IDENTITY_KEY, JSON.stringify(d));
  } catch {
    /* noop */
  }
}

/** Identidade atual (persistida em localStorage + em memória nesta aba). */
export function currentIdentity(): IdentifyData {
  if (typeof window === 'undefined') return {};
  return { ...loadIdentity(), ...((window as unknown as W).__ECOM_IDENTITY__ ?? {}) };
}
/** `{ fbp, fbc }` atuais — usado no checkout p/ enviar ao pedido (CAPI). */
export function currentFbCookies(): { fbp?: string; fbc?: string } {
  return typeof window === 'undefined' ? {} : fbCookies();
}

/** client_id do GA4 (cookie `_ga`: "GA1.1.<client_id>.<ts>") — p/ o `refund` server-side. */
export function currentGaClientId(): string | undefined {
  const raw = getCookie('_ga');
  if (!raw) return undefined;
  const parts = raw.split('.');
  return parts.length >= 4 ? `${parts[parts.length - 2]}.${parts[parts.length - 1]}` : undefined;
}

/** Subconjunto que o Google Enhanced Conversions entende (`gtag('set','user_data')`). */
function googleUserData(id: IdentifyData): Record<string, unknown> {
  const address: Record<string, unknown> = {};
  if (id.firstName) address.first_name = norm(id.firstName);
  if (id.lastName) address.last_name = norm(id.lastName);
  if (id.street) address.street = id.street;
  if (id.city) address.city = norm(id.city);
  if (id.state) address.region = norm(id.state);
  if (id.zip) address.postal_code = digits(id.zip);
  if (id.country) address.country = norm(id.country);
  const ud: Record<string, unknown> = {};
  if (norm(id.email)) ud.email = norm(id.email);
  if (id.phone) ud.phone_number = id.phone.replace(/[^\d+]/g, '');
  if (Object.keys(address).length) ud.address = address;
  return ud;
}

/**
 * Bloco `user_data` completo para o `dataLayer` (padrão comum de GTM web →
 * GTM server → Meta CAPI / Google EC). Não é hasheado — as tags/servidor
 * fazem o hash. Inclui SEMPRE `fbp`/`fbc`/`client_user_agent` quando existem.
 */
function fullUserData(id: IdentifyData): Record<string, unknown> {
  const ud = googleUserData(id);
  if (id.externalId) ud.external_id = String(id.externalId);
  const { fbp, fbc } = fbCookies();
  if (fbp) ud.fbp = fbp;
  if (fbc) ud.fbc = fbc;
  if (typeof navigator !== 'undefined' && navigator.userAgent) {
    ud.client_user_agent = navigator.userAgent;
  }
  return ud;
}

/** "a/b/c" (path da categoria) → item_category, item_category2..5 */
function categoryFields(it: TrackItem): Record<string, string> {
  const parts = (it.categoryPath ?? it.category ?? '')
    .split('/')
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 5);
  const out: Record<string, string> = {};
  parts.forEach((p, i) => {
    out[i === 0 ? 'item_category' : `item_category${i + 1}`] = p;
  });
  return out;
}

function ga4Items(items: TrackItem[] = [], payload: TrackPayload = {}) {
  return items.map((it, i) =>
    prune({
      item_id: it.id,
      item_name: it.name,
      affiliation: payload.affiliation,
      coupon: it.coupon ?? payload.coupon,
      discount: typeof it.discount === 'number' ? round(it.discount) : undefined,
      index: it.index ?? i,
      item_brand: it.brand ?? undefined,
      ...categoryFields(it),
      item_list_id: it.item_list_id ?? payload.item_list_id,
      item_list_name: it.item_list_name ?? payload.item_list_name,
      item_variant: it.variant ?? undefined,
      price: round(it.price),
      quantity: it.quantity ?? 1,
    }),
  );
}

function metaContents(items: TrackItem[] = []) {
  const only = items.length === 1 ? items[0] : undefined;
  return {
    content_type: 'product',
    content_ids: items.map((it) => it.id),
    content_name: only?.name,
    content_category: only?.category ?? undefined,
    contents: items.map((it) => ({
      id: it.id,
      quantity: it.quantity ?? 1,
      item_price: round(it.price),
    })),
    num_items: items.reduce((n, it) => n + (it.quantity ?? 1), 0),
  };
}

function computedValue(p: TrackPayload): number {
  if (typeof p.value === 'number') return round(p.value);
  if (p.items?.length) return round(p.items.reduce((s, it) => s + it.price * (it.quantity ?? 1), 0));
  return 0;
}

/* -------------------------------------------------------------- identify() */

/**
 * Informa quem é o cliente para casar conversões:
 *  - Meta: Advanced Matching (re-`fbq('init', pixel, userData)`)
 *  - Google Ads: Enhanced Conversions (`gtag('set', 'user_data', ...)`)
 *  - GTM: `dataLayer.push({ event: 'identify', user_data })`
 */
export function identify(data: IdentifyData = {}): void {
  if (typeof window === 'undefined') return;
  const w = window as unknown as W;
  const prev = { ...loadIdentity(), ...(w.__ECOM_IDENTITY__ ?? {}) };
  const merged: IdentifyData = {
    ...prev,
    ...Object.fromEntries(Object.entries(data).filter(([, v]) => v)),
  };
  w.__ECOM_IDENTITY__ = merged;
  saveIdentity(merged);
  const cfg = w.__ECOM_ANALYTICS__;

  // ---------- Meta Advanced Matching (o pixel gere _fbp/_fbc sozinho) ----------
  try {
    if (typeof w.fbq === 'function' && cfg?.pixel) {
      const am: Record<string, string> = {};
      if (norm(merged.email)) am.em = norm(merged.email)!;
      if (digits(merged.phone)) am.ph = digits(merged.phone)!;
      if (norm(merged.firstName)) am.fn = norm(merged.firstName)!;
      if (norm(merged.lastName)) am.ln = norm(merged.lastName)!;
      if (norm(merged.city)) am.ct = norm(merged.city)!.replace(/\s/g, '');
      if (norm(merged.state)) am.st = norm(merged.state)!;
      if (digits(merged.zip)) am.zp = digits(merged.zip)!;
      if (norm(merged.country)) am.country = norm(merged.country)!;
      if (merged.externalId) am.external_id = String(merged.externalId);
      if (Object.keys(am).length) w.fbq('init', cfg.pixel, am);
    }
  } catch {
    /* noop */
  }

  // ---------- Google Enhanced Conversions ----------
  try {
    if (typeof w.gtag === 'function') {
      const ud = googleUserData(merged);
      if (Object.keys(ud).length) w.gtag('set', 'user_data', ud);
    }
  } catch {
    /* noop */
  }

  // ---------- GTM: evento `user_data` DEDICADO (Enhanced Conversions / CAPI server)
  // Fica SEPARADO dos objetos `ecommerce` — nunca é misturado a eventos GA4.
  try {
    if (Array.isArray(w.dataLayer)) {
      const ud = fullUserData(merged);
      if (Object.keys(ud).length) {
        w.dataLayer.push({
          event: 'user_data',
          ...(merged.externalId ? { user_id: String(merged.externalId) } : {}),
          user_data: ud,
        });
        logEvent('user_data', Object.keys(ud));
      }
    }
  } catch {
    /* noop */
  }
}

/* ----------------------------------------------------------------- track() */

/** Eventos que carregam o bloco `ecommerce` (GA4 Enhanced Ecommerce). */
const ECOMMERCE_EVENTS = new Set<TrackEvent>([
  'view_promotion',
  'select_promotion',
  'view_item',
  'view_item_list',
  'select_item',
  'view_search_results',
  'add_to_cart',
  'remove_from_cart',
  'view_cart',
  'begin_checkout',
  'add_shipping_info',
  'add_payment_info',
  'purchase',
  'refund',
  'add_to_wishlist',
]);
/** Eventos com `value`/`currency` (monetários). */
const MONETARY_EVENTS = new Set<TrackEvent>([
  'view_item',
  'add_to_cart',
  'remove_from_cart',
  'view_cart',
  'begin_checkout',
  'add_shipping_info',
  'add_payment_info',
  'purchase',
  'refund',
  'add_to_wishlist',
]);

export function track(event: TrackEvent, payload: TrackPayload = {}): void {
  if (typeof window === 'undefined') return;
  const w = window as unknown as W;
  const cfg = w.__ECOM_ANALYTICS__;
  const currency = payload.currency ?? 'BRL';
  const value = computedValue(payload);
  const isEcom = ECOMMERCE_EVENTS.has(event);
  const isMoney = MONETARY_EVENTS.has(event);

  // ---------- bloco `ecommerce` (GA4) ----------
  const ecommerce: Record<string, unknown> = {};
  if (isMoney) {
    ecommerce.currency = currency;
    ecommerce.value = value;
  }
  if (payload.transaction_id) ecommerce.transaction_id = payload.transaction_id;
  if (payload.coupon) ecommerce.coupon = payload.coupon;
  if (typeof payload.shipping === 'number') ecommerce.shipping = round(payload.shipping);
  if (typeof payload.tax === 'number') ecommerce.tax = round(payload.tax);
  if (payload.affiliation) ecommerce.affiliation = payload.affiliation;
  if (payload.item_list_id) ecommerce.item_list_id = payload.item_list_id;
  if (payload.item_list_name) ecommerce.item_list_name = payload.item_list_name;
  if (payload.items?.length) ecommerce.items = ga4Items(payload.items, payload);

  // ---------- params de eventos NÃO-ecommerce (page_view, search, login, ...) ----------
  const plain: Record<string, unknown> = {};
  if (payload.search_term) plain.search_term = payload.search_term;
  if (payload.method) {
    const key =
      event === 'add_shipping_info'
        ? 'shipping_tier'
        : event === 'add_payment_info'
          ? 'payment_type'
          : 'method';
    (isEcom ? ecommerce : plain)[key] = payload.method;
  }
  if (payload.share_method) plain.method = payload.share_method;
  if (payload.content_type) plain.content_type = payload.content_type;
  if (payload.item_id) plain.item_id = payload.item_id;

  const dlEvent: Record<string, unknown> = { event };
  if (payload.event_id) dlEvent.event_id = payload.event_id;
  if (isEcom) dlEvent.ecommerce = prune(ecommerce);
  Object.assign(dlEvent, prune(plain));

  logEvent(event, isEcom ? dlEvent.ecommerce : plain);

  // ---------- dataLayer é a FONTE ÚNICA — sempre empurra ----------
  try {
    if (Array.isArray(w.dataLayer)) {
      if (isEcom) w.dataLayer.push({ ecommerce: null });
      w.dataLayer.push(dlEvent);
    }
  } catch {
    /* noop */
  }

  // ---------- gtag (mantido: config GA4/Ads no <head> segue como está) ----------
  try {
    if (typeof w.gtag === 'function') {
      const gaParams = isEcom
        ? { ...(dlEvent.ecommerce as Record<string, unknown>) }
        : { ...prune(plain) };
      w.gtag('event', event, gaParams);
      if (event === 'purchase' && cfg?.ads) {
        w.gtag('event', 'conversion', {
          send_to: cfg.adsPurchaseLabel ? `${cfg.ads}/${cfg.adsPurchaseLabel}` : cfg.ads,
          value,
          currency,
          transaction_id: payload.transaction_id,
        });
      }
    }
  } catch {
    /* noop */
  }

  // ---------- Meta Pixel (secundário — a fonte é o dataLayer) ----------
  try {
    if (typeof w.fbq === 'function' && event !== 'page_view') {
      const name = META_NAME[event];
      const meta: Record<string, unknown> = isMoney ? { currency, value } : {};
      if (payload.items?.length) Object.assign(meta, metaContents(payload.items));
      if (payload.search_term) meta.search_string = payload.search_term;
      if (payload.transaction_id) meta.order_id = payload.transaction_id;
      if (payload.method && event === 'add_shipping_info') meta.delivery_category = 'home_delivery';
      const opts = payload.event_id ? { eventID: payload.event_id } : undefined;
      if (META_STANDARD.has(name)) w.fbq('track', name, meta, opts);
      else w.fbq('trackCustom', name, meta);
    }
  } catch {
    /* noop */
  }
}

/** PageView em navegação SPA (o carregamento inicial já vem das tags base). */
/** `page_view` na navegação SPA (o 1º load já é coberto pela Google Tag base). */
export function trackPageView(url: string): void {
  if (typeof window === 'undefined') return;
  const w = window as unknown as W;
  const params = { page_path: url, page_location: window.location.href, page_title: document.title };
  logEvent('page_view', params);
  try {
    // dataLayer: fonte única — sempre.
    if (Array.isArray(w.dataLayer)) w.dataLayer.push({ event: 'page_view', ...params });
    // gtag: só quando o GA4 está configurado direto no <head> (mantido como está).
    if (typeof w.gtag === 'function' && w.__ECOM_ANALYTICS__?.ga4) {
      w.gtag('event', 'page_view', params);
    }
    if (typeof w.fbq === 'function') w.fbq('track', 'PageView');
  } catch {
    /* noop */
  }
}

/** view_promotion / select_promotion — promoções internas (banners/campanhas). */
export function trackPromotion(kind: 'view' | 'select', promo: TrackPromotion): void {
  if (typeof window === 'undefined') return;
  const w = window as unknown as W;
  const event: TrackEvent = kind === 'view' ? 'view_promotion' : 'select_promotion';
  const ecommerce = prune({
    creative_name: promo.creative_name,
    creative_slot: promo.creative_slot,
    promotion_id: promo.promotion_id,
    promotion_name: promo.promotion_name,
    items: promo.items?.length ? ga4Items(promo.items) : undefined,
  });
  logEvent(event, ecommerce);
  try {
    if (Array.isArray(w.dataLayer)) {
      w.dataLayer.push({ ecommerce: null });
      w.dataLayer.push({ event, ecommerce });
    }
    if (typeof w.gtag === 'function') w.gtag('event', event, ecommerce);
  } catch {
    /* noop */
  }
}
