"""Testes do handler global de exceção (`app.core.errors`).

Bug real que motivou isso: um `TypeError` sem handler específico (não é
`DomainError`) voltava como 500 de texto puro sem corpo interpretável --
o painel admin recebia `content-type: text/plain`, o front não conseguia
extrair mensagem nenhuma e mostrava algo genérico tipo "Failed to fetch"
mesmo a requisição tendo ido e voltado normalmente. `register_error_handlers`
agora sempre devolve JSON com a causa raiz, mesmo pra exceção não prevista.
"""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from starlette.requests import Request

from app.core.errors import register_error_handlers, unhandled_exception_handler


@pytest.mark.asyncio
async def test_unhandled_exception_returns_json_with_root_cause():
    """Testa a função do handler direto (não via client/ASGI) porque o
    `ServerErrorMiddleware` do Starlette sempre re-levanta a exceção depois
    de mandar a resposta -- de propósito, pra debugging em teste -- então
    passar pelo client de teste faria esse teste "falhar" mesmo com o
    handler funcionando certinho em produção de verdade."""
    scope = {"type": "http", "method": "GET", "path": "/api/admin/nfe/orders/X/draft", "headers": []}
    request = Request(scope)
    exc = TypeError("um bug qualquer, não relacionado a regra de negócio")

    response = await unhandled_exception_handler(request, exc)
    assert response.status_code == 500
    body = json.loads(bytes(response.body))
    assert body["error"]["code"] == "internal_error"
    assert "um bug qualquer" in body["error"]["message"]


@pytest.mark.asyncio
async def test_unhandled_exception_handler_is_registered():
    """Confere que o app de verdade registra o handler (não só que a função
    isolada funciona) -- pega regressão se `register_error_handlers` for
    editado e o `add_exception_handler(Exception, ...)` for removido."""
    app = FastAPI()
    register_error_handlers(app)
    assert app.exception_handlers[Exception] is unhandled_exception_handler
