'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { ImageUploader } from '@/components/image-uploader';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { appearanceApi, type SealColumn, type Theme } from '@/modules/appearance/api';
import { revalidateStore } from '@/lib/revalidate-store';

const COLUMNS: { key: SealColumn; label: string }[] = [
  { key: 'payment', label: 'Formas de Pagamento' },
  { key: 'shipping', label: 'Formas de Entrega' },
  { key: 'security', label: 'Loja Segura' },
];

export default function SelosRodapePage() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => appearanceApi.getTheme());
  const [draft, setDraft] = useState<Theme | null>(null);
  const [savingText, setSavingText] = useState(false);

  const theme = draft ?? data;
  const dirty = draft !== null;

  function setSeal(col: SealColumn, field: 'title' | 'text', value: string) {
    if (!theme) return;
    setDraft({
      ...theme,
      footer_seals_json: {
        ...theme.footer_seals_json,
        [col]: { ...theme.footer_seals_json[col], [field]: value },
      },
    });
  }

  async function saveTexts() {
    if (!theme) return;
    setSavingText(true);
    const res = await appearanceApi.putTheme({
      footer_seals_enabled: theme.footer_seals_enabled,
      footer_seals_json: theme.footer_seals_json,
    });
    setSavingText(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    await revalidateStore('theme');
    setData(res.data);
    setDraft(null);
    toast.success('Selos salvos e aplicados na loja.');
  }

  async function toggleEnabled(v: boolean) {
    if (!theme) return;
    const res = await appearanceApi.putTheme({ footer_seals_enabled: v });
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    await revalidateStore('theme');
    setData(res.data);
    setDraft(null);
  }

  async function upload(col: SealColumn, index: number, file: File) {
    const res = await appearanceApi.uploadSealImage(col, index, file);
    if (!res.ok) throw new Error(res.error.message);
    await revalidateStore('theme');
    setData(res.data);
    setDraft(null);
    toast.success('Selo enviado.');
  }

  async function remove(col: SealColumn, index: number) {
    const res = await appearanceApi.removeSealImage(col, index);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    await revalidateStore('theme');
    setData(res.data);
    setDraft(null);
    toast.success('Selo removido.');
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Selos do rodapé"
        description="Três blocos no rodapé da loja. Em cada bloco você envia até 3 imagens (selos de pagamento, transportadora, segurança…)."
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {theme && (
          <>
            <Card variant="outline">
              <Checkbox
                label="Exibir os selos no rodapé da loja"
                checked={theme.footer_seals_enabled}
                onChange={(v) => void toggleEnabled(v)}
              />
            </Card>

            <div className="grid gap-5 lg:grid-cols-3">
              {COLUMNS.map(({ key, label }) => {
                const col = theme.footer_seals_json[key];
                return (
                  <Card key={key} variant="outline" className="flex flex-col gap-4">
                    <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                      {label}
                    </span>
                    <Input
                      label="Título exibido"
                      value={col.title}
                      onChange={(e) => setSeal(key, 'title', e.target.value)}
                    />

                    <div className="flex flex-col gap-4">
                      {[0, 1, 2].map((i) => (
                        <ImageUploader
                          key={i}
                          label={`Selo ${i + 1}`}
                          aspect="wide"
                          currentUrl={col.image_urls[i] ?? null}
                          onSelect={(file) => upload(key, i, file)}
                          onRemove={col.image_urls[i] ? () => remove(key, i) : undefined}
                          hint={i === 0 ? 'PNG ou SVG com fundo transparente fica melhor.' : undefined}
                        />
                      ))}
                    </div>

                    {key === 'security' && (
                      <Input
                        label="Texto de segurança"
                        value={col.text}
                        onChange={(e) => setSeal(key, 'text', e.target.value)}
                      />
                    )}
                  </Card>
                );
              })}
            </div>

            <div className="flex items-center gap-3">
              <Button loading={savingText} onClick={() => void saveTexts()}>
                Salvar títulos e textos
              </Button>
              {dirty && (
                <button
                  type="button"
                  className="text-sm text-text-muted underline"
                  onClick={() => setDraft(null)}
                >
                  Descartar
                </button>
              )}
              <span className="text-xs text-text-muted">
                As imagens são aplicadas na hora do envio; os textos, ao salvar.
              </span>
            </div>
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
