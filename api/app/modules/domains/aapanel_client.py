"""Cliente da API do aaPanel (BT-Panel) — cria site + proxy reverso e emite
SSL (Let's Encrypt) via HTTP, sem sessão de navegador.

Auth: `request_token = md5(request_time + md5(api_key))`, enviado junto com
`request_time` em toda chamada (padrão documentado em aapanel.com/docs/api/).

Tudo abaixo foi **confirmado contra a instância real** (não é mais chute):

- `AddSite` e os nomes dos demais `/site?action=...` batem com o código
  aberto do aaPanel (github.com/aaPanel/aaPanel, `class/panelSite.py`).
- **Não existe** um `CreateProxy` genérico que funcione pra sites em
  OpenLiteSpeed (só é pensado pra nginx) — ele devolve 404 puro (nginx do
  próprio aaPanel, nem chega a rotear). O jeito que funciona de verdade pra
  LiteSpeed é escrever o contexto de proxy reverso direto no arquivo que o
  vhost já inclui (`vhost/openlitespeed/proxy/<host>/*.conf`), via API de
  arquivos (`CreateDir`/`CreateFile`/`SaveFileBody`) + `ServiceAdmin` pra
  recarregar. Isso também tem a vantagem de **não** marcar o site como
  "tem proxy reverso" no rastreamento interno do aaPanel — o que importa
  porque `CreateLet` **recusa emitir certificado pra site com proxy reverso
  ligado** (mensagem literal: "Sites that have reverse proxy turned on
  cannot request SSL!"). Usando só o arquivo (sem passar pela ação/])
  "oficial" de proxy reverso do painel), esse bloqueio não é acionado.
- SSL usa `CreateLet` (não existe `ApplyCertApi`) — `domains` é uma lista
  JSON, não string separada por vírgula.
- A validação HTTP-01 do Let's Encrypt bate em
  `http://<host>/.well-known/acme-challenge/<token>` — como o contexto `/`
  vira proxy reverso (tudo vai pro container), essa validação cairia no
  Next.js/FastAPI (404) se não abrirmos uma exceção estática pra esse
  caminho específico ANTES do contexto proxy. É por isso que o proxy
  reverso já nasce com essa exceção — sem ela, `CreateLet` falha com
  "Invalid response ... 404".
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time

import httpx

logger = logging.getLogger("domains.aapanel")

# mensagens de "já existe"/"já está ok" que tratamos como sucesso — a
# automação precisa ser idempotente (reprocessa domínios em `failed`/
# `dns_pending` sem parar de novo por causa de um passo que outra tentativa
# já completou).
_IDEMPOTENT_OK_SUBSTRINGS = (
    "already exist",
    "already ok",
    "already have",
)


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

    async def _post(self, path: str, data: dict, *, ignore_existing: bool = False) -> dict:
        if not self.base_url or not self.api_key:
            raise AaPanelError("aaPanel não configurado: informe URL e API key no admin.")
        url = f"{self.base_url}{path}"
        body = {**self._auth(), **data}
        try:
            async with httpx.AsyncClient(timeout=60, verify=False) as c:  # noqa: S501 — painel próprio, IP interno
                resp = await c.post(url, data=body)
            result = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("aaPanel indisponível: %s", exc)
            raise AaPanelError("Falha de comunicação com o aaPanel.") from exc
        except ValueError as exc:
            raise AaPanelError(
                f"Resposta inesperada do aaPanel em {path} (não é JSON)."
            ) from exc
        if isinstance(result, dict) and result.get("status") is False:
            msg = str(result.get("msg") or "aaPanel recusou a operação.")
            if ignore_existing and any(s in msg.lower() for s in _IDEMPOTENT_OK_SUBSTRINGS):
                return result
            raise AaPanelError(msg)
        return result if isinstance(result, dict) else {}

    async def ping(self) -> None:
        """Chamada leve e somente-leitura — só pra validar URL + API key."""
        await self._post("/system?action=GetSystemTotal", {})

    async def ensure_site(self, hostname: str) -> None:
        """Cria o site no aaPanel — idempotente (site já existir não é erro)."""
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
            ignore_existing=True,
        )

    async def set_reverse_proxy(self, *, hostname: str, upstream: str) -> None:
        """Escreve o contexto de proxy reverso do LiteSpeed direto no arquivo
        que o vhost já inclui — com a exceção do `.well-known/acme-challenge`
        já embutida (pré-requisito pro `issue_ssl` funcionar depois)."""
        webroot = f"/www/wwwroot/{hostname}"
        proxy_dir = f"/www/server/panel/vhost/openlitespeed/proxy/{hostname}"

        await self._post(
            "/files?action=CreateDir",
            {"path": f"{webroot}/.well-known/acme-challenge"},
            ignore_existing=True,
        )
        await self._post("/files?action=CreateDir", {"path": proxy_dir}, ignore_existing=True)

        handler = "proxy_" + hostname.replace(".", "_")
        conf = (
            "context /.well-known/acme-challenge/ {\n"
            "  location                $DOC_ROOT/.well-known/acme-challenge/\n"
            "  allowBrowse             1\n"
            "}\n"
            "\n"
            "context / {\n"
            "  type                    proxy\n"
            f"  handler                 {handler}\n"
            "  addDefaultCharset       off\n"
            "}\n"
            "\n"
            f"extprocessor {handler} {{\n"
            "  type                    proxy\n"
            f"  address                 {upstream.replace('http://', '')}\n"
            "  maxConns                200\n"
            "  initTimeout             60\n"
            "  retryTimeout            0\n"
            "  respBuffer              0\n"
            "}\n"
        )
        path = f"{proxy_dir}/proxy.conf"
        await self._post("/files?action=CreateFile", {"path": path, "data": ""}, ignore_existing=True)
        await self._post("/files?action=SaveFileBody", {"path": path, "data": conf, "encoding": "utf-8"})

    async def reload_web_server(self) -> None:
        await self._post("/system?action=ServiceAdmin", {"name": "openlitespeed", "type": "restart"})
        # dá um tempo pro LiteSpeed voltar antes do próximo passo (ex.: SSL)
        # tentar bater nele — sem isso a primeira tentativa logo em seguida
        # às vezes pega o servidor ainda reiniciando.
        await asyncio.sleep(2)

    async def issue_ssl(self, hostname: str, *, email: str = "") -> None:
        """Emite (ou renova) o certificado Let's Encrypt via validação HTTP,
        e liga o HTTPS no vhost. Só funciona se `set_reverse_proxy` já tiver
        rodado (a exceção do acme-challenge precisa existir) — e só se o
        site NÃO tiver sido marcado como "proxy reverso" pelo mecanismo
        oficial do aaPanel (por isso `set_reverse_proxy` nunca usa a ação de
        proxy reverso do painel, só escreve o arquivo por baixo)."""
        await self._post(
            "/site?action=CreateLet",
            {
                "domains": f'["{hostname}"]',
                "siteName": hostname,
                "email": email or f"admin@{hostname}",
                "auth_type": "http",
                "auth_to": "auto",
                "id": "0",
            },
        )
        await self._post(
            "/site?action=SetSSLConf",
            {"siteName": hostname, "first_domain": hostname},
            ignore_existing=True,
        )
