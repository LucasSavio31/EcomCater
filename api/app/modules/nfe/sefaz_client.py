"""Cliente que fala com a SEFAZ de verdade: assina o XML (certificado A1),
envia pro webservice de autorização da UF certa, consulta o recibo e envia
eventos de cancelamento.

`erpbrasil.edoc.nfe.NFe.envia_documento()` (a conveniência pronta da lib) não
dá pra usar direto — ela espera um objeto do "generateDS" antigo (que tem um
método `.export()`), e o `nfelib` moderno (que usamos em `mapping.py` pra
montar o XML com o schema tipado) gera dataclasses via `xsdata`, sem esse
método. A própria lib já lida bem com receber um `lxml._Element` pronto
(`_generateds_to_string_etree` faz `if type(ds) == _Element: return
etree.tostring(ds), ds`), então serializamos com o `xsdata` antes de entregar
pra ela assinar/enviar — só isso, o resto (roteamento por UF/ambiente,
assinatura, parsing da resposta) é a lib mesma.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass

from erpbrasil.assinatura.certificado import Certificado
from erpbrasil.edoc.nfe import NFe as EdocNFe
from erpbrasil.transmissao.transmissao import TransmissaoSOAP
from lxml import etree
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig

_SERIALIZER = XmlSerializer(config=SerializerConfig(xml_declaration=False))


@dataclass
class SefazResultado:
    ok: bool
    codigo_status: str | None
    motivo: str | None
    numero_recibo: str | None = None
    numero_protocolo: str | None = None


class SefazError(RuntimeError):
    pass


def _to_etree(edoc_dataclass) -> etree._Element:
    xml_str = _SERIALIZER.render(edoc_dataclass)
    return etree.fromstring(xml_str.encode("utf-8"))


class SefazClient:
    """Uma instância por emissão -- carrega o certificado uma vez, fala com
    a UF/ambiente informados."""

    def __init__(self, *, pfx_bytes: bytes, senha: str, uf: str, cuf: int, ambiente: str):
        self._tmp_path = None
        fd, self._tmp_path = tempfile.mkstemp(suffix=".pfx")
        with os.fdopen(fd, "wb") as f:
            f.write(pfx_bytes)
        self.certificado = Certificado(self._tmp_path, senha)
        transmissao = TransmissaoSOAP(self.certificado)
        tp_amb = "2" if ambiente == "homologacao" else "1"
        self._nfe = EdocNFe(transmissao, cuf, ambiente=tp_amb)

    def __del__(self):
        if self._tmp_path and os.path.exists(self._tmp_path):
            os.unlink(self._tmp_path)

    def enviar(self, edoc_dataclass, doc_id: str) -> tuple[SefazResultado, bytes]:
        """Assina e envia o lote (1 NF-e, síncrono desativado -- SEFAZ
        processa em fila, resultado vem depois via `consultar_recibo`).
        Retorna o resultado E o XML assinado (pra guardar mesmo que a
        autorização ainda esteja pendente -- permite reconsultar depois sem
        precisar remontar o documento)."""
        import datetime

        from erpbrasil.nfelib_legacy.v4_00 import retEnviNFe

        xml_etree = _to_etree(edoc_dataclass)
        xml_assinado = self._nfe.assina_raiz(xml_etree, doc_id)
        # `assina_xml2` (erpbrasil.assinatura) às vezes devolve str em vez de
        # bytes, dependendo do caminho interno -- normaliza aqui pra nunca
        # quebrar quem grava isso no storage (bug real visto em produção:
        # TypeError salvando o XML assinado com certificado de verdade).
        if isinstance(xml_assinado, str):
            xml_assinado = xml_assinado.encode("utf-8")

        raiz = retEnviNFe.TEnviNFe(
            versao="4.00",
            idLote=datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            indSinc="0",
        )
        raiz.original_tagname_ = "enviNFe"
        _xml_str, xml_envio_etree = self._nfe._generateds_to_string_etree(raiz)
        xml_envio_etree.append(etree.fromstring(xml_assinado))

        from erpbrasil.edoc.nfe import WS_NFE_AUTORIZACAO

        resposta = self._nfe._post(
            xml_envio_etree,
            self._nfe._get_ws_endpoint(WS_NFE_AUTORIZACAO),
            "nfeAutorizacaoLote",
            retEnviNFe,
        )
        r = resposta.resposta
        resultado = SefazResultado(
            ok=str(getattr(r, "cStat", "")) in ("103", "104"),
            codigo_status=str(getattr(r, "cStat", "") or ""),
            motivo=str(getattr(r, "xMotivo", "") or ""),
            numero_recibo=str(getattr(getattr(r, "infRec", None), "nRec", "") or "") or None,
        )
        return resultado, xml_assinado

    def consultar_recibo(self, numero_recibo: str) -> SefazResultado:
        resposta = self._nfe.consulta_recibo(numero=numero_recibo)
        r = resposta.resposta
        cstat_lote = str(getattr(r, "cStat", "") or "")
        protocolos = getattr(r, "protNFe", None) or []
        if protocolos:
            p0 = protocolos[0].infProt if hasattr(protocolos[0], "infProt") else protocolos[0]
            cstat_doc = str(getattr(p0, "cStat", "") or "")
            return SefazResultado(
                ok=cstat_doc == "100",
                codigo_status=cstat_doc,
                motivo=str(getattr(p0, "xMotivo", "") or ""),
                numero_protocolo=str(getattr(p0, "nProt", "") or "") or None,
            )
        # lote ainda em processamento (cStat 105) ou erro no lote em si
        return SefazResultado(ok=False, codigo_status=cstat_lote, motivo=str(getattr(r, "xMotivo", "") or ""))

    def cancelar(self, *, chave: str, protocolo: str, justificativa: str) -> SefazResultado:
        evento_info = self._nfe.cancela_documento(chave, protocolo, justificativa)
        resposta = self._nfe.enviar_lote_evento([evento_info])
        r = resposta.resposta
        ev = getattr(r, "retEvento", None) or []
        if ev:
            info = ev[0].infEvento
            cstat = str(getattr(info, "cStat", "") or "")
            return SefazResultado(
                ok=cstat == "135",
                codigo_status=cstat,
                motivo=str(getattr(info, "xMotivo", "") or ""),
            )
        return SefazResultado(ok=False, codigo_status=str(getattr(r, "cStat", "") or ""), motivo="Sem retorno de evento.")
