# E-commerce (single-tenant, estilo VTEX)

Monorepo: loja headless (Next.js) + painel admin (Next.js) + API (FastAPI async) +
PostgreSQL + Redis, orquestrado por Docker Compose. Arquitetura modular
(`api/app/modules/*`), smart checkout, PWA mobile-first.

> Proposta de arquitetura: [`PROPOSTA-FASE-0.md`](PROPOSTA-FASE-0.md) ·
> Plano de execução: [`docs/PLANO-EXECUCAO.md`](docs/PLANO-EXECUCAO.md) ·
> Rodar localmente: [`RODAR-LOCAL.md`](RODAR-LOCAL.md) ·
> Checklist pra apontar o domínio real em produção: [`docs/DOMINIO-PRODUCAO.md`](docs/DOMINIO-PRODUCAO.md)

## Requisitos

- Docker + Docker Compose v2
- (opcional) Node 20+ e Python 3.12+ no host para rodar ferramentas fora do container

## Subir o ambiente de dev

```bash
cp .env.example .env
make up          # build + sobe api, frontend, admin, db, redis, mailpit
make migrate     # aplica o schema
make seed        # cria admin padrão, tema neutro, menus e registro de módulos
```

| Serviço | URL |
|---|---|
| API (OpenAPI) | http://localhost:8000/docs |
| Loja | http://localhost:3000 |
| Admin | http://localhost:3001/administracao |
| Mailpit (e-mails de teste) | http://localhost:8025 |

`db` e `redis` **não** publicam porta — acesso só via `make db-sh` / `make redis-sh`.

## Estrutura

```
api/         FastAPI + SQLAlchemy async + Alembic; um módulo por pasta em app/modules/
frontend/    Next.js (App Router) — loja, mobile-first, PWA
admin/       Next.js — painel sob /administracao
packages/ui/ design system compartilhado (React + Tailwind preset)
infra/       initdb do Postgres; exemplos de vhost LiteSpeed (fase 9)
docs/        proposta, plano, arquitetura
```

## Fases

1. Fundação · 2. Catálogo · 3. Páginas core · 4. Carrinho e frete ·
5. Checkout e pagamento · 6. Pós-compra · 7. Admin completo ·
8. Polimento e validação local · 9. Conteinerização de produção *(travada até aprovação da fase 8)*
