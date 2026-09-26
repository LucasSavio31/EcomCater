"""Multi-domínio: a mesma loja em vários domínios, cada um independente
(CORS, feed, links de senha) -- e o pedido só ganha `domain_name` informativo."""
from __future__ import annotations

from xml.etree import ElementTree as ET

import pytest

from app.modules.domains import sites
from app.modules.domains.models import STATUS_ACTIVE, STATUS_PENDING, Domain


@pytest.fixture
async def two_domains(db):
    db.add_all([
        Domain(hostname="loja-a.com.br", is_primary=True, status=STATUS_ACTIVE),
        Domain(hostname="loja-b.com.br", is_primary=False, status=STATUS_ACTIVE),
        Domain(hostname="pendente.com.br", is_primary=False, status=STATUS_PENDING),
    ])
    await db.commit()
    sites.invalidate()
    yield
    sites.invalidate()


@pytest.mark.asyncio
async def test_public_sites_lists_only_active(client, two_domains):
    r = await client.get("/api/domains/sites")
    assert r.status_code == 200
    body = r.json()
    assert body == {"primary": "loja-a.com.br", "hosts": ["loja-a.com.br", "loja-b.com.br"]}


@pytest.mark.asyncio
async def test_cors_allows_every_active_domain(client, two_domains):
    for origin in ("https://loja-b.com.br", "https://admin.loja-b.com.br", "https://www.loja-a.com.br"):
        r = await client.options(
            "/api/domains/sites",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )
        assert r.headers.get("access-control-allow-origin") == origin, origin
    for origin in ("https://pendente.com.br", "https://evil.com", "http://loja-b.com.br"):
        r = await client.options(
            "/api/domains/sites",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )
        assert r.headers.get("access-control-allow-origin") != origin, origin


@pytest.mark.asyncio
async def test_site_of_resolves_subdomains():
    sites._cache["hosts"] = frozenset({"loja-b.com.br"})
    try:
        assert sites.site_of("https://api.loja-b.com.br/x") == "loja-b.com.br"
        assert sites.site_of("admin.loja-b.com.br:443") == "loja-b.com.br"
        assert sites.site_of("loja-c.com.br") is None
        assert sites.site_of("127.0.0.1") is None
    finally:
        sites.invalidate()
        sites._cache["hosts"] = frozenset()


@pytest.mark.asyncio
async def test_feed_links_follow_requesting_domain(client, admin_token, auth_headers, two_domains):
    import io

    from PIL import Image

    h = auth_headers(admin_token)
    cat = (await client.post("/api/admin/categories", json={"name": "C"}, headers=h)).json()
    p = (await client.post(
        "/api/admin/products",
        json={"name": "Bota X", "category_id": cat["id"], "price_cents": 1000, "status": "active"},
        headers=h,
    )).json()
    buf = io.BytesIO()
    Image.new("RGB", (50, 50)).save(buf, format="PNG")
    await client.post(
        f"/api/admin/products/{p['id']}/images", files={"file": ("f.png", buf.getvalue(), "image/png")}, headers=h
    )

    r = await client.get("/api/products/feed/google-merchant.xml", headers={"Host": "api.loja-b.com.br"})
    link = ET.fromstring(r.content).find("channel").find("item").find("link").text
    assert link == f"https://loja-b.com.br/produto/{p['slug']}"

    r = await client.get("/api/products/feed/google-merchant.xml", headers={"Host": "api.evil.com"})
    link = ET.fromstring(r.content).find("channel").find("item").find("link").text
    assert "evil.com" not in link  # host desconhecido cai no domínio principal


@pytest.mark.asyncio
async def test_tags_and_seo_are_per_domain(client, admin_token, auth_headers, two_domains):
    """Cada domínio tem as próprias tags/verificação/SEO; um domínio extra
    nunca herda o pixel do principal."""
    h = auth_headers(admin_token)
    r = await client.put(
        "/api/admin/analytics",
        json={"meta_pixel_enabled": True, "meta_pixel_id": "111111111", "seo_title": "Loja A"},
        headers=h,
    )
    assert r.status_code == 200, r.text

    b = (await client.get("/api/analytics/config", params={"site": "loja-b.com.br"})).json()
    assert b["meta_pixel_enabled"] is False and b["meta_pixel_id"] is None
    assert b["seo_title"] is None

    r = await client.put(
        "/api/admin/analytics/sites/loja-b.com.br",
        json={
            "meta_pixel_enabled": True, "meta_pixel_id": "222222222",
            "merchant_center_enabled": True, "merchant_center_verification_code": "codigo-b",
            "seo_title": "Loja B", "seo_noindex": True,
        },
        headers=h,
    )
    assert r.status_code == 200, r.text

    a = (await client.get("/api/analytics/config", params={"site": "loja-a.com.br"})).json()
    b = (await client.get("/api/analytics/config", params={"site": "loja-b.com.br"})).json()
    assert (a["meta_pixel_id"], a["seo_title"], a["seo_noindex"]) == ("111111111", "Loja A", False)
    assert (b["meta_pixel_id"], b["seo_title"], b["seo_noindex"]) == ("222222222", "Loja B", True)
    assert b["merchant_center_verification_code"] == "codigo-b"

    listing = (await client.get("/api/admin/analytics/sites", headers=h)).json()
    by_host = {x["hostname"]: x for x in listing}
    assert listing[0]["is_primary"] is True
    assert by_host["loja-b.com.br"]["seo_urls"]["feed_url"] == (
        "https://api.loja-b.com.br/api/products/feed/google-merchant.xml"
    )
    assert by_host["loja-b.com.br"]["seo_urls"]["sitemap_url"] == "https://loja-b.com.br/sitemap.xml"
    assert by_host["pendente.com.br"]["status"] == "pending"

    # domínio não ativo não pode ser configurado
    r = await client.put("/api/admin/analytics/sites/pendente.com.br", json={"seo_title": "x"}, headers=h)
    assert r.status_code == 404
