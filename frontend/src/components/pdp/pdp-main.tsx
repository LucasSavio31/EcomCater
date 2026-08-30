'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import type { ProductDetail } from '@/modules/catalog/types';
import { ProductGallery } from '@/components/pdp/product-gallery';
import { PdpBuyBox } from '@/components/pdp/pdp-buy-box';
import { ShippingCalculator } from '@/components/pdp/shipping-calculator';
import { Stars } from '@/components/catalog/stars';

interface PdpMainProps {
  product: ProductDetail;
  redirectAfterAdd: boolean;
  miniCart: boolean;
}

export function PdpMain({ product, redirectAfterAdd, miniCart }: PdpMainProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const colorType = useMemo(
    () => product.option_types.find((t) => t.is_color) ?? null,
    [product.option_types],
  );

  /** variantId -> id do valor de cor que ela carrega */
  const variantColor = useMemo(() => {
    const map = new Map<string, string>();
    if (!colorType) return map;
    const colorIds = new Set(colorType.values.map((v) => v.id));
    for (const v of product.variants) {
      const cv = v.option_value_ids.find((id) => colorIds.has(id));
      if (cv) map.set(v.id, cv);
    }
    return map;
  }, [colorType, product.variants]);

  const initialColorId = useMemo(() => {
    if (!colorType || colorType.values.length === 0) return null;
    const slug = searchParams.get('cor');
    const bySlug = colorType.values.find((v) => v.slug === slug);
    return bySlug?.id ?? colorType.values[0]?.id ?? null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [colorType]);

  const [colorValueId, setColorValueId] = useState<string | null>(initialColorId);

  useEffect(() => {
    setColorValueId(initialColorId);
  }, [initialColorId]);

  const galleryImages = useMemo(() => {
    if (!colorType || !colorValueId) return product.images;
    const forColor = product.images.filter(
      (img) => img.variant_id && variantColor.get(img.variant_id) === colorValueId,
    );
    const val = colorType.values.find((v) => v.id === colorValueId);
    const swatch = val?.image_id
      ? product.images.find((img) => img.id === val.image_id)
      : undefined;
    const merged = swatch ? [swatch, ...forColor.filter((i) => i.id !== swatch.id)] : forColor;
    return merged.length > 0 ? merged : product.images;
  }, [colorType, colorValueId, product.images, variantColor]);

  const onColorChange = useCallback(
    (valueId: string) => {
      setColorValueId(valueId);
      const val = colorType?.values.find((v) => v.id === valueId);
      const url = val?.slug ? `${pathname}?cor=${encodeURIComponent(val.slug)}` : pathname;
      window.history.replaceState(window.history.state, '', url);
    },
    [colorType, pathname],
  );

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1.38fr)_minmax(0,1fr)] lg:gap-12">
      <ProductGallery
        key={colorValueId ?? 'default'}
        images={galleryImages}
        productName={product.name}
      />

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

        <PdpBuyBox
          product={product}
          redirectAfterAdd={redirectAfterAdd}
          miniCart={miniCart}
          colorType={colorType}
          colorValueId={colorValueId}
          onColorChange={onColorChange}
        />

        <div className="rounded-card border border-surface-border p-4">
          <p className="mb-2 text-sm font-semibold">Calcular frete e prazo</p>
          <ShippingCalculator product={product} />
        </div>
      </div>
    </div>
  );
}
