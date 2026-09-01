'use client';

import { useState } from 'react';
import { Input } from '@ecom/ui';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { ColorField } from '@/components/color-field';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { maskPhone } from '@/lib/phone';
import { appearanceApi, type Theme } from '@/modules/appearance/api';
import { useThemeEditor } from './use-theme-editor';
import { ColorGrid, SaveBar, SectionCard, type ColorFieldDef } from './_shared';

const TOPBAR: ColorFieldDef[] = [
  { key: 'top_bar_bg_color', label: 'Fundo da barra' },
  { key: 'top_bar_text_color', label: 'Texto da barra' },
];

const CART_BADGE: ColorFieldDef[] = [
  { key: 'cart_badge_bg_color', label: 'Fundo da bolinha' },
  { key: 'cart_badge_text_color', label: 'Número' },
];

const SOCIAL_NETS = ['instagram', 'facebook', 'tiktok', 'youtube'] as const;
type SocialNet = (typeof SOCIAL_NETS)[number];
const SOCIAL_ENABLED_KEY: Record<SocialNet, keyof Theme> = {
  instagram: 'footer_social_instagram_enabled',
  facebook: 'footer_social_facebook_enabled',
  tiktok: 'footer_social_tiktok_enabled',
  youtube: 'footer_social_youtube_enabled',
};
const SOCIAL_LABEL: Record<SocialNet, string> = {
  instagram: 'Instagram',
  facebook: 'Facebook',
  tiktok: 'TikTok',
  youtube: 'YouTube',
};

