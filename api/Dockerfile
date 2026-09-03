# syntax=docker/dockerfile:1
# ---------- base ----------
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false
WORKDIR /app
# - postgresql-client-16 (pg_dump/pg_restore, repo PGDG) p/ backup/restauração
# - libpango/harfbuzz + fontes (Liberation ~= Arial) p/ o WeasyPrint gerar a
#   fatura em PDF (HTML+CSS -> PDF, sem browser)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl ca-certificates gnupg \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8 \
        fonts-liberation fonts-dejavu-core \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install poetry poetry-plugin-export \
    && poetry export -f requirements.txt --output requirements.txt --without-hashes --with dev \
    && pip install -r requirements.txt

# ---------- dev ----------
FROM base AS dev
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------- prod ----------
FROM base AS prod
# remove toolchain de build para imagem menor
RUN apt-get purge -y build-essential && apt-get autoremove -y
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
