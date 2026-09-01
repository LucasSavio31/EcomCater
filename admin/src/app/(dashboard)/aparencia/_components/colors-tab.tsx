'use client';

import { Input } from '@ecom/ui';
import { AsyncBoundary } from '@/components/async-boundary';
import { ImageUploader } from '@/components/image-uploader';
import { useThemeEditor } from './use-theme-editor';
import { ColorGrid, SaveBar, SectionCard, type ColorFieldDef } from './_shared';

const PALETTE: ColorFieldDef[] = [
  { key: 'primary_color', label: 'Primária' },
  { key: 'secondary_color', label: 'Secundária' },
  { key: 'accent_color', label: 'Destaque' },
  { key: 'text_color', label: 'Texto' },
  { key: 'bg_color', label: 'Fundo' },
];
const BUTTONS: ColorFieldDef[] = [
  { key: 'button_bg_color', label: 'Fundo do botão' },
  { key: 'button_text_color', label: 'Texto do botão' },
  { key: 'button_hover_color', label: 'Botão (hover)' },
];
const HEADER: ColorFieldDef[] = [
  { key: 'header_bg_color', label: 'Fundo do menu superior' },
  { key: 'header_text_color', label: 'Texto do menu superior' },
];
const FOOTER: ColorFieldDef[] = [
  { key: 'footer_bg_color', label: 'Fundo do rodapé' },
  { key: 'footer_text_color', label: 'Texto do rodapé' },
];

export function ColorsTab() {
  const { theme, dirty, saving, loading, error, reload, set, save, discard, upload } = useThemeEditor();

  return (
    <AsyncBoundary loading={loading} error={error} onRetry={reload}>
      {theme && (
        <div className="flex max-w-3xl flex-col gap-6">
          <SectionCard title="Paleta base">
            <ColorGrid fields={PALETTE} theme={theme} set={set} />
            <Input
              label="Família de fonte"
              value={theme.font_family}
              onChange={(e) => set('font_family', e.target.value)}
            />
          </SectionCard>

          <SectionCard title="Botões (geral)" hint="Vale para os botões da loja inteira.">
            <Input
              label="Raio das bordas (px)"
              inputMode="numeric"
              hint="0 = quadrado."
              value={String(theme.button_radius_px ?? 12)}
              onChange={(e) =>
                set('button_radius_px', Math.max(0, Math.min(40, Number(e.target.value) || 0)))
              }
              className="w-40"
            />
            <ColorGrid fields={BUTTONS} theme={theme} set={set} />
          </SectionCard>

          <SectionCard title="Menu superior">
            <ColorGrid fields={HEADER} theme={theme} set={set} />
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium" htmlFor="header-width">
                Largura do menu superior (px)
              </label>
              <input
                id="header-width"
                type="range"
                min={960}
                max={1920}
                step={20}
                value={theme.header_max_width_px}
                onChange={(e) => set('header_max_width_px', Number(e.target.value))}
              />
              <Input
                inputMode="numeric"
                value={String(theme.header_max_width_px)}
                onChange={(e) => set('header_max_width_px', Number(e.target.value) || 0)}
                className="w-28"
                hint="entre 640 e 2560"
              />
            </div>
          </SectionCard>

          <SectionCard title="Rodapé (cores)">
            <ColorGrid fields={FOOTER} theme={theme} set={set} />
          </SectionCard>

          <SectionCard title="Logo e favicon" hint="Uma imagem só, usada em todas as telas.">
            <div className="flex flex-wrap gap-6">
              <ImageUploader
                label="Logo"
                aspect="wide"
                currentUrl={theme.logo_url ?? null}
                onSelect={(file) => upload('logo', file)}
              />
              <ImageUploader
                label="Favicon"
                aspect="square"
                currentUrl={theme.favicon_url ?? null}
                onSelect={(file) => upload('favicon', file)}
              />
            </div>
          </SectionCard>

          <SaveBar dirty={dirty} saving={saving} onSave={() => void save()} onDiscard={discard} />
        </div>
      )}
    </AsyncBoundary>
  );
}
