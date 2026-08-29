'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { Checkbox } from '@/components/form-controls';
import { ImageUploader } from '@/components/image-uploader';
import { useToast } from '@/components/toast';
import { AsyncBoundary } from '@/components/async-boundary';
import { useResource } from '@/lib/use-resource';
import { centsToInput, inputToCents } from '@/lib/format';
import { appearanceApi, type Theme, type ThemeImageKind } from '@/modules/appearance/api';
import { revalidateStore } from '@/lib/revalidate-store';

type ColorField = { key: keyof Theme; label: string };

const PALETTE_FIELDS: ColorField[] = [
  { key: 'primary_color', label: 'Primária' },
  { key: 'secondary_color', label: 'Secundária' },
  { key: 'accent_color', label: 'Destaque' },
  { key: 'text_color', label: 'Texto' },
  { key: 'bg_color', label: 'Fundo' },
];
const BUTTON_FIELDS: ColorField[] = [
  { key: 'button_bg_color', label: 'Fundo do botão' },
  { key: 'button_text_color', label: 'Texto do botão' },
  { key: 'button_hover_color', label: 'Botão (hover)' },
];
const HEADER_FIELDS: ColorField[] = [
  { key: 'header_bg_color', label: 'Fundo do menu superior' },
  { key: 'header_text_color', label: 'Texto do menu superior' },
];
const FOOTER_FIELDS: ColorField[] = [
  { key: 'footer_bg_color', label: 'Fundo do rodapé' },
  { key: 'footer_text_color', label: 'Texto do rodapé' },
];

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;

