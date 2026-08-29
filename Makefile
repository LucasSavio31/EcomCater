# Atalhos de desenvolvimento. Requer Docker Compose v2.
COMPOSE = docker compose

.PHONY: help up down build logs ps restart \
        migrate makemigration downgrade seed \
        api-sh db-sh redis-sh \
        test test-api lint fmt clean

help:
	@echo "up            - sobe todo o stack de dev"
	@echo "down          - derruba o stack"
	@echo "build         - rebuild das imagens"
	@echo "logs          - segue os logs de todos os serviços"
	@echo "migrate       - aplica migrations Alembic (head)"
	@echo "makemigration - gera migration autogenerate (m=\"mensagem\")"
	@echo "downgrade     - desfaz última migration"
	@echo "seed          - roda o seed inicial (admin, tema, menus, modules)"
	@echo "test          - roda a suíte de testes da API"
	@echo "lint / fmt    - ruff + mypy / formatação"

up:
	$(COMPOSE) up -d --build
	@echo "API   -> http://localhost:8000/docs"
	@echo "Loja  -> http://localhost:3000"
	@echo "Admin -> http://localhost:3001/administracao"
	@echo "Mail  -> http://localhost:8025"

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

restart:
	$(COMPOSE) restart $(s)

migrate:
	$(COMPOSE) run --rm api alembic upgrade head

makemigration:
	$(COMPOSE) run --rm api alembic revision --autogenerate -m "$(m)"

downgrade:
	$(COMPOSE) run --rm api alembic downgrade -1

seed:
	$(COMPOSE) run --rm api python -m app.seed.run

seed-catalog:
	$(COMPOSE) run --rm api python -m app.seed.run --catalog

api-sh:
	$(COMPOSE) exec api bash

db-sh:
	$(COMPOSE) exec db psql -U $${POSTGRES_USER:-ecom} -d $${POSTGRES_DB:-ecom}

redis-sh:
	$(COMPOSE) exec redis redis-cli

test test-api:
	$(COMPOSE) run --rm -e API_ENV=test api pytest -q

lint:
	$(COMPOSE) run --rm api ruff check . && $(COMPOSE) run --rm api mypy app

fmt:
	$(COMPOSE) run --rm api ruff format .

clean:
	$(COMPOSE) down -v
