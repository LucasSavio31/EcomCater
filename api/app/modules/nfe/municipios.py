"""Código IBGE do município (7 dígitos), exigido no endereço do emitente e
do destinatário na NF-e. Tabela estática (fonte: API pública do IBGE,
`servicodados.ibge.gov.br/api/v1/localidades/municipios`, baixada nesta
sessão) — dado público e estável, carregado uma vez em memória em vez de
bater na rede a cada emissão.
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

_FIXTURE_PATH = Path(__file__).parent / "municipios_ibge.json"


def _normalize(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return sem_acento.upper().strip()


@lru_cache(maxsize=1)
def _load() -> dict[str, str]:
    with _FIXTURE_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def find_codigo_ibge(cidade: str, uf: str) -> str | None:
    """Retorna o código IBGE (string, 7 dígitos) de `(cidade, uf)`, ou None
    se não encontrado (nome digitado diferente do oficial -- quem chama
    decide se bloqueia ou deixa o admin preencher manualmente)."""
    if not cidade or not uf:
        return None
    key = f"{_normalize(cidade)}|{uf.strip().upper()}"
    return _load().get(key)
