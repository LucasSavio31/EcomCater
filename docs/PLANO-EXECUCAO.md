# Plano de execução — Fases 1 a 8

> Gerado pelo agente de planejamento a partir de `PROPOSTA-FASE-0.md`.
> A Fase 9 (produção/VPS) está **fora de escopo e travada** até aprovação da Fase 8.
> IDs de tarefa: `F<fase>.<n>`. "Serial" = arquivo compartilhado / dono único. "Paralelo" = isolado por convenção de módulo.

## Visão geral do build order

```
F1 Fundação ─┬─> F2 Catálogo (back+admin) ─┬─> F3 Vitrine (loja) ──> F4 Carrinho ──┐
             │                              │                                       ├─> F6 Checkout+Pedidos ──> F7 Pagamento+E-mails ──> F8 Conta/Conteúdo/QA
             └──────────────────────────────┴─> F5 Frete + Promoções ───────────────┘
```

- **F2 e F5** podem começar assim que F1 fecha (F5 só precisa de `cart` da F4 para a integração de totais).
- **F3** depende de F2. **F4** depende de F3 + `cart` backend. **F6** depende de F4 + F5. **F7** depende de F6. **F8** depende de tudo (passes transversais + E2E).

### Espinha serial (dono único, sensível a merge)

| Arquivo / área | Fases | Regra |
|---|---|---|
| `api/app/core/*` | F1 | Congelar ao fim da F1 |
| `api/alembic/versions/` | F1–F8 | Baseline 0001 na F1 + deltas aditivos com 1 integrador |
| `api/app/modules/cart/service.py` | F4, F5, F6 | Dono único (F5.8, F6.7 são edições agendadas) |
| `api/app/modules/orders/service.py` | F6, F7 | Dono único (F7.9 agendada) |
| `frontend/src/app/layout.tsx` | F3, F4 | Header/footer/tema/mini-cart em sequência |
| `frontend/src/lib/api-client.ts`, `seo.ts` | F3, F8 | Criar 1x; uso por rota é paralelo |
| `packages/ui/**` | F1, F2, F8 | PRs serializados |
| `api/app/main.py` | F1 | Auto-discovery de módulos → módulos novos NÃO editam main.py |

### Grupos paralelizáveis

- Cada `api/app/modules/<x>/` exceto `cart` e `orders`: `products`, `categories`, `shipping`, `promotions`, `payment`, `banners`, `menus`, `theme`, `newsletter`, `pages`, `wishlist`.
- Cada `frontend/src/modules/<x>/`, `admin/src/modules/<x>/`, cada pasta de rota (`layout.tsx` é exceção), testes por módulo.

### Tracks sugeridos

- **A — Core/Infra:** F1 espinha, migrations, CI, Docker.
- **B — Catálogo:** `products`/`categories` back+admin (F2), `catalog` loja (F3).
- **C — Storefront:** layout, tema SSR, home/PLP/PDP/busca, SEO, PWA (F3, F8).
- **D — Comércio:** `cart`, `orders`, checkout (F4, F6).
- **E — Integrações:** `shipping`+Melhor Envio, `promotions`, `payment`+Appmax, SMTP (F5, F7).

---

## FASE 1 — Fundação

