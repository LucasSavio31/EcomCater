'use client';

import { Input } from '@ecom/ui';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { useThemeEditor } from './use-theme-editor';
import { ColorGrid, SaveBar, SectionCard, type ColorFieldDef } from './_shared';

const VARIATION: ColorFieldDef[] = [
  { key: 'variation_bg_color', label: 'Fundo da caixa selecionada' },
  { key: 'variation_text_color', label: 'Texto da caixa selecionada' },
  { key: 'variation_border_color', label: 'Borda da caixa' },
];
const SIZE_CHART: ColorFieldDef[] = [
  { key: 'size_chart_bg_color', label: 'Fundo do popup' },
  { key: 'size_chart_header_bg_color', label: 'Fundo do cabeçalho' },
  { key: 'size_chart_header_text_color', label: 'Texto do cabeçalho' },
  { key: 'size_chart_text_color', label: 'Texto da tabela' },
];
const FREIGHT_BTN: ColorFieldDef[] = [
  { key: 'freight_button_bg_color', label: 'Fundo' },
  { key: 'freight_button_text_color', label: 'Texto' },
  { key: 'freight_button_hover_color', label: 'Hover' },
  { key: 'freight_button_border_color', label: 'Borda' },
];
const PROMO_BADGE: ColorFieldDef[] = [
  { key: 'promo_badge_bg_color', label: 'Fundo do selo' },
  { key: 'promo_badge_text_color', label: 'Texto do selo' },
  { key: 'promo_badge_border_color', label: 'Borda do selo' },
];
const WISHLIST_BTN: ColorFieldDef[] = [
  { key: 'pdp_wishlist_bg_color', label: 'Fundo (quando favoritado)' },
  { key: 'pdp_wishlist_border_color', label: 'Borda (quando favoritado)' },
  { key: 'pdp_wishlist_icon_color', label: 'Coração (quando favoritado)' },
];

