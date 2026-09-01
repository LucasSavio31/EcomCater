'use client';

import { Button, Input } from '@ecom/ui';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { ImageUploader } from '@/components/image-uploader';
import { useThemeEditor } from './use-theme-editor';
import { ColorGrid, SaveBar, SectionCard, type ColorFieldDef } from './_shared';

const LEAD_COLORS: ColorFieldDef[] = [
  { key: 'lead_popup_bg_color', label: 'Fundo do popup' },
  { key: 'lead_popup_text_color', label: 'Texto do popup' },
  { key: 'lead_popup_button_color', label: 'Fundo do botão' },
  { key: 'lead_popup_button_text_color', label: 'Texto do botão' },
];
const NEWSLETTER_COLORS: ColorFieldDef[] = [
  { key: 'newsletter_bg_color', label: 'Fundo do bloco' },
  { key: 'newsletter_text_color', label: 'Texto do bloco' },
  { key: 'newsletter_button_color', label: 'Fundo do botão' },
  { key: 'newsletter_button_text_color', label: 'Texto do botão' },
];

export function PopupsTab() {
  const { theme, dirty, saving, loading, error, reload, set, save, discard, upload, removeImage } =
    useThemeEditor();

  return (
    <AsyncBoundary loading={loading} error={error} onRetry={reload}>
      {theme && (
        <div className="flex max-w-3xl flex-col gap-6">
          {/* --------------------------------------------------- Popup de leads */}
          <SectionCard
            title="Popup de captura de leads"
            hint="O mesmo popup (título, subtítulo, cupom e cores abaixo) é usado nos dois modos. Os inscritos ficam em Marketing → Newsletter."
          >
            <Checkbox
              label="Ativar o formulário de captura na home"
              checked={theme.lead_capture_enabled}
              onChange={(v) => set('lead_capture_enabled', v)}
            />
            <Checkbox
              label="Ativar o popup automático na loja"
              hint="Abre sozinho ~6s após o visitante entrar; some por 7 dias depois de fechado e volta a aparecer."
              checked={theme.lead_popup_enabled}
              onChange={(v) => set('lead_popup_enabled', v)}
            />
            <Checkbox
              label="Ativar na página do produto"
              hint='Mostra o link “Cadastre-se e ganhe…” abaixo do botão comprar; abre o popup ao clicar.'
              checked={theme.lead_popup_pdp_enabled}
              onChange={(v) => set('lead_popup_pdp_enabled', v)}
            />
            <Input label="Título" value={theme.lead_popup_title} onChange={(e) => set('lead_popup_title', e.target.value)} />
            <Input
              label="Subtítulo"
              value={theme.lead_popup_subtitle}
              onChange={(e) => set('lead_popup_subtitle', e.target.value)}
            />
            <Input
              label="Cupom enviado ao lead (opcional)"
              placeholder="Ex.: BEMVINDO10"
              value={theme.lead_popup_coupon_code ?? ''}
              onChange={(e) => set('lead_popup_coupon_code', e.target.value || null)}
            />

            <div className="flex flex-col gap-3 rounded-card border border-surface-border p-3">
              <Checkbox
                label="Mostrar logo no topo do popup"
                checked={theme.lead_popup_show_logo}
                onChange={(v) => set('lead_popup_show_logo', v)}
                hint="Sem um logo próprio, usa o logo da loja. Desmarque para não mostrar logo nenhum."
              />
              {theme.lead_popup_show_logo && (
                <div className="flex flex-wrap items-end gap-4">
                  <ImageUploader
                    label="Logo do popup"
                    aspect="square"
                    currentUrl={theme.lead_popup_logo_url ?? theme.logo_url ?? null}
                    hint="PNG com fundo transparente fica melhor."
                    onSelect={(file) => upload('lead_popup_logo', file)}
                  />
                  {theme.lead_popup_logo_url && (
                    <Button size="sm" variant="ghost" onClick={() => void removeImage('lead_popup_logo')}>
                      Remover logo do popup
                    </Button>
                  )}
                </div>
              )}
            </div>

            <ColorGrid fields={LEAD_COLORS} theme={theme} set={set} />
          </SectionCard>

          {/* --------------------------------------------------- Aviso de cookies */}
          <SectionCard title="Aviso de cookies">
            <Checkbox
              label="Exibir aviso de cookies de terceiros no site"
              checked={theme.cookie_consent_enabled}
              onChange={(v) => set('cookie_consent_enabled', v)}
            />
            <Input
              label="Texto do aviso"
              value={theme.cookie_consent_text}
              onChange={(e) => set('cookie_consent_text', e.target.value)}
            />
          </SectionCard>

          {/* --------------------------------------------------- Bloco newsletter */}
          <SectionCard title="Bloco de newsletter na home">
            <Checkbox
              label="Exibir o bloco de newsletter na home"
              checked={theme.newsletter_enabled}
              onChange={(v) => set('newsletter_enabled', v)}
            />
            <Input label="Título" value={theme.newsletter_title} onChange={(e) => set('newsletter_title', e.target.value)} />
            <Input
              label="Subtítulo"
              value={theme.newsletter_subtitle}
              onChange={(e) => set('newsletter_subtitle', e.target.value)}
            />
            <ColorGrid fields={NEWSLETTER_COLORS} theme={theme} set={set} />
          </SectionCard>

          <SaveBar dirty={dirty} saving={saving} onSave={() => void save()} onDiscard={discard} />
        </div>
      )}
    </AsyncBoundary>
  );
}
