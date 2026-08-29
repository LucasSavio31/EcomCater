# Proposta — Fase 0 (pré-Fase 1)

E-commerce single-tenant estilo VTEX (headless + smart checkout) com admin nos
moldes do WooCommerce.

Stack: **Next.js + TypeScript** (loja e admin), **FastAPI async + SQLAlchemy async
+ Alembic**, **PostgreSQL** (`pg_trgm`/GIN + `citext`), **Redis**, **Docker Compose**
(profiles `dev` e `prod`, sem proxy reverso no Docker — LiteSpeed/aaPanel no host
com Cloudflare na frente).

Este documento cobre os 3 itens pedidos antes da Fase 1:

1. Estrutura de pastas do monorepo
2. Estrutura interna de cada módulo
3. Schema inicial do banco

---

## 1. Estrutura de pastas do monorepo

```
ecom/
├── docker-compose.yml               # base (todos os serviços)
├── docker-compose.override.yml      # profile dev (portas expostas, hot reload)
├── docker-compose.prod.yml          # profile prod — ESQUELETO só; foco real na Fase 9
├── .env.example                     # todas as variáveis (secrets nunca versionados)
├── .gitignore
├── Makefile                         # make up / make seed / make migrate / make test
├── README.md
│
├── api/                             # ── FastAPI (Python 3.12+) ────────────────
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py                   # async
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                  # cria FastAPI, monta routers via module_registry
│   │   ├── core/
│   │   │   ├── config.py            # Settings (pydantic-settings, lê env)
│   │   │   ├── database.py          # engine async, get_db
│   │   │   ├── redis.py             # cliente Redis compartilhado
│   │   │   ├── security.py          # argon2, JWT access/refresh, revogação
│   │   │   ├── deps.py              # current_customer / current_admin / require_permission
│   │   │   ├── pagination.py
│   │   │   ├── errors.py            # exceções de domínio + exception handlers
│   │   │   ├── events.py            # event bus in-process (order.paid, payment.confirmed…)
│   │   │   ├── ratelimit.py         # rate limiting via Redis
│   │   │   └── module_registry.py   # descobre módulos, habilita/monta routers
│   │   ├── modules/                 # 1 pasta por módulo (ver seção 2)
│   │   │   ├── products/
│   │   │   ├── categories/
│   │   │   ├── cart/
│   │   │   ├── orders/
│   │   │   ├── customers/
│   │   │   ├── payment/
│   │   │   ├── shipping/
│   │   │   ├── promotions/
│   │   │   ├── banners/
│   │   │   ├── menus/
│   │   │   ├── theme/
│   │   │   ├── newsletter/
│   │   │   └── admin/
│   │   ├── shared/
│   │   │   ├── models_base.py       # Base declarativa + mixins (uuid pk, timestamps)
│   │   │   ├── slugify.py           # slug com tratamento de acento/caractere especial
│   │   │   ├── images.py            # pipeline WebP + 3 tamanhos (Pillow)
│   │   │   └── storage.py           # abstração de storage (local em dev, S3-compat depois)
│   │   └── seed/
│   │       └── initial.py           # admin padrão (env), tema neutro, menus básicos
│   └── tests/
│       ├── conftest.py             # DB de teste, fixtures de auth, factory de dados
│       ├── modules/<module>/…      # unit/integration por módulo
│       └── e2e/                    # carrinho → checkout → pagamento → confirmação
│
├── packages/
│   └── ui/                          # ── Design system compartilhado ──────────
│       ├── package.json
│       ├── tailwind-preset.js       # tokens, breakpoints (mobile-first), plugin
│       └── src/
│           ├── tokens/              # cores/tipografia como CSS vars (tema vem do banco)
│           ├── components/          # Button, Input, Drawer, Accordion, Card, Modal…
│           └── index.ts
│
├── frontend/                        # ── Next.js (App Router) — LOJA ───────────
│   ├── Dockerfile
│   ├── next.config.mjs
│   ├── tailwind.config.ts           # estende packages/ui/tailwind-preset
│   ├── public/
│   │   ├── manifest.json            # PWA: standalone, ícones, theme color
│   │   └── icons/                   # 192/512, maskable
│   └── src/
│       ├── app/
│       │   ├── layout.tsx           # header/footer dinâmicos, registra service worker
│       │   ├── page.tsx                          # /
│       │   ├── categoria/[...slug]/page.tsx      # /categoria/feminino/vestidos
│       │   ├── produto/[slug]/page.tsx           # /produto/vestido-longo-floral
│       │   ├── carrinho/page.tsx
│       │   ├── checkout/page.tsx
│       │   ├── checkout/obrigado/page.tsx
│       │   ├── minha-conta/
│       │   │   ├── page.tsx                      # dados pessoais
│       │   │   ├── enderecos/page.tsx
│       │   │   └── pedidos/page.tsx
│       │   ├── sitemap.ts                        # sitemap.xml dinâmico
│       │   └── robots.ts
│       ├── modules/                 # espelha o backend — só o que a loja consome
│       │   ├── catalog/             # produto, categoria, busca instantânea
│       │   ├── cart/                # useCart, drawer, barra de frete grátis
│       │   ├── checkout/            # máquina de estados do smart checkout
│       │   ├── customer/            # auth cliente + minha-conta
│       │   ├── shipping/            # campo CEP + cotação
│       │   ├── promotions/          # cupom no carrinho/checkout
│       │   ├── banners/  menus/  theme/
│       ├── lib/
│       │   ├── api-client.ts        # fetch tipado (client + server components)
│       │   ├── seo.ts               # metadata dinâmica + JSON-LD schema.org
│       │   └── sw-register.ts
│       ├── sw.ts                    # service worker (cache de assets estáticos)
│       └── styles/
│
├── admin/                           # ── Next.js — PAINEL /administracao ───────
│   ├── Dockerfile
│   ├── next.config.mjs              # basePath: "/administracao"
│   └── src/
│       ├── app/
│       │   ├── layout.tsx           # shell do admin (sidebar, guarda de auth)
│       │   ├── login/page.tsx       # + fluxo "trocar senha no 1º login"
│       │   ├── (dashboard)/page.tsx # pedidos recentes, faturamento, estoque baixo
│       │   ├── produtos/…  categorias/…  pedidos/…  clientes/…
│       │   ├── promocoes/…  menus/…  aparencia/…
│       │   ├── modulos/…            # habilitar/configurar pagamento e frete
│       │   ├── smtp/…               # config + teste de envio
│       │   └── usuarios/…           # admin users + papéis/permissões
│       ├── modules/                 # espelha o backend — visão admin
│       ├── lib/admin-api-client.ts
│       └── styles/
│
├── infra/
│   ├── postgres/initdb/             # CREATE EXTENSION pg_trgm, citext
│   └── litespeed/                   # (Fase 9) exemplos de vhost — vazio por enquanto
│
└── docs/
    ├── PROPOSTA-FASE-0.md           # este arquivo
    ├── ARQUITETURA.md
    └── MODULOS.md                   # contrato de cada módulo
```

