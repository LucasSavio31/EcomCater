"""Testes do módulo `products` — CRUD, variações, listagem/filtros, busca, reviews."""
from __future__ import annotations

import pytest


async def _mk_category(client, h, name="Feminino", parent_id=None):
    body = {"name": name}
    if parent_id:
        body["parent_id"] = parent_id
    return (await client.post("/api/admin/categories", json=body, headers=h)).json()


async def _mk_product(client, h, cat_id, name="Vestido Longo Floral", price=12990, status="active"):
    r = await client.post(
        "/api/admin/products",
        json={"name": name, "category_id": cat_id, "price_cents": price, "status": status},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_product_crud_and_slug(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])
    assert p["slug"] == "vestido-longo-floral"

    detail = await client.get(f"/api/products/{p['slug']}")
    assert detail.status_code == 200
    assert detail.json()["price_cents"] == 12990
    # o breadcrumb traz a cadeia de categorias (o front prefixa "Início");
    # não há mais um item "Home" repetido vindo da API.
    assert detail.json()["breadcrumb"][0]["name"] == "Feminino"


@pytest.mark.asyncio
async def test_draft_not_public(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"], name="Rascunho", status="draft")
    assert (await client.get(f"/api/products/{p['slug']}")).status_code == 404


@pytest.mark.asyncio
async def test_variants_and_size_option(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])

    ot = await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "Numeração", "is_size": True, "values": [{"value": "38"}, {"value": "40"}]}],
        headers=h,
    )
    assert ot.status_code == 200

    detail = await client.get(f"/api/products/{p['slug']}")
    val_ids = [v["id"] for v in detail.json()["option_types"][0]["values"]]

    v1 = await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "VLF-38", "option_value_ids": [val_ids[0]], "stock_qty": 5},
        headers=h,
    )
    assert v1.status_code == 201
    v2 = await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "VLF-40", "option_value_ids": [val_ids[1]], "stock_qty": 0},
        headers=h,
    )
    assert v2.status_code == 201

    detail = (await client.get(f"/api/products/{p['slug']}")).json()
    stock = {v["sku"]: v["in_stock"] for v in detail["variants"]}
    assert stock == {"VLF-38": True, "VLF-40": False}


@pytest.mark.asyncio
async def test_duplicate_sku_rejected(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])
    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "Cor", "values": [{"value": "Preto"}]}],
        headers=h,
    )
    vid = (await client.get(f"/api/products/{p['slug']}")).json()["option_types"][0]["values"][0]["id"]
    a = await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "DUP", "option_value_ids": [vid], "stock_qty": 1},
        headers=h,
    )
    assert a.status_code == 201
    b = await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "DUP", "option_value_ids": [vid], "stock_qty": 1},
        headers=h,
    )
    assert b.status_code == 409


