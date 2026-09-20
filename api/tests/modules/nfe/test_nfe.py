"""Testes do módulo `nfe`: config/certificado (super_admin), rascunho, emissão
(SEFAZ mockada), download de XML/DANFE, cancelamento."""
from __future__ import annotations

import datetime
import io

import pytest
import pytest_asyncio

VALID_CPF = "52998224725"  # CPF de teste clássico (válido nos dígitos verificadores)

ADDRESS = {
    "recipient_name": "Cliente Teste",
    "zip": "01001000",
    "street": "Praça da Sé",
    "number": "1",
    "district": "Sé",
    "city": "São Paulo",
    "state": "SP",
}


def _make_test_pfx(cn: str = "LOJA TESTE LTDA:12345678000199", *, expired: bool = False) -> bytes:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    now = datetime.datetime.now(datetime.UTC)
    not_before = now - datetime.timedelta(days=400) if expired else now
    not_after = now - datetime.timedelta(days=1) if expired else now + datetime.timedelta(days=365)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        name=b"teste",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(b"senha123"),
    )


@pytest_asyncio.fixture
async def staff_token(client, db) -> str:
    from app.core.security import hash_password
    from app.modules.admin.models import AdminUser

    db.add(
        AdminUser(
            email="staff-nfe@test.example",
            name="Staff",
            password_hash=hash_password("supersecret1"),
            role="admin",
            must_change_password=False,
        )
    )
    await db.commit()
    r = await client.post(
        "/api/admin/auth/login", json={"email": "staff-nfe@test.example", "password": "supersecret1"}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def test_pfx() -> bytes:
    return _make_test_pfx()


async def _setup_store_settings(client, headers) -> None:
    r = await client.put(
        "/api/admin/settings",
        json={
            "legal_name": "Loja Teste LTDA",
            "cnpj": "12345678000199",
            "ie": "123456789",
            "regime_tributario": "1",
            "cnae_fiscal": "4791100",
            "address_json": {
                "street": "Rua da Loja",
                "number": "500",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "zip": "01001000",
            },
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text


async def _make_product_with_fiscal(client, headers) -> tuple[str, str]:
    cat = (await client.post("/api/admin/categories", json={"name": "Cat NFe"}, headers=headers)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={
                "name": "Produto NFe",
                "category_id": cat["id"],
                "price_cents": 19990,
                "status": "active",
                "ncm": "64041100",
                "cfop": "5102",
                "csosn_cst": "102",
                "origem": "0",
                "unidade": "UN",
            },
            headers=headers,
        )
    ).json()
    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "T", "values": [{"value": "U"}]}],
        headers=headers,
    )
    vid = (await client.get(f"/api/products/{p['slug']}")).json()["option_types"][0]["values"][0]["id"]
    v = (
        await client.post(
            f"/api/admin/products/{p['id']}/variants",
            json={"sku": "NFE-U", "option_value_ids": [vid], "stock_qty": 10},
            headers=headers,
        )
    ).json()
    return p["id"], v["id"]


async def _make_order(client, variant_id: str) -> str:
    await client.post("/api/cart/items", json={"variant_id": variant_id, "quantity": 1})
    r = await client.post(
        "/api/orders/checkout", json={"email": "cliente@test.example", "shipping_address": ADDRESS}
    )
    assert r.status_code == 201, r.text
    return r.json()["number"]