export function HeaderFooterTab() {
  const toast = useToast();
  const { theme, dirty, saving, loading, error, reload, set, save, discard } = useThemeEditor();
  const settingsRes = useResource(() => appearanceApi.getSettings());
  const [socialDraft, setSocialDraft] = useState<Record<string, string> | null>(null);

  const social = socialDraft ?? settingsRes.data?.social_json ?? {};
  const setSocial = (net: SocialNet, url: string): void => setSocialDraft({ ...social, [net]: url });

  async function saveAll(): Promise<void> {
    const okTheme = await save();
    if (okTheme && socialDraft) {
      const r = await appearanceApi.putSettings({ social_json: socialDraft });
      if (!r.ok) {
        toast.error(r.error.message);
        return;
      }
      setSocialDraft(null);
      settingsRes.reload();
    }
  }

  return (
    <AsyncBoundary loading={loading} error={error} onRetry={reload}>
      {theme && (
        <div className="flex max-w-3xl flex-col gap-6">
          <SectionCard title="Barra superior">
            <Checkbox label="Exibir barra superior" checked={theme.top_bar_enabled} onChange={(v) => set('top_bar_enabled', v)} />
            <Checkbox
              label="Texto em carrossel (até 3 mensagens girando)"
              hint="Desligado: mostra só uma mensagem fixa."
              checked={theme.top_bar_carousel}
              onChange={(v) => set('top_bar_carousel', v)}
            />
            <Checkbox
              label="Texto centralizado"
              checked={theme.top_bar_centered}
              onChange={(v) => set('top_bar_centered', v)}
            />
            <Input label="Mensagem 1" value={theme.top_bar_message ?? ''} onChange={(e) => set('top_bar_message', e.target.value)} />
            {theme.top_bar_carousel && (
              <>
                <Input label="Mensagem 2" value={theme.top_bar_message_2 ?? ''} onChange={(e) => set('top_bar_message_2', e.target.value || null)} />
                <Input label="Mensagem 3" value={theme.top_bar_message_3 ?? ''} onChange={(e) => set('top_bar_message_3', e.target.value || null)} />
              </>
            )}
            <ColorGrid fields={TOPBAR} theme={theme} set={set} />
            <Input
              label="WhatsApp"
              inputMode="numeric"
              placeholder="(11) 99999-9999"
              value={maskPhone(theme.whatsapp_number ?? '')}
              onChange={(e) => set('whatsapp_number', e.target.value.replace(/\D/g, ''))}
            />
            <p className="text-xs text-text-muted">
              O valor de frete grátis fica em <b>Frete</b>. A barra mostra o progresso automaticamente.
            </p>
          </SectionCard>

          <SectionCard
            title="Sacola do cabeçalho"
            hint="A bolinha com a quantidade de itens sobre o ícone da sacola."
          >
            <ColorGrid fields={CART_BADGE} theme={theme} set={set} />
          </SectionCard>

          <SectionCard title="Rodapé — texto e copyright">
            <label className="flex flex-col gap-1 text-sm font-medium text-text">
              Texto abaixo do logo do rodapé
              <textarea
                value={theme.footer_note_text ?? ''}
                onChange={(e) => set('footer_note_text', e.target.value)}
                rows={2}
                className="rounded-card border border-surface-border bg-surface px-3 py-2 text-sm font-normal"
              />
              <span className="text-xs text-text-muted">Herda a cor do texto do rodapé. Vazio = não exibe.</span>
            </label>
            <div className="flex flex-col gap-3 border-t border-surface-border pt-4">
              <Checkbox
                label="Exibir tarja de copyright (abaixo de tudo)"
                checked={theme.footer_copyright_enabled}
                onChange={(v) => set('footer_copyright_enabled', v)}
              />
              {theme.footer_copyright_enabled && (
                <>
                  <label className="flex flex-col gap-1 text-sm font-medium text-text">
                    Texto do copyright
                    <input
                      value={theme.footer_copyright_text ?? ''}
                      onChange={(e) => set('footer_copyright_text', e.target.value)}
                      className="rounded-card border border-surface-border bg-surface px-3 py-2 text-sm font-normal"
                    />
                    <span className="text-xs text-text-muted">
                      Variáveis: <code>{'{ano}'}</code>, <code>{'{loja}'}</code>, <code>{'{cnpj}'}</code>.
                    </span>
                  </label>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <ColorField
                      label="Fundo da tarja de copyright"
                      value={String(theme.footer_copyright_bg_color ?? '#FFFFFF')}
                      onChange={(hex) => set('footer_copyright_bg_color', hex as Theme['footer_copyright_bg_color'])}
                    />
                    <ColorField
                      label="Texto da tarja de copyright"
                      value={String(theme.footer_copyright_text_color ?? '#6B7280')}
                      onChange={(hex) => set('footer_copyright_text_color', hex as Theme['footer_copyright_text_color'])}
                    />
                  </div>
                </>
              )}
            </div>
          </SectionCard>

          <SectionCard title="Redes sociais (coluna “Siga-nos”)" hint="Sem link, a rede não aparece mesmo ligada.">
            {SOCIAL_NETS.map((net) => {
              const on = Boolean(theme[SOCIAL_ENABLED_KEY[net]]);
              return (
                <div key={net} className="flex flex-col gap-1.5">
                  <Checkbox
                    label={SOCIAL_LABEL[net]}
                    checked={on}
                    onChange={(v) => set(SOCIAL_ENABLED_KEY[net], v as never)}
                  />
                  {on && (
                    <Input
                      placeholder={`https://${net}.com/sua-loja`}
                      value={social[net] ?? ''}
                      onChange={(e) => setSocial(net, e.target.value)}
                    />
                  )}
                </div>
              );
            })}
          </SectionCard>

          <SectionCard title="Banner principal (Hero)">
            <Checkbox label="Exibir o banner principal na home" checked={theme.hero_enabled} onChange={(v) => set('hero_enabled', v)} />
            <div className="flex gap-2">
              {(['carousel', 'static'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => set('hero_mode', m)}
                  className={`min-h-touch flex-1 rounded-card border px-3 text-sm font-medium ${
                    theme.hero_mode === m ? 'border-primary bg-primary/5' : 'border-surface-border'
                  }`}
                >
                  {m === 'carousel' ? 'Carrossel' : 'Imagem estática'}
                </button>
              ))}
            </div>
            {theme.hero_mode === 'carousel' && (
              <Input
                label="Autoplay (segundos, 0 = desligado)"
                inputMode="numeric"
                value={String(theme.hero_autoplay_seconds)}
                onChange={(e) => set('hero_autoplay_seconds', Math.max(0, Math.min(30, Number(e.target.value) || 0)))}
                className="w-40"
              />
            )}
            <p className="text-xs text-text-muted">
              As imagens do hero são cadastradas na aba <strong>Banners</strong> (slot “hero”).
            </p>
          </SectionCard>

          <SaveBar
            dirty={dirty || socialDraft !== null}
            saving={saving}
            onSave={() => void saveAll()}
            onDiscard={() => {
              discard();
              setSocialDraft(null);
            }}
          />
        </div>
      )}
    </AsyncBoundary>
  );
}
