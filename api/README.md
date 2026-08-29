# API (FastAPI)

FastAPI assíncrono, modular. Um módulo por pasta em `app/modules/<slug>/`.

## Layout

```
app/
  bootstrap.py        auto-discovery de módulos (app.modules.<x>.module)
  main.py             cria o FastAPI, monta os routers de todos os módulos
  models.py           importa TODOS os modelos (Alembic / create_all)
  core/               config, database, redis, security, deps, errors, events,
                      pagination, ratelimit, module_registry
  shared/             models_base, slugify, images (WebP + 3 tamanhos), storage
  seed/               seed inicial idempotente (admin, tema, menus, módulos)
  modules/<slug>/
    module.py         registra o ModuleSpec (slug, label, toggleable, routers)
    models.py         modelos SQLAlchemy do módulo
    schemas.py        DTOs Pydantic
    service.py        REGRA DE NEGÓCIO — fonte única da verdade
    router_public.py  rotas da loja   -> /api/<slug>/...
    router_admin.py   rotas do admin  -> /api/admin/<slug>/...
    providers/        só em payment e shipping (interface abstrata + concretos)
alembic/              migrations (0001 = baseline via Base.metadata)
tests/                pytest (asyncio); tests/modules/<slug>/, tests/e2e/
```

## Comandos (via Docker, a partir da raiz do monorepo)

```bash
make migrate                       # alembic upgrade head
make makemigration m="mensagem"    # autogenerate
make seed                          # python -m app.seed.run
make test                          # pytest
make lint                          # ruff + mypy
```

## Convenções

- Dinheiro sempre em centavos (`*_cents`, int).
- PK `uuid` (`gen_random_uuid`), timestamps `timestamptz`.
- Erros de domínio: levantar `app.core.errors.DomainError` (e subclasses) — os
  handlers convertem para JSON `{"error": {"code", "message", "details"}}`.
- Auth: JWT com `scope` (`customer` | `admin`); dependências em `app.core.deps`.
- Módulo togglável: `require_module_enabled(slug)` já é aplicado pelo registry.
