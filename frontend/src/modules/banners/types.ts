/** Tipos de `GET /api/banners?slot=…`. */

export type BannerSlot = 'hero' | 'showcase' | 'top_bar' | string;

export interface Banner {
  id: string;
  slot: BannerSlot;
  title: string | null;
  /** Uma imagem só — o `next/image` redimensiona para cada tela. */
  image_url: string | null;
  /** compat */
  image_desktop_url?: string | null;
  image_mobile_url?: string | null;
  /** Variante menor (mesma imagem) — pra grids pequenos (ex.: showcase),
   * onde servir a zoom full-bleed desperdiça banda. `next/image` roda com
   * `unoptimized: true`, então quem escolhe o tamanho é o chamador. */
  image_desktop_medium_url?: string | null;
  image_mobile_medium_url?: string | null;
  link_url: string | null;
  alt: string | null;
  position: number;
}
