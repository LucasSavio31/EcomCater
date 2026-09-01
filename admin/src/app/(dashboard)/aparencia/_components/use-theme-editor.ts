'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { appearanceApi, type Theme, type ThemeImageKind } from '@/modules/appearance/api';
import { revalidateStore } from '@/lib/revalidate-store';

/**
 * Editor compartilhado do tema. Cada sub-aba da Aparência usa esta hook: carrega
 * uma cópia do tema, edita só a sua fatia e salva o objeto inteiro (os campos das
 * outras abas passam sem alteração).
 */
export function useThemeEditor() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => appearanceApi.getTheme());
  const [draft, setDraft] = useState<Theme | null>(null);
  const [saving, setSaving] = useState(false);

  const theme = draft ?? data;
  const dirty = draft !== null;

  // Espelho do estado atual: o ColorField propaga com debounce, então o clique
  // em "Salvar" pode chegar 1 render antes de `theme` atualizar. O ref é lido
  // no `save()` para nunca enviar um valor defasado.
  const themeRef = useRef<Theme | null>(theme);
  useEffect(() => {
    themeRef.current = theme;
  }, [theme]);

  // Identidade estável: os campos memoizados (ColorField) dependem disso para
  // não re-renderar a cada tecla/arrasto de outro campo.
  const set = useCallback(
    <K extends keyof Theme>(k: K, v: Theme[K]): void => {
      setDraft((prev) => {
        const base = prev ?? data;
        return base ? { ...base, [k]: v } : prev;
      });
    },
    [data],
  );

  async function save(): Promise<boolean> {
    const current = themeRef.current ?? theme;
    if (!current) return false;
    setSaving(true);
    const result = await appearanceApi.putTheme(current);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return false;
    }
    await revalidateStore('theme');
    setData(result.data);
    setDraft(null);
    toast.success('Aparência salva e aplicada na loja.');
    return true;
  }

  async function upload(kind: ThemeImageKind, file: File): Promise<void> {
    const result = await appearanceApi.uploadThemeImage(kind, file);
    if (!result.ok) throw new Error(result.error.message);
    await revalidateStore('theme');
    setData(result.data);
    setDraft(null);
    toast.success('Imagem atualizada.');
  }

  async function removeImage(kind: ThemeImageKind): Promise<void> {
    const result = await appearanceApi.removeThemeImage(kind);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    await revalidateStore('theme');
    setData(result.data);
    setDraft(null);
    toast.success('Imagem removida.');
  }

  const discard = (): void => setDraft(null);

  return { theme, dirty, saving, loading, error, reload, set, save, discard, upload, removeImage };
}
