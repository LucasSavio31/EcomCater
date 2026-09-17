"""Cliente da API do aaPanel (BT-Panel) — cria vhost com proxy reverso e
emite SSL (Let's Encrypt) via HTTP, sem tocar em arquivo/host diretamente.

Auth: `request_token = md5(request_time + md5(api_key))`, enviado junto com
`request_time` em toda chamada (padrão documentado em aapanel.com/docs/api/).

Endpoints usados (`/site?action=...`) seguem a convenção conhecida do
BT-Panel/aaPanel — **confirmar contra a instância real na primeira execução**
(painel → Configurações → API só documenta a autenticação, não cada ação;
o forum/SDKs de terceiros foram a referência pros nomes de parâmetro).
"""
from __future__ import annotations

import hashlib
import logging
import time

import httpx

logger = logging.getLogger("domains.aapanel")


class AaPanelError(RuntimeError):
    pass


class AaPanelClient:
    def __init__(self, *, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _auth(self) -> dict:
        request_time = str(int(time.time()))
        token = hashlib.md5(
            (request_time + hashlib.md5(self.api_key.encode()).hexdigest()).encode()
        ).hexdigest()
        return {"request_time": request_time, "request_token": token}

    async def _post(self, path: str, data: dict) -> dict:
        if not self.base_url or not self.api_key:
            raise AaPanelError("aaPanel não configurado: informe URL e API key no admin.")
        url = f"{self.base_url}{path}"
        body = {**self._auth(), **data}
        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as c:  # noqa: S501 — painel próprio, IP interno
                resp = await c.post(url, data=body)
            result = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("aaPanel indisponível: %s", exc)
            raise AaPanelError("Falha de comunicação com o aaPanel.") from exc
        except ValueError as exc:
            raise AaPanelError("Resposta inesperada do aaPanel (não é JSON).") from exc
        if isinstance(result, dict) and result.get("status") is False:
            raise AaPanelError(str(result.get("msg") or "aaPanel recusou a operação."))
        return result if isinstance(result, dict) else {}

    async def ping(self) -> None:
        """Chamada leve e somente-leitura — só pra validar URL + API key."""
        await self._post("/system?action=GetSystemTotal", {})

    async def create_reverse_proxy_site(self, *, hostname: str, upstream: str) -> None:
        """Cria o site (se não existir) e a regra de proxy reverso raiz -> upstream."""
        await self._post(
            "/site?action=AddSite",
            {
                "webname": f'{{"domain":"{hostname}","domainlist":[],"count":0}}',
                "path": f"/www/wwwroot/{hostname}",
                "type_id": "0",
                "type": "PHP",
                "port": "80",
                "ps": hostname,
                "ftp": "false",
                "sql": "false",
                "codeing": "utf8",
            },
        )
        await self._post(
            "/site?action=CreateProxy",
            {
                "siteName": hostname,
                "proxyname": "default",
                "proxydir": "/",
                "proxysite": upstream,
                "type": "0",
                "cache": "0",
                "cachetime": "1",
                "advanced": "0",
                "subfilter": "0",
            },
        )

    async def issue_ssl(self, hostname: str, *, extra_domains: list[str] | None = None) -> None:
        domains = [hostname, *(extra_domains or [])]
        await self._post(
            "/site?action=ApplyCertApi",
            {"domains": ",".join(domains), "siteName": hostname},
        )
        await self._post("/site?action=SetSSLConf", {"siteName": hostname, "https": "1"})