### Decisões de arquitetura relevantes

- **Dois apps Next distintos** (`frontend` e `admin`), compartilhando `packages/ui`.
  Em dev: portas diretas (`:3000` loja, `:3001` admin, `:8000` api). Em prod: o
  LiteSpeed no host roteia `/administracao` → container admin e o resto → frontend
  (o admin usa `basePath: "/administracao"`). Nenhum proxy dentro do Docker.
- **Portas**: em `prod`, `frontend`/`admin`/`api` publicam só em `127.0.0.1`.
  `db` e `redis` **nunca** publicam porta — só rede interna Docker, em qualquer profile.
- **Regra de negócio única por módulo**: `service.py` é a fonte da verdade;
  `router_public.py` e `router_admin.py` só chamam o service. Nada de lógica
  duplicada entre loja e admin.
- **Módulos habilitáveis**: tabela `modules` (`slug`, `enabled`, `config_json`).
  Módulos de CRUD de domínio existem sempre (não desligam); `payment`, `shipping`,
  `promotions`, `banners`, `newsletter`, barra utilitária etc. são toggláveis.
- **Tema sem rebuild**: `theme_settings`/`store_settings` no banco → API expõe
  `GET /api/theme` → frontend injeta como CSS variables no `layout.tsx` (SSR).
- **Imagens**: todo upload passa por `shared/images.py` → converte para WebP e gera
  `thumb` (~130), `medium` (~600), `zoom` (original/maior). Metadados da original
  (nome, dimensões) ficam no banco. `next/image` cuida de `srcset`/lazy em cima.

---

## 2. Estrutura interna de cada módulo

### 2.1 Layout padrão (backend) — todos os módulos seguem

