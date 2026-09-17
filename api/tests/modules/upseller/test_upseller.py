"""Testes do módulo `upseller`: credenciais/gate e sincronização de estoque
(mockando o cliente HTTP -- nunca bate na rede real deles)."""
from __future__ import annotations

import pytest

from app.modules.upseller.client import UpSellerClient


@pytest.fixture
async def variant(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = (await client.post("/api/admin/categories", json={"name": "C"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Item", "category_id": cat["id"], "price_cents": 7000, "status": "active"},
            headers=h,
        )
    ).json()
    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "T", "values": [{"value": "U"}]}],
        headers=h,
    )
    vid = (await client.get(f"/api/products/{p['slug']}")).json()["option_types"][0]["values"][0]["id"]
    v = (
        await client.post(
            f"/api/admin/products/{p['id']}/variants",
            json={"sku": "IT-U", "option_value_ids": [vid], "stock_qty": 5},
            headers=h,
        )
    ).json()
    return {"product_id": p["id"], "variant_id": v["id"], "slug": p["slug"]}


@pytest.mark.asyncio
async def test_state_requires_admin(client):
    r = await client.get("/api/admin/upseller")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_initial_state_not_connected(client, admin_token, auth_headers):
    r = await client.get("/api/admin/upseller", headers=auth_headers(admin_token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["connected"] is False
    assert data["stock_sync_enabled"] is True


@pytest.mark.asyncio
async def test_save_credentials(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.put(
        "/api/admin/upseller/credentials",
        json={"client_id": "cid-1", "api_token": "tok-1"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["connected"] is True
    assert r.json()["has_api_token"] is True


@pytest.mark.asyncio
async def test_connection_test_endpoint(client, admin_token, auth_headers, monkeypatch):
    h = auth_headers(admin_token)
    await client.put(
        "/api/admin/upseller/credentials", json={"client_id": "c", "api_token": "t"}, headers=h
    )

    async def fake_list_warehouses(self, *, page_no=1, page_size=50):
        assert self.client_id == "c"
        assert self.api_token == "t"
        return {"list": [{"warehouseId": "1", "warehouseName": "Principal"}], "total": 1}

    monkeypatch.setattr(UpSellerClient, "list_warehouses", fake_list_warehouses)
    r = await client.post("/api/admin/upseller/test", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert "1 arma" in r.json()["message"]


@pytest.mark.asyncio
async def test_connection_test_surfaces_error(client, admin_token, auth_headers, monkeypatch):
    from app.modules.upseller.client import UpSellerError

    h = auth_headers(admin_token)
    await client.put(
        "/api/admin/upseller/credentials", json={"client_id": "c", "api_token": "wrong"}, headers=h
    )

    async def fake_list_warehouses(self, *, page_no=1, page_size=50):
        raise UpSellerError("credencial inválida")

    monkeypatch.setattr(UpSellerClient, "list_warehouses", fake_list_warehouses)
    r = await client.post("/api/admin/upseller/test", headers=h)
    assert r.status_code == 200
    assert r.json() == {"ok": False, "message": "credencial inválida"}


@pytest.mark.asyncio
async def test_sync_updates_matching_sku_stock(client, admin_token, auth_headers, variant, monkeypatch):
    h = auth_headers(admin_token)
    await client.put(
        "/api/admin/upseller/credentials", json={"client_id": "c", "api_token": "t"}, headers=h
    )

    async def fake_all_warehouses(self):
        return [{"warehouseId": "1", "warehouseName": "A"}, {"warehouseId": "2", "warehouseName": "B"}]

    async def fake_all_warehouse_skus(self, warehouse_id):
        if warehouse_id == "1":
            return [{"skuId": "IT-U", "quantity": 30}, {"skuId": "SEM-CORRESPONDENCIA", "quantity": 9}]
        return [{"skuId": "IT-U", "quantity": 12}]  # soma entre depósitos: 30+12=42

    monkeypatch.setattr(UpSellerClient, "all_warehouses", fake_all_warehouses)
    monkeypatch.setattr(UpSellerClient, "all_warehouse_skus", fake_all_warehouse_skus)

    r = await client.post("/api/admin/upseller/sync", headers=h)
    assert r.status_code == 200, r.text
    assert r.json() == {"skus_found": 2, "variants_updated": 1}

    pdp = (await client.get(f"/api/products/{variant['slug']}")).json()
    assert pdp["variants"][0]["stock_qty"] == 42

    state = (await client.get("/api/admin/upseller", headers=h)).json()
    assert state["last_sync_summary"] == "2 SKU(s) na UP Seller, 1 atualizado(s) na loja"
    assert state["last_sync_at"]


@pytest.mark.asyncio
async def test_sync_requires_credentials(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.post("/api/admin/upseller/sync", headers=h)
    assert r.status_code == 400, r.text
