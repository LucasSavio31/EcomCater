"""Testes do módulo `categories` — árvore, slug/path, reorder, regras de exclusão."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_tree_and_paths(client, admin_token, auth_headers):
    h = auth_headers(admin_token)

    fem = await client.post("/api/admin/categories", json={"name": "Feminino"}, headers=h)
    assert fem.status_code == 201, fem.text
    fem_id = fem.json()["id"]
    assert fem.json()["slug"] == "feminino"
    assert fem.json()["path"] == "feminino"

    vest = await client.post(
        "/api/admin/categories",
        json={"name": "Vestidos", "parent_id": fem_id},
        headers=h,
    )
    assert vest.status_code == 201
    assert vest.json()["path"] == "feminino/vestidos"

    tree = await client.get("/api/categories/tree")
    assert tree.status_code == 200
    roots = tree.json()
    assert roots[0]["slug"] == "feminino"
    assert roots[0]["children"][0]["slug"] == "vestidos"


@pytest.mark.asyncio
async def test_rename_repaths_children(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    a = (await client.post("/api/admin/categories", json={"name": "Pai"}, headers=h)).json()
    b = (
        await client.post(
            "/api/admin/categories", json={"name": "Filho", "parent_id": a["id"]}, headers=h
        )
    ).json()
    assert b["path"] == "pai/filho"

    r = await client.patch(
        f"/api/admin/categories/{a['id']}", json={"name": "Pai Renomeado"}, headers=h
    )
    assert r.status_code == 200
    assert r.json()["path"] == "pai-renomeado"

    child = await client.get(f"/api/admin/categories/{b['id']}", headers=h)
    assert child.json()["path"] == "pai-renomeado/filho"


@pytest.mark.asyncio
async def test_slug_uniqueness_per_parent(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    await client.post("/api/admin/categories", json={"name": "Calçados"}, headers=h)
    second = await client.post("/api/admin/categories", json={"name": "Calçados"}, headers=h)
    assert second.status_code == 201
    assert second.json()["slug"] == "calcados-2"


@pytest.mark.asyncio
async def test_cannot_delete_category_with_children(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    a = (await client.post("/api/admin/categories", json={"name": "ComFilho"}, headers=h)).json()
    await client.post(
        "/api/admin/categories", json={"name": "F", "parent_id": a["id"]}, headers=h
    )
    r = await client.delete(f"/api/admin/categories/{a['id']}", headers=h)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_move_into_own_subtree_rejected(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    a = (await client.post("/api/admin/categories", json={"name": "A"}, headers=h)).json()
    b = (
        await client.post("/api/admin/categories", json={"name": "B", "parent_id": a["id"]}, headers=h)
    ).json()
    r = await client.patch(
        f"/api/admin/categories/{a['id']}", json={"parent_id": b["id"]}, headers=h
    )
    assert r.status_code == 422
