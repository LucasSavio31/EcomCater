import type { ProductDetail } from '@/modules/catalog/types';
import type { ThemeSettings } from '@/modules/theme/types';
import { ProductGallery } from '@/components/pdp/product-gallery';
import { PdpBuyBox } from '@/components/pdp/pdp-buy-box';
import { ShippingCalculator } from '@/components/pdp/shipping-calculator';
import { ColorSiblings } from '@/components/pdp/color-siblings';
import { Stars } from '@/components/catalog/stars';
import type { LeadPopupConfig } from '@/components/lead-popup';

interface PdpMainProps {
  product: ProductDetail;
  redirectAfterAdd: boolean;
  miniCart: boolean;
  theme: ThemeSettings;
}

/**
 * Bloco principal da PDP: galeria + infos. Proporção de colunas ~58/42 como no
 * modelo de referência. A variação de COR são produtos irmãos (miniaturas que
 * navegam); TAMANHO/numeração ficam nas caixinhas do buy-box.
 */
export function PdpMain({ product, redirectAfterAdd, miniCart, theme }: PdpMainProps) {
  const leadPopup: LeadPopupConfig = {
    enabled: theme.lead_popup_enabled,
    title: theme.lead_popup_title,
    subtitle: theme.lead_popup_subtitle,
    logoUrl: theme.logo_url ?? null,
    bg: theme.lead_popup_bg_color,
    text: theme.lead_popup_text_color,
    btn: theme.lead_popup_button_color,
    btnText: theme.lead_popup_button_text_color,
  };
  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1.38fr)_minmax(0,1fr)] lg:gap-12">
      <ProductGallery images={product.images} productName={product.name} />

      <div className="flex flex-col gap-5">
        {product.brand && (
          <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
            {product.brand}
          </span>
        )}
        <h1 className="text-2xl font-bold leading-tight sm:text-3xl">{product.name}</h1>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <Stars value={product.rating_avg} count={product.rating_count} size="md" />
          {product.sku_root && (
            <span className="text-xs text-text-muted">Referência: {product.sku_root}</span>
          )}
        </div>

        <ColorSiblings
          currentColorName={product.color_name}
          siblings={product.color_siblings}
        />

        <PdpBuyBox
          product={product}
          redirectAfterAdd={redirectAfterAdd}
          miniCart={miniCart}
          leadPopup={leadPopup}
        />

        <div className="rounded-card border border-surface-border p-4">
          <p className="mb-2 text-sm font-semibold">Calcular frete e prazo</p>
          <ShippingCalculator product={product} />
        </div>
      </div>
    </div>
  );
}
