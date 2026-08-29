"""Config persistida do módulo `payment` (em `modules.config_json`)."""
from __future__ import annotations

from pydantic import BaseModel


class MethodsEnabled(BaseModel):
    credit_card: bool = True
    pix: bool = True
    boleto: bool = True


class PaymentConfig(BaseModel):
    active_provider: str = "appmax"          # appmax | fake
    appmax_access_token: str = ""            # sobrescreve o .env quando preenchido
    appmax_sandbox: bool = True
    appmax_webhook_secret: str = ""
    methods: MethodsEnabled = MethodsEnabled()
    max_installments: int = 12
