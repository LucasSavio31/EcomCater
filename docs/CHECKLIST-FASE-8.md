# Checklist de validação — Fase 8 (revisar antes de autorizar a Fase 9)

Legenda: ✅ feito · 🟡 parcial · ⬜ pendente · ⚠️ precisa de ambiente (Docker/Postgres) para validar

> **Importante:** todo o desenvolvimento foi feito em máquina sem Docker/Postgres.
> A verificação estática (compilação, import da app, configuração de mappers,
> geração do OpenAPI, build do frontend/admin) está ✅. A verificação **funcional
> com banco** (migrations aplicando, `make test`, e2e, fluxo real de compra)
> depende de você rodar `make up && make migrate && make seed && make test`.

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
- 🟡 Admin UI de produtos/categorias — agente em execução

## Vitrine (Fase 3)
- ✅ Endpoints públicos: `/api/theme`, `/api/menus/{location}`, `/api/banners`, `/api/theme/pages/{slug}`, catálogo, busca
- 🟡 Home, categoria/PLP, produto/PDP, busca instantânea, header (mega menu) / footer, SEO/JSON-LD, sitemap — agente em execução
- ✅ Tema SSR sem FOUC (CSS vars injetadas no `<head>`), fallback quando API fora
- ✅ PWA: manifest `standalone` + service worker de assets + ícones

## Carrinho e frete (Fases 4-5)
- ✅ Carrinho persistente convidado (cookie httpOnly + espelho Redis) / logado; snapshot de preço; validação de estoque; merge no login; `price_changed`
- ✅ Cupons (percent/fixed/free_shipping) com janela, mínimo, limites global/por usuário, resgate idempotente
- ✅ Frete Melhor Envio: cotação (`/api/v2/me/shipment/calculate`, Bearer token) com cache Redis + auditoria; módulo toggsteável; config no admin
- ✅ Webhook Melhor Envio → pedido POSTADO / EM TRÂNSITO / ENTREGUE
- ✅ Totais: itens − desconto + frete + threshold de frete grátis, consistentes
- 🟡 UI de carrinho, drawer, barra de frete grátis, campo de CEP/cupom — Fase 4 do frontend (depende da vitrine)

## Checkout e pagamento (Fases 6-7)
- ✅ Número de pedido `AAAA-000123` sob advisory lock; snapshot imutável de itens/endereço/frete/cupom
- ✅ Baixa de estoque na criação; restauração no cancelamento; carrinho esvaziado após criar o pedido
- ✅ Máquina de estados do pedido com transições válidas + `order_events` (linha do tempo)
- ✅ Pagamento Appmax (API v3): cliente → pedido → pagamento PIX / cartão / boleto; módulo toggleável; só token
- ✅ Webhook Appmax → PAGO / AGUARDANDO PAGAMENTO / CANCELADO; idempotente (`UNIQUE(provider, event_id)`) com validação de assinatura; reprocessar no admin
- ✅ Gateway `fake` para dev/testes sem credenciais
- ✅ Reembolso no admin
- ✅ E-mail transacional (SMTP config no banco, templates Jinja, `email_log`): pedido criado, pago, falhou, enviado, entregue
- 🟡 UI do smart checkout single-page + página de obrigado + step de pagamento (PIX/cartão/boleto) — Fase 6-7 do frontend

## Minha conta / conteúdo / admin (Fase 8)
- ✅ Endereços do cliente (CRUD + padrão), perfil, troca de senha
- ✅ Wishlist (backend)
- ✅ Menus (mega menu + atalhos de tamanho), banners, tema/aparência, páginas institucionais, newsletter — backend
- ✅ Dashboard admin (pedidos hoje/pendentes, faturamento do mês, estoque baixo, recentes)
- ✅ SMTP config + teste de envio; gestão de módulos; usuários admin com papéis
- 🟡 Minha conta (páginas), todas as telas de CRUD do admin — agente em execução

## Não funcionais (Fase 8) — pendentes de máquina com ambiente
- ⚠️ Lighthouse mobile ≥ 90 (Performance/SEO/Acessibilidade) em home/PLP/PDP/carrinho/checkout
- ⚠️ CWV mobile (LCP/CLS/INP) dentro da meta
- ⚠️ axe-core / a11y ≥ 95; navegação por teclado no mega menu / seletor de variação / drawer / checkout
- ⚠️ E2E Playwright dos fluxos críticos (compra convidado PIX, logado cartão, boleto, falha+retry, reembolso, merge de carrinho, ciclo admin→loja, primeiro login, toggle de módulo, tema sem rebuild)
- ✅ Rate limiting (login, registro, cupom, review, quote, charge, newsletter)
- ✅ Secrets só via env; `.env.example` completo (Appmax, Melhor Envio, SMTP, JWT, storage, DB, Redis)
- 🟡 Sanitização de HTML em `description` / `pages.body` (a fazer no hardening)
- 🟡 Cifragem em repouso dos segredos de provider em `modules.config_json` (TODO marcado; entra na Fase 9)
- ✅ `docker-compose.prod.yml` permanece esqueleto; nada de VPS no caminho de dev

## Portas de saída para a Fase 9 (só após seu OK)
Profile prod com apps em `127.0.0.1`, exemplo de vhost LiteSpeed/aaPanel, TLS Cloudflare
(Full strict + cert de origem), volumes persistentes, rotina de backup do Postgres,
cifragem dos segredos, SPF/DKIM do e-mail.
