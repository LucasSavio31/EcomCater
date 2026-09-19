"""Exceções de domínio + handlers HTTP padronizados."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("errors")


class DomainError(Exception):
    """Erro de regra de negócio. Mapeado para HTTP pelos handlers."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "domain_error"

    def __init__(self, message: str, *, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details or {}


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationError(DomainError):
    status_code = 422
    code = "validation_error"


class AuthError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "auth_error"


class ForbiddenError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class PaymentError(DomainError):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    code = "payment_error"


class ModuleDisabledError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "module_disabled"


async def _domain_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Rede de segurança pra qualquer exceção sem handler específico (bug de
    programação, não erro de negócio). Sem isso o cliente recebe um 500 de
    texto puro sem corpo interpretável -- o admin (painel autenticado, não a
    loja pública) vê a causa raiz de verdade em vez de "Failed to fetch"/erro
    genérico; o traceback completo sempre vai pro log do servidor de
    qualquer forma. Função nomeada (não aninhada) pra dar pra testar direto,
    sem depender do comportamento de propagação de exceção do client ASGI
    de teste (Starlette sempre re-levanta a exceção depois de mandar a
    resposta, de propósito, pra visibilidade em teste -- ver
    `ServerErrorMiddleware`)."""
    logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": f"Erro interno: {exc}",
                "details": {"type": type(exc).__name__},
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
