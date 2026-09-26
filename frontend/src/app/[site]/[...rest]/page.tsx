import { notFound } from 'next/navigation';

// URL inexistente dentro de um domínio -> 404 da loja (com cabeçalho/rodapé
// do layout [site]). Sem isto, o Next cairia no 404 padrão, sem layout.
export default function CatchAllNotFound(): never {
  notFound();
}
