'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import type { ColorSibling } from '@/modules/catalog/types';
import { resolveMediaUrl } from '@/lib/media';

interface Props {
  currentColorName: string | null;
  siblings: ColorSibling[];
}

/**
 * Variação de COR = produtos irmãos (mesmo modelo, outra cor).
 * Miniatura = imagem principal de cada produto; clicar navega para ele.
 * Recolhe acima de 8 cores no desktop / 6 no mobile: mostra `limite-1` + um
 * card "ver mais cores" (prévia ofuscada da próxima). Ao clicar, carrega o
 * resto das miniaturas.
 */
export function ColorSiblings({ currentColorName, siblings }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);

  // chave estável do grupo de cor (igual em qualquer produto irmão)
  const groupKey =
    siblings && siblings.length > 1
      ? 'cs-exp:' + siblings.map((s) => s.id).slice().sort().join('|')
      : '';

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)');
    const sync = () => setIsDesktop(mq.matches);
    sync();
    mq.addEventListener('change', sync);
    return () => mq.removeEventListener('change', sync);
  }, []);

  // uma vez que o cliente abriu "ver mais cores" nesta sessão, não recolhe mais
  // (vale ao navegar entre as cores do mesmo modelo). Zera só em nova sessão.
  useEffect(() => {
    if (!groupKey) return;
    try {
      if (sessionStorage.getItem(groupKey)) setExpanded(true);
    } catch {
      /* sessionStorage indisponível */
    }
  }, [groupKey]);

  const openAll = () => {
    setExpanded(true);
    try {
      sessionStorage.setItem(groupKey, '1');
    } catch {
      /* ok */
    }
  };

  if (!siblings || siblings.length < 2) return null;
  const LIMIT = isDesktop ? 8 : 6;
  const current = siblings.find((s) => s.is_current);
  const label = current?.color_name || currentColorName;

  const swatchCls = (isCurrent: boolean) =>
    `relative block h-[70px] w-[103px] overflow-hidden rounded-card border-2 bg-white ${
      isCurrent ? 'border-var-border' : 'border-surface-border hover:border-var-border'
    }`;

  const swatch = (s: ColorSibling) => {
    const src = resolveMediaUrl(s.image_url ?? undefined);
    const inner = src ? (
      <Image src={src} alt={s.color_name} fill sizes="103px" className="object-contain" />
    ) : (
      <span className="flex h-full items-center justify-center px-1 text-xs">{s.color_name}</span>
    );
    return s.is_current ? (
      <span className={swatchCls(true)} aria-current="true" title={s.color_name}>
        {inner}
      </span>
    ) : (
      <Link href={`/produto/${s.slug}`} className={swatchCls(false)} title={s.color_name}>
        {inner}
      </Link>
    );
  };

  const collapsed = !expanded && siblings.length > LIMIT;
  const visible = collapsed ? siblings.slice(0, LIMIT - 1) : siblings;
  const teaser = collapsed ? siblings[LIMIT - 1] : null;
  const hiddenCount = siblings.length - (LIMIT - 1);

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-semibold uppercase tracking-wide">
        Cor
        {label && <span className="font-normal normal-case text-text-muted">: {label}</span>}
      </span>
      <ul className="flex flex-wrap gap-2">
        {visible.map((s) => (
          <li key={s.id}>{swatch(s)}</li>
        ))}
        {teaser && (
          <li>
            <button
              type="button"
              onClick={openAll}
              title="Ver mais cores"
              className="relative block h-[70px] w-[103px] overflow-hidden rounded-card border-2 border-surface-border bg-white hover:border-var-border"
            >
              {resolveMediaUrl(teaser.image_url ?? undefined) && (
                <Image
                  src={resolveMediaUrl(teaser.image_url ?? undefined) as string}
                  alt=""
                  fill
                  sizes="103px"
                  className="object-contain opacity-30"
                />
              )}
              <span className="absolute inset-0 flex flex-col items-center justify-center gap-0.5 bg-white/55 text-center">
                <span className="text-[11px] font-bold leading-none">+{hiddenCount}</span>
                <span className="text-[10px] font-semibold leading-tight text-text-muted">
                  ver mais cores
                </span>
              </span>
            </button>
          </li>
        )}
      </ul>
    </div>
  );
}
