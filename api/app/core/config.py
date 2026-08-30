"""Configuração central — lê tudo de variáveis de ambiente (nunca hardcode)."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
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
    # token para o cron externo disparar o envio de recuperação de carrinho
    recovery_cron_token: str = "dev-recovery-token"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