| ID | Tarefa | Arquivos | Depende |
|---|---|---|---|
| F1.1 | Skeleton monorepo | README, Makefile, .env.example, docker-compose*, infra/postgres/initdb | — |
| F1.2 | Scaffold API | api/pyproject.toml, Dockerfile, app/main.py, core/config.py | F1.1 |
| F1.3 | Núcleo DB | core/database.py, alembic.ini, alembic/env.py (async), shared/models_base.py | F1.2 |
| F1.4 | Redis + infra | core/redis.py, ratelimit.py, errors.py, pagination.py, events.py | F1.2 |
| F1.5 | Segurança | core/security.py (argon2, JWT), core/deps.py | F1.3, F1.4 |
| F1.6 | Registry módulos | core/module_registry.py, model `modules`, require_module_enabled | F1.3 |
| F1.7 | Serviços shared | shared/slugify.py, images.py (WebP+3 tamanhos), storage.py (disco local) | F1.2 |
| F1.8 | Schema baseline + 0001 | modules/*/models.py (todas as tabelas), alembic/versions/0001_initial.py | F1.3, F1.6, F1.7 |
| F1.9 | Módulo admin (auth) | modules/admin/{module,schemas,service,router_admin}.py | F1.5, F1.8 |
| F1.10 | Módulo customers (auth) | modules/customers/{module,schemas,service,router_public}.py | F1.5, F1.8 |
| F1.11 | Seed inicial | seed/initial.py — admin via env, theme neutro, menus, linhas de modules | F1.8 |
| F1.12 | Harness de testes | tests/conftest.py + smoke de auth | F1.9, F1.10 |
| F1.13 | Scaffold packages/ui | package.json, tailwind-preset.js, tokens/, components/ (Button, Input, Drawer, Accordion, Card, Modal) | F1.1 |
| F1.14 | Scaffold frontend | next.config.mjs, tailwind.config.ts, app/layout.tsx, lib/api-client.ts, public/manifest.json | F1.13 |
| F1.15 | Scaffold admin | next.config.mjs (basePath /administracao), app/layout.tsx, login/page.tsx, lib/admin-api-client.ts | F1.13, F1.9 |
| F1.16 | Wiring Docker dev | 5 serviços, volume mídia, hot reload, portas 3000/3001/8000, Makefile | F1.2, F1.14, F1.15 |
| F1.17 | CI | .github/workflows/ci.yml — ruff/mypy, eslint/tsc, pytest, build | F1.12, F1.14 |
| F1.18 | Docs base | docs/ARQUITETURA.md, docs/MODULOS.md | — |

**Serial:** F1.1→F1.2→F1.3→F1.5→F1.8→(F1.9,F1.10)→F1.12. **Paralelo após F1.2:** F1.4, F1.7. **Track front:** F1.13→F1.14; F1.15 (após F1.9). **Fecho:** F1.16→F1.17.

**Riscos:** migração baseline vs incremental (→ baseline agora); transporte de JWT (cookie httpOnly vs header — cross-port dev exige decidir CORS/SameSite já); pipeline de imagem síncrono (`BackgroundTasks`) vs worker; event bus in-process sem durabilidade (aceitável 1–8); tooling JS (pnpm vs npm workspaces); parâmetros argon2 dev/prod; extensões PG exigem superuser no init; **auto-discovery de módulos** para não editar main.py.

**Pronto quando:** `make up` sobe 5 serviços; `make migrate` aplica 0001; `make seed` cria admin; login admin retorna tokens + fluxo troca-senha; register/login cliente retorna JWT; `GET /api/theme` devolve tema neutro; `GET /api/admin/modules` lista módulos; loja em :3000 com CSS vars SSR; admin em :3001/administracao; util de imagem gera WebP+3 tamanhos; CI verde.

---

## FASE 2 — Catálogo (backend + admin)

| ID | Tarefa | Arquivos | Depende |
|---|---|---|---|
| F2.1 | categories service | modules/categories/{service,repository,schemas,events}.py — árvore, path, slug único por pai, reorder | F1.8 |
| F2.2 | categories routers | router_public (árvore, por path/slug), router_admin (CRUD, reorder, upload imagem) | F2.1, F1.7, F1.9 |
| F2.3 | products service | modules/products/{service,repository,schemas}.py — CRUD, draft/active/archived, preço, publish | F1.8 |
| F2.4 | Variações | products/service_variants.py — option types/values, variants, estoque, matriz | F2.3 |
| F2.5 | Imagens de produto | products/service.py + shared/images.py → product_images; primária/reorder; imagem por variante | F2.3, F1.7 |
| F2.6 | Specs/relacionados/reviews | specs CRUD; product_related N:N; moderação review + rating_avg/count | F2.3 |
| F2.7 | products routers | router_public (detalhe por slug, lista por categoria + filtros + paginação, featured), router_admin (CRUD completo) | F2.3–F2.6 |
| F2.8 | Busca | GET /api/catalog/search?q= — pg_trgm similarity ranqueado, payload typeahead | F2.1, F2.3 |
| F2.9 | Seed/factories catálogo | árvore + produtos com variantes e imagens | F2.7 |
| F2.10 | Testes backend | tests/modules/{categories,products}/ | F2.7, F2.8 |
| F2.11 | Client admin catalog | admin/src/modules/catalog/{api,types,components,hooks} | F2.7 |
| F2.12 | Admin categorias | admin/src/app/categorias/* — editor de árvore, form, imagem, reorder | F2.11, F2.2 |
| F2.13 | Admin produtos | admin/src/app/produtos/* — lista+filtros, form, matriz de variantes, imagens, specs, SEO, reviews | F2.11, F2.7 |
| F2.14 | Componentes admin em ui | RichText, ImageUploader, DataTable | F1.13 |

**Paralelo:** track categories (F2.1→F2.2) e track products (F2.3→...→F2.7) independentes. **Serial:** F2.14 (packages/ui); F2.11 pré-requisito dos dois telões. **Paralelo admin:** F2.12 e F2.13.

**Riscos:** variações dentro de products (arquivos separados); manutenção recursiva de `categories.path`; busca só pg_trgm vs tsvector (acento/stemming), threshold; facetas da PLP (query a cada request vs contadores materializados); import CSV fora de escopo; estoque só na variante (oversell adiado p/ orders); sanitização de HTML da description.

**Pronto quando:** admin cria árvore + produto com 2 eixos e N variantes, sobe imagens (WebP+tamanhos no volume), specs, modera review; `GET /api/catalog/products?category=` lista paginada/filtrada; `GET /api/catalog/products/{slug}` payload PDP completo; `search?q=` fuzzy ranqueado; testes verdes; seed navegável.

---

## FASE 3 — Vitrine da loja (frontend público)

| ID | Tarefa | Arquivos | Depende |
|---|---|---|---|
| F3.0 | Endpoints públicos menus/banners/theme/pages | modules/{menus,banners,theme,pages}/{service,router_public}.py | F1.8 |
| F3.1 | Camada de dados SSR | frontend/src/lib/api-client.ts — server/client, erros, tags de revalidação | F1.14, F2.7 |
| F3.2 | Tema SSR | modules/theme/, CSS vars no layout.tsx, cache tag `theme`, sem FOUC | F3.1, F1.11, F3.0 |
| F3.3 | Header | modules/menus/, header no layout — mega menu, atalhos de tamanho, highlight, top bar, busca, placeholder mini-cart | F3.1, F3.0 |
| F3.4 | Footer | footer no layout — links institucionais (pages), social, bandeiras, form newsletter | F3.1, F3.0 |
| F3.5 | Home | app/page.tsx, modules/banners/ — hero/showcase, destaques, categorias | F3.1, F3.0 |
| F3.6 | Categoria/PLP | app/categoria/[...slug]/page.tsx — lista SSR, paginação, sort, filtros/facetas, breadcrumb | F3.6a, F2.7/F2.8 |
| F3.7 | PDP | app/produto/[slug]/page.tsx — galeria+zoom, seletor de variante, preço/parcelas/pix, specs accordion, relacionados, reviews, add-to-cart (fio na F4) | F3.6a, F2.7 |
| F3.8 | Busca instantânea | dropdown typeahead + app/busca/page.tsx | F3.6a, F2.8 |
| F3.9 | SEO base | lib/seo.ts — metadata dinâmica + JSON-LD (Product, BreadcrumbList, Organization, WebSite+SearchAction), canonical, OG | F3.5–F3.7 |
| F3.10 | sitemap/robots | app/sitemap.ts, app/robots.ts | F3.10a |
| F3.11 | next/image + responsivas | next.config.mjs (loader storage local), mapeamento thumb/medium/zoom | F1.7, F3.7 |
| F3.12 | loading/skeleton/erro + 404/500 | app/**/{loading,error}.tsx, not-found.tsx | F3.5–F3.8 |
| F3.13 | Testes componente + smoke Playwright | render home/PLP/PDP | F3.5–F3.8 |

