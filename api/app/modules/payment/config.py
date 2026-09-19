"""Config persistida do módulo `payment` (em `modules.config_json`).

Dois eixos separados, de propósito (pedido do usuário): `providers` --
credenciais e liga/desliga de CADA provedor (AppMax, Fake, ...) -- e
`method_providers` -- qual provedor ativo atende cada método de pagamento
(cartão/pix/boleto). Adicionar um provedor novo não mexe em qual método usa
o quê; trocar quem atende um método não mexe nas credenciais de ninguém.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderEntry(BaseModel):
    enabled: bool = False
    # campos próprios do provedor (ex.: access_token/sandbox/webhook_secret
    # do AppMax) -- genérico de propósito, cada provedor usa as chaves que
    # precisa; quem interpreta é `service._build_gateway`.
    config: dict = Field(default_factory=dict)


class PaymentConfig(BaseModel):
    providers: dict[str, ProviderEntry] = Field(
        default_factory=lambda: {
            "appmax": ProviderEntry(enabled=True),
            "fake": ProviderEntry(enabled=True),
        }
    )
    # método -> slug do provedor que atende (ausente = método desligado)
    method_providers: dict[str, str] = Field(
        default_factory=lambda: {"credit_card": "appmax", "pix": "appmax", "boleto": "appmax"}
    )
    max_installments: int = 12
