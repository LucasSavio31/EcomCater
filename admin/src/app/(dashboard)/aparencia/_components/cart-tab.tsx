'use client';

import { Input } from '@ecom/ui';
import { AsyncBoundary } from '@/components/async-boundary';
import { useThemeEditor } from './use-theme-editor';
import { ColorGrid, SaveBar, SectionCard, type ColorFieldDef } from './_shared';

const CHECKOUT_BTN: ColorFieldDef[] = [
  { key: 'cart_checkout_btn_bg_color', label: 'Fundo' },
  { key: 'cart_checkout_btn_text_color', label: 'Texto' },
  { key: 'cart_checkout_btn_hover_color', label: 'Hover' },
  { key: 'cart_checkout_btn_border_color', label: 'Borda' },
];
const FREIGHT_BTN: ColorFieldDef[] = [
  { key: 'cart_freight_btn_bg_color', label: 'Fundo' },
  { key: 'cart_freight_btn_text_color', label: 'Texto' },
  { key: 'cart_freight_btn_hover_color', label: 'Hover' },
  { key: 'cart_freight_btn_border_color', label: 'Borda' },
];
const QTY: ColorFieldDef[] = [
  { key: 'cart_qty_bg_color', label: 'Fundo da caixinha' },
  { key: 'cart_qty_text_color', label: 'Texto (número e −/+)' },
];
const COUPON_BTN: ColorFieldDef[] = [
  { key: 'cart_coupon_btn_bg_color', label: 'Fundo' },
  { key: 'cart_coupon_btn_text_color', label: 'Texto' },
  { key: 'cart_coupon_btn_hover_color', label: 'Hover' },
  { key: 'cart_coupon_btn_border_color', label: 'Borda' },
];

function RadiusInput({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <Input
      label="Raio (px)"
      inputMode="numeric"
      hint="0 = quadrado · máx. 40"
      className="w-40"
      value={String(value ?? 12)}
      onChange={(e) => onChange(Math.max(0, Math.min(40, Number(e.target.value) || 0)))}
    />
  );
}

export function CartTab() {
  const { theme, dirty, saving, loading, error, reload, set, save, discard } = useThemeEditor();

  return (
    <AsyncBoundary loading={loading} error={error} onRetry={reload}>
      {theme && (
        <div className="flex max-w-3xl flex-col gap-6">
          <SectionCard title="Botão “Finalizar compra”">
            <ColorGrid fields={CHECKOUT_BTN} theme={theme} set={set} />
            <RadiusInput
              value={theme.cart_checkout_btn_radius_px}
              onChange={(v) => set('cart_checkout_btn_radius_px', v)}
            />
          </SectionCard>

          <SectionCard title="Botão “Calcular” (frete) no carrinho">
            <ColorGrid fields={FREIGHT_BTN} theme={theme} set={set} />
            <RadiusInput
              value={theme.cart_freight_btn_radius_px}
              onChange={(v) => set('cart_freight_btn_radius_px', v)}
            />
          </SectionCard>

          <SectionCard title="Caixinhas de quantidade (−  valor  +)">
            <ColorGrid fields={QTY} theme={theme} set={set} />
            <RadiusInput
              value={theme.cart_qty_radius_px}
              onChange={(v) => set('cart_qty_radius_px', v)}
            />
          </SectionCard>

          <SectionCard title="Botão “Aplicar” do cupom">
            <ColorGrid fields={COUPON_BTN} theme={theme} set={set} />
            <RadiusInput
              value={theme.cart_coupon_btn_radius_px}
              onChange={(v) => set('cart_coupon_btn_radius_px', v)}
            />
          </SectionCard>

          <SaveBar dirty={dirty} saving={saving} onSave={() => void save()} onDiscard={discard} />
        </div>
      )}
    </AsyncBoundary>
  );
}
