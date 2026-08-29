# Arquitetura

## Visão geral

```
Cloudflare (TLS borda)  ─►  LiteSpeed/aaPanel (host, reverse proxy)  ─►  containers
                                                                         ├─ frontend  :3000  (Next.js — loja)
                                                                         ├─ admin     :3001  (Next.js — /administracao)
                                                                         └─ api       :8000  (FastAPI)
                                                                              ├─ db     (Postgres, rede interna)
                                                                              └─ redis  (rede interna)
```

Em **dev** não há proxy: o navegador fala direto com `:3000`, `:3001`, `:8000`.
Em **prod** (Fase 9) os apps publicam só em `127.0.0.1`; o LiteSpeed roteia por vhost.

## Backend modular

- Cada domínio/feature é um **módulo** em `api/app/modules/<slug>/`.
- `bootstrap.discover_modules()` importa `app.modules.<slug>.module` automaticamente
  → adicionar módulo **não** exige editar `main.py`.
- `module.py` registra um `ModuleSpec` (slug, label, `toggleable`, `default_config`,
  routers público/admin/webhook).
- `register_all()` monta:
  - `public_router`  → `/api/<slug>/...`
  - `admin_router`   → `/api/admin/<slug>/...`  (o módulo `admin` fica em `/api/admin`)
  - `webhook_router` → `/api/webhooks/<slug>/...`  (sem auth; valida assinatura)
- Módulo togglável: `require_module_enabled(slug)` (lê a tabela `modules`) → 404 se off.
- **Regra de negócio mora em `service.py`** — routers público e admin só orquestram.

## Auth

- JWT `HS256` com claim `scope` (`customer` | `admin`) e `type` (`access` | `refresh`).
- Refresh tokens persistidos (`auth_refresh_tokens`), rotacionados e revogáveis.
- Senha: Argon2 (`argon2-cffi`).
- Dependências: `get_current_customer`, `get_current_admin`, `require_role(*roles)`.
- RBAC: papéis simples `super_admin` / `admin` / `staff` (super_admin passa em tudo).

## Dados

- Postgres + `pg_trgm` (GIN em `products.name`, `categories.name` — busca fuzzy) + `citext`.
- SQLAlchemy async; sessão por request com commit/rollback automático (`get_db`).
- Alembic: `0001` cria o schema inteiro a partir de `Base.metadata`; deltas seguintes
  são autogenerate incrementais (um integrador serializa a cadeia).
- Dinheiro em centavos (`int`). PK `uuid`. Timestamps `timestamptz`.

## Imagens

- `shared/images.py`: todo upload → WebP + 3 tamanhos (`thumb` ~130, `medium` ~600,
  `zoom` ~1600). Metadados da original guardados. `shared/storage.py` abstrai o
  backend (disco local em dev, via volume Docker).

## Cache / fila

- Redis: sessão de carrinho (espelho), cache de cotação de frete, rate limiting.
- Event bus **in-process** (`core/events.py`): `emit(evento, payload)` +
  `@on(evento)`. Sem durabilidade — webhooks são a fonte da verdade em pagamento/frete.

## Frontend

- Dois apps Next.js (App Router, TS) compartilhando `packages/ui` (Tailwind preset +
  componentes). Loja: mobile-first, PWA (`manifest.json` + service worker de assets).
- Tema vem do banco (`GET /api/theme`) e é injetado como CSS variables no SSR —
  troca de cor/logo no admin reflete sem rebuild (revalidação por tag).
