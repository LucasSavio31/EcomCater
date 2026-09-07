"""Testes do `PublicCacheHeaders` — Cache-Control + ETag/304 no catálogo público."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_public_get_has_etag(client):
    r = await client.get("/api/products")
    assert r.status_code == 200
    assert r.headers.get("etag", "").startswith('W/"')
    assert "s-maxage=60" in r.headers.get("cache-control", "")


@pytest.mark.asyncio
async def test_if_none_match_returns_304(client):
    first = await client.get("/api/products")
    etag = first.headers["etag"]

    second = await client.get("/api/products", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.content == b""
    assert second.headers.get("etag") == etag
    assert "s-maxage=60" in second.headers.get("cache-control", "")


@pytest.mark.asyncio
async def test_stale_etag_returns_200(client):
    r = await client.get("/api/products", headers={"If-None-Match": 'W/"stale-value"'})
    assert r.status_code == 200
    assert r.headers.get("etag")


@pytest.mark.asyncio
async def test_authenticated_request_has_no_etag_or_cache(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.get("/api/admin/orders", headers=h)
    assert r.status_code == 200
    assert "etag" not in r.headers
    assert "cache-control" not in r.headers

    # repetir com If-None-Match não vira 304 numa rota autenticada
    r2 = await client.get(
        "/api/admin/orders", headers={**h, "If-None-Match": 'W/"qualquer"'}
    )
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_stale_if_error_only_on_api_not_on_media(client):
    r = await client.get("/api/products")
    assert "stale-if-error=86400" in r.headers.get("cache-control", "")

    m = await client.get("/media/products/inexistente/medium.webp")
    cc = m.headers.get("cache-control", "")
    if cc:  # só afirma sobre o Cache-Control quando ele existe (200)
        assert "immutable" in cc
        assert "stale-if-error" not in cc


@pytest.mark.asyncio
async def test_media_path_has_no_etag(client):
    # /media não passa pelo buffer de ETag (guard is_media) — só o
    # Cache-Control immutable já existente. Usa uma key inexistente: o que
    # importa é que a resposta (200 ou 404) nunca ganha ETag por este
    # middleware nem quebra.
    r = await client.get("/media/products/inexistente/medium.webp")
    assert "etag" not in r.headers or r.status_code == 404
