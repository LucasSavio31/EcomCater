# Rodar localmente (sem Docker)

Stack nativo montado para a máquina de dev. Docker **não** é usado aqui.

## Componentes

| Peça | Como roda | Porta |
|---|---|---|
| PostgreSQL 16 | binários portáteis em `C:\Users\lsavy\pgsql\pgsql`, cluster em `C:\Users\lsavy\ecom-pgdata` | **5433** |
| Redis | `fakeredis` em memória (no processo da API) — `REDIS_URL=fakeredis://` | — |
| API (FastAPI) | venv em `api/.venv` | 8000 |
| Loja (Next) | `npm run dev --workspace=frontend` | 3000 |
| Admin (Next) | `npm run dev --workspace=admin` | 3001 |

Config em `api/.env` (não versionado).

## Subir tudo

```bash
# 1) Postgres (uma vez por boot da máquina)
"C:/Users/lsavy/pgsql/pgsql/bin/pg_ctl.exe" -D "C:/Users/lsavy/ecom-pgdata" \
  -l "C:/Users/lsavy/ecom-pgdata/server.log" -o "-p 5433" start

# 2) API
cd api
./.venv/Scripts/python.exe -m alembic upgrade head      # migrations
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3) Loja + Admin (na raiz, em terminais separados)
npm run dev --workspace=frontend
npm run dev --workspace=admin
```

## URLs

- Loja: http://localhost:3000
- Admin: http://localhost:3001/administracao — **admin@lojateste.com / admin12345** (troca de senha no 1º acesso)
- API docs: http://localhost:8000/docs

## Seeds

```bash
cd api
./.venv/Scripts/python.exe -m app.seed.run            # admin, tema, menus, módulos, páginas, banners
./.venv/Scripts/python.exe -m app.seed.sneaker        # cadastra 1 tênis aleatório com numeração/estoque
```

## Parar

```bash
"C:/Users/lsavy/pgsql/pgsql/bin/pg_ctl.exe" -D "C:/Users/lsavy/ecom-pgdata" stop
# e Ctrl+C nos processos da API / Next
```

## Notas

- `fakeredis` é só para dev local: cache de frete, carrinho e rate-limit ficam em memória e somem ao reiniciar a API.
- A `:5432` desta máquina já tem outro PostgreSQL (instalação anterior). Por isso este projeto usa a **:5433**.
- Ao salvar Aparência ou Rastreamento no admin, ele chama `POST http://localhost:3000/api/revalidate` para a loja refletir na hora.
