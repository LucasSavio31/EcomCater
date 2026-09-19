"""Monta o payload editável da NF-e a partir do pedido (`build_draft`) e
depois converte esse payload (possivelmente editado pelo admin na tela de
revisão) no objeto `nfelib` de verdade pra assinar/enviar (`build_xml`).

Cobertura fiscal desta primeira versão (documentado de propósito -- ver
"Fora de escopo" no plano): **Simples Nacional** (CSOSN, não CST) é o caminho
testado; ICMS por CST (Lucro Presumido/Real), Substituição Tributária, IPI,
comércio exterior e a Reforma Tributária (IBS/CBS) NÃO são tratados aqui --
`Product.csosn_cst` guarda o código como o lojista/contador informar, mas o
bloco de imposto montado em `_imposto()` assume regime Simples Nacional. Se a
loja for Regime Normal, isso precisa de mais trabalho antes de emitir em
produção.
"""
from __future__ import annotations

import random
from datetime import datetime

from app.modules.admin.models import StoreSettings
from app.modules.nfe.config import NfeConfig
from app.modules.nfe.municipios import find_codigo_ibge
from app.modules.orders.models import Order
from app.modules.payment.models import Payment

# tPag (forma de pagamento) -- tabela oficial da NF-e, só os métodos que a loja usa
_TPAG_BY_METHOD = {
    "credit_card": "03",
    "pix": "17",
    "boleto": "15",
}
_TPAG_OUTROS = "99"

UF_TO_CUF = {
    "AC": 12, "AL": 27, "AM": 13, "AP": 16, "BA": 29, "CE": 23, "DF": 53, "ES": 32,
    "GO": 52, "MA": 21, "MG": 31, "MS": 50, "MT": 51, "PA": 15, "PB": 25, "PE": 26,
    "PI": 22, "PR": 41, "RJ": 33, "RN": 24, "RO": 11, "RR": 14, "RS": 43, "SC": 42,
    "SE": 28, "SP": 35, "TO": 17,
}


def _addr(a: dict) -> dict:
    """Normaliza um `*_address_json` (Order/StoreSettings) pro formato do rascunho."""
    cidade = a.get("city") or ""
    uf = (a.get("state") or "").upper()
    return {
        "logradouro": a.get("street") or "",
        "numero": a.get("number") or "S/N",
        "complemento": a.get("complement") or "",
        "bairro": a.get("district") or "",
        "municipio": cidade,
        "codigo_municipio": find_codigo_ibge(cidade, uf) or "",
        "uf": uf,
        "cep": (a.get("zip") or "").replace("-", ""),
        "telefone": (a.get("phone") or "").strip(),
    }