```
api/app/modules/<module>/
├── __init__.py
├── module.py            # metadados: slug, label, kind (domain|feature),
│                        #   toggleable, config_model, routers, on_enable/on_disable
├── models.py            # modelos SQLAlchemy do módulo
├── schemas.py           # DTOs Pydantic (entrada/saída) — compartilhados loja/admin
├── service.py           # REGRA DE NEGÓCIO — única fonte da verdade
├── repository.py        # queries mais complexas (opcional)
├── events.py            # publishers/subscribers do event bus
├── dependencies.py      # dependências específicas do módulo
├── config.py            # Pydantic model das configs persistidas (se toggleable)
├── router_public.py     # rotas da loja   → /api/<module>/...
└── router_admin.py      # rotas do admin  → /api/admin/<module>/...
```

Testes correspondentes em `api/tests/modules/<module>/` (`test_service.py`,
`test_router_public.py`, `test_router_admin.py`).

### 2.2 Módulos com provedores (interface abstrata) — `payment` e `shipping`

Acrescentam a pasta `providers/`:

```
modules/payment/
├── module.py            # toggleable=True, config_model=PaymentConfig
├── models.py            # payments, payment_webhook_events
├── schemas.py
├── service.py           # cria cobrança pelo provider ativo; concilia webhook; reembolso
├── config.py            # provider ativo + chaves de API (guardado em modules.config_json)
├── webhooks.py          # POST /api/webhooks/payment/{provider} — sem auth, valida assinatura
├── router_public.py     # POST /api/payment/charge (checkout); GET status
├── router_admin.py      # config, listagem, reembolso, reprocessar webhook
└── providers/
    ├── base.py          # class PaymentGateway(ABC):
    │                    #   create_charge(order, method, ...) -> Charge
    │                    #   parse_webhook(headers, body) -> WebhookResult
    │                    #   refund(payment, amount) -> RefundResult
    └── appmax.py        # implementação real (Appmax — cartão, Pix, boleto + webhooks)
```

```
modules/shipping/
├── module.py            # toggleable=True, config_model=ShippingConfig
├── models.py            # shipping_quotes (espelho/auditoria; TTL real no Redis)
├── schemas.py
├── service.py           # quote(cep_dest, itens): Redis → provider → cacheia (Redis + tabela)
├── config.py            # provider ativo, token Melhor Envio, CEP origem, dims padrão
├── router_public.py     # POST /api/shipping/quote
├── router_admin.py      # config + botão "testar cotação"
└── providers/
    ├── base.py          # class ShippingProvider(ABC):
    │                    #   quote(origin, dest, packages) -> list[ShippingRate]
    └── melhor_envio.py  # implementação real (API Melhor Envio)
```

Adicionar um novo gateway/transportadora = criar um arquivo em `providers/` e
registrá-lo no `module.py`. Nada mais no sistema muda.

### 2.3 Registro e habilitação de módulos

- Cada `module.py` exporta um objeto `Module(...)`.
- `core/module_registry.py` importa todos, cruza com a tabela `modules`
  (`enabled`, `config_json`) e monta os routers em `main.py`.
- Dependência `require_module_enabled("<slug>")` → rotas de módulo desligado
  respondem 404.
- `admin` expõe `/api/admin/modules` (listar, ligar/desligar, salvar config).

### 2.4 Módulo `admin` (é um módulo também)

```
modules/admin/
├── module.py
├── models.py            # admin_users, admin_roles (RBAC simples), auth_refresh_tokens (admin)
├── schemas.py
├── service.py           # login admin, troca de senha obrigatória, gestão de usuários/papéis
├── security.py          # emissão/rotação de JWT do admin (separado do cliente)
├── router_admin.py      # /api/admin/auth/*, /api/admin/users/*, /api/admin/dashboard,
│                        #   /api/admin/settings (store_settings gerais)
└── (sem router_public)
```

### 2.5 Layout padrão (frontend) — `frontend/src/modules/<module>` e `admin/src/modules/<module>`

```
modules/<module>/
├── api.ts              # chamadas à API desse módulo (tipadas)
├── types.ts            # tipos TS espelhando schemas.py
├── components/         # componentes de domínio (ProductGallery, MegaMenu, CheckoutSection…)
├── hooks/              # useCart, useShippingQuote, useCoupon…
└── index.ts
```

O `packages/ui` guarda só componentes genéricos sem regra de negócio.

---

## 3. Schema inicial do banco

Convenções: PK `uuid` (default `gen_random_uuid()`), `created_at`/`updated_at`
`timestamptz` em quase tudo, dinheiro sempre em **centavos `int`** (`*_cents`),
extensões `pg_trgm` (índices GIN em `products.name`, `categories.name` para busca
fuzzy) e `citext` (e-mails/códigos de cupom case-insensitive).

