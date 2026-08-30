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
    melhor_envio_token: str = ""          # sobrescreve o .env quando preenchido
    melhor_envio_sandbox: bool = True
    webhook_token: str = ""               # querystring ?token= no webhook
    default_package: DefaultPackage = Field(default_factory=DefaultPackage)
    free_shipping_services: list[str] = []
    # Frete grátis para tudo: o checkout não calcula frete e vai direto ao pagamento
    free_shipping_all: bool = False
    # Frete grátis automático quando o subtotal do pedido atinge este valor
    # (em centavos). None/0 = desligado.
    free_shipping_min_cents: int | None = None