def build_draft(
    *,
    order: Order,
    store: StoreSettings,
    cfg: NfeConfig,
    payment: Payment | None,
    products_by_id: dict,
) -> dict:
    """Monta o rascunho editável (dict serializável em JSON) a partir do
    pedido. Não bate em nenhuma API externa, não grava nada -- é só a
    "melhor tentativa" com o que já está cadastrado; campos em branco ficam
    em branco pro admin preencher na tela de revisão."""
    a_dest = order.shipping_address_json or {}
    a_emit = store.address_json or {}
    uf_emit = (a_emit.get("state") or "").upper()
    uf_dest = (a_dest.get("state") or "").upper()

    itens = []
    for idx, item in enumerate(order.items, start=1):
        produto = products_by_id.get(item.product_id)
        cfop = (produto.cfop if produto and produto.cfop else None) or (
            cfg.cfop_padrao_dentro_uf if uf_dest == uf_emit else cfg.cfop_padrao_fora_uf
        )
        itens.append(
            {
                "n_item": idx,
                "sku": item.sku,
                "descricao": item.name,
                "ncm": (produto.ncm if produto else None) or "",
                "cfop": cfop,
                "cest": (produto.cest if produto else None) or "",
                "csosn_cst": (produto.csosn_cst if produto else None) or "102",
                "origem": (produto.origem if produto else None) or "0",
                "unidade": (produto.unidade if produto else None) or "UN",
                "quantidade": item.quantity,
                "valor_unitario_cents": item.unit_price_cents,
                "valor_total_cents": item.total_cents,
            }
        )

    if payment is None:
        forma_pagamento = _TPAG_OUTROS
    else:
        forma_pagamento = _TPAG_BY_METHOD.get(payment.method, _TPAG_OUTROS)

    return {
        "ambiente": cfg.ambiente,
        "natureza_operacao": cfg.natureza_operacao,
        "serie": cfg.serie_nfe,
        "numero": cfg.proximo_numero,
        "emitente": {
            "cnpj": (store.cnpj or "").replace(".", "").replace("/", "").replace("-", ""),
            "razao_social": store.legal_name or store.store_name,
            "nome_fantasia": store.store_name,
            "ie": store.ie or "",
            "cnae": store.cnae_fiscal or "",
            "regime_tributario": store.regime_tributario or "1",
            "endereco": {**_addr(a_emit), "codigo_municipio": store.municipio_ibge or find_codigo_ibge(a_emit.get("city") or "", uf_emit) or ""},
            "telefone": store.contact_phone or "",
        },
        "destinatario": {
            "nome": a_dest.get("recipient_name") or order.email,
            "cpf": order.cpf or "",
            "cnpj": "",
            "email": order.email,
            "endereco": _addr(a_dest),
        },
        "itens": itens,
        "totais": {
            "valor_produtos_cents": order.items_total_cents,
            "valor_desconto_cents": order.discount_cents,
            "valor_frete_cents": order.shipping_cents,
            "valor_total_cents": order.grand_total_cents,
        },
        "pagamento": {"forma": forma_pagamento, "valor_cents": order.grand_total_cents},
        "informacoes_complementares": f"Pedido nº {order.number}",
    }


def _cents_to_str(cents: int) -> str:
    return f"{cents / 100:.2f}"


def _calcula_dv(chave_43: str) -> str:
    """Dígito verificador (módulo 11) da chave de acesso -- mesmo algoritmo
    usado em todos os documentos fiscais eletrônicos brasileiros: pesos 2..9
    ciclando da direita pra esquerda, resto < 2 -> DV 0, senão DV = 11 - resto."""
    soma = 0
    peso = 2
    for digito in reversed(chave_43):
        soma += int(digito) * peso
        peso = peso + 1 if peso < 9 else 2
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def monta_chave_acesso(
    *, uf: str, emissao: datetime, cnpj: str, serie: int, numero: int, cnf: int
) -> str:
    cuf = UF_TO_CUF.get(uf.upper())
    if cuf is None:
        raise ValueError(f"UF desconhecida: {uf}")
    aamm = emissao.strftime("%y%m")
    cnpj_limpo = "".join(ch for ch in cnpj if ch.isdigit()).zfill(14)
    chave_43 = (
        f"{cuf:02d}{aamm}{cnpj_limpo}55{serie:03d}{numero:09d}1{cnf:08d}"
    )
    return chave_43 + _calcula_dv(chave_43)