**Serial (layout.tsx):** F3.2→F3.3→F3.4. **Serial (criar 1x):** F3.1, F3.6a, F3.9. **Paralelo:** rotas F3.5/F3.6/F3.7/F3.8.

**Riscos:** SSR do tema sem rebuild — fetch por request vs cache + revalidação por tag disparada pelo admin (precisa canal admin→frontend com secret, ou TTL curto); FOUC (inline CSS vars no head); next/image com disco (loader, servir via API ou mount); ISR vs SSR vs PPR + janela stale; performance de facetas; SEO de paginação/facetas (canonical/rel-next-prev); rate limit no POST público de review.

**Pronto quando:** anônimo navega home→categoria→produto via SSR com cores do DB (muda no DB + revalida → reflete sem rebuild); mega menu/atalhos/top bar do DB; busca instantânea + /busca; sitemap.xml e robots.txt; JSON-LD valida no Rich Results; baseline Lighthouse mobile capturada.

---

## FASE 4 — Carrinho

| ID | Tarefa | Arquivos | Depende |
|---|---|---|---|
| F4.1 | cart service | modules/cart/{service,repository,schemas,events}.py — get/create (convidado via session_token, logado via id), add/update/remove com snapshot unit_price_cents, recálculo, expiração | F1.8, F2.3, F1.10 |
| F4.2 | Espelho Redis | cart/service.py + core/redis.py — token em Redis, TTL, cookie | F4.1 |
| F4.3 | cart router_public | GET/POST/PATCH/DELETE /api/cart, POST /api/cart/items — cookie | F4.1, F4.2 |
| F4.4 | Validação de estoque | cart/service.py — stock_qty, limite, esgotado | F4.1 |
| F4.5 | Merge convidado→usuário no login | subscriber do evento de login | F4.1, F1.10 |
| F4.6 | Testes backend | convidado, merge, snapshot, estoque, expiração | F4.3–F4.5 |
| F4.7 | Módulo cart frontend | modules/cart/{api,types}, useCart (otimista), cookie no api-client | F4.3, F3.1 |
| F4.8 | Drawer/mini-cart | modules/cart/components/CartDrawer, badge no header | F4.7, F1.13 |
| F4.9 | Barra de frete grátis | FreeShippingBar (free_shipping_threshold_cents) | F4.7, F3.2 |
| F4.10 | Página do carrinho | app/carrinho/page.tsx — itens, qty, remover, totais, CTA, cupom (stub), CEP (stub) | F4.7 |
| F4.11 | Fio add-to-cart PDP/PLP | modules/catalog + cart | F4.7, F3.7 |
| F4.12 | E2E | add convidado → refresh persiste → login faz merge | F4.8, F4.10, F4.11 |

