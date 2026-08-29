# Checklist de validação — Fase 8 (revisar antes de autorizar a Fase 9)

Legenda: ✅ feito · 🟡 parcial · ⬜ pendente · ⚠️ precisa de ambiente (Docker/Postgres) para validar

> **Importante:** todo o desenvolvimento foi feito em máquina sem Docker/Postgres.
> A verificação estática está ✅: `tsc --noEmit` + `next lint` + `next build`
> limpos nos 3 workspaces (`frontend`, `admin`, `@ecom/ui`); no backend,
> `compileall` + import da app + `configure_mappers()` + geração do OpenAPI
> (98 rotas, 37 tabelas) + `pytest --collect-only`. A verificação **funcional
> com banco** (migrations aplicando, `make test`, e2e, fluxo real de compra)
> depende de você rodar `make up && make migrate && make seed && make test`.
>
> Frente de trabalho concluída nesta rodada: editor de aparência estilo
> Customizer (cores de botão/header/footer + largura do header + DnD no menu) e
> todo o frontend de carrinho/checkout/conta (Fases 4-6), antes distribuídos a
> um agente que não chegou a produzir — foram feitos direto no `main`.

## Infra / fundação
- ✅ Monorepo (npm workspaces), Docker Compose dev + prod (esqueleto), sem proxy no Docker
- ✅ `db`/`redis` sem porta publicada; prod expõe apps só em `127.0.0.1`
- ✅ API modular com auto-discovery; 13 módulos; `require_module_enabled` para toggláveis
- ✅ Migration `0001` baseline (37 tabelas) a partir de `Base.metadata`
- ✅ Seed idempotente (admin via env + troca de senha obrigatória, tema neutro, menus, módulos, páginas, banners)
- ✅ Auth JWT cliente + admin (scopes separados, argon2, refresh rotacionado/revogável)
- ✅ CI (GitHub Actions: ruff/mypy, alembic upgrade, pytest, build dos 3 apps)
- ⚠️ `make up` sobe os 5 serviços · `make migrate` · `make seed` — validar localmente

## Catálogo (Fase 2)
- ✅ Categorias: árvore, slug único por pai, `path` materializado + repath recursivo, reorder, imagem WebP
- ✅ Produtos: CRUD, status draft/active/archived, variações/SKU com eixos (is_size), estoque, imagens (3 tamanhos WebP), specs, relacionados, reviews com moderação + rating agregado
- ✅ Listagem por categoria (com descendentes) + filtros (preço/tamanho/estoque) + ordenação + facetas
- ✅ Busca fuzzy `pg_trgm` (produtos + categorias) com payload de typeahead
- ✅ Seed de catálogo (`make seed-catalog`): árvore + 24 produtos com variações e imagens geradas
- ✅ Admin UI de produtos/categorias (CRUDs completos, build verde)

## Vitrine (Fase 3)
- ✅ Endpoints públicos: `/api/theme`, `/api/menus/{location}`, `/api/banners`, `/api/theme/pages/{slug}`, catálogo, busca
- ✅ Home, categoria/PLP, produto/PDP, busca instantânea, header (mega menu) / footer, SEO/JSON-LD, sitemap
- ✅ Tema SSR sem FOUC (CSS vars injetadas no `<head>`), fallback quando API fora
- ✅ PWA: manifest `standalone` + service worker de assets + ícones

## Editor de aparência estilo Customizer (WooCommerce/WordPress)
- ✅ Admin/Aparência: cores de botão (fundo/texto/hover), fundo+texto do menu superior, fundo+texto do rodapé, largura do menu superior em px (slider + campo)
- ✅ Pré-visualização ao vivo (top bar + header com largura aplicada + botão com hover real + rodapé)
- ✅ Menu com arrastar-e-soltar (soltar sobre = subitem; metade de cima = irmão antes; trava subárvore; setas ↑↓ mantidas p/ teclado)
- ✅ Backend: 8 colunas novas em `theme_settings` + migration `0002` + validação de hex e clamp de largura (640–2560)
- ✅ Loja consome as variáveis: `--color-btn-*`, `--color-header-*`, `--color-footer-*`, `--header-max-width` (fallback = paleta neutra); header/footer/`Button` aplicam

