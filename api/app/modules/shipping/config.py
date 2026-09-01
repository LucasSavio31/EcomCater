"""Configuração persistida do módulo `shipping` (em `modules.config_json`)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class DefaultPackage(BaseModel):
    weight_grams: int = 300
    length_mm: int = 200
    width_mm: int = 150
    height_mm: int = 100


class ShippingConfig(BaseModel):
    active_provider: str = "melhor_envio"
    origin_zip: str = "01001000"
    melhor_envio_token: str = ""          # access_token (JWT) — sobrescreve o .env
    melhor_envio_sandbox: bool = True
    webhook_token: str = ""               # querystring ?token= no webhook
    # CPF do responsável pelo envio (obrigatório p/ gerar etiqueta no ME)
    sender_cpf: str = ""
    # Impressão de etiquetas: "termica_10x15" (1/página) ou "a4_4up" (4/página A4)
    label_format: str = "termica_10x15"
    # Anexar a Declaração de Conteúdo depois de cada etiqueta
    print_declaration: bool = False
    # De quantos em quantos segundos a rotina consulta a API do Melhor Envio
    # para atualizar rastreio/status. 0 = usa o padrão do servidor. Mínimo 120 s.
    me_poll_interval_seconds: int = 0

    # OAuth do Melhor Envio (fluxo "Conectar" no admin)
    melhor_envio_client_id: str = ""
    melhor_envio_client_secret: str = ""
    melhor_envio_refresh_token: str = ""
    melhor_envio_token_expires_at: str = ""   # ISO 8601; vazio = desconhecido
    melhor_envio_oauth_state: str = ""        # CSRF do fluxo em andamento
    melhor_envio_oauth_state_at: str = ""     # ISO 8601 de quando o state foi criado
    default_package: DefaultPackage = Field(default_factory=DefaultPackage)
    # Serviços oferecidos ao cliente (nomes normalizados, minúsculas). Padrão: só Correios.
    allowed_services: list[str] = Field(default_factory=lambda: ["pac", "sedex"])
    free_shipping_services: list[str] = []
    # Frete grátis para tudo: o checkout não calcula frete e vai direto ao pagamento
    free_shipping_all: bool = False
    # Frete grátis automático quando o subtotal do pedido atinge este valor
    # (em centavos). None/0 = desligado.
    free_shipping_min_cents: int | None = None
