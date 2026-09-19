"""Configuração persistida do módulo `nfe` (em `modules.config_json`).

Dados fiscais da empresa (razão social/CNPJ/endereço) ficam em `StoreSettings`
(já usada pela Fatura não-fiscal) -- aqui só o que é específico de emissão de
NF-e: ambiente, série/numeração, certificado, CFOP padrão. Sem criptografia
em repouso pro certificado/senha, mesmo padrão já usado por
`shipping`/`payment`/`domains`.
"""
from __future__ import annotations

from pydantic import BaseModel

AMBIENTE_HOMOLOGACAO = "homologacao"
AMBIENTE_PRODUCAO = "producao"


class NfeConfig(BaseModel):
    ambiente: str = AMBIENTE_HOMOLOGACAO  # só o lojista muda pra produção depois de testar
    serie_nfe: int = 1
    proximo_numero: int = 1
    cfop_padrao_dentro_uf: str = "5102"  # venda de mercadoria, dentro do estado
    cfop_padrao_fora_uf: str = "6108"    # venda de mercadoria, fora do estado, consumidor final
    natureza_operacao: str = "Venda de mercadoria"

    certificado_storage_key: str = ""   # chave no private_storage do .pfx
    certificado_senha: str = ""         # texto puro (padrão do projeto, ver docstring acima)
    certificado_validade: str = ""      # ISO 8601 (data), extraída no upload
    certificado_titular: str = ""       # CN do certificado, pra conferência visual
