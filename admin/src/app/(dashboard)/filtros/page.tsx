'use client';

import { useState } from 'react';
import { Button, Card } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { appearanceApi, type Theme } from '@/modules/appearance/api';
import { revalidateStore } from '@/lib/revalidate-store';

export default function FiltrosPage() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => appearanceApi.getTheme());
  const [draft, setDraft] = useState<Theme | null>(null);
  const [saving, setSaving] = useState(false);

  const theme = draft ?? data;
  const dirty = draft !== null;
  const set = <K extends keyof Theme>(k: K, v: Theme[K]) => {
    if (!theme) return;
    setDraft({ ...theme, [k]: v });
  };

  async function save() {
    if (!theme) return;
    setSaving(true);
    const res = await appearanceApi.putTheme({
      filter_size_enabled: theme.filter_size_enabled,
      filter_price_enabled: theme.filter_price_enabled,
      filter_category_enabled: theme.filter_category_enabled,
      filter_color_enabled: theme.filter_color_enabled,
      filter_material_enabled: theme.filter_material_enabled,
      filters_on_home: theme.filters_on_home,
    });
    setSaving(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    await revalidateStore('theme');
    setData(res.data);
    setDraft(null);
    toast.success('Filtros salvos e aplicados na loja.');
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Filtros"
        description="Quais filtros aparecem na coluna esquerda da página de categorias (e resumidos na home)."
      />
      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {theme && (
          <Card variant="outline" className="flex max-w-lg flex-col gap-4">
            <Checkbox
              label="Filtro de categorias"
              hint="Lista de subcategorias navegáveis."
              checked={theme.filter_category_enabled}
              onChange={(v) => set('filter_category_enabled', v)}
            />
            <Checkbox
              label="Filtro de preço"
              hint="Faixa mínima/máxima."
              checked={theme.filter_price_enabled}
              onChange={(v) => set('filter_price_enabled', v)}
            />
            <Checkbox
              label="Filtro de tamanho"
              hint="Marcações por numeração/tamanho disponível."
              checked={theme.filter_size_enabled}
              onChange={(v) => set('filter_size_enabled', v)}
            />
            <Checkbox
              label="Filtro de cor"
              hint="Cores dos produtos (nome da cor no cadastro)."
              checked={theme.filter_color_enabled}
              onChange={(v) => set('filter_color_enabled', v)}
            />
            <Checkbox
              label="Filtro de material"
              hint="Valores do eixo de variação chamado “Material”."
              checked={theme.filter_material_enabled}
              onChange={(v) => set('filter_material_enabled', v)}
            />
            <div className="border-t border-surface-border pt-4">
              <Checkbox
                label="Mostrar atalhos de filtro também na home"
                hint="Desligado: os filtros aparecem só nas telas de categoria."
                checked={theme.filters_on_home}
                onChange={(v) => set('filters_on_home', v)}
              />
            </div>
            <div className="flex items-center gap-3">
              <Button loading={saving} onClick={() => void save()}>
                Salvar
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
            </div>
          </Card>
        )}
      </AsyncBoundary>
    </div>
  );
}