### Módulo `customers` / `admin` (identidade e auth)

**users** (clientes da loja)
| coluna | tipo | notas |
|---|---|---|
| id | uuid PK | |
| email | citext UNIQUE | |
| password_hash | text | argon2 |
| full_name | text | |
| phone | text | |
| cpf | varchar(11) NULL | |
| is_active | bool | |
| email_verified_at | timestamptz NULL | |
| created_at / updated_at | timestamptz | |

**customer_addresses**
`id` uuid PK · `user_id`→users · `label` · `recipient_name` · `zip` varchar(8) ·
`street` · `number` · `complement` · `district` · `city` · `state` char(2) ·
`is_default` bool · timestamps

**admin_users**
`id` uuid PK · `email` citext UNIQUE · `password_hash` · `name` ·
`role` enum(`super_admin`,`admin`,`staff`) · `permissions_json` jsonb (RBAC fino
opcional) · `must_change_password` bool default true · `last_login_at` ·
`is_active` bool · timestamps

**auth_refresh_tokens** (clientes **e** admins — colunas de escopo)
`id` uuid PK · `subject_type` enum(`customer`,`admin`) · `subject_id` uuid ·
`token_hash` text · `expires_at` · `revoked_at` NULL · `user_agent` · `ip` ·
`created_at` · INDEX(`subject_type`,`subject_id`)

**wishlists** `id` · `user_id` UNIQUE →users
**wishlist_items** `wishlist_id` · `product_id` · `created_at` · PK(`wishlist_id`,`product_id`)

### Módulo `categories`

**categories** (árvore)
`id` uuid PK · `parent_id`→categories NULL · `name` · `slug` text · `path` text
(`feminino/vestidos`, resolve `/categoria/[...slug]`) · `description` ·
`image_key` NULL · `position` int · `is_active` bool · `seo_title` ·
`seo_description` · timestamps · UNIQUE(`parent_id`,`slug`) · INDEX GIN em `name`
(pg_trgm)

### Módulo `products`

