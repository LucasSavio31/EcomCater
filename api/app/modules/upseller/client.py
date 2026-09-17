"""Cliente da API própria da UP Seller (`openapi.upseller.com`) -- só
leitura de armazém/estoque, é tudo que a API pública deles documenta hoje
(não existe endpoint de pedidos/produtos publicado).

Fonte: central de ajuda deles, artigo "API e MCP"
(upseller.com/pt/help-doc-article-3398). Confirmado de lá: os 2 endpoints,
método POST, corpo/resposta JSON com envelope `{code, msg, data}`,
paginação por `pageNo`/`pageSize`. **Não confirmado**: o nome exato dos
headers de autenticação -- a doc deles mostra isso como imagem, que não
dá pra ler por aqui. Uso `client-id`/`api-token` (leitura mais direta dos
nomes dos campos "Client ID"/"API Token" do painel deles); se a UP Seller
recusar com 401/403, é o primeiro lugar pra ajustar (`_headers` abaixo).
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("upseller.client")

BASE_URL = "https://openapi.upseller.com/erp/inventory"


class UpSellerError(RuntimeError):
    pass


class UpSellerClient:
    def __init__(self, *, client_id: str, api_token: str) -> None:
        self.client_id = client_id
        self.api_token = api_token

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "client-id": self.client_id,
            "api-token": self.api_token,
        }

    async def _post(self, path: str, body: dict) -> dict:
        url = f"{BASE_URL}/{path.lstrip('/')}"
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                resp = await c.post(url, json=body, headers=self._headers())
        except httpx.HTTPError as exc:
            raise UpSellerError("Não foi possível falar com a UP Seller agora.") from exc
        if resp.status_code >= 400:
            logger.warning("UP Seller %s -> HTTP %s: %s", path, resp.status_code, resp.text[:300])
            raise UpSellerError(f"UP Seller recusou a chamada (HTTP {resp.status_code}).")
        try:
            data = resp.json()
        except ValueError as exc:
            raise UpSellerError("Resposta da UP Seller não é JSON.") from exc
        if data.get("code") not in (0, None):
            raise UpSellerError(str(data.get("msg") or "UP Seller recusou a operação."))
        return data.get("data") or {}

    async def list_warehouses(self, *, page_no: int = 1, page_size: int = 50) -> dict:
        return await self._post(
            "getWarehouseList/v1", {"pageNo": page_no, "pageSize": page_size}
        )

    async def list_warehouse_skus(
        self, *, warehouse_id: str, page_no: int = 1, page_size: int = 100
    ) -> dict:
        return await self._post(
            "pageWarehouseSku/v1",
            {"warehouseId": warehouse_id, "pageNo": page_no, "pageSize": page_size},
        )

    async def all_warehouses(self) -> list[dict]:
        out: list[dict] = []
        page = 1
        while True:
            data = await self.list_warehouses(page_no=page, page_size=100)
            rows = data.get("list") or []
            out.extend(rows)
            if len(rows) < 100 or len(out) >= int(data.get("total") or len(out)):
                break
            page += 1
        return out

    async def all_warehouse_skus(self, warehouse_id: str) -> list[dict]:
        out: list[dict] = []
        page = 1
        while True:
            data = await self.list_warehouse_skus(warehouse_id=warehouse_id, page_no=page, page_size=100)
            rows = data.get("list") or []
            out.extend(rows)
            if len(rows) < 100 or len(out) >= int(data.get("total") or len(out)):
                break
            page += 1
        return out
