"""Orquestração do módulo `nfe`: config, certificado, rascunho, emissão,
consulta de status e cancelamento."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.modules.nfe.certificate import inspect_pfx
from app.modules.nfe.config import NfeConfig
from app.modules.nfe.mapping import build_draft as _build_draft
from app.modules.nfe.mapping import build_xml
from app.modules.nfe.models import NfeDocument
from app.modules.orders.models import Order

logger = logging.getLogger("nfe.service")

_CERT_STORAGE_KEY = "nfe/certificado.pfx"


# --------------------------------------------------------------- config
async def load_config(db: AsyncSession) -> NfeConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "nfe")
    raw = dict(row.config_json) if row and row.config_json else {}
    return NfeConfig(**raw)


async def save_config(db: AsyncSession, patch: dict) -> NfeConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "nfe")
    current = dict(row.config_json) if row and row.config_json else {}
    for k, v in patch.items():
        if v is not None:
            current[k] = v
    cfg = NfeConfig(**current)
    if row is None:
        row = ModuleRow(slug="nfe", enabled=True, config_json=cfg.model_dump())
        db.add(row)
    else:
        row.config_json = cfg.model_dump()
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return cfg


async def upload_certificate(db: AsyncSession, pfx_bytes: bytes, senha: str) -> NfeConfig:
    from app.shared.storage import private_storage

    info = inspect_pfx(pfx_bytes, senha)
    if info.is_expired:
        raise ValidationError(f"Certificado vencido em {info.validade_iso} — envie um certificado válido.")
    private_storage.save(_CERT_STORAGE_KEY, pfx_bytes)
    return await save_config(
        db,
        {
            "certificado_storage_key": _CERT_STORAGE_KEY,
            "certificado_senha": senha,
            "certificado_validade": info.validade_iso,
            "certificado_titular": info.titular,
        },
    )


async def _load_order_context(db: AsyncSession, order: Order):
    from app.modules.admin.models import StoreSettings
    from app.modules.payment.models import Payment
    from app.modules.products.models import Product

    store = await db.get(StoreSettings, 1)
    if store is None:
        raise ValidationError("Dados da loja não configurados — preencha em Aparência antes de emitir NF-e.")
    payment = await db.scalar(
        select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
    )
    product_ids = [i.product_id for i in order.items if i.product_id]
    products = {}
    if product_ids:
        rows = await db.scalars(select(Product).where(Product.id.in_(product_ids)))
        products = {p.id: p for p in rows}
    return store, payment, products


# --------------------------------------------------------------- rascunho
async def build_draft(db: AsyncSession, order: Order) -> dict:
    store, payment, products = await _load_order_context(db, order)
    cfg = await load_config(db)
    return _build_draft(order=order, store=store, cfg=cfg, payment=payment, products_by_id=products)


# --------------------------------------------------------------- consulta
async def latest_for_order(db: AsyncSession, order_id: uuid.UUID) -> NfeDocument | None:
    return await db.scalar(
        select(NfeDocument)
        .where(NfeDocument.order_id == order_id)
        .order_by(NfeDocument.created_at.desc())
        .limit(1)
    )


async def latest_for_order_numbers(db: AsyncSession, numbers: list[str]) -> dict[str, NfeDocument]:
    """Última `NfeDocument` de cada número de pedido, numa única consulta
    (pro status em lote na listagem de pedidos, sem um SELECT por linha)."""
    if not numbers:
        return {}
    rows = list(
        await db.scalars(
            select(NfeDocument)
            .where(NfeDocument.order_number.in_(numbers))
            .order_by(NfeDocument.order_number, NfeDocument.created_at.desc())
        )
    )
    latest: dict[str, NfeDocument] = {}
    for doc in rows:
        latest.setdefault(doc.order_number, doc)  # primeira ocorrência = mais recente (já ordenado)
    return latest


async def _get_certificate(cfg: NfeConfig) -> bytes:
    from app.shared.storage import private_storage

    if not cfg.certificado_storage_key:
        raise ValidationError("Certificado digital não cadastrado — envie o arquivo .pfx em NF-e → Configuração.")
    return private_storage.read(cfg.certificado_storage_key)


def _uf_cuf(uf: str) -> int:
    from app.modules.nfe.mapping import UF_TO_CUF

    cuf = UF_TO_CUF.get(uf.upper())
    if cuf is None:
        raise ValidationError(f"UF do emitente inválida: {uf}")
    return cuf


# --------------------------------------------------------------- emissão
async def request_emission(
    db: AsyncSession, order: Order, payload: dict, admin_id: uuid.UUID | None
) -> NfeDocument:
    from app.modules.nfe.sefaz_client import SefazClient, SefazError

    cfg = await load_config(db)
    pfx_bytes = await _get_certificate(cfg)
    cuf = _uf_cuf(payload["emitente"]["endereco"]["uf"])

    try:
        edoc, chave = build_xml(payload)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    doc = NfeDocument(
        order_id=order.id,
        order_number=order.number,
        status="processing",
        ambiente=payload["ambiente"],
        numero=payload["numero"],
        serie=payload["serie"],
        chave_acesso=chave,
        total_cents=payload["totais"]["valor_total_cents"],
        payload_json=payload,
        requested_by_admin_id=admin_id,
        requested_at=datetime.now(UTC),
    )
    db.add(doc)

    try:
        client = SefazClient(
            pfx_bytes=pfx_bytes,
            senha=cfg.certificado_senha,
            uf=payload["emitente"]["endereco"]["uf"],
            cuf=cuf,
            ambiente=payload["ambiente"],
        )
        # SefazClient é síncrono (zeep/requests, sem suporte async) -- roda
        # numa thread pra não travar o event loop da API enquanto espera a rede.
        resultado, xml_assinado = await asyncio.to_thread(client.enviar, edoc, "NFe" + chave)
    except SefazError as exc:
        doc.status = "error"
        doc.status_message = str(exc)
        await db.flush()
        return doc
    except Exception as exc:  # falha de rede/SOAP inesperada -- não derruba o request
        logger.exception("Falha ao enviar NF-e %s pra SEFAZ", order.number)
        doc.status = "error"
        doc.status_message = f"Falha de comunicação com a SEFAZ: {exc}"
        await db.flush()
        return doc

    from app.shared.storage import private_storage

    xml_key = f"nfe/{order.number}/{chave}.xml"
    private_storage.save(xml_key, xml_assinado)
    doc.xml_key = xml_key

    if not resultado.ok:
        doc.status = "rejected"
        doc.status_message = f"[{resultado.codigo_status}] {resultado.motivo}"
    else:
        doc.recibo = resultado.numero_recibo
        doc.status_message = f"[{resultado.codigo_status}] {resultado.motivo} — aguardando autorização."

    # numeração só avança se de fato saiu pro ar (mesmo que ainda pendente de
    # autorização) -- rejeição/erro de assinatura não consome o número
    if doc.status != "rejected":
        await save_config(db, {"proximo_numero": cfg.proximo_numero + 1})

    await db.flush()
    await _log_event(db, order, "nfe_requested", f"NF-e {chave} enviada — {doc.status_message or doc.status}")
    return doc


async def bulk_emit(db: AsyncSession, order_numbers: list[str], admin_id: uuid.UUID | None) -> list[dict]:
    """Emite vários pedidos de uma vez, sem revisão manual -- monta o
    rascunho automático (mesmo default de `build_draft`) e envia direto.
    Um erro num pedido não derruba os outros; resultado por pedido."""
    from app.modules.orders.service import get_by_number

    results: list[dict] = []
    for number in order_numbers:
        try:
            order = await get_by_number(db, number)
            if not order:
                results.append({"number": number, "ok": False, "message": "Pedido não encontrado."})
                continue
            payload = await build_draft(db, order)
            doc = await request_emission(db, order, payload, admin_id)
            ok = doc.status not in ("rejected", "error")
            results.append(
                {"number": number, "ok": ok, "status": doc.status, "message": doc.status_message}
            )
        except Exception as exc:  # noqa: BLE001 -- um pedido ruim não pode travar o lote
            logger.exception("Falha ao emitir NF-e em lote pro pedido %s", number)
            results.append({"number": number, "ok": False, "message": str(exc)})
    return results


async def poll_pending(db: AsyncSession) -> int:
    """Consulta a SEFAZ pelos documentos ainda em `processing`. Retorna
    quantos avançaram de status (autorizada/rejeitada)."""
    from app.modules.nfe.sefaz_client import SefazClient

    pendentes = list(
        await db.scalars(select(NfeDocument).where(NfeDocument.status == "processing"))
    )
    if not pendentes:
        return 0

    cfg = await load_config(db)
    if not cfg.certificado_storage_key:
        return 0
    pfx_bytes = await _get_certificate(cfg)

    avancados = 0
    for doc in pendentes:
        if not doc.recibo:
            continue
        order = await db.get(Order, doc.order_id)
        if order is None:
            continue
        try:
            client = SefazClient(
                pfx_bytes=pfx_bytes,
                senha=cfg.certificado_senha,
                uf=(doc.payload_json.get("emitente", {}).get("endereco", {}) or {}).get("uf", "SP"),
                cuf=_uf_cuf((doc.payload_json.get("emitente", {}).get("endereco", {}) or {}).get("uf", "SP")),
                ambiente=doc.ambiente,
            )
            resultado = await asyncio.to_thread(client.consultar_recibo, doc.recibo)
        except Exception as exc:
            logger.warning("Falha ao consultar recibo da NF-e %s: %s", doc.order_number, exc)
            continue

        if resultado.codigo_status in ("105", ""):
            continue  # ainda em processamento na SEFAZ

        avancados += 1
        if resultado.ok:
            doc.status = "authorized"
            doc.protocolo_autorizacao = resultado.numero_protocolo
            doc.authorized_at = datetime.now(UTC)
            doc.status_message = f"[{resultado.codigo_status}] {resultado.motivo}"
            await _gerar_danfe(db, doc)
            await _log_event(db, order, "nfe_authorized", f"NF-e {doc.chave_acesso} autorizada.")
        else:
            doc.status = "rejected"
            doc.status_message = f"[{resultado.codigo_status}] {resultado.motivo}"
            await _log_event(db, order, "nfe_rejected", f"NF-e {doc.chave_acesso} rejeitada: {resultado.motivo}")
        await db.flush()
    return avancados


async def _gerar_danfe(db: AsyncSession, doc: NfeDocument) -> None:
    from app.shared.storage import private_storage

    if not doc.xml_key:
        return
    try:
        from brazilfiscalreport.danfe import Danfe

        xml_bytes = private_storage.read(doc.xml_key)
        danfe = Danfe(xml=xml_bytes.decode("utf-8"))
        danfe_bytes = bytes(danfe.output())
        danfe_key = doc.xml_key.rsplit(".", 1)[0] + "_danfe.pdf"
        private_storage.save(danfe_key, danfe_bytes)
        doc.danfe_key = danfe_key
    except Exception:
        logger.exception("Falha ao gerar DANFE da NF-e %s", doc.order_number)


async def get_xml(db: AsyncSession, order_number: str) -> tuple[bytes, str]:
    from app.shared.storage import private_storage

    doc = await db.scalar(
        select(NfeDocument)
        .where(NfeDocument.order_number == order_number, NfeDocument.status.in_(("authorized", "processing")))
        .order_by(NfeDocument.created_at.desc())
        .limit(1)
    )
    if not doc or not doc.xml_key:
        raise NotFoundError("XML da NF-e ainda não disponível.")
    return private_storage.read(doc.xml_key), f"nfe-{order_number}.xml"


async def get_danfe(db: AsyncSession, order_number: str) -> tuple[bytes, str]:
    from app.shared.storage import private_storage

    doc = await db.scalar(
        select(NfeDocument)
        .where(NfeDocument.order_number == order_number, NfeDocument.status == "authorized")
        .order_by(NfeDocument.created_at.desc())
        .limit(1)
    )
    if not doc or not doc.danfe_key:
        raise NotFoundError("DANFE ainda não disponível.")
    return private_storage.read(doc.danfe_key), f"danfe-{order_number}.pdf"


async def get_mini_danfe(db: AsyncSession, order_number: str) -> tuple[bytes, str]:
    """DANFE Simplificado – Etiqueta (NT 2020.004), formato 10x15 pra
    impressora térmica -- gerado na hora a partir do XML já assinado (não
    precisa de um `_key` próprio guardado, é leve montar de novo)."""
    from app.modules.nfe.mini_danfe import build_mini_danfe
    from app.shared.storage import private_storage

    doc = await db.scalar(
        select(NfeDocument)
        .where(NfeDocument.order_number == order_number, NfeDocument.status == "authorized")
        .order_by(NfeDocument.created_at.desc())
        .limit(1)
    )
    if not doc or not doc.xml_key:
        raise NotFoundError("NF-e ainda não autorizada.")
    xml_bytes = private_storage.read(doc.xml_key)
    pdf = build_mini_danfe(xml_bytes, doc.protocolo_autorizacao)
    return pdf, f"etiqueta-nfe-{order_number}.pdf"


async def export_month_zip(db: AsyncSession, year: int, month: int) -> tuple[bytes, str]:
    """Todas as NF-e autorizadas num mês, num .zip só (uma delas por
    arquivo, nome = chave de acesso -- é o formato que o contador espera pra
    escrituração fiscal). O XML já fica guardado no sistema desde a emissão
    (`NfeDocument.xml_key`, no private_storage); isso aqui só agrupa por mês
    pra download, não é um armazenamento novo."""
    import calendar
    import io
    import zipfile

    from app.shared.storage import private_storage

    if not (1 <= month <= 12):
        raise ValidationError("Mês inválido.")
    start = datetime(year, month, 1, tzinfo=UTC)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)

    docs = list(
        await db.scalars(
            select(NfeDocument)
            .where(
                NfeDocument.status == "authorized",
                NfeDocument.authorized_at >= start,
                NfeDocument.authorized_at <= end,
            )
            .order_by(NfeDocument.authorized_at)
        )
    )
    if not docs:
        raise NotFoundError(f"Nenhuma NF-e autorizada em {month:02d}/{year}.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in docs:
            if not doc.xml_key:
                continue
            try:
                xml_bytes = private_storage.read(doc.xml_key)
            except Exception:
                logger.exception("Falha ao ler XML da NF-e %s pro export mensal", doc.order_number)
                continue
            zf.writestr(f"{doc.chave_acesso}-nfe.xml", xml_bytes)

    return buf.getvalue(), f"nfe-{year}-{month:02d}.zip"


async def bulk_danfe_pdf(
    db: AsyncSession, order_numbers: list[str], *, mini: bool = False
) -> tuple[bytes, list[str]]:
    """Junta o DANFE (ou o Simplificado – Etiqueta, se `mini=True`) de vários
    pedidos num PDF só (cada DANFE já é gerado e guardado por separado --
    diferente do PDF de etiquetas do Melhor Envio, que vem pronto combinado
    da API deles; aqui precisa concatenar de verdade). Pedidos sem NF-e
    autorizada são pulados, não erram o lote -- retorna a lista de quem
    ficou de fora pra avisar o admin."""
    import io

    from pypdf import PdfReader, PdfWriter

    from app.modules.nfe.mini_danfe import build_mini_danfe
    from app.shared.storage import private_storage

    latest = await latest_for_order_numbers(db, order_numbers)
    writer = PdfWriter()
    skipped: list[str] = []
    for number in order_numbers:
        doc = latest.get(number)
        if not doc or doc.status != "authorized" or not doc.xml_key:
            skipped.append(number)
            continue
        try:
            if mini:
                xml_bytes = private_storage.read(doc.xml_key)
                pdf_bytes = build_mini_danfe(xml_bytes, doc.protocolo_autorizacao)
            else:
                if not doc.danfe_key:
                    skipped.append(number)
                    continue
                pdf_bytes = private_storage.read(doc.danfe_key)
            writer.append(PdfReader(io.BytesIO(pdf_bytes)))
        except Exception:
            logger.exception("Falha ao ler DANFE do pedido %s pro PDF em lote", number)
            skipped.append(number)

    if len(writer.pages) == 0:
        raise ValidationError("Nenhum dos pedidos selecionados tem NF-e autorizada com DANFE disponível.")

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue(), skipped


# --------------------------------------------------------------- cancelamento
async def cancel(db: AsyncSession, doc: NfeDocument, justificativa: str, admin_id: uuid.UUID | None) -> NfeDocument:
    from app.modules.nfe.sefaz_client import SefazClient

    if doc.status != "authorized":
        raise ValidationError("Só é possível cancelar uma NF-e autorizada.")
    if len(justificativa or "") < 15:
        raise ValidationError("Justificativa precisa ter pelo menos 15 caracteres (exigência da SEFAZ).")
    if not doc.chave_acesso or not doc.protocolo_autorizacao:
        raise ValidationError("NF-e sem chave/protocolo — não é possível cancelar.")

    cfg = await load_config(db)
    pfx_bytes = await _get_certificate(cfg)
    uf = (doc.payload_json.get("emitente", {}).get("endereco", {}) or {}).get("uf", "SP")
    client = SefazClient(pfx_bytes=pfx_bytes, senha=cfg.certificado_senha, uf=uf, cuf=_uf_cuf(uf), ambiente=doc.ambiente)
    resultado = await asyncio.to_thread(
        client.cancelar, chave=doc.chave_acesso, protocolo=doc.protocolo_autorizacao, justificativa=justificativa
    )
    if not resultado.ok:
        raise ValidationError(f"SEFAZ recusou o cancelamento: [{resultado.codigo_status}] {resultado.motivo}")

    doc.status = "canceled"
    doc.canceled_at = datetime.now(UTC)
    doc.cancel_justificativa = justificativa
    await db.flush()

    order = await db.get(Order, doc.order_id)
    if order is not None:
        await _log_event(db, order, "nfe_canceled", f"NF-e {doc.chave_acesso} cancelada: {justificativa}")
    return doc


async def _log_event(db: AsyncSession, order: Order, event_type: str, message: str) -> None:
    from app.modules.orders.models import OrderEvent

    db.add(
        OrderEvent(
            order_id=order.id,
            type=event_type,
            actor_type="admin",
            message=message,
            created_at=datetime.now(UTC),
        )
    )
    await db.flush()
