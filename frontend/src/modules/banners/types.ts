/** Tipos de `GET /api/banners?slot=…`. */

export type BannerSlot = 'hero' | 'showcase' | 'top_bar' | string;

export interface Banner {
  id: string;
  slot: BannerSlot;
  title: string | null;
  image_desktop_url: string | null;
  image_mobile_url: string | null;
  link_url: string | null;
  alt: string | null;
  position: number;
}
