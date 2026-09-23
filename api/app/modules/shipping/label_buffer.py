"""Buffer local de etiquetas do Melhor Envio já geradas -- 1h por padrão,
pra não precisar reabrir a página deles num navegador headless (Playwright,
caro) a cada clique dentro da janela. Fica no storage privado, sob
`label-buffer/`.

Chave = hash do PEDIDO do PDF (pedidos + formato + declaração), não por
pedido individual -- uma etiqueta única (`/{number}/melhor-envio/label`) e
um lote (`/melhor-envio/labels?numbers=...`) são pedidos diferentes,
bufferizados cada um por si.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

_TTL = timedelta(hours=1)
_INDEX_KEY = "label-buffer/_index.json"


def compute_key(order_numbers: list[str], fmt: str, want_declaration: bool) -> str:
    raw = "|".join(sorted(order_numbers)) + f"|{fmt}|{want_declaration}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _blob_key(key: str) -> str:
    return f"label-buffer/{key}.pdf"


def _meta_key(key: str) -> str:
    return f"label-buffer/{key}.meta.json"


def _load_index() -> list[str]:
    from app.shared.storage import private_storage

    if not private_storage.exists(_INDEX_KEY):
        return []
    try:
        return list(json.loads(private_storage.read(_INDEX_KEY)))
    except Exception:  # noqa: BLE001 - índice corrompido -- trata como vazio
        return []


def _save_index(keys: list[str]) -> None:
    from app.shared.storage import private_storage

    data = json.dumps(sorted(set(keys))).encode("utf-8")
    private_storage.save(_INDEX_KEY, data, content_type="application/json")


def read_buffer(key: str) -> bytes | None:
    from app.shared.storage import private_storage

    meta_key = _meta_key(key)
    if not private_storage.exists(meta_key):
        return None
    try:
        meta = json.loads(private_storage.read(meta_key))
        generated_at = datetime.fromisoformat(meta["generated_at"])
        if datetime.now(UTC) - generated_at > _TTL:
            return None
        blob_key = _blob_key(key)
        if not private_storage.exists(blob_key):
            return None
        return private_storage.read(blob_key)
    except Exception:  # noqa: BLE001 - buffer corrompido/formato antigo -- regenera
        return None


def write_buffer(key: str, pdf: bytes) -> None:
    from app.shared.storage import private_storage

    private_storage.save(_blob_key(key), pdf, content_type="application/pdf")
    meta = json.dumps({"generated_at": datetime.now(UTC).isoformat()}).encode("utf-8")
    private_storage.save(_meta_key(key), meta, content_type="application/json")
    idx = _load_index()
    if key not in idx:
        idx.append(key)
        _save_index(idx)


def clear_buffer() -> int:
    """Apaga TODAS as etiquetas em buffer -- botão "Limpar buffer" no admin.
    Devolve quantas entradas foram removidas."""
    from app.shared.storage import private_storage

    idx = _load_index()
    removed = 0
    for key in idx:
        for storage_key in (_blob_key(key), _meta_key(key)):
            if private_storage.exists(storage_key):
                private_storage.delete(storage_key)
                removed += 1
    if private_storage.exists(_INDEX_KEY):
        private_storage.delete(_INDEX_KEY)
    return removed
