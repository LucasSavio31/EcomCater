-- Extensões exigidas pelo schema (busca fuzzy e tipos).
-- Roda automaticamente no 1º boot do container Postgres.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
