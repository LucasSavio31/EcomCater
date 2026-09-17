"""Configuração persistida do módulo `domains` (em `modules.config_json`).

Credenciais de automação — controlam o servidor de verdade (vhost, SSL, DNS),
por isso ficam restritas a `super_admin` no router. Sem criptografia em
repouso, mesmo padrão já usado hoje por `shipping`/`payment`.
"""
from __future__ import annotations

from pydantic import BaseModel


class DomainsConfig(BaseModel):
    # aaPanel — painel da VPS (Configurações → API)
    aapanel_url: str = ""            # ex.: http://127.0.0.1:7800
    aapanel_api_key: str = ""
    # Cloudflare — API Token com permissão só "Zone / DNS / Edit", restrito à zona
    cloudflare_api_token: str = ""
    # IP público da VPS, usado nas instruções de DNS (registro A)
    server_ip: str = ""
