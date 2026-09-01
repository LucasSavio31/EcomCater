-- Extensões exigidas pelo schema (busca fuzzy e tipos).
-- Roda automaticamente no 1º boot do container Postgres.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- busca textual sem acento ("acucar" == "açúcar"); a migration 0054 também
-- a cria, isto é só uma rede de segurança para o 1º boot.
CREATE EXTENSION IF NOT EXISTS unaccent;