**products**
`id` uuid PK · `name` · `slug` text UNIQUE · `sku_root` text NULL (exibe "Ref:
11206-00") · `short_description` · `description` text · `brand` NULL ·
`category_id`→categories (principal) · `status` enum(`draft`,`active`,`archived`) ·
`is_featured` bool · `price_cents` int (a partir de) · `compare_at_price_cents`
int NULL (de/por) · `pix_discount_pct` numeric NULL · `installments_max` int NULL ·
`weight_grams` · `length_mm`/`width_mm`/`height_mm` (frete) · `rating_avg` numeric ·
`rating_count` int · `seo_title` · `seo_description` · `published_at` NULL ·
timestamps · INDEX GIN em `name` (pg_trgm)

**product_categories** (N:N adicional) — `product_id` · `category_id` · PK composto

**product_variants** (SKU filho)
`id` uuid PK · `product_id`→products · `sku` text UNIQUE · `price_cents` int NULL
(override; herda do produto se null) · `compare_at_price_cents` NULL ·
`stock_qty` int · `weight_grams` NULL (override) · `barcode` NULL ·
`is_active` bool · `position` int · timestamps

**variant_option_types** (eixos de variação por produto)
`id` · `product_id`→products · `name` ("Numeração", "Cor") · `is_size` bool
(marca o eixo dos atalhos "compre por tamanho") · `position`

**variant_option_values** — `id` · `option_type_id`→variant_option_types ·
`value` ("38", "Preto") · `position`

**product_variant_options** — `variant_id`→product_variants ·
`option_value_id`→variant_option_values · PK(`variant_id`,`option_value_id`)

**product_images**
`id` · `product_id`→products · `variant_id`→product_variants NULL (imagem por cor) ·
`alt` · `position` · `is_primary` bool · `original_filename` ·
`original_width`/`original_height` · `thumb_key` (~130) · `medium_key` (~600) ·
`zoom_key` (original) · `created_at`

**product_specs** (chave-valor) — `id` · `product_id` · `group` NULL ("Materiais") ·
`label` ("Solado") · `value` · `position`

**product_related** (N:N "quem viu também gostou") — `product_id` ·
`related_product_id` · `position` · PK composto

**product_reviews** — `id` · `product_id` · `user_id` NULL · `author_name` ·
`rating` int(1–5) · `title` · `body` · `status` enum(`pending`,`approved`,`rejected`) ·
`created_at` (mantém `rating_avg`/`rating_count` em products via service)

### Módulo `cart`

**carts**
`id` uuid PK · `user_id`→users NULL (null = convidado) · `session_token` text
UNIQUE (cookie; espelhado no Redis) · `coupon_id`→coupons NULL ·
`shipping_zip` varchar(8) NULL · `selected_shipping_json` jsonb NULL ·
`expires_at` timestamptz · timestamps

**cart_items**
`id` · `cart_id`→carts · `product_id`→products · `variant_id`→product_variants ·
`quantity` int · `unit_price_cents` int (snapshot na adição) · timestamps ·
UNIQUE(`cart_id`,`variant_id`)

### Módulo `promotions`

**coupons**
`id` · `code` citext UNIQUE · `description` · `type` enum(`percent`,`fixed`,`free_shipping`) ·
`value` numeric · `min_order_cents` NULL · `max_discount_cents` NULL ·
`starts_at` · `ends_at` · `usage_limit` int NULL (global) ·
`usage_limit_per_user` int NULL · `used_count` int · `applies_to_json` jsonb NULL
(categorias/produtos alvo — futuro) · `is_active` bool · timestamps

**coupon_redemptions** — `id` · `coupon_id`→coupons · `user_id` NULL ·
`order_id`→orders · `discount_cents` · `created_at`

### Módulo `orders`

**orders**
`id` uuid PK · `number` text UNIQUE (humano, ex. `2026-000123`) · `user_id` NULL ·
`email` · `cpf` varchar(11) NULL · `status` enum(`pending_payment`,`paid`,
`processing`,`shipped`,`delivered`,`canceled`,`refunded`) ·
`payment_status` enum(`pending`,`authorized`,`paid`,`failed`,`refunded`,`chargeback`) ·
`fulfillment_status` enum(`unfulfilled`,`partial`,`fulfilled`) ·
`items_total_cents` · `discount_cents` · `shipping_cents` · `grand_total_cents` ·
`coupon_id` NULL · `coupon_code` text NULL · `shipping_method` text ·
`shipping_service_json` jsonb (prazo, transportadora, id do serviço) ·
`shipping_address_json` jsonb (snapshot) · `billing_address_json` jsonb NULL ·
`customer_note` NULL · `placed_at` · timestamps

**order_items**
`id` · `order_id`→orders · `product_id`→products NULL · `variant_id` NULL ·
`sku` · `name` · `variant_label` ("Numeração 38 / Preto") · `image_key` NULL ·
`unit_price_cents` · `quantity` · `total_cents` (tudo snapshot p/ histórico imutável)

**order_events** (linha do tempo)
`id` · `order_id`→orders · `type` ("status_changed","payment_confirmed","note") ·
`from_status` NULL · `to_status` NULL · `message` NULL ·
`actor_type` enum(`system`,`admin`,`customer`) · `actor_id` uuid NULL · `created_at`

### Módulo `payment`

**payments**
`id` · `order_id`→orders · `provider` text ("pagarme") ·
`method` enum(`credit_card`,`pix`,`boleto`) ·
`status` enum(`pending`,`authorized`,`paid`,`failed`,`refunded`,`chargeback`) ·
`amount_cents` · `installments` int NULL · `provider_charge_id` text ·
`provider_payload_json` jsonb · `pix_qr_code` NULL · `pix_expires_at` NULL ·
`boleto_url` NULL · `boleto_barcode` NULL · `paid_at` NULL · timestamps

**payment_webhook_events** (idempotência)
`id` · `provider` · `provider_event_id` · `signature_valid` bool ·
`payload_json` jsonb · `processed_at` NULL · `order_id` NULL · `created_at` ·
UNIQUE(`provider`,`provider_event_id`)

### Módulo `shipping`

**shipping_quotes** (espelho/auditoria — TTL real no Redis)
`id` · `cache_key` text (hash origem+destino+pacotes) · `origin_zip` ·
`dest_zip` · `packages_json` jsonb · `rates_json` jsonb (serviço, transportadora,
preço, prazo) · `provider` · `created_at` · `expires_at`

### Módulo `banners`

**banners**
`id` · `slot` text (`top_bar`,`hero`,`showcase`,…) · `title` ·
`image_desktop_key` · `image_mobile_key` NULL · `link_url` · `alt` ·
`position` int · `starts_at` NULL · `ends_at` NULL · `is_active` bool · timestamps

### Módulo `menus`

**menus** — `id` · `location` enum(`header`,`footer`) · `name` · `position` · `is_active`

**menu_items**
`id` · `menu_id`→menus · `parent_id`→menu_items NULL · `label` ·
`link_type` enum(`category`,`url`,`page`) · `category_id`→categories NULL ·
`url` text NULL · `position` · `is_megamenu` bool (item de topo com dropdown rico) ·
`highlight` bool ("ATÉ 50% OFF" em destaque) · `show_size_shortcuts` bool
(bloco "compre por tamanho" no mega menu) · `size_shortcut_category_id` NULL · timestamps

### Módulo `theme` + configs de loja

**theme_settings** (linha única, `id smallint PK CHECK (id = 1)`)
`primary_color` · `secondary_color` · `accent_color` · `text_color` · `bg_color` ·
`logo_key` · `logo_mobile_key` · `favicon_key` · `font_family` ·
`free_shipping_threshold_cents` int NULL · `whatsapp_number` NULL ·
`top_bar_message` NULL · `top_bar_enabled` bool · `updated_at`

**store_settings** (linha única) — `store_name` · `legal_name` · `cnpj` ·
`address_json` jsonb · `social_json` jsonb · `contact_phone` ·
`contact_whatsapp` · `payment_flags_json` jsonb (bandeiras do rodapé) · `updated_at`

**pages** (institucionais do rodapé — Quem Somos, Políticas, FAQ; sem hardcode)
`id` · `slug` UNIQUE · `title` · `body` html · `is_published` bool · `seo_title` ·
`seo_description` · `updated_at`

### Módulo `admin` (infra)

**smtp_settings** (linha única) — `host` · `port` · `username` · `password_enc` ·
`use_tls` bool · `use_ssl` bool · `from_email` · `from_name` · `updated_at`

**email_log** — `id` · `to_email` · `template` · `subject` ·
`status` enum(`sent`,`failed`) · `error` NULL · `order_id` NULL · `created_at`

**modules** (registro/habilitação) — `slug` text PK · `enabled` bool ·
`config_json` jsonb · `updated_at`

### Módulo `newsletter`

**newsletter_subscribers** — `id` · `email` citext UNIQUE · `name` NULL ·
`source` ("home_form") · `confirmed_at` NULL · `unsubscribed_at` NULL · `created_at`

### Diagrama de relacionamentos (resumo)

```
users ─┬─< customer_addresses
       ├─< wishlists ─< wishlist_items >─ products
       ├─< carts ─< cart_items >─ product_variants >─ products
       └─< orders ─┬─< order_items
                   ├─< order_events
                   ├─< payments ── payment_webhook_events
                   └─── coupons ─< coupon_redemptions

categories ─< categories (self, árvore)
products ─┬─< product_variants ─< product_variant_options >─ variant_option_values >─ variant_option_types
          ├─< product_images
          ├─< product_specs
          ├─< product_reviews
          ├─< product_categories >─ categories
          └─< product_related (self N:N)

menus ─< menu_items (self, árvore) ──> categories
banners            (independente, por slot)
theme_settings / store_settings / smtp_settings / modules / pages   (singletons/config)
shipping_quotes / newsletter_subscribers / email_log                (independentes)
```

---

## Seed inicial (Fase 1)

- **admin padrão** a partir de `ADMIN_EMAIL` / `ADMIN_PASSWORD` (env),
  `must_change_password = true` (força troca no 1º login).
- **theme_settings**: paleta neutra.
- **menus**: `header` e `footer` mínimos, para a loja não subir vazia.
- **modules**: linhas com defaults (`payment`/`shipping` desabilitados até configurar
  chaves; CRUDs de domínio habilitados).

---

## Decisões tomadas (29/08/2026)

1. **Repositório git** — `git init` próprio em `ecom/` (repo separado do `wisc`).
2. **Gateway de pagamento** — **Appmax** como primeiro provedor real
   (`modules/payment/providers/appmax.py`): cartão, Pix e boleto, com webhook de
   confirmação. Interface `PaymentGateway` continua permitindo outros depois.
3. **RBAC do admin** — papéis simples: `role` = `super_admin` / `admin` / `staff`
   (coluna `permissions_json` fica reservada para evolução futura).
4. **Storage de imagens (Fases 1–8)** — disco local em volume Docker, via
   abstração `shared/storage.py` (troca para S3-compatível só se/quando na Fase 9).

Revise os 3 blocos acima. Ao seu OK explícito, começo a **Fase 1 — Fundação**:
`git init` em `ecom/`, monorepo, Docker Compose de dev, schema/migrations,
autenticação (JWT cliente + admin) e seed do admin padrão.
```
