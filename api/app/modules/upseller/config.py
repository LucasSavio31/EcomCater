"""Configuração persistida do módulo `upseller` (em `modules.config_json`,
mesmo padrão de Frete/Pagamento)."""
from __future__ import annotations

from pydantic import BaseModel


class UpSellerConfig(BaseModel):
    client_id: str = ""
    api_token: str = ""
    # estoque UP Seller -> loja é 1 via só (não existe API deles pra pedido,
    # só leitura de armazém/SKU) -- ligado por padrão quando há credencial.
    stock_sync_enabled: bool = True
    last_sync_at: str = ""  # ISO 8601
    last_sync_summary: str = ""
