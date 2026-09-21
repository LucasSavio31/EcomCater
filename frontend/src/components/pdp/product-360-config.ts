/**
 * Mínimo de fotos pra habilitar o giro 360° — poucas fotos deixam a
 * animação "pulada" demais e a experiência pior do que só a galeria normal.
 *
 * Fica num módulo SEM "use client" de propósito: `page.tsx` (Server
 * Component) precisa ler esse valor pra decidir se renderiza a seção; um
 * valor importado de um módulo "use client" chega como `undefined` do lado
 * do servidor (o cruzamento de fronteira RSC não resolve exports que não
 * são componentes), e `length >= undefined` é sempre `false` sem erro
 * nenhum — foi exatamente esse bug que fez a seção nunca aparecer.
 */
export const PRODUCT_360_MIN_IMAGES = 4;