@pytest.mark.asyncio
async def test_list_by_category_and_price_filter(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    top = await _mk_category(client, h, "Masculino")
    sub = await _mk_category(client, h, "Camisetas", parent_id=top["id"])
    await _mk_product(client, h, sub["id"], name="Camiseta Barata", price=5000)
    await _mk_product(client, h, sub["id"], name="Camiseta Cara", price=20000)

    all_in_top = await client.get("/api/products", params={"category": "masculino"})
    assert all_in_top.status_code == 200
    assert all_in_top.json()["total"] == 2  # inclui subcategoria

    cheap = await client.get(
        "/api/products", params={"category": "masculino/camisetas", "price_max": 9999}
    )
    names = [i["name"] for i in cheap.json()["items"]]
    assert names == ["Camiseta Barata"]


@pytest.mark.asyncio
async def test_list_by_ambiguous_slug_prefers_top_level_path(client, admin_token, auth_headers):
    """Quando o mesmo slug existe no topo e como subcategoria (ex.: 'botas'),
    `?category=botas` tem que resolver o do TOPO (match por path), não o filho."""
    h = auth_headers(admin_token)
    top_botas = await _mk_category(client, h, "Botas")
    masc = await _mk_category(client, h, "Masculino")
    sub_botas = await _mk_category(client, h, "Botas", parent_id=masc["id"])
    assert sub_botas["path"] == "masculino/botas"

    # produto cuja categoria principal é a subcategoria, mas com a do topo como extra
    r = await client.post(
        "/api/admin/products",
        json={
            "name": "Coturno Teste",
            "category_id": sub_botas["id"],
            "extra_category_ids": [top_botas["id"]],
            "price_cents": 9990,
            "status": "active",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text

    top = await client.get("/api/products", params={"category": "botas"})
    assert top.status_code == 200
    assert [i["name"] for i in top.json()["items"]] == ["Coturno Teste"]

    child = await client.get("/api/products", params={"category": "masculino/botas"})
    assert [i["name"] for i in child.json()["items"]] == ["Coturno Teste"]


@pytest.mark.asyncio
async def test_home_sections_deterministic_by_seed(client, admin_token, auth_headers, db):
    from app.modules.products import service

    h = auth_headers(admin_token)
    fem = await _mk_category(client, h, "Feminino")
    fem_tenis = await _mk_category(client, h, "Tênis", parent_id=fem["id"])
    for i in range(10):
        await _mk_product(client, h, fem_tenis["id"], name=f"TENIS {i:02d}", price=1000 + i)

    a = await service.home_sections(db, seed=2026090310)
    b = await service.home_sections(db, seed=2026090310)
    c = await service.home_sections(db, seed=2026090311)

    assert [p["id"] for p in a["mais_buscados"]] == [p["id"] for p in b["mais_buscados"]]
    assert len(a["tenis"]) == 8 and len(a["feminino"]) == 4
    # troca de hora (seed) muda a ordem de pelo menos um bloco
    assert [p["id"] for p in a["mais_buscados"]] != [p["id"] for p in c["mais_buscados"]]


@pytest.mark.asyncio
async def test_home_sections_one_product_per_model(client, admin_token, auth_headers, db):
    """Mesmo modelo em várias cores (color_group_id) entra 1x só no bloco."""
    from app.modules.products import service

    h = auth_headers(admin_token)
    cat = await _mk_category(client, h, "Tênis")
    ids = []
    for cor in ("Preto", "Branco", "Azul"):
        p = await _mk_product(client, h, cat["id"], name=f"TENIS 900 {cor}", price=9990)
        ids.append(p["id"])
    # liga os três como irmãos de cor
    await client.put(
        f"/api/admin/products/{ids[0]}/color-group",
        json={"color_name": "Preto", "sibling_ids": ids[1:]},
        headers=h,
    )
    # mais um modelo, cor única
    solo = await _mk_product(client, h, cat["id"], name="TENIS 901 Verde", price=9990)

    res = await service.home_sections(db, seed=2026090312)
    # "mais_buscados" nunca repete modelo
    names = [p["name"] for p in res["mais_buscados"]]
    modelos = [n.split()[1] for n in names if n.startswith("TENIS 90")]
    assert modelos.count("900") == 1  # só um dos 3 irmãos
    assert "TENIS 901 Verde" in names
    assert len(names) == len(set(names))
    # "tenis" PODE repetir modelo (cores do mesmo) pra completar a contagem
    tnames = [p["name"] for p in res["tenis"]]
    assert len(tnames) == 4  # 3 cores do 900 + o 901

    # endpoint público responde com as três chaves
    res = await client.get("/api/products/home-sections")
    assert res.status_code == 200
    assert set(res.json()) == {"mais_buscados", "tenis", "feminino"}


@pytest.mark.asyncio
async def test_related_products_excludes_own_model_and_dedupes(client, admin_token, auth_headers, db):
    """'Você também pode gostar': nunca repete modelo, nem o do produto na tela."""
    import uuid as _uuid

    from app.modules.products import service
    from app.modules.products.models import Product

    h = auth_headers(admin_token)
    cat = await _mk_category(client, h, "Tênis")

    own_ids = [
        (await _mk_product(client, h, cat["id"], name=f"TENIS 700 {cor}", price=9990))["id"]
        for cor in ("Preto", "Branco", "Azul")
    ]
    await client.put(
        f"/api/admin/products/{own_ids[0]}/color-group",
        json={"color_name": "Preto", "sibling_ids": own_ids[1:]},
        headers=h,
    )
    await _mk_product(client, h, cat["id"], name="TENIS 701 Verde", price=9990)
    other_ids = [
        (await _mk_product(client, h, cat["id"], name=f"TENIS 702 {cor}", price=9990))["id"]
        for cor in ("Cinza", "Bege")
    ]
    await client.put(
        f"/api/admin/products/{other_ids[0]}/color-group",
        json={"color_name": "Cinza", "sibling_ids": other_ids[1:]},
        headers=h,
    )

    product = await db.get(Product, _uuid.UUID(own_ids[0]))
    related = await service.related_products(db, product, limit=10)
    names = [r["name"] for r in related]

    assert not any(n.startswith("TENIS 700") for n in names)  # não recomenda o próprio modelo
    assert "TENIS 701 Verde" in names
    assert sum(n.startswith("TENIS 702") for n in names) == 1  # 1 das 2 cores do 702
    assert len(names) == len(set(names))


@pytest.mark.asyncio
async def test_related_products_hourly_stable_and_reshuffles(client, admin_token, auth_headers, db):
    import uuid as _uuid
    from datetime import UTC, datetime

    from app.modules.products import service
    from app.modules.products.models import Product

    h = auth_headers(admin_token)
    cat = await _mk_category(client, h, "Tênis")
    for i in range(12):
        await _mk_product(client, h, cat["id"], name=f"TENIS {800 + i} Cor", price=9990)
    viewer = await _mk_product(client, h, cat["id"], name="TENIS 999 Base", price=9990)
    product = await db.get(Product, _uuid.UUID(viewer["id"]))

    hour1 = datetime(2026, 9, 4, 10, tzinfo=UTC)
    hour2 = datetime(2026, 9, 4, 11, tzinfo=UTC)
    a = await service.related_products(db, product, limit=10, now=hour1)
    b = await service.related_products(db, product, limit=10, now=hour1)
    c = await service.related_products(db, product, limit=10, now=hour2)

    assert len(a) == 10
    assert [r["id"] for r in a] == [r["id"] for r in b]  # mesma hora -> mesma lista
    assert [r["id"] for r in a] != [r["id"] for r in c]  # hora seguinte -> re-sorteia


@pytest.mark.asyncio
async def test_related_products_endpoint_on_pdp(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h, "Tênis")
    ids = []
    for cor in ("Preto", "Branco"):
        p = await _mk_product(client, h, cat["id"], name=f"TENIS 600 {cor}", price=9990)
        ids.append(p["id"])
    await client.put(
        f"/api/admin/products/{ids[0]}/color-group",
        json={"color_name": "Preto", "sibling_ids": ids[1:]},
        headers=h,
    )
    for i in range(3):
        await _mk_product(client, h, cat["id"], name=f"TENIS {601 + i} Único", price=9990)

    slug = (await client.get(f"/api/admin/products/{ids[0]}", headers=h)).json()["slug"]
    detail = (await client.get(f"/api/products/{slug}")).json()
    related_names = [r["name"] for r in detail["related"]]
    assert not any(n.startswith("TENIS 600") for n in related_names)
    assert len(related_names) == len(set(related_names))
    assert len(related_names) <= 10


@pytest.mark.asyncio
async def test_search_fuzzy(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    await _mk_product(client, h, cat["id"], name="Vestido Midi Preto")
    res = await client.get("/api/products/search", params={"q": "vestid"})
    assert res.status_code == 200
    assert any(r["type"] == "product" and "Vestido" in r["name"] for r in res.json())


@pytest.mark.asyncio
async def test_review_flow(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])

    # avaliação exige cliente autenticado
    anon = await client.post(
        f"/api/products/{p['slug']}/reviews",
        json={"rating": 5, "title": "Amei", "body": "Perfeito"},
    )
    assert anon.status_code == 401

    reg = await client.post(
        "/api/customers/auth/register",
        json={"full_name": "Maria", "email": "maria@test.example", "password": "clientsecret1"},
    )
    ch = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    r = await client.post(
        f"/api/products/{p['slug']}/reviews",
        json={"rating": 5, "title": "Amei", "body": "Perfeito"},
        headers=ch,
    )
    assert r.status_code == 201, r.text
    review_id = r.json()["id"]

    # ainda não aparece (pending)
    detail = (await client.get(f"/api/products/{p['slug']}")).json()
    assert detail["reviews"] == []
    assert detail["rating_count"] == 0

    mod = await client.post(
        f"/api/admin/products/{p['id']}/reviews/{review_id}/moderate",
        json={"status": "approved"},
        headers=h,
    )
    assert mod.status_code == 200

    detail = (await client.get(f"/api/products/{p['slug']}")).json()
    assert detail["rating_count"] == 1
    assert detail["rating_avg"] == 5.0
