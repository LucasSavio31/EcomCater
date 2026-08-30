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
 * "COR: <nome>" como no modelo da referência.
 */
export function ColorSiblings({ currentColorName, siblings }: Props) {
  if (!siblings || siblings.length < 2) return null;
  const current = siblings.find((s) => s.is_current);
  const label = current?.color_name || currentColorName;

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-semibold uppercase tracking-wide">
        Cor
        {label && <span className="font-normal normal-case text-text-muted">: {label}</span>}
      </span>
      <ul className="flex flex-wrap gap-2">
        {siblings.map((s) => {
          const src = resolveMediaUrl(s.image_url ?? undefined);
          const inner = src ? (
            <Image src={src} alt={s.color_name} fill sizes="103px" className="object-contain" />
          ) : (
            <span className="flex h-full items-center justify-center px-1 text-xs">{s.color_name}</span>
          );
          const cls = `relative block h-[70px] w-[103px] overflow-hidden rounded-card border-2 bg-white ${
            s.is_current ? 'border-var-border' : 'border-surface-border hover:border-var-border'
          }`;
          return (
            <li key={s.id}>
              {s.is_current ? (
                <span className={cls} aria-current="true" title={s.color_name}>
                  {inner}
                </span>
              ) : (
                <Link href={`/produto/${s.slug}`} className={cls} title={s.color_name}>
                  {inner}
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