export function ThemeTab() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => appearanceApi.getTheme());
  const [draft, setDraft] = useState<Theme | null>(null);
  const [saving, setSaving] = useState(false);

  const theme = draft ?? data;
  const dirty = draft !== null;
  const set = <K extends keyof Theme>(k: K, v: Theme[K]): void => {
    if (!theme) return;
    setDraft({ ...theme, [k]: v });
  };

  function ColorRow({ f }: { f: ColorField }) {
    if (!theme) return null;
    const raw = String(theme[f.key] ?? '#000000');
    const valid = HEX_RE.test(raw);
    return (
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium" htmlFor={`color-${f.key}`}>
          {f.label}
        </label>
        <div className="flex items-center gap-2">
          <input
            id={`color-${f.key}`}
            type="color"
            value={valid ? raw.slice(0, 7) : '#000000'}
            onChange={(e) => set(f.key, e.target.value as Theme[typeof f.key])}
            className="h-10 w-14 shrink-0 rounded-card border border-surface-border"
            aria-label={f.label}
          />
          <Input
            value={raw}
            aria-invalid={!valid}
            onChange={(e) => set(f.key, e.target.value as Theme[typeof f.key])}
            className="flex-1"
          />
        </div>
        {!valid && <span className="text-xs text-red-600">Use #RRGGBB.</span>}
      </div>
    );
  }

  async function save(): Promise<void> {
    if (!theme) return;
    setSaving(true);
    const result = await appearanceApi.putTheme(theme);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    await revalidateStore('theme');
    toast.success('Tema salvo e aplicado na loja.');
    setData(result.data);
    setDraft(null);
  }

  async function upload(kind: ThemeImageKind, file: File): Promise<void> {
    const result = await appearanceApi.uploadThemeImage(kind, file);
    if (!result.ok) throw new Error(result.error.message);
    await revalidateStore('theme');
    setData(result.data);
    setDraft(null);
    toast.success('Imagem atualizada.');
  }

  return (
    <AsyncBoundary loading={loading} error={error} onRetry={reload}>
      {theme && (
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <div className="flex flex-col gap-6">
            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Paleta base</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {PALETTE_FIELDS.map((f) => (
                  <ColorRow key={f.key} f={f} />
                ))}
              </div>
              <Input
                label="Família de fonte"
                value={theme.font_family}
                onChange={(e) => set('font_family', e.target.value)}
              />
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Botões</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {BUTTON_FIELDS.map((f) => (
                  <ColorRow key={f.key} f={f} />
                ))}
              </div>
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Menu superior</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {HEADER_FIELDS.map((f) => (
                  <ColorRow key={f.key} f={f} />
                ))}
              </div>
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
                <div className="flex items-center gap-2">
                  <Input
                    inputMode="numeric"
                    value={String(theme.header_max_width_px)}
                    onChange={(e) => set('header_max_width_px', Number(e.target.value) || 0)}
                    className="w-28"
                  />
                  <span className="text-sm text-muted">px (entre 640 e 2560)</span>
                </div>
              </div>
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Rodapé</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {FOOTER_FIELDS.map((f) => (
                  <ColorRow key={f.key} f={f} />
                ))}
              </div>
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Barra superior e contato</h2>
              <Checkbox
                label="Exibir barra superior"
                checked={theme.top_bar_enabled}
                onChange={(v) => set('top_bar_enabled', v)}
              />
              <Input
                label="Mensagem da barra superior"
                value={theme.top_bar_message ?? ''}
                onChange={(e) => set('top_bar_message', e.target.value)}
              />
              <Input
                label="WhatsApp"
                value={theme.whatsapp_number ?? ''}
                onChange={(e) => set('whatsapp_number', e.target.value)}
              />
              <Input
                label="Frete grátis a partir de (R$)"
                inputMode="decimal"
                value={centsToInput(theme.free_shipping_threshold_cents)}
                onChange={(e) => set('free_shipping_threshold_cents', inputToCents(e.target.value))}
              />
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Comportamento da loja</h2>
              <Checkbox
                label="Ir para o carrinho logo após adicionar um produto"
                hint="Desligado: o cliente permanece na página do produto (com a confirmação)."
                checked={theme.cart_redirect_after_add}
                onChange={(v) => set('cart_redirect_after_add', v)}
              />
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Banner principal (Hero)</h2>
              <Checkbox
                label="Exibir o banner principal na home"
                checked={theme.hero_enabled}
                onChange={(v) => set('hero_enabled', v)}
              />
              <div className="flex flex-col gap-1">
                <span className="text-sm font-medium">Tipo</span>
                <div className="flex gap-2">
                  {(['carousel', 'static'] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => set('hero_mode', m)}
                      className={`min-h-touch flex-1 rounded-card border px-3 text-sm font-medium ${
                        theme.hero_mode === m
                          ? 'border-primary bg-primary/5'
                          : 'border-surface-border'
                      }`}
                    >
                      {m === 'carousel' ? 'Carrossel' : 'Imagem estática'}
                    </button>
                  ))}
                </div>
              </div>
              {theme.hero_mode === 'carousel' && (
                <Input
                  label="Autoplay (segundos, 0 = desligado)"
                  inputMode="numeric"
                  value={String(theme.hero_autoplay_seconds)}
                  onChange={(e) =>
                    set('hero_autoplay_seconds', Math.max(0, Math.min(30, Number(e.target.value) || 0)))
                  }
                  className="w-40"
                />
              )}
              <p className="text-xs text-muted">
                As imagens do banner são cadastradas na aba <strong>Banners</strong> (slot “hero”).
                No modo estático a loja mostra só a primeira.
              </p>
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Logo e favicon</h2>
              <div className="flex flex-wrap gap-6">
                <ImageUploader
                  label="Logo"
                  aspect="wide"
                  currentUrl={theme.logo_url ?? null}
                  onSelect={(file) => upload('logo', file)}
                />
                <ImageUploader
                  label="Logo (mobile)"
                  aspect="square"
                  currentUrl={theme.logo_mobile_url ?? null}
                  onSelect={(file) => upload('logo_mobile', file)}
                />
                <ImageUploader
                  label="Favicon"
                  aspect="square"
                  currentUrl={theme.favicon_url ?? null}
                  onSelect={(file) => upload('favicon', file)}
                />
              </div>
            </Card>

            <div className="flex items-center gap-3">
              <Button loading={saving} onClick={() => void save()}>
                Salvar tema
              </Button>
              {dirty && (
                <button
                  type="button"
                  className="text-sm text-muted underline"
                  onClick={() => setDraft(null)}
                >
                  Descartar alterações
                </button>
              )}
            </div>
          </div>

          {/* -------------------- Pré-visualização ao vivo -------------------- */}
          <Card variant="elevated" className="flex flex-col gap-3 lg:sticky lg:top-4 lg:self-start">
            <h2 className="text-lg font-semibold">Pré-visualização ao vivo</h2>
            <div
              className="overflow-hidden rounded-card border"
              style={{ borderColor: theme.secondary_color, fontFamily: theme.font_family }}
            >
              {theme.top_bar_enabled && theme.top_bar_message && (
                <div
                  className="px-3 py-1 text-center text-xs"
                  style={{ background: theme.primary_color, color: theme.bg_color }}
                >
                  {theme.top_bar_message}
                </div>
              )}
              {/* header mock: largura limitada por header_max_width_px */}
              <div style={{ background: theme.header_bg_color, color: theme.header_text_color }}>
                <div
                  className="mx-auto flex items-center justify-between gap-4 px-4 py-3"
                  style={{ maxWidth: `${theme.header_max_width_px}px` }}
                >
                  <span className="text-base font-bold">Sua Loja</span>
                  <nav className="hidden gap-4 text-sm sm:flex">
                    <span>Lançamentos</span>
                    <span>Feminino</span>
                    <span>Masculino</span>
                  </nav>
                  <span aria-hidden className="text-sm">
                    🔍 ♡ 👤 🛒
                  </span>
                </div>
              </div>
              <div
                className="flex flex-col gap-3 p-4"
                style={{ background: theme.bg_color, color: theme.text_color }}
              >
                <p className="text-sm">Um parágrafo de exemplo mostrando a cor do texto.</p>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded-card px-4 py-2 text-sm font-medium transition-colors"
                    style={{ background: theme.button_bg_color, color: theme.button_text_color }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = theme.button_hover_color)}
                    onMouseLeave={(e) => (e.currentTarget.style.background = theme.button_bg_color)}
                  >
                    COMPRAR
                  </button>
                  <span
                    className="rounded-card px-3 py-1.5 text-sm font-medium"
                    style={{ background: theme.accent_color, color: '#fff' }}
                  >
                    5% NO PIX
                  </span>
                </div>
              </div>
              {/* footer mock */}
              <div
                className="px-4 py-4 text-xs"
                style={{ background: theme.footer_bg_color, color: theme.footer_text_color }}
              >
                <div className="flex flex-wrap gap-4">
                  <span>Quem Somos</span>
                  <span>Política de Privacidade</span>
                  <span>Trocas e Devoluções</span>
                  <span>Fale Conosco</span>
                </div>
                <p className="mt-2 opacity-70">© Sua Loja — CNPJ 00.000.000/0001-00</p>
              </div>
            </div>
            <p className="text-xs text-muted">
              As mudanças aparecem aqui na hora. Na loja, aplicam após salvar + revalidação.
            </p>
          </Card>
        </div>
      )}
    </AsyncBoundary>
  );
}