export function ProductPageTab() {
  const { theme, dirty, saving, loading, error, reload, set, save, discard } = useThemeEditor();

  return (
    <AsyncBoundary loading={loading} error={error} onRetry={reload}>
      {theme && (
        <div className="flex max-w-3xl flex-col gap-6">
          <SectionCard title="Página do produto">
            <Checkbox
              label="Mostrar seletor de quantidade"
              hint="Desligado: o botão Comprar ocupa toda a largura."
              checked={theme.pdp_qty_selector_enabled}
              onChange={(v) => set('pdp_qty_selector_enabled', v)}
            />
            <Checkbox
              label="Mostrar “Você também pode gostar” (relacionados)"
              hint="No fim da página, abaixo das avaliações."
              checked={theme.pdp_related_enabled}
              onChange={(v) => set('pdp_related_enabled', v)}
            />
            <Checkbox
              label="Ativar favoritos (coração + menu)"
              checked={theme.wishlist_enabled}
              onChange={(v) => set('wishlist_enabled', v)}
            />
            <Checkbox
              label="Exibir o selo de desconto (-XX%)"
              hint="Chave geral (preço 'de' x promocional). Onde ele aparece se ajusta em “Selo de promoção (-XX%)” abaixo."
              checked={theme.discount_badge_enabled}
              onChange={(v) => set('discount_badge_enabled', v)}
            />
          </SectionCard>

          <SectionCard
            title="Caixas de variação"
            hint="Cor e raio das caixas de numeração/cor e do botão Calcular frete — independente dos botões gerais."
          >
            <ColorGrid fields={VARIATION} theme={theme} set={set} />
            <Input
              label="Raio da caixa (px)"
              inputMode="numeric"
              hint="0 = quadrado · máx. 40"
              className="w-40"
              value={String(theme.variation_radius_px ?? 12)}
              onChange={(e) =>
                set('variation_radius_px', Math.max(0, Math.min(40, Number(e.target.value) || 0)))
              }
            />
          </SectionCard>

          <SectionCard title="Popup “Tabela de medidas” (cores)">
            <ColorGrid fields={SIZE_CHART} theme={theme} set={set} />
          </SectionCard>

          <SectionCard title="Botão “Calcular frete” (cores)" hint="Fica na página do produto, abaixo do preço.">
            <ColorGrid fields={FREIGHT_BTN} theme={theme} set={set} />
            <Input
              label="Raio do botão (px)"
              inputMode="numeric"
              hint="0 = quadrado · máx. 40"
              className="w-40"
              value={String(theme.freight_button_radius_px ?? 12)}
              onChange={(e) =>
                set('freight_button_radius_px', Math.max(0, Math.min(40, Number(e.target.value) || 0)))
              }
            />
          </SectionCard>

          <SectionCard
            title="Selo de promoção (-XX%)"
            hint="Precisa do selo ligado em “Página do produto” (topo). Aqui você escolhe onde ele aparece e as cores."
          >
            <Checkbox
              label="Mostrar na vitrine (cards)"
              checked={theme.promo_badge_card_enabled}
              onChange={(v) => set('promo_badge_card_enabled', v)}
            />
            <Checkbox
              label="Mostrar na página do produto"
              checked={theme.promo_badge_pdp_enabled}
              onChange={(v) => set('promo_badge_pdp_enabled', v)}
            />
            <ColorGrid fields={PROMO_BADGE} theme={theme} set={set} />
            <Input
              label="Raio da borda (px)"
              inputMode="numeric"
              hint="0 = quadrado · máx. 40"
              className="w-40"
              value={String(theme.promo_badge_radius_px ?? 6)}
              onChange={(e) =>
                set('promo_badge_radius_px', Math.max(0, Math.min(40, Number(e.target.value) || 0)))
              }
            />
          </SectionCard>

          <SectionCard
            title="Botão de favoritar (coração)"
            hint="Ao lado do botão Comprar. As cores valem quando o item está favoritado; sem favoritar, fica com contorno neutro."
          >
            <ColorGrid fields={WISHLIST_BTN} theme={theme} set={set} />
          </SectionCard>

          <SectionCard
            title="Bloco de garantias"
            hint="Aparece na página do produto (abaixo do botão comprar) e no resumo do carrinho. Pode incluir emoji no começo de cada linha."
          >
            <Checkbox
              label="Mostrar o bloco (página do produto + carrinho)"
              checked={theme.pdp_reassurance_enabled}
              onChange={(v) => set('pdp_reassurance_enabled', v)}
            />
            {theme.pdp_reassurance_enabled && (
              <div className="flex flex-col gap-2">
                {theme.pdp_reassurance_items.map((item, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input
                      value={item}
                      onChange={(e) => {
                        const next = [...theme.pdp_reassurance_items];
                        next[i] = e.target.value;
                        set('pdp_reassurance_items', next);
                      }}
                      className="flex-1"
                    />
                    <button
                      type="button"
                      aria-label="Remover linha"
                      className="text-text-muted hover:text-danger"
                      onClick={() =>
                        set(
                          'pdp_reassurance_items',
                          theme.pdp_reassurance_items.filter((_, j) => j !== i),
                        )
                      }
                    >
                      ×
                    </button>
                  </div>
                ))}
                {theme.pdp_reassurance_items.length < 6 && (
                  <button
                    type="button"
                    className="self-start text-sm text-accent hover:underline"
                    onClick={() =>
                      set('pdp_reassurance_items', [...theme.pdp_reassurance_items, ''])
                    }
                  >
                    + adicionar linha
                  </button>
                )}
              </div>
            )}
          </SectionCard>

          <SectionCard title="Cards da vitrine">
            <Checkbox
              label="Zoom suave na imagem ao passar o mouse"
              checked={theme.card_hover_zoom_enabled}
              onChange={(v) => set('card_hover_zoom_enabled', v)}
            />
            <Checkbox
              label="Botão de compra abaixo do card"
              hint="Segue a cor do botão de comprar, sem o ícone do carrinho."
              checked={theme.card_buy_button_enabled}
              onChange={(v) => set('card_buy_button_enabled', v)}
            />
            {theme.card_buy_button_enabled && (
              <Input
                label="Texto do botão do card"
                value={theme.card_buy_button_label}
                onChange={(e) => set('card_buy_button_label', e.target.value)}
                className="w-48"
              />
            )}
          </SectionCard>

          <SectionCard title="Ao adicionar ao carrinho">
            <Checkbox
              label="Abrir mini-carrinho lateral"
              hint="Tem precedência sobre a opção abaixo."
              checked={theme.mini_cart_enabled}
              onChange={(v) => set('mini_cart_enabled', v)}
            />
            <Checkbox
              label="Ir direto para o carrinho"
              hint="Só quando o mini-carrinho está desligado."
              checked={theme.cart_redirect_after_add}
              onChange={(v) => set('cart_redirect_after_add', v)}
            />
          </SectionCard>

          <SaveBar dirty={dirty} saving={saving} onSave={() => void save()} onDiscard={discard} />
        </div>
      )}
    </AsyncBoundary>
  );
}
