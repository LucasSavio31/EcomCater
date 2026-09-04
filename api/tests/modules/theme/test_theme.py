"""Tema: opção de borda do botão "Comprar" (loja) e dos botões do checkout."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_button_border_colors_roundtrip(client, admin_token, auth_headers):
    h = auth_headers(admin_token)

    got = (await client.get("/api/admin/theme", headers=h)).json()
    # padrão = igual ao fundo (borda invisível)
    assert got["button_border_color"] == got["button_bg_color"]
    assert got["checkout_button_border_color"] == got["checkout_button_color"]
    assert got["checkout_step_button_border_color"] == got["checkout_step_button_color"]

    r = await client.put(
        "/api/admin/theme",
        json={
            "button_border_color": "#FF0000",
            "checkout_button_border_color": "#00FF00",
            "checkout_step_button_border_color": "#0000FF",
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["button_border_color"] == "#FF0000"
    assert body["checkout_button_border_color"] == "#00FF00"
    assert body["checkout_step_button_border_color"] == "#0000FF"

    # a loja pública também reflete (mesmo endpoint que o front consome)
    public = (await client.get("/api/theme")).json()
    assert public["button_border_color"] == "#FF0000"
    assert public["checkout_button_border_color"] == "#00FF00"
    assert public["checkout_step_button_border_color"] == "#0000FF"


@pytest.mark.asyncio
async def test_button_border_color_rejects_invalid_hex(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.put("/api/admin/theme", json={"button_border_color": "not-a-color"}, headers=h)
    assert r.status_code == 422, r.text
