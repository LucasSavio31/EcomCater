"""Teste ISOLADO e temporário: valida se o Sandbox do Melhor Envio devolve o
PDF oficial da etiqueta Jadlog direto por API (`GET /me/imprimir/pdf/{id}`),
sem Chromium/Playwright/navegador algum.

NÃO integra com o fluxo de produção e NÃO modifica `shipping/service.py`.
Reaproveita, só leitura/chamada, sem alterar nada:
  - `shipping.service.load_config` / `_me_base` / `_me_from_block` (remetente)
  - `shipping.service.quote()` (cotação real, já cuida do refresh de token)
O carrinho/checkout/geração/PDF são chamadas HTTP próprias deste script,
espelhando o mesmo formato de payload já usado em `_me_label_for_order`,
sem criar nenhum `Order`/`OrderItem` no banco.

Aborta imediatamente se a config não estiver em modo sandbox — nunca chama
produção.

Uso:
    cd api && ./.venv/Scripts/python.exe -m app.scripts.test_me_jadlog_pdf_sandbox
"""
from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.shipping import service as shipping_service
from app.modules.shipping.providers.base import Package
from app.modules.shipping.providers.melhor_envio import MelhorEnvioProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scripts.test_me_jadlog_pdf_sandbox")

DEST_ZIP = "01310100"  # CEP fictício de destino (existe de verdade; Sandbox aceita CEPs reais)

DEST_FAKE = {
    "recipient_name": "Cliente Teste Sandbox",
    "phone": "11999999999",
    "email": "teste.sandbox@example.com",
    "cpf": "11144477735",  # CPF válido (dígito verificador ok) só para teste
    "street": "Avenida Paulista",
    "number": "1000",
    "complement": "",
    "district": "Bela Vista",
    "city": "São Paulo",
    "state": "SP",
    "zip": "01310100",
}


def _mask(order_id: str) -> str:
    s = str(order_id)
    return f"{s[:4]}…{s[-4:]}" if len(s) > 8 else f"…{s[-4:]}"


def _report(r: httpx.Response, *, label: str = "") -> None:
    body = r.content
    ct = r.headers.get("content-type", "")
    cd = r.headers.get("content-disposition", "")
    cl = r.headers.get("content-length", str(len(body)))
    is_pdf = body[:4] == b"%PDF"
    print(f"---- Resposta {label} ----")
    print(f"status={r.status_code} content-type={ct!r} content-disposition={cd!r} content-length={cl}")
    print(f"tamanho_body={len(body)} bytes | começa com %PDF: {is_pdf}")
    print(f"primeiros_bytes={body[:200]!r}")
    if not is_pdf and (b"application/json" in ct.encode() or body[:1] in (b"{", b"[")):
        try:
            print("json=", json.dumps(r.json(), indent=2, ensure_ascii=False)[:2000])
        except Exception:  # noqa: BLE001
            pass
    if is_pdf:
        out = Path(tempfile.gettempdir()) / "melhor-envio-jadlog-test.pdf"
        out.write_bytes(body)
        print(f"PDF salvo em: {out} ({len(body)} bytes)")