@pytest.mark.asyncio
async def test_config_requires_super_admin(client, staff_token, auth_headers):
    r = await client.get("/api/admin/nfe/config", headers=auth_headers(staff_token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_config_get_put_masks_secret(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.get("/api/admin/nfe/config", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["certificado_senha"] == ""
    assert r.json()["certificado_configurado"] is False

    r = await client.put("/api/admin/nfe/config", json={"serie_nfe": 2, "proximo_numero": 10}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["serie_nfe"] == 2
    assert r.json()["proximo_numero"] == 10


@pytest.mark.asyncio
async def test_certificate_upload_happy_path(client, admin_token, auth_headers, test_pfx):
    h = auth_headers(admin_token)
    files = {"file": ("cert.pfx", test_pfx, "application/x-pkcs12")}
    r = await client.post(
        "/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["certificado_configurado"] is True
    assert "LOJA TESTE LTDA" in data["certificado_titular"]
    assert data["certificado_senha"] == "•••• configurado"


@pytest.mark.asyncio
async def test_certificate_upload_wrong_password(client, admin_token, auth_headers, test_pfx):
    h = auth_headers(admin_token)
    files = {"file": ("cert.pfx", test_pfx, "application/x-pkcs12")}
    r = await client.post(
        "/api/admin/nfe/config/certificate", files=files, data={"senha": "senha-errada"}, headers=h
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_certificate_upload_expired_rejected(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    expired_pfx = _make_test_pfx(expired=True)
    files = {"file": ("cert.pfx", expired_pfx, "application/x-pkcs12")}
    r = await client.post(
        "/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h
    )
    assert r.status_code == 422, r.text
    assert "vencido" in r.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_draft_requires_editor_role(client, staff_token, auth_headers):
    r = await client.get("/api/admin/nfe/orders/NAOEXISTE/draft", headers=auth_headers(staff_token))
    # staff (admin/staff role) é aceito pelo gate -- 404 é o esperado (pedido não existe), não 403
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_build_draft_from_real_order(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + number, json={"cpf": VALID_CPF}, headers=h)

    r = await client.get(f"/api/admin/nfe/orders/{number}/draft", headers=h)
    assert r.status_code == 200, r.text
    draft = r.json()
    assert draft["emitente"]["cnpj"] == "12345678000199"
    assert draft["emitente"]["endereco"]["codigo_municipio"] == "3550308"  # São Paulo
    assert draft["destinatario"]["cpf"] == VALID_CPF
    assert draft["destinatario"]["endereco"]["codigo_municipio"] == "3550308"
    assert len(draft["itens"]) == 1
    assert draft["itens"][0]["ncm"] == "64041100"
    assert draft["totais"]["valor_total_cents"] == draft["pagamento"]["valor_cents"]


@pytest.mark.asyncio
async def test_emit_without_certificate_fails_clearly(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + number, json={"cpf": VALID_CPF}, headers=h)
    draft = (await client.get(f"/api/admin/nfe/orders/{number}/draft", headers=h)).json()

    r = await client.post(f"/api/admin/nfe/orders/{number}", json=draft, headers=h)
    assert r.status_code == 422, r.text
    assert "certificado" in r.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_emit_authorize_download_cancel_flow(
    client, db, admin_token, auth_headers, test_pfx, monkeypatch
):
    from app.modules.nfe.sefaz_client import SefazClient, SefazResultado

    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + number, json={"cpf": VALID_CPF}, headers=h)

    files = {"file": ("cert.pfx", test_pfx, "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    def fake_enviar(self, edoc_dataclass, doc_id):
        # devolve o XML real (serializado, sem assinatura de verdade) pra
        # exercitar a geração do DANFE de ponta a ponta, não um placeholder.
        from xsdata.formats.dataclass.serializers import XmlSerializer
        from xsdata.formats.dataclass.serializers.config import SerializerConfig

        serializer = XmlSerializer(config=SerializerConfig(xml_declaration=False))
        xml_bytes = serializer.render(edoc_dataclass).encode("utf-8")
        return (
            SefazResultado(
                ok=True, codigo_status="103", motivo="Lote recebido com sucesso",
                numero_recibo="123456789012345",
            ),
            xml_bytes,
        )

    monkeypatch.setattr(SefazClient, "enviar", fake_enviar)

    draft = (await client.get(f"/api/admin/nfe/orders/{number}/draft", headers=h)).json()
    r = await client.post(f"/api/admin/nfe/orders/{number}", json=draft, headers=h)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["status"] == "processing"
    assert doc["chave_acesso"] and len(doc["chave_acesso"]) == 44

    r = await client.get(f"/api/admin/nfe/orders/{number}", headers=h)
    assert r.json()["status"] == "processing"

    # DANFE/XML ainda não existem -- 404 claro, não 500
    assert (await client.get(f"/api/admin/nfe/orders/{number}/xml", headers=h)).status_code == 200
    assert (await client.get(f"/api/admin/nfe/orders/{number}/danfe", headers=h)).status_code == 404

    # simula a SEFAZ autorizando no poll seguinte (chamado direto -- mesmo
    # trabalho que o scheduler faria, sem depender de tempo real no teste)
    def fake_consultar_recibo(self, numero_recibo):
        return SefazResultado(
            ok=True, codigo_status="100", motivo="Autorizado o uso da NF-e",
            numero_protocolo="135260000000001",
        )

    monkeypatch.setattr(SefazClient, "consultar_recibo", fake_consultar_recibo)

    from app.modules.nfe import service

    avancados = await service.poll_pending(db)
    await db.commit()
    assert avancados == 1

    r = await client.get(f"/api/admin/nfe/orders/{number}", headers=h)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["status"] == "authorized"
    assert doc["protocolo_autorizacao"] == "135260000000001"
    assert doc["has_xml"] is True
    assert doc["has_danfe"] is True

    r = await client.get(f"/api/admin/nfe/orders/{number}/xml", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")

    r = await client.get(f"/api/admin/nfe/orders/{number}/danfe", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"

    def fake_cancelar(self, *, chave, protocolo, justificativa):
        return SefazResultado(ok=True, codigo_status="135", motivo="Evento registrado e vinculado a NF-e")

    monkeypatch.setattr(SefazClient, "cancelar", fake_cancelar)

    r = await client.post(
        f"/api/admin/nfe/orders/{number}/cancel",
        json={"justificativa": "Cliente desistiu da compra"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_cancel_requires_justificativa_min_length(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    r = await client.post(f"/api/admin/nfe/orders/{number}/cancel", json={"justificativa": "curta"}, headers=h)
    assert r.status_code in (400, 422)


# ------------------------------------------------ lote (seleção múltipla)

async def _emit_authorized(client, h, db, monkeypatch, number: str) -> None:
    """Emite e autoriza uma NF-e de teste pra um pedido -- helper pros testes
    em lote, que precisam de pedidos já com NF-e autorizada."""
    from app.modules.nfe.sefaz_client import SefazClient, SefazResultado

    def fake_enviar(self, edoc_dataclass, doc_id):
        from xsdata.formats.dataclass.serializers import XmlSerializer
        from xsdata.formats.dataclass.serializers.config import SerializerConfig

        serializer = XmlSerializer(config=SerializerConfig(xml_declaration=False))
        xml_bytes = serializer.render(edoc_dataclass).encode("utf-8")
        return (
            SefazResultado(ok=True, codigo_status="103", motivo="Lote recebido", numero_recibo="1"),
            xml_bytes,
        )

    def fake_consultar_recibo(self, numero_recibo):
        return SefazResultado(ok=True, codigo_status="100", motivo="Autorizado", numero_protocolo="135000000001")

    monkeypatch.setattr(SefazClient, "enviar", fake_enviar)
    monkeypatch.setattr(SefazClient, "consultar_recibo", fake_consultar_recibo)

    draft = (await client.get(f"/api/admin/nfe/orders/{number}/draft", headers=h)).json()
    r = await client.post(f"/api/admin/nfe/orders/{number}", json=draft, headers=h)
    assert r.status_code == 200, r.text

    from app.modules.nfe import service

    avancados = await service.poll_pending(db)
    await db.commit()
    assert avancados == 1


@pytest.mark.asyncio
async def test_status_map_batch(client, admin_token, auth_headers, db, monkeypatch):
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid1 = await _make_product_with_fiscal(client, h)
    n1 = await _make_order(client, vid1)
    await client.patch("/api/admin/orders/" + n1, json={"cpf": VALID_CPF}, headers=h)
    await _emit_authorized(client, h, db, monkeypatch, n1)

    n2 = await _make_order(client, vid1)  # sem NF-e nenhuma

    r = await client.post("/api/admin/nfe/status-map", json={"numbers": [n1, n2, "NAOEXISTE"]}, headers=h)
    assert r.status_code == 200, r.text
    results = {item.get("order_number", "NAOEXISTE"): item for item in r.json()["results"]}
    assert results[n1]["status"] == "authorized"
    assert results[n2]["status"] == "none"
    assert results["NAOEXISTE"]["status"] == "none"


@pytest.mark.asyncio
async def test_bulk_emit_partial_failure(client, admin_token, auth_headers, monkeypatch):
    from app.modules.nfe.sefaz_client import SefazClient, SefazResultado

    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid = await _make_product_with_fiscal(client, h)
    n1 = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + n1, json={"cpf": VALID_CPF}, headers=h)

    def fake_enviar(self, edoc_dataclass, doc_id):
        return (
            SefazResultado(ok=True, codigo_status="103", motivo="Lote recebido", numero_recibo="1"),
            b"<xml/>",
        )

    monkeypatch.setattr(SefazClient, "enviar", fake_enviar)

    r = await client.post("/api/admin/nfe/bulk-emit", json={"numbers": [n1, "NAOEXISTE"]}, headers=h)
    assert r.status_code == 200, r.text
    results = {item["number"]: item for item in r.json()["results"]}
    assert results[n1]["ok"] is True
    assert results["NAOEXISTE"]["ok"] is False


@pytest.mark.asyncio
async def test_bulk_danfe_merges_and_reports_skipped(client, admin_token, auth_headers, db, monkeypatch):
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid = await _make_product_with_fiscal(client, h)
    n1 = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + n1, json={"cpf": VALID_CPF}, headers=h)
    await _emit_authorized(client, h, db, monkeypatch, n1)

    n2 = await _make_order(client, vid)  # sem NF-e -- deve ficar de fora, sem quebrar o lote

    r = await client.get(f"/api/admin/nfe/bulk-danfe?numbers={n1},{n2}", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers.get("x-nfe-skipped") == n2

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(r.content))
    assert len(reader.pages) >= 1


@pytest.mark.asyncio
async def test_mini_danfe_single_order(client, admin_token, auth_headers, db, monkeypatch):
    """DANFE Simplificado – Etiqueta (NT 2020.004), 10x15 -- o layout
    alternativo pra impressora térmica pedido pelo usuário."""
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + number, json={"cpf": VALID_CPF}, headers=h)
    await _emit_authorized(client, h, db, monkeypatch, number)

    r = await client.get(f"/api/admin/nfe/orders/{number}/mini-danfe", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(r.content))
    assert len(reader.pages) == 1
    page = reader.pages[0]
    # 100x150mm em pontos (1mm = 2.8346pt) -- confere que é mesmo formato etiqueta, não A4
    assert round(float(page.mediabox.width) / 2.8346) == 100
    assert round(float(page.mediabox.height) / 2.8346) == 150


@pytest.mark.asyncio
async def test_export_month_zip(client, admin_token, auth_headers, db, monkeypatch):
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + number, json={"cpf": VALID_CPF}, headers=h)
    await _emit_authorized(client, h, db, monkeypatch, number)

    now = datetime.datetime.now(datetime.UTC)
    r = await client.get(f"/api/admin/nfe/export-month?year={now.year}&month={now.month}", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"

    import zipfile

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert len(names) == 1
    assert names[0].endswith("-nfe.xml")


@pytest.mark.asyncio
async def test_export_month_empty_returns_404(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.get("/api/admin/nfe/export-month?year=2020&month=1", headers=h)
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_bulk_danfe_mini_layout(client, admin_token, auth_headers, db, monkeypatch):
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + number, json={"cpf": VALID_CPF}, headers=h)
    await _emit_authorized(client, h, db, monkeypatch, number)

    r = await client.get(f"/api/admin/nfe/bulk-danfe?numbers={number}&mini=true", headers=h)
    assert r.status_code == 200, r.text
    assert "etiquetas-nfe.pdf" in r.headers["content-disposition"]


@pytest.mark.asyncio
async def test_bulk_danfe_all_skipped_returns_error(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)

    r = await client.get(f"/api/admin/nfe/bulk-danfe?numbers={number}", headers=auth_headers(admin_token))
    assert r.status_code == 422, r.text


# ------------------------------------------------ listagem (todas as NF-e)


async def _emit_rejected(client, h, number: str, monkeypatch) -> None:
    """Emite uma NF-e que a SEFAZ recusa de cara (sem precisar de poll)."""
    from app.modules.nfe.sefaz_client import SefazClient, SefazResultado

    def fake_enviar(self, edoc_dataclass, doc_id):
        from xsdata.formats.dataclass.serializers import XmlSerializer
        from xsdata.formats.dataclass.serializers.config import SerializerConfig

        serializer = XmlSerializer(config=SerializerConfig(xml_declaration=False))
        xml_bytes = serializer.render(edoc_dataclass).encode("utf-8")
        return (
            SefazResultado(ok=False, codigo_status="225", motivo="Rejeição: CNPJ do emitente inválido"),
            xml_bytes,
        )

    monkeypatch.setattr(SefazClient, "enviar", fake_enviar)
    await client.patch("/api/admin/orders/" + number, json={"cpf": VALID_CPF}, headers=h)
    draft = (await client.get(f"/api/admin/nfe/orders/{number}/draft", headers=h)).json()
    r = await client.post(f"/api/admin/nfe/orders/{number}", json=draft, headers=h)
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_documents_list_and_detail(client, admin_token, auth_headers, db, monkeypatch):
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + number, json={"cpf": VALID_CPF}, headers=h)
    await _emit_authorized(client, h, db, monkeypatch, number)

    r = await client.get("/api/admin/nfe/documents", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 10
    item = body["items"][0]
    assert item["order_number"] == number
    assert item["status"] == "authorized"
    assert item["total_cents"] > 0
    assert item["natureza_operacao"]
    assert item["destinatario_nome"]

    r2 = await client.get(f"/api/admin/nfe/documents/{item['id']}", headers=h)
    assert r2.status_code == 200, r2.text
    assert r2.json()["chave_acesso"] == item["chave_acesso"]


@pytest.mark.asyncio
async def test_documents_list_invalid_page_size_falls_back_to_10(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.get("/api/admin/nfe/documents?page_size=999", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["page_size"] == 10


@pytest.mark.asyncio
async def test_document_detail_not_found(client, admin_token, auth_headers):
    import uuid

    h = auth_headers(admin_token)
    r = await client.get(f"/api/admin/nfe/documents/{uuid.uuid4()}", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_document_delete_blocked_when_authorized(client, admin_token, auth_headers, db, monkeypatch):
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + number, json={"cpf": VALID_CPF}, headers=h)
    await _emit_authorized(client, h, db, monkeypatch, number)

    doc_id = (await client.get("/api/admin/nfe/documents", headers=h)).json()["items"][0]["id"]
    r = await client.delete(f"/api/admin/nfe/documents/{doc_id}", headers=h)
    assert r.status_code in (400, 422), r.text

    still_there = await client.get(f"/api/admin/nfe/documents/{doc_id}", headers=h)
    assert still_there.status_code == 200


@pytest.mark.asyncio
async def test_document_delete_allowed_when_rejected(client, admin_token, auth_headers, monkeypatch):
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await _emit_rejected(client, h, number, monkeypatch)

    doc_id = (await client.get("/api/admin/nfe/documents", headers=h)).json()["items"][0]["id"]
    assert (await client.get(f"/api/admin/nfe/documents/{doc_id}", headers=h)).json()["status"] == "rejected"

    r = await client.delete(f"/api/admin/nfe/documents/{doc_id}", headers=h)
    assert r.status_code == 200, r.text
    assert (await client.get(f"/api/admin/nfe/documents/{doc_id}", headers=h)).status_code == 404


@pytest.mark.asyncio
async def test_document_cancel_via_id_shows_reason_and_justificativa(
    client, admin_token, auth_headers, db, monkeypatch
):
    from app.modules.nfe.sefaz_client import SefazClient, SefazResultado

    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + number, json={"cpf": VALID_CPF}, headers=h)
    await _emit_authorized(client, h, db, monkeypatch, number)
    doc_id = (await client.get("/api/admin/nfe/documents", headers=h)).json()["items"][0]["id"]

    def fake_cancelar(self, *, chave, protocolo, justificativa):
        return SefazResultado(ok=True, codigo_status="135", motivo="Evento registrado e vinculado a NF-e")

    monkeypatch.setattr(SefazClient, "cancelar", fake_cancelar)
    r = await client.post(
        f"/api/admin/nfe/documents/{doc_id}/cancel",
        json={"justificativa": "Cancelamento solicitado pelo cliente via suporte"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "canceled"
    assert body["cancel_justificativa"] == "Cancelamento solicitado pelo cliente via suporte"


@pytest.mark.asyncio
async def test_document_email_requires_authorized(client, admin_token, auth_headers, monkeypatch):
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await _emit_rejected(client, h, number, monkeypatch)
    doc_id = (await client.get("/api/admin/nfe/documents", headers=h)).json()["items"][0]["id"]

    r = await client.post(
        f"/api/admin/nfe/documents/{doc_id}/email", json={"to": "contador@test.example"}, headers=h
    )
    assert r.status_code in (400, 422), r.text


@pytest.mark.asyncio
async def test_document_email_sends_with_attachment(client, admin_token, auth_headers, db, monkeypatch):
    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    _pid, vid = await _make_product_with_fiscal(client, h)
    number = await _make_order(client, vid)
    await client.patch("/api/admin/orders/" + number, json={"cpf": VALID_CPF}, headers=h)
    await _emit_authorized(client, h, db, monkeypatch, number)
    doc_id = (await client.get("/api/admin/nfe/documents", headers=h)).json()["items"][0]["id"]

    r = await client.post(
        f"/api/admin/nfe/documents/{doc_id}/email",
        json={"to": "contador@test.example", "mini": False},
        headers=h,
    )
    assert r.status_code == 200, r.text

    from sqlalchemy import select as _select

    from app.modules.admin.models import EmailLog

    rows = list(await db.scalars(_select(EmailLog).where(EmailLog.template == "nfe_document")))
    assert len(rows) == 1
    assert rows[0].to_email == "contador@test.example"


# ------------------------------------------------ teste de conexão


@pytest.mark.asyncio
async def test_test_connection_requires_super_admin(client, staff_token, auth_headers):
    h = auth_headers(staff_token)
    r = await client.get("/api/admin/nfe/test-connection", headers=h)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_test_connection_without_certificate_fails_clearly(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.get("/api/admin/nfe/test-connection", headers=h)
    assert r.status_code in (400, 422)


@pytest.mark.asyncio
async def test_test_connection_reports_ok_and_reports_failure_reason(client, admin_token, auth_headers, monkeypatch):
    from app.modules.nfe.sefaz_client import SefazClient, SefazResultado

    h = auth_headers(admin_token)
    await _setup_store_settings(client, h)
    files = {"file": ("cert.pfx", _make_test_pfx(), "application/x-pkcs12")}
    await client.post("/api/admin/nfe/config/certificate", files=files, data={"senha": "senha123"}, headers=h)

    monkeypatch.setattr(
        SefazClient, "status", lambda self: SefazResultado(ok=True, codigo_status="107", motivo="Serviço em Operação")
    )
    r = await client.get("/api/admin/nfe/test-connection", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert r.json()["codigo_status"] == "107"

    monkeypatch.setattr(
        SefazClient, "status", lambda self: SefazResultado(ok=False, codigo_status="108", motivo="Serviço Paralisado")
    )
    r2 = await client.get("/api/admin/nfe/test-connection", headers=h)
    assert r2.status_code == 200, r2.text
    assert r2.json()["ok"] is False
    assert "Paralisado" in r2.json()["motivo"]
