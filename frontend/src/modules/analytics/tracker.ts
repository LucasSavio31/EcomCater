'use client';

import type { TrackEvent, TrackItem } from './types';

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
  view_item: 'ViewContent',
  view_item_list: 'ViewItemList',
  select_item: 'SelectItem',
  search: 'Search',
  add_to_cart: 'AddToCart',
  remove_from_cart: 'RemoveFromCart',
  view_cart: 'ViewCart',
  begin_checkout: 'InitiateCheckout',
  add_shipping_info: 'AddShippingInfo',
  add_payment_info: 'AddPaymentInfo',
  purchase: 'Purchase',
  add_to_wishlist: 'AddToWishlist',
  sign_up: 'CompleteRegistration',
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
const norm = (v?: string | null) => (v ?? '').trim().toLowerCase() || undefined;
const digits = (v?: string | null) => (v ?? '').replace(/\D/g, '') || undefined;

function ga4Items(items: TrackItem[] = [], payload: TrackPayload = {}) {
  return items.map((it, i) => ({
    item_id: it.id,
    item_name: it.name,
    affiliation: payload.affiliation,
    coupon: payload.coupon,
    discount: payload.discount && items.length ? round(payload.discount / items.length) : undefined,
    index: i,
    item_brand: it.brand ?? undefined,
    item_category: it.category ?? undefined,
    item_list_id: payload.item_list_id,
    item_list_name: payload.item_list_name,
    item_variant: it.variant ?? undefined,
    price: round(it.price),
    quantity: it.quantity ?? 1,
  }));
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
export function identify(data: IdentifyData): void {
  if (typeof window === 'undefined') return;
  const w = window as unknown as W;
  const prev = w.__ECOM_IDENTITY__ ?? {};
  const merged: IdentifyData = { ...prev, ...Object.fromEntries(Object.entries(data).filter(([, v]) => v)) };
  w.__ECOM_IDENTITY__ = merged;
  const cfg = w.__ECOM_ANALYTICS__;

  // ---------- Meta Advanced Matching ----------
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
      const ud: Record<string, unknown> = {};
      if (norm(merged.email)) ud.email = norm(merged.email);
      if (merged.phone) ud.phone_number = merged.phone.replace(/[^\d+]/g, '');
      const addr: Record<string, unknown> = {};
      if (merged.firstName) addr.first_name = merged.firstName;
      if (merged.lastName) addr.last_name = merged.lastName;
      if (merged.street) addr.street = merged.street;
      if (merged.city) addr.city = merged.city;
      if (merged.state) addr.region = merged.state;
      if (merged.zip) addr.postal_code = merged.zip;
      if (merged.country) addr.country = merged.country;
      if (Object.keys(addr).length) ud.address = addr;
      if (Object.keys(ud).length) w.gtag('set', 'user_data', ud);
    }
  } catch {
    /* noop */
  }

  // ---------- GTM ----------
  try {
    if (Array.isArray(w.dataLayer)) {
      w.dataLayer.push({
        event: 'identify',
        user_data: {
          email: norm(merged.email),
          phone: digits(merged.phone),
          first_name: merged.firstName ?? undefined,
          last_name: merged.lastName ?? undefined,
          city: merged.city ?? undefined,
          region: merged.state ?? undefined,
          postal_code: merged.zip ?? undefined,
          country: merged.country ?? undefined,
          external_id: merged.externalId ?? undefined,
        },
      });
    }
  } catch {
    /* noop */
  }
}

/* ----------------------------------------------------------------- track() */

export function track(event: TrackEvent, payload: TrackPayload = {}): void {
  if (typeof window === 'undefined') return;
  const w = window as unknown as W;
  const cfg = w.__ECOM_ANALYTICS__;
  const currency = payload.currency ?? 'BRL';
  const value = computedValue(payload);

  // ---------- Google (GA4 + Google Ads) ----------
  const gaParams: Record<string, unknown> = { currency, value };
  if (payload.items?.length) gaParams.items = ga4Items(payload.items, payload);
  if (payload.transaction_id) gaParams.transaction_id = payload.transaction_id;
  if (payload.coupon) gaParams.coupon = payload.coupon;
  if (typeof payload.shipping === 'number') gaParams.shipping = round(payload.shipping);
  if (typeof payload.tax === 'number') gaParams.tax = round(payload.tax);
  if (typeof payload.discount === 'number') gaParams.discount = round(payload.discount);
  if (payload.affiliation) gaParams.affiliation = payload.affiliation;
  if (payload.search_term) gaParams.search_term = payload.search_term;
  if (payload.item_list_id) gaParams.item_list_id = payload.item_list_id;
  if (payload.item_list_name) gaParams.item_list_name = payload.item_list_name;
  if (payload.method)
    gaParams[event === 'add_shipping_info' ? 'shipping_tier' : 'payment_type'] = payload.method;

  try {
    if (typeof w.gtag === 'function') {
      w.gtag('event', event, gaParams);
      if (event === 'purchase' && cfg?.ads) {
        w.gtag('event', 'conversion', {
          send_to: cfg.adsPurchaseLabel ? `${cfg.ads}/${cfg.adsPurchaseLabel}` : cfg.ads,
          value,
          currency,
          transaction_id: payload.transaction_id,
        });
      }
    } else if (Array.isArray(w.dataLayer)) {
      w.dataLayer.push({ ecommerce: null });
      w.dataLayer.push({ event, ecommerce: gaParams });
    }
  } catch {
    /* noop */
  }

  // ---------- Meta Pixel ----------
  try {
    if (typeof w.fbq === 'function') {
      const name = META_NAME[event];
      const meta: Record<string, unknown> = { currency, value };
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
export function trackPageView(url: string): void {
  if (typeof window === 'undefined') return;
  const w = window as unknown as W;
  const cfg = w.__ECOM_ANALYTICS__;
  try {
    if (typeof w.gtag === 'function') {
      if (cfg?.ga4)
        w.gtag('event', 'page_view', { page_path: url, page_location: window.location.href });
    } else if (Array.isArray(w.dataLayer)) {
      w.dataLayer.push({ event: 'page_view', page_path: url });
    }
    if (typeof w.fbq === 'function') w.fbq('track', 'PageView');
  } catch {
    /* noop */
  }
}
