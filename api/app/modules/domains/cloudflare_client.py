"""Cliente da API v4 da Cloudflare — cria/atualiza registros DNS.

Auth: Bearer token (API Token escopado a `Zone / DNS / Edit`, restrito à
zona do domínio — não a Global API Key). Docs:
https://developers.cloudflare.com/api/
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("domains.cloudflare")

_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareError(RuntimeError):
    pass


class CloudflareClient:
    def __init__(self, *, api_token: str) -> None:
        self.api_token = api_token

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        if not self.api_token:
            raise CloudflareError("Cloudflare não configurada: informe o token no admin.")
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                resp = await c.request(method, f"{_BASE}{path}", headers=headers, **kwargs)
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Cloudflare indisponível: %s", exc)
            raise CloudflareError("Falha de comunicação com a Cloudflare.") from exc
        if not data.get("success"):
            errors = data.get("errors") or []
            msg = errors[0].get("message") if errors else "Cloudflare recusou a operação."
            raise CloudflareError(str(msg))
        return data

    async def verify_token(self) -> None:
        """Endpoint dedicado da Cloudflare pra validar um API Token."""
        data = await self._request("GET", "/user/tokens/verify")
        if (data.get("result") or {}).get("status") != "active":
            raise CloudflareError("Token da Cloudflare inválido ou inativo.")

    async def find_zone(self, hostname: str) -> dict | None:
        """Zona (domínio raiz) que contém `hostname`, ou None se a conta não a gerencia.
        Retorna `{id, status, name_servers}` — `status` vira "active" só depois
        que os nameservers apontados no registrador propagam."""
        data = await self._request("GET", "/zones", params={"name": hostname})
        result = data.get("result") or []
        if not result:
            return None
        z = result[0]
        return {"id": z["id"], "status": z["status"], "name_servers": z.get("name_servers") or []}

    async def create_zone(self, hostname: str) -> dict:
        """Cria a zona na conta Cloudflare — a API já devolve os nameservers
        que a Cloudflare atribuiu pra esse domínio (a gente só exibe, nunca
        configura o registrador por fora — isso é sempre manual, em outro
        provedor)."""
        data = await self._request(
            "POST", "/zones", json={"name": hostname, "jump_start": False}
        )
        z = data.get("result") or {}
        return {"id": z["id"], "status": z["status"], "name_servers": z.get("name_servers") or []}

    async def get_zone_status(self, zone_id: str) -> str:
        data = await self._request("GET", f"/zones/{zone_id}")
        return (data.get("result") or {}).get("status", "pending")

    async def set_cache_rules(self, *, zone_id: str, rules: list[dict]) -> None:
        """Substitui por inteiro o ruleset de cache (fase
        `http_request_cache_settings`) da zona pelo `rules` dado — idempotente,
        não precisa gerenciar ID de regra individual. Requer a permissão
        `Zone / Cache Rules / Edit` no token (além de `Zone / DNS / Edit`)."""
        await self._request(
            "PUT",
            f"/zones/{zone_id}/rulesets/phases/http_request_cache_settings/entrypoint",
            json={"rules": rules},
        )

    async def upsert_dns_record(
        self, *, zone_id: str, name: str, record_type: str, content: str, proxied: bool = True
    ) -> None:
        existing = await self._request(
            "GET",
            f"/zones/{zone_id}/dns_records",
            params={"type": record_type, "name": name},
        )
        results = existing.get("result") or []
        payload = {"type": record_type, "name": name, "content": content, "proxied": proxied, "ttl": 1}
        if results:
            record_id = results[0]["id"]
            await self._request("PUT", f"/zones/{zone_id}/dns_records/{record_id}", json=payload)
        else:
            await self._request("POST", f"/zones/{zone_id}/dns_records", json=payload)