def build_xml(payload: dict):
    """Converte o payload (já revisado/editado pelo admin) no objeto
    `nfelib` (schema oficial 4.00), pronto pra assinar. Levanta `ValueError`
    com mensagem clara se faltar algo obrigatório -- validação de negócio
    fica aqui, antes de gastar uma tentativa de envio na SEFAZ."""
    import nfelib.nfe.bindings.v4_0.leiaute_nfe_v4_00 as leiaute
    import nfelib.nfe.bindings.v4_0.nfe_v4_00 as nfe_mod

    Tnfe = nfe_mod.Tnfe
    InfNfe = Tnfe.InfNfe

    emit = payload["emitente"]
    dest = payload["destinatario"]
    totais = payload["totais"]
    pagamento = payload["pagamento"]

    # o formulário do admin usa máscara (CPF/CNPJ/CEP com pontuação) -- a
    # SEFAZ exige esses campos só com dígitos, então normaliza aqui, não
    # confia que quem chamou já mandou limpo (defesa em profundidade: tanto
    # o popup de emissão quanto uma eventual chamada direta da API caem aqui).
    def _digits(v: str | None) -> str:
        return "".join(ch for ch in (v or "") if ch.isdigit())

    emit["cnpj"] = _digits(emit.get("cnpj"))
    if emit.get("ie") and emit["ie"].strip().upper() != "ISENTO":
        emit["ie"] = _digits(emit["ie"])
    emit["endereco"]["cep"] = _digits(emit["endereco"].get("cep"))
    dest["cpf"] = _digits(dest.get("cpf"))
    dest["cnpj"] = _digits(dest.get("cnpj"))
    dest["endereco"]["cep"] = _digits(dest["endereco"].get("cep"))
    for it in payload["itens"]:
        it["ncm"] = _digits(it.get("ncm"))
        it["cfop"] = _digits(it.get("cfop"))
        it["cest"] = _digits(it.get("cest"))

    faltando = []
    if not emit.get("cnpj"):
        faltando.append("CNPJ do emitente")
    if not emit["endereco"].get("codigo_municipio"):
        faltando.append("código IBGE do município do emitente")
    if not dest["endereco"].get("codigo_municipio"):
        faltando.append("código IBGE do município do destinatário")
    if not dest.get("cpf") and not dest.get("cnpj"):
        faltando.append("CPF/CNPJ do destinatário")
    for it in payload["itens"]:
        if not it.get("ncm"):
            faltando.append(f"NCM do item '{it.get('descricao')}'")
    if faltando:
        raise ValueError("Campos obrigatórios faltando: " + "; ".join(faltando))

    now = datetime.now().astimezone()
    cnf = random.randint(10000000, 99999999)
    chave = monta_chave_acesso(
        uf=emit["endereco"]["uf"],
        emissao=now,
        cnpj=emit["cnpj"],
        serie=payload["serie"],
        numero=payload["numero"],
        cnf=cnf,
    )
    tp_amb = "2" if payload["ambiente"] == "homologacao" else "1"

    def _end_emit():
        e = emit["endereco"]
        return leiaute.TenderEmi(
            xLgr=e["logradouro"], nro=e["numero"], xCpl=e.get("complemento") or None,
            xBairro=e["bairro"], cMun=e["codigo_municipio"], xMun=e["municipio"],
            UF=e["uf"], CEP=e["cep"], cPais="1058", xPais="Brasil", fone=e.get("telefone") or None,
        )

    def _end_dest():
        e = dest["endereco"]
        return leiaute.Tendereco(
            xLgr=e["logradouro"], nro=e["numero"], xCpl=e.get("complemento") or None,
            xBairro=e["bairro"], cMun=e["codigo_municipio"], xMun=e["municipio"],
            UF=e["uf"], CEP=e["cep"], cPais="1058", xPais="Brasil", fone=e.get("telefone") or None,
        )

    def _det(it: dict):
        vprod_cents = it["valor_total_cents"]
        prod = InfNfe.Det.Prod(
            cProd=it["sku"], cEAN="SEM GTIN", xProd=it["descricao"], NCM=it["ncm"],
            CEST=it.get("cest") or None, CFOP=it["cfop"], uCom=it["unidade"],
            qCom=str(it["quantidade"]), vUnCom=_cents_to_str(it["valor_unitario_cents"]),
            vProd=_cents_to_str(vprod_cents), cEANTrib="SEM GTIN", uTrib=it["unidade"],
            qTrib=str(it["quantidade"]), vUnTrib=_cents_to_str(it["valor_unitario_cents"]),
            indTot="1",
        )
        Icms = InfNfe.Det.Imposto.Icms
        icms = Icms(ICMSSN102=Icms.Icmssn102(orig=it["origem"], CSOSN=it["csosn_cst"]))
        Pis = InfNfe.Det.Imposto.Pis
        pis = Pis(PISOutr=Pis.Pisoutr(CST="99", vBC="0.00", pPIS="0.0000", vPIS="0.00"))
        Cofins = InfNfe.Det.Imposto.Cofins
        cofins = Cofins(
            COFINSOutr=Cofins.Cofinsoutr(CST="99", vBC="0.00", pCOFINS="0.0000", vCOFINS="0.00")
        )
        imposto = InfNfe.Det.Imposto(ICMS=icms, PIS=pis, COFINS=cofins)
        return InfNfe.Det(nItem=str(it["n_item"]), prod=prod, imposto=imposto)

    det_list = [_det(it) for it in payload["itens"]]

    total = InfNfe.Total(
        ICMSTot=InfNfe.Total.Icmstot(
            vBC="0.00", vICMS="0.00", vICMSDeson="0.00", vFCP="0.00", vBCST="0.00",
            vST="0.00", vFCPST="0.00", vFCPSTRet="0.00",
            vProd=_cents_to_str(totais["valor_produtos_cents"]),
            vFrete=_cents_to_str(totais["valor_frete_cents"]),
            vSeg="0.00", vDesc=_cents_to_str(totais["valor_desconto_cents"]),
            vII="0.00", vIPI="0.00", vIPIDevol="0.00", vPIS="0.00", vCOFINS="0.00",
            vOutro="0.00", vNF=_cents_to_str(totais["valor_total_cents"]),
        )
    )

    pag = InfNfe.Pag(
        detPag=[
            InfNfe.Pag.DetPag(
                tPag=pagamento["forma"], vPag=_cents_to_str(pagamento["valor_cents"])
            )
        ]
    )

    ide = InfNfe.Ide(
        cUF=UF_TO_CUF[emit["endereco"]["uf"].upper()],
        cNF=f"{cnf:08d}",
        natOp=payload["natureza_operacao"],
        mod="55",
        serie=str(payload["serie"]),
        nNF=str(payload["numero"]),
        dhEmi=now.isoformat(timespec="seconds"),
        tpNF="1",  # saída
        idDest="1" if dest["endereco"]["uf"] == emit["endereco"]["uf"] else "2",
        cMunFG=emit["endereco"]["codigo_municipio"],
        tpImp="1",  # DANFE retrato
        tpEmis="1",  # normal
        cDV=chave[-1],
        tpAmb=tp_amb,
        finNFe="1",  # normal
        indFinal="1",  # consumidor final
        indPres="2",  # não presencial, venda pela internet
        procEmi="0",
        verProc="1.0",
    )

    emit_obj = InfNfe.Emit(
        CNPJ=emit["cnpj"], xNome=emit["razao_social"], xFant=emit.get("nome_fantasia") or None,
        enderEmit=_end_emit(), IE=emit.get("ie") or None, CNAE=emit.get("cnae") or None,
        CRT=emit.get("regime_tributario") or "1",
    )

    dest_kwargs: dict = {"xNome": dest["nome"], "enderDest": _end_dest(), "indIEDest": "9"}
    if dest.get("cnpj"):
        dest_kwargs["CNPJ"] = dest["cnpj"]
    else:
        dest_kwargs["CPF"] = dest["cpf"]
    if dest.get("email"):
        dest_kwargs["email"] = dest["email"]
    dest_obj = InfNfe.Dest(**dest_kwargs)

    inf_adic = InfNfe.InfAdic(infCpl=payload.get("informacoes_complementares") or None)
    # modFrete "9" = sem transporte formal identificado -- padrão simples,
    # editável futuramente se a loja quiser declarar a transportadora.
    transp = InfNfe.Transp(modFrete="9")

    inf_nfe = InfNfe(
        ide=ide, emit=emit_obj, dest=dest_obj, det=det_list, total=total, transp=transp,
        pag=pag, infAdic=inf_adic, versao="4.00", Id="NFe" + chave,
    )
    edoc = Tnfe(infNFe=inf_nfe)
    return edoc, chave