**Paralelo:** todo backend cart. **Serial:** F4.8 toca layout.tsx.

**Riscos:** estratégia de sessão de carrinho convidado (cookie name, token assinado vs opaco, httpOnly, SameSite cross-port, TTL, Redis vs DB, regras de merge); preço defasado (re-precificar no checkout, banner "preço alterado"); abas concorrentes (versão/etag); limpeza de abandonado (sem scheduler); cupom/CEP stub vs esconder por flag.

**Pronto quando:** convidado adiciona itens, persiste entre reloads (cookie+Redis), totais com snapshot; login faz merge; drawer+badge+barra ao vivo; página funcional exceto cupom/frete; E2E verde.

---

## FASE 5 — Frete + Promoções

| ID | Tarefa | Arquivos | Depende |
|---|---|---|---|
| F5.1 | Base providers de frete | shipping/providers/base.py — ShippingProvider.quote(origin,dest,packages)->list[ShippingRate] | F1.6 |
| F5.2 | Provider Melhor Envio | shipping/providers/melhor_envio.py — auth, cálculo, mapeamento, timeouts/erros | F5.1 |
| F5.3 | shipping service | {service,schemas,config}.py — monta pacotes dos itens, cache Redis por hash, fallback, persiste shipping_quotes | F5.1, F5.2, F4.1 |
| F5.4 | shipping routers | router_public POST /api/shipping/quote; router_admin config + "testar cotação"; require_module_enabled | F5.3, F1.9 |
| F5.5 | Registro módulo + config | shipping/module.py (toggleable, config_model), config em modules.config_json, segredo cifrado | F1.6, F5.3 |
| F5.6 | promotions service | {service,schemas}.py — validar/aplicar cupom (percent/fixed/free_shipping), min order, max desconto, limites, janela, redemption | F1.8, F4.1 |
| F5.7 | promotions routers | router_public POST /api/cart/coupon; router_admin CRUD + estatística | F5.6, F1.9 |
| F5.8 | **Integração no carrinho** | cart/service.py — totais consideram cupom + frete; grava coupon_id, selected_shipping_json, shipping_zip | F5.3, F5.6 |
| F5.9 | Testes backend | cache de quote, montagem de pacote, edge cases de cupom, free_shipping vs custo, stacking | F5.4, F5.7, F5.8 |
| F5.10 | Módulo shipping frontend | modules/shipping/{api,types}, useShippingQuote, input CEP com máscara | F5.4, F3.1 |
| F5.11 | Módulo promotions frontend | modules/promotions/, useCoupon | F5.7, F3.1 |
| F5.12 | Fio no carrinho + simulador PDP | caixa CEP/quote na PDP e carrinho; cupom ativo no carrinho | F5.10, F5.11, F4.10 |
| F5.13 | Telas admin | admin/src/app/promocoes/* (CRUD cupom), admin/src/app/modulos/* (config frete + teste) | F5.4, F5.7 |
| F5.14 | E2E | cotar CEP, aplicar cupom, totais corretos, free_shipping zera frete | F5.12 |

**Paralelo:** backends shipping e promotions. **Serial:** F5.8 (cart/service.py, um dono). **Serial:** F5.12 (carrinho + PDP).

**Riscos:** Melhor Envio (OAuth2 client-credentials vs token pessoal, URL sandbox, rate limits, payload de /me/shipment/calculate, serviços a expor, prazo, CEP inválido); **webhook Melhor Envio fora de escopo 1–8** (só cotação; fulfillment/tracking depois); algoritmo de caixa (soma vs bin-packing, dims default); chave/TTL do cache; stacking (um cupom por carrinho); arredondamento de desconto percentual → distribuição por item; limite por usuário para convidado (e-mail? CPF?); cifrar segredo de provider em repouso.

**Pronto quando:** quote retorna tarifas reais (sandbox), cacheadas + auditadas; módulo off → 404; cupons de todos os tipos aplicam com limites; total = itens − desconto + frete consistente API↔UI; admin gerencia cupons + config frete; E2E verde.

---

## FASE 6 — Checkout e Pedidos

| ID | Tarefa | Arquivos | Depende |
|---|---|---|---|
| F6.1 | Número de pedido | orders/service.py — sequência por ano AAAA-000123, seguro sob concorrência | F1.8 |
| F6.2 | orders service — criar do carrinho | snapshot itens/endereços/frete/cupom, totais, pending_payment, baixa/reserva estoque, order_events, emite order.created | F6.1, F4.1, F5.3, F5.6 |
| F6.3 | Máquina de estados | orders/{service,events}.py — transições status/payment_status/fulfillment_status + guardas + log | F6.2 |
| F6.4 | orders router_public | POST /api/checkout/orders, GET /api/checkout/orders/{number}, lookup convidado por número+e-mail | F6.2 |
| F6.5 | orders router_admin | listar/filtrar/buscar, detalhe, timeline, status manual, nota, hooks cancelar/reembolsar | F6.2, F1.9 |
| F6.6 | Endereços do cliente | customers/{service,router_public}.py — CRUD customer_addresses, default | F1.10 |
| F6.7 | Estado/sessão de checkout | cart/service.py — checkout validado no servidor: identificação, endereço, frete, revisão; estado em campos do cart + token de step | F6.2, F5.8, F6.6 |
| F6.8 | Testes backend | criação do carrinho, paridade de totais, baixa de estoque, transições, lookup convidado | F6.4, F6.5 |
| F6.9 | Módulo checkout frontend | modules/checkout/ — máquina de estados, steps: identificação, entrega, pagamento (placeholder), revisão; useCheckout | F6.4, F4.7, F5.10 |
| F6.10 | Módulo customer frontend | modules/customer/ — auth inline no checkout + reuso em minha-conta | F6.6, F1.10 |
| F6.11 | Página de checkout | app/checkout/page.tsx (single-page), app/checkout/obrigado/page.tsx | F6.9, F6.10 |
| F6.12 | Form de endereço + autofill CEP | componente no módulo customer, compartilhado com minha-conta | F6.10, F5.10 |
| F6.13 | Admin pedidos | admin/src/app/pedidos/* — lista, detalhe, timeline, ações de status, notas | F6.5 |
| F6.14 | E2E | checkout convidado até pending_payment; logado com endereço salvo | F6.11, F6.13 |

**Paralelo:** backend orders + edições de customers. **Serial:** F6.7 (cart/service.py); F7.9 já toca orders/service.py — dono único.

**Riscos:** estratégia de estoque (baixar na criação vs reservar com TTL vs baixar na confirmação — recomenda reserva com TTL p/ boleto/pix); persistência do estado de checkout (server-side vs client+validação); ciclo carrinho→pedido (manter até pago ou limpar na criação); idempotência do POST (idempotency key); validação de endereço (ViaCEP vs Melhor Envio), CPF PII; reembolso/cancelamento agora vs F7; envio único em 1–8; rollover de ano no número.

**Pronto quando:** convidado e logado concluem checkout até revisão → pedido pending_payment com snapshots e totais idênticos ao carrinho; estoque baixado/reservado; timeline populada; thank-you com número+resumo; convidado reabre por número+e-mail; admin lista/busca/detalha/muda status/nota; E2E verde.

---

## FASE 7 — Pagamento (Appmax) + e-mails transacionais

| ID | Tarefa | Arquivos | Depende |
|---|---|---|---|
| F7.1 | Base providers pagamento | payment/providers/base.py — create_charge, parse_webhook, refund; DTOs Charge/WebhookResult/RefundResult | F1.6 |
| F7.2 | Provider Appmax | payment/providers/appmax.py — auth, criar cliente/pedido, tokenização cartão, charge credit_card/pix/boleto, parse QR Pix + boleto, status, assinatura do webhook | F7.1 |
| F7.3 | payment service | {service,schemas,config}.py — criar pagamento via provider ativo, persistir payments, confirmação assíncrona, reconciliar pedido, idempotência via payment_webhook_events | F7.2, F6.3 |
| F7.4 | Webhook | payment/webhooks.py — POST /api/webhooks/payment/{provider} sem auth, verifica assinatura, grava evento, processa, 200 no aceite | F7.3 |
| F7.5 | payment routers | router_public POST /api/payment/charge, GET /api/payment/status/{order}; router_admin config (chaves Appmax, provider ativo), listar, reembolso, reprocessar webhook | F7.3, F1.9 |
| F7.6 | Registro + config módulo | payment/module.py (toggleable, PaymentConfig), segredos cifrados | F1.6, F7.3 |
| F7.7 | Infra SMTP + mailer | shared/mailer.py + modules/admin/ — smtp_settings service, envio com config do DB, email_log, templates (confirmação, pago, falhou, pix/boleto, status) | F1.8 |
| F7.8 | Subscribers de e-mail | modules/*/events.py — order.created (pix/boleto), payment.confirmed (recibo), order.status_changed (enviado/entregue) | F7.3, F7.7 |
| F7.9 | Finalização do pedido no pagamento | orders/service.py — limpar carrinho, finalizar estoque, paid/processing, commit da redemption | F7.3, F6.3 |
| F7.10 | Testes backend | charge por método (Appmax mock), idempotência + assinatura webhook, reembolso, reconciliação, email_log | F7.4, F7.5, F7.8 |
| F7.11 | Step de pagamento frontend | modules/checkout/components/Payment* — cartão (tokenização/iframe), Pix (QR + copiar + polling), boleto (link/barcode) | F7.5, F6.9 |
| F7.12 | Finalização thank-you | app/checkout/obrigado/page.tsx — instruções por método + polling → sucesso | F7.11, F6.11 |
| F7.13 | Telas admin | modulos/* (config pagamento), pedidos/* (reembolso, reprocessar), smtp/* (config + teste) | F7.5, F7.7 |
| F7.14 | E2E completo | carrinho → checkout → Pix/boleto/cartão (sandbox) → webhook confirma → paid → e-mail logado → thank-you sucesso | F7.11–F7.13 |

**Paralelo:** módulo payment + SMTP/mailer (dois tracks). Convergem em F7.8 e F7.9 (orders/service.py — dono único).

**Riscos (maior incógnita — obter docs + credenciais sandbox Appmax antes):** URLs base, auth (header access-token), fluxo (criar cliente → pedido → pagamento), **tokenização de cartão client-side** (fica fora do PCI-DSS SAQ-D), 3DS, payload Pix (QR string, expiração), campos boleto, tipos de evento + header de assinatura/HMAC do webhook, retry, reembolso parcial. Segurança do webhook (assinatura, IP allowlist, replay, ordenação, processamento assíncrono sem fila → BackgroundTasks ou worker leve); reconciliação com webhook atrasado (polling de fallback + "sincronizar" no admin); idempotência UNIQUE(provider, event_id); parcelas/juros (pass-through vs config); **carrinho limpa na criação do pedido** (boleto/pix são assíncronos); cifragem das chaves; deliverability (SPF/DKIM p/ Fase 9, templates + email_log + envio assíncrono com retry agora).

**Pronto quando:** pagamento sandbox p/ cartão/Pix/boleto cria payments + charge; webhook valida assinatura, idempotente, leva a paid e finaliza (carrinho limpo, estoque final, cupom redimido); failed/refund/chargeback atualizam; reembolso e reprocessar no admin; e-mails renderizam + gravam em email_log; teste SMTP pelo admin; thank-you reflete em tempo real; E2E completo verde.

---

## FASE 8 — Minha Conta, conteúdo, PWA, hardening e QA final

| ID | Tarefa | Arquivos | Depende |
|---|---|---|---|
| F8.1 | CRUD admin menus | admin/src/app/menus/* + menus/router_admin.py — mega menu, atalhos, highlight, reorder | F3.0, F1.9 |
| F8.2 | CRUD admin banners | admin/src/app/aparencia/* + banners/router_admin.py — slots, agendamento, imagem desktop/mobile | F3.0 |
| F8.3 | Admin theme + store_settings | aparencia/* + theme/router_admin.py — cores, logo/favicon, fontes, threshold, top bar, dados da loja, bandeiras; dispara revalidação | F3.2, F1.9 |
| F8.4 | Páginas institucionais (pages) | modules/pages (service + público + admin CRUD); frontend/src/app/[slug]/page.tsx; links do footer | F3.0, F3.4 |
| F8.5 | Módulo newsletter | modules/newsletter/ — subscribe/confirm/unsubscribe + admin list/export; forms footer e home | F1.8, F3.4 |
| F8.6 | Minha conta | frontend/src/app/minha-conta/{page,enderecos,pedidos}/ — dados, endereços (reusa form F6), histórico + detalhe + recomprar, troca de senha | F6.10, F6.6, F6.4 |
| F8.7 | Wishlist | modules/wishlist (service + público) + botão PDP/PLP + lista em minha-conta | F1.8, F3.7 |
| F8.8 | Dashboard admin | admin/src/app/(dashboard)/page.tsx + endpoint — pedidos recentes, faturamento, estoque baixo, reviews pendentes | F6.5, F2.6 |
| F8.9 | usuarios + RBAC | admin/src/app/usuarios/* + gates de papel via require_permission em todos os router_admin | F1.9 |
| F8.10 | PWA | manifest.json final, ícones 192/512 maskable, sw.ts + lib/sw-register.ts (cache assets), registro no layout | F3.x |
| F8.11 | Passe de performance | tamanhos/priority de imagem, code-splitting, next/font, redução de JS PDP/PLP, cache headers, índices/N+1, cache Redis (theme, menus, PLP) | todas |
| F8.12 | Passe de SEO | metadata em toda rota, JSON-LD, canonicals, sitemap completo, robots, 301 slug, OG/Twitter | F8.4, todas |
| F8.13 | Passe de acessibilidade | landmarks, foco (drawer/modal/menu), teclado no mega menu e seletor de variante, ARIA carrossel/accordion, contraste, labels/erros, skip link, reduced motion | UI completa |
| F8.14 | Hardening de segurança | rate limits (login, cupom, review, quote, webhook), validação, sanitização HTML, CORS/cookie, brute-force lockout admin, audit deps, .env.example completo | todas |
| F8.15 | Observabilidade | logging estruturado, request IDs, exception handlers, telas email_log / payment_webhook_events, healthchecks | todas |
| F8.16 | Suíte E2E | Playwright — compra convidado (Pix), logado (cartão), cupom+frete, falha+retry, admin cria produto→loja→compra, primeiro login, viewport mobile | todas |
| F8.17 | Lighthouse CI + smoke de carga | Lighthouse mobile home/PLP/PDP/carrinho/checkout com thresholds; k6 em catálogo + quote | F8.11–F8.13 |
| F8.18 | Docs finais | ARQUITETURA.md, MODULOS.md, API.md, README; nota "Fase 9 travada" | todas |

**Altamente paralelo:** telas admin F8.1/8.2/8.3/8.9; módulos backend F8.4/8.5/8.7; F8.6 minha-conta. **Serial:** passes F8.11/8.12/8.13 (arquivos compartilhados); F8.14 (core). **Por último:** F8.16/8.17.

**Riscos:** canal revalidação admin→frontend (revalidateTag + secret ou TTL curto); PWA com App Router (next-pwa/Serwist vs sw.ts custom; cache só de assets estáticos); mapa papel→rota/ação; thresholds Lighthouse/CWV como gate de CI; newsletter double opt-in usa mailer da F7; pages como módulo próprio vs dentro de theme; 301 quando slug muda (tabela de redirects/histórico).

---

## Checklist de validação final — Fase 8

### Performance / Lighthouse mobile (Moto G / 4G throttled, CI gate)
- [ ] Performance ≥ 90 em home, PLP, PDP, carrinho, checkout.
- [ ] LCP ≤ 2.5s · CLS ≤ 0.1 · INP ≤ 200ms · TBT ≤ 200ms (lab).
- [ ] WebP servido, srcset/sizes corretos, priority só no LCP, resto lazy; tamanho certo por contexto (thumb/medium/zoom).
- [ ] JS inicial PDP/PLP dentro do orçamento (ex. ≤ 200 KB gzip); code-splitting; sem libs pesadas no crítico.
- [ ] Fontes via next/font, font-display: swap, preconnect mínimo.
- [ ] SSR do tema sem flash (CSS vars inline no head); mudança no admin reflete sem rebuild.
- [ ] Cache headers em assets; endpoints quentes com cache Redis; ISR/tags validados.
- [ ] Sem N+1 em PLP/PDP/checkout; índices GIN pg_trgm confirmados via EXPLAIN.
- [ ] Smoke de carga em /api/catalog/* e /api/shipping/quote sem degradação.

### SEO
- [ ] title/description únicos e dinâmicos por rota; canonical correto (paginação e facetas).
- [ ] JSON-LD válido (Rich Results): Product (offers, aggregateRating, brand, disponibilidade), BreadcrumbList, Organization, WebSite + SearchAction.
- [ ] sitemap.xml dinâmico (categorias + produtos + páginas); robots.txt; noindex em carrinho/checkout/minha-conta/busca.
- [ ] OG/Twitter com imagem em home/PLP/PDP.
- [ ] URLs limpas; 301 para slug alterado.
- [ ] Status HTTP corretos (200/404/410); sem soft-404; sem links internos quebrados.
- [ ] lang="pt-BR", headings hierárquicos, conteúdo no HTML do servidor (verificável com JS off).

### Acessibilidade (WCAG 2.1 AA)
- [ ] axe-core / Lighthouse a11y ≥ 95, sem violações críticas.
- [ ] Navegação 100% por teclado: mega menu, seletor de variante, drawer, modais, steps do checkout; foco visível e ordem lógica.
- [ ] Foco preso em modal/drawer e devolvido ao fechar; Esc fecha.
- [ ] Imagens com alt significativo (ou vazio se decorativa); ícones-botão com aria-label.
- [ ] Forms: label associado, erros com aria-describedby, aria-invalid, foco no primeiro erro.
- [ ] Contraste ≥ 4.5:1 texto / 3:1 UI contra os tokens do tema do seed.
- [ ] Landmarks, skip link, prefers-reduced-motion respeitado.
- [ ] Carrossel/accordion/tabs com padrão ARIA; live region para "item adicionado ao carrinho".

### Testes
- [ ] Unit dos service.py de cada módulo + integração router_public/router_admin; meta ≥ 80% em cart/orders/payment/promotions/shipping.
- [ ] Idempotência e assinatura do webhook de pagamento; reconciliação de estados.
- [ ] Paridade de totais carrinho ↔ pedido ↔ pagamento com cupom + frete + arredondamento.
- [ ] Concorrência: número de pedido único, estoque sem oversell, double-submit do checkout.
- [ ] RBAC (staff não acessa o que é de admin/super_admin).
- [ ] CI roda tudo (lint, type-check, pytest, build dos 3 apps, E2E headless) como gate de merge.

### E2E dos fluxos críticos (Playwright, desktop + mobile viewport)
- [ ] Compra convidado com Pix (webhook sandbox confirma → paid → email_log → thank-you sucesso).
- [ ] Compra logado com cartão (tokenização → aprovado → paid).
- [ ] Boleto (pending_payment, carrinho limpo, instruções na thank-you, webhook → paid).
- [ ] Falha e retry de pagamento (recusado → segue pending → nova tentativa OK).
- [ ] Reembolso/chargeback (admin dispara → refunded; chargeback via webhook).
- [ ] Merge de carrinho (convidado → login → consolidado).
- [ ] Ciclo admin→loja (cria categoria+produto+variantes+imagens → PLP/PDP/busca → compra → aparece em pedidos e dashboard).
- [ ] Primeiro login do admin (força troca de senha).
- [ ] Toggle de módulo (desabilitar shipping/payment → 404 + UI se adapta).
- [ ] Tema sem rebuild (trocar cor/logo → reflete após revalidação).
- [ ] Minha conta (editar dados, endereço padrão, histórico e detalhe, recomprar).
- [ ] SEO/robots (noindex em carrinho/checkout; sitemap acessível; JSON-LD no HTML servido).

### Sanidade de release da Fase 8
- [ ] `make up && make migrate && make seed` do zero funciona; `make test` verde.
- [ ] `.env.example` cobre 100% das variáveis (Appmax, Melhor Envio, SMTP, JWT, storage, DB, Redis).
- [ ] `docker-compose.prod.yml` permanece esqueleto; nenhuma dependência de VPS/proxy no caminho de dev.
- [ ] docs atualizados; PROPOSTA movida para docs/.
- [ ] Nenhum segredo versionado; segredos de provider cifrados em repouso.