async def main() -> None:
    async with SessionLocal() as db:
        cfg = await shipping_service.load_config(db)
        if not cfg.melhor_envio_sandbox:
            raise SystemExit(
                "ABORTADO: melhor_envio_sandbox=False na config atual — este "
                "script só roda contra o Sandbox, nunca produção."
            )
        token = cfg.melhor_envio_token or settings.melhor_envio_token
        if not token:
            raise SystemExit("ABORTADO: nenhum token do Melhor Envio configurado (menu Frete).")

        base = shipping_service._me_base(cfg)
        origin = cfg.origin_zip or settings.shipping_origin_zip
        pkg = cfg.default_package
        print(f"== Base URL (sandbox): {base}")

        # Renova o token se preciso (mesmo comportamento existente que
        # `shipping.service.quote()` já dispara sozinho — só chamado aqui
        # explicitamente porque, abaixo, uso o provider bruto em vez de
        # `service.quote()`, que filtra pelos serviços permitidos da loja
        # (`cfg.allowed_services`, padrão PAC/SEDEX) e esconderia Jadlog).
        cfg = await shipping_service._maybe_refresh_me_token(db, cfg)
        await db.commit()
        token = cfg.melhor_envio_token or settings.melhor_envio_token

        print("== Passo 1: cotação real (reaproveitando MelhorEnvioProvider.quote, sem alterações)")
        provider = MelhorEnvioProvider(token=token, base_url=base)
        rate_objs = await provider.quote(
            origin_zip=origin,
            dest_zip=DEST_ZIP,
            packages=[
                Package(
                    weight_grams=pkg.weight_grams,
                    length_mm=pkg.length_mm,
                    width_mm=pkg.width_mm,
                    height_mm=pkg.height_mm,
                )
            ],
        )
        rates = [r.as_dict() for r in rate_objs]

        jadlog = [r for r in rates if "jadlog" in str(r.get("carrier", "")).lower()]
        if not jadlog:
            print(json.dumps(rates, indent=2, ensure_ascii=False, default=str))
            raise SystemExit("ABORTADO: nenhuma tarifa Jadlog retornada pela cotação no Sandbox.")
        rate = jadlog[0]
        service_id = rate.get("id")
        print(f"   Jadlog escolhido: {rate.get('carrier')} / {rate.get('service')} (id={service_id})")

        from_block = await shipping_service._me_from_block(db, cfg, origin)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": settings.melhor_envio_user_agent,
    }

    async with httpx.AsyncClient(timeout=40, headers=headers) as c:
        print("== Passo 2: adicionar ao carrinho do Melhor Envio (POST /me/cart)")
        cart_payload = {
            "service": int(service_id) if str(service_id).isdigit() else service_id,
            "from": from_block,
            "to": {
                "name": DEST_FAKE["recipient_name"],
                "phone": DEST_FAKE["phone"],
                "email": DEST_FAKE["email"],
                "document": DEST_FAKE["cpf"],
                "address": DEST_FAKE["street"],
                "number": DEST_FAKE["number"],
                "complement": DEST_FAKE["complement"],
                "district": DEST_FAKE["district"],
                "city": DEST_FAKE["city"],
                "state_abbr": DEST_FAKE["state"],
                "country_id": "BR",
                "postal_code": DEST_FAKE["zip"],
            },
            "products": [{"name": "Produto Teste Sandbox", "quantity": 1, "unitary_value": 100.0}],
            "volumes": [
                {
                    "height": max(1, round(pkg.height_mm / 10)),
                    "width": max(1, round(pkg.width_mm / 10)),
                    "length": max(1, round(pkg.length_mm / 10)),
                    "weight": round(max(1, pkg.weight_grams) / 1000, 3),
                }
            ],
            "options": {
                "insurance_value": 100.0,
                "receipt": False,
                "own_hand": False,
                "reminder": "Teste sandbox Jadlog PDF",
                "platform": "Loja - teste isolado",
                "tags": [{"tag": "teste-sandbox-jadlog-pdf", "url": None}],
            },
        }
        r = await c.post(f"{base}/api/v2/me/cart", json=cart_payload)
        print(f"   status={r.status_code}")
        if r.status_code >= 300:
            print(f"   body={r.text[:1000]}")
            raise SystemExit("ABORTADO: falha ao adicionar ao carrinho.")
        order_id = str((r.json() or {}).get("id") or "")
        if not order_id:
            print(f"   body={r.text[:1000]}")
            raise SystemExit("ABORTADO: carrinho não retornou id.")
        print(f"   Order ID (mascarado): {_mask(order_id)}")

        print("== Passo 3: checkout — pagar com saldo fictício do Sandbox (POST /shipment/checkout)")
        r = await c.post(f"{base}/api/v2/me/shipment/checkout", json={"orders": [order_id]})
        print(f"   status={r.status_code}")
        print(f"   body={r.text[:500]}")
        if r.status_code >= 300:
            print("   AVISO: checkout falhou — sem saldo/pagamento no Sandbox. Seguindo mesmo assim")
            print("   para ver como generate/pdf respondem sem compra confirmada.")

        print("== Passo 4: gerar etiqueta (POST /shipment/generate)")
        r = await c.post(f"{base}/api/v2/me/shipment/generate", json={"orders": [order_id]})
        print(f"   status={r.status_code}")
        print(f"   body={r.text[:500]}")

        print("== Passo 5: tentar obter PDF direto — GET /me/imprimir/pdf/{id}")
        print("   (a geração é assíncrona no ME — faz polling curto, só HTTP, sem navegador)")
        pdf_headers = dict(headers)
        pdf_headers["Accept"] = "application/pdf"
        r = None
        max_attempts = 24
        for attempt in range(1, max_attempts + 1):
            r = await c.get(
                f"{base}/api/v2/me/imprimir/pdf/{order_id}",
                headers=pdf_headers,
                follow_redirects=False,
            )
            if r.status_code != 422 or b"E-PRT-0011" not in r.content:
                break
            print(f"   tentativa {attempt}/{max_attempts}: ainda gerando (E-PRT-0011) — aguardando 5s")
            await asyncio.sleep(5)
        _report(r)

        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
            loc = r.headers["location"]
            print(f"== Redirect detectado -> seguindo server-to-server (sem navegador): {loc}")
            r2 = await c.get(loc, headers=pdf_headers, follow_redirects=False)
            _report(r2, label="(após redirect)")

    print("\n== FIM DO TESTE ==")
    print(f"Order ID de teste (mascarado): {_mask(order_id)}")


if __name__ == "__main__":
    asyncio.run(main())
