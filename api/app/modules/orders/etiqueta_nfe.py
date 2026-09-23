"""Etiqueta de envio + NF-e numa página só ("Gerar Etq/NFe") -- a etiqueta do
Melhor Envio fica INTOCADA (tamanho e conteúdo originais), a tarja da NF-e é
empilhada embaixo dela na MESMA largura (a página fica mais alta pra caber
as duas). Não altera o fluxo de etiqueta comum
(`shipping.service.melhor_envio_labels_pdf`).

Cada página (etiqueta + tarja) já pronta fica em cache no storage privado
por até 6h -- gerar de novo envolve abrir a página do Melhor Envio num
navegador headless (Playwright), então é caro pra pedir toda hora; o cache é
por pedido, então um lote com pedidos já gerados recentemente só renderiza
de verdade os que faltam.
"""
from __future__ import annotations

import io
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

_CACHE_TTL = timedelta(hours=6)


def _cache_key(order_number: str) -> str:
    return f"nfe-label-cache/{order_number}.pdf"


def _cache_meta_key(order_number: str) -> str:
    return f"nfe-label-cache/{order_number}.meta.json"


def _read_cached_page(order_number: str) -> bytes | None:
    from app.shared.storage import private_storage

    meta_key = _cache_meta_key(order_number)
    if not private_storage.exists(meta_key):
        return None
    try:
        meta = json.loads(private_storage.read(meta_key))
        generated_at = datetime.fromisoformat(meta["generated_at"])
        if datetime.now(UTC) - generated_at > _CACHE_TTL:
            return None
        pdf_key = _cache_key(order_number)
        if not private_storage.exists(pdf_key):
            return None
        return private_storage.read(pdf_key)
    except Exception:  # noqa: BLE001 - cache corrompido/formato antigo -- regenera
        return None


def _write_cache(order_number: str, pdf: bytes) -> None:
    from app.shared.storage import private_storage

    private_storage.save(_cache_key(order_number), pdf, content_type="application/pdf")
    meta = json.dumps({"generated_at": datetime.now(UTC).isoformat()}).encode("utf-8")
    private_storage.save(_cache_meta_key(order_number), meta, content_type="application/json")


def _merge_label_with_strip(label_page_pdf: bytes, strip_pdf: bytes) -> bytes:
    """Empilha a tarja da NF-e embaixo da etiqueta do Melhor Envio -- a
    etiqueta fica INTOCADA (tamanho e posição originais), a página só fica
    mais alta pra caber a tarja embaixo, na MESMA largura da etiqueta
    (nunca mais larga nem mais estreita que o box dela)."""
    from pypdf import PdfReader, PdfWriter, Transformation

    label_page = PdfReader(io.BytesIO(label_page_pdf)).pages[0]
    strip_page = PdfReader(io.BytesIO(strip_pdf)).pages[0]

    lw, lh = float(label_page.mediabox.width), float(label_page.mediabox.height)
    sw = float(strip_page.mediabox.width)
    scale = (lw / sw) if sw else 1.0  # tarja escalada pra MESMA largura da etiqueta
    strip_h = float(strip_page.mediabox.height) * scale

    writer = PdfWriter()
    sheet = writer.add_blank_page(width=lw, height=lh + strip_h)
    sheet.merge_transformed_page(label_page, Transformation().translate(0, strip_h))
    sheet.merge_transformed_page(strip_page, Transformation().scale(scale))

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


async def build_etiqueta_nfe_pdf(db: AsyncSession, order_numbers: list[str]) -> bytes:
    """Etiqueta (Melhor Envio, 10x15, intocada) + tarja da NF-e empilhada
    embaixo, uma página por pedido selecionado, na mesma ordem de
    `order_numbers`. Pedidos sem NF-e autorizada saem só com a etiqueta
    (sem tarja) -- nunca bloqueia o download do lote todo por causa de um
    pedido sem nota. Cada página fica em cache por pedido (6h) -- só
    re-renderiza (Playwright) os pedidos que não têm cache válido."""
    from pypdf import PdfReader, PdfWriter

    from app.modules.nfe.label_strip import build_nfe_strip_pdf
    from app.modules.nfe.service import latest_for_order_numbers
    from app.modules.shipping.service import melhor_envio_label_pages_for_nfe_merge
    from app.shared.timez import store_tz

    pages_by_number: dict[str, bytes] = {}
    to_render = []
    for number in order_numbers:
        cached = _read_cached_page(number)
        if cached is not None:
            pages_by_number[number] = cached
        else:
            to_render.append(number)

    if to_render:
        pages_pdf = await melhor_envio_label_pages_for_nfe_merge(db, to_render)
        reader = PdfReader(io.BytesIO(pages_pdf))
        nfe_by_number = await latest_for_order_numbers(db, to_render)

        for i, number in enumerate(to_render):
            if i >= len(reader.pages):
                break  # o ME pode devolver menos páginas se algum pedido falhar no render
            doc = nfe_by_number.get(number)
            if doc and doc.status == "authorized" and doc.chave_acesso:
                emissao = (
                    doc.authorized_at.astimezone(store_tz()).strftime("%d/%m/%Y")
                    if doc.authorized_at
                    else "—"
                )
                strip_pdf = build_nfe_strip_pdf(
                    numero=doc.numero, serie=doc.serie, emissao=emissao, chave=doc.chave_acesso
                )
                label_page_buf = io.BytesIO()
                single = PdfWriter()
                single.add_page(reader.pages[i])
                single.write(label_page_buf)
                page_pdf = _merge_label_with_strip(label_page_buf.getvalue(), strip_pdf)
            else:
                single = PdfWriter()
                single.add_page(reader.pages[i])
                buf = io.BytesIO()
                single.write(buf)
                page_pdf = buf.getvalue()
            pages_by_number[number] = page_pdf
            _write_cache(number, page_pdf)

    writer = PdfWriter()
    for number in order_numbers:
        page_pdf = pages_by_number.get(number)
        if page_pdf is None:
            continue  # pedido falhou no render (etiqueta ainda não pronta no ME) -- pula, não quebra o lote
        writer.add_page(PdfReader(io.BytesIO(page_pdf)).pages[0])

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
