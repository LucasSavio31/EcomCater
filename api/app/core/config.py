"""Configuração central — lê tudo de variáveis de ambiente (nunca hardcode)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # ambiente
    api_env: str = "dev"

    # postgres
    postgres_user: str = "ecom"
    postgres_password: str = "ecom-local-dev"
    postgres_db: str = "ecom"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # redis
    redis_url: str = "redis://redis:6379/0"

    # cache de leitura (catálogo/tema/menus) em Redis — best-effort
    cache_enabled: bool = True

    # segurança
    api_secret_key: str = "dev-secret-troque-em-producao"
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_seconds: int = 1_209_600
    jwt_algorithm: str = "HS256"

    # cors / urls
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    public_api_url: str = "http://localhost:8000"
    site_url: str = "http://localhost:3000"
    admin_url: str = "http://localhost:3001/administracao"
    # segredo p/ o API chamar o POST /api/revalidate da loja (Next). Vazio = liberado.
    revalidate_secret: str = ""
    # token para o cron externo disparar o envio de recuperação de carrinho
    recovery_cron_token: str = "dev-recovery-token"
    # agendador interno da recuperação de carrinho (roda no processo da API)
    recovery_scheduler_enabled: bool = True
    recovery_scheduler_interval_seconds: int = 300
    # fila de reenvio de e-mail (SMTP offline não bloqueia a compra)
    email_retry_enabled: bool = True
    email_retry_interval_seconds: int = 120
    # token para o cron externo disparar o backup agendado
    system_cron_token: str = "dev-system-token"

    # backup / sistema
    backup_dir: str = "./.data/backups"
    # diretório dos binários do Postgres (pg_dump/pg_restore). Vazio = usa o PATH.
    pg_bin_dir: str = ""
    # fuso da loja — usado pelo agendador de backup (a "hora" é local, não UTC)
    store_timezone: str = "America/Sao_Paulo"
    # agendador interno de backup (roda no processo da API; além do cron externo)
    backup_scheduler_enabled: bool = True
    backup_scheduler_interval_seconds: int = 600

    # sincronização automática de rastreio com o Melhor Envio (roda no processo da API)
    me_poll_enabled: bool = True
    me_poll_interval_seconds: int = 900

    # amostra de saúde dos serviços gravada a cada janela de 15 min, mesmo com
    # ninguém olhando o painel (roda no processo da API)
    health_scheduler_enabled: bool = True

    # resumo diário por e-mail para o admin (pedidos, faturamento, saúde)
    daily_digest_enabled: bool = True
    daily_digest_hour: int = 20  # hora local da loja

    # seed admin
    admin_email: str = "admin@loja.local"
    admin_password: str = "admin12345"
    admin_name: str = "Administrador"

    # storage
    storage_backend: str = "local"
    storage_local_dir: str = "/data/media"
    media_base_url: str = "http://localhost:8000/media"

    # imagem
    image_webp_quality: int = 82
    image_thumb_size: int = 150
    image_medium_size: int = 600
    image_zoom_size: int = 1600

    # rate limit
    rate_limit_default: str = "120/minute"

    # pagamento appmax
    appmax_api_url: str = "https://homolog.sandboxappmax.com.br/api/v3"
    appmax_access_token: str = ""
    appmax_webhook_secret: str = ""

    # frete melhor envio
    melhor_envio_api_url: str = "https://sandbox.melhorenvio.com.br"
    melhor_envio_token: str = ""
    melhor_envio_user_agent: str = "Loja (contato@loja.local)"
    shipping_origin_zip: str = "01001000"
    shipping_quote_cache_ttl: int = 3600

    # smtp fallback
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    smtp_from_email: str = "loja@loja.local"
    smtp_from_name: str = "Minha Loja"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Usado pelo Alembic."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.api_env == "prod"

    def assert_prod_secrets(self) -> None:
        """Em produção, recusa subir com segredos/tokens ainda no valor de dev."""
        if not self.is_prod:
            return
        weak = {
            "API_SECRET_KEY": self.api_secret_key == "dev-secret-troque-em-producao",
            "RECOVERY_CRON_TOKEN": self.recovery_cron_token == "dev-recovery-token",
            "SYSTEM_CRON_TOKEN": self.system_cron_token == "dev-system-token",
            "ADMIN_PASSWORD": self.admin_password in ("admin12345", "admin"),
        }
        bad = [k for k, is_weak in weak.items() if is_weak]
        if bad:
            raise RuntimeError(
                "API_ENV=prod com segredos padrão de desenvolvimento: "
                + ", ".join(bad)
                + ". Defina valores fortes no .env antes de subir."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