## Carrinho e frete (Fases 4-5)
- ✅ Carrinho persistente convidado (cookie httpOnly + espelho Redis) / logado; snapshot de preço; validação de estoque; merge no login; `price_changed`
- ✅ Cupons (percent/fixed/free_shipping) com janela, mínimo, limites global/por usuário, resgate idempotente
- ✅ Frete Melhor Envio: cotação (`/api/v2/me/shipment/calculate`, Bearer token) com cache Redis + auditoria; módulo toggsteável; config no admin
- ✅ Webhook Melhor Envio → pedido POSTADO / EM TRÂNSITO / ENTREGUE
- ✅ Totais: itens − desconto + frete + threshold de frete grátis, consistentes
- ✅ UI de carrinho (`/carrinho`): itens com stepper/remover, campo de cupom, CEP + opções de frete (Melhor Envio), resumo de valores, avisos de estoque/preço; badge do header e barra de frete grátis lendo o carrinho real
- ✅ PDP adiciona a variante real ao carrinho (`POST /api/cart/items`) com link "ir para o carrinho"

## Checkout e pagamento (Fases 6-7)
- ✅ Número de pedido `AAAA-000123` sob advisory lock; snapshot imutável de itens/endereço/frete/cupom
- ✅ Baixa de estoque na criação; restauração no cancelamento; carrinho esvaziado após criar o pedido
- ✅ Máquina de estados do pedido com transições válidas + `order_events` (linha do tempo)
- ✅ Pagamento Appmax (API v3): cliente → pedido → pagamento PIX / cartão / boleto; módulo toggleável; só token
- ✅ Webhook Appmax → PAGO / AGUARDANDO PAGAMENTO / CANCELADO; idempotente (`UNIQUE(provider, event_id)`) com validação de assinatura; reprocessar no admin
- ✅ Gateway `fake` para dev/testes sem credenciais
- ✅ Reembolso no admin
- ✅ E-mail transacional (SMTP config no banco, templates Jinja, `email_log`): pedido criado, pago, falhou, enviado, entregue
- ✅ UI do smart checkout single-page (`/checkout`): contato, endereço com autofill de CEP (ViaCEP), frete (Melhor Envio), pagamento PIX/cartão/boleto filtrado por `/api/payment/methods`, parcelas; cria pedido + charge
- ✅ Página de obrigado (`/checkout/obrigado`): status do pedido/pagamento, PIX copia-e-cola / boleto, resumo e endereço, polling do pagamento (~2 min) com atualização automática

## Minha conta / conteúdo / admin (Fase 8)
- ✅ Endereços do cliente (CRUD + padrão), perfil, troca de senha
- ✅ Wishlist (backend)
- ✅ Menus (mega menu + atalhos de tamanho), banners, tema/aparência, páginas institucionais, newsletter — backend
- ✅ Dashboard admin (pedidos hoje/pendentes, faturamento do mês, estoque baixo, recentes)
- ✅ SMTP config + teste de envio; gestão de módulos; usuários admin com papéis
- ✅ Minha conta (`/minha-conta`): login/cadastro em aba única (funde carrinho de convidado ao entrar), painel com dados editáveis, `/minha-conta/pedidos` (status pagamento/envio + timeline), `/minha-conta/enderecos` (CRUD + autofill CEP); `authFetch` com refresh single-flight no 401
- ✅ Telas de CRUD do admin (produtos, categorias, pedidos, promoções, menus, aparência, módulos, SMTP, usuários) — build verde

## Não funcionais (Fase 8) — pendentes de máquina com ambiente
- ⚠️ Lighthouse mobile ≥ 90 (Performance/SEO/Acessibilidade) em home/PLP/PDP/carrinho/checkout
- ⚠️ CWV mobile (LCP/CLS/INP) dentro da meta
- ⚠️ axe-core / a11y ≥ 95; navegação por teclado no mega menu / seletor de variação / drawer / checkout
- ⚠️ E2E Playwright dos fluxos críticos (compra convidado PIX, logado cartão, boleto, falha+retry, reembolso, merge de carrinho, ciclo admin→loja, primeiro login, toggle de módulo, tema sem rebuild)
- ✅ Rate limiting (login, registro, cupom, review, quote, charge, newsletter)
- ✅ Secrets só via env; `.env.example` completo (Appmax, Melhor Envio, SMTP, JWT, storage, DB, Redis)
- ✅ Sanitização de HTML (`nh3`) em `description` de produto / `pages.body`
- 🟡 Cifragem em repouso dos segredos de provider em `modules.config_json` (TODO marcado; entra na Fase 9)
- ✅ `docker-compose.prod.yml` permanece esqueleto; nada de VPS no caminho de dev

## Portas de saída para a Fase 9 (só após seu OK)
Profile prod com apps em `127.0.0.1`, exemplo de vhost LiteSpeed/aaPanel, TLS Cloudflare
(Full strict + cert de origem), volumes persistentes, rotina de backup do Postgres,
cifragem dos segredos, SPF/DKIM do e-mail.
