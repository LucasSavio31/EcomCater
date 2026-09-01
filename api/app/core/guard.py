"""Salvaguardas contra exclusão acidental.

Regra do projeto: **nada de dado transacional (pedido, item de pedido, pagamento,
evento de pedido) pode ser apagado** pela aplicação. Clientes com histórico de
compra também não podem ser apagados — no máximo anonimizados. Demais exclusões
(produto, categoria, cupom, tabela de medidas, etc.) só quando não houver
referência que gere perda silenciosa de dados, e sempre com confirmação
explícita quando o efeito for irreversível.
"""
from __future__ import annotations

from app.core.errors import ConflictError, ForbiddenError, ValidationError


def require_confirmation(confirm: bool | str | None, *, what: str) -> None:
    """Exige `?confirm=true` (ou campo `confirm`) para operações irreversíveis."""
    ok = confirm is True or (isinstance(confirm, str) and confirm.strip().lower() in ("true", "1", "sim"))
    if not ok:
        raise ValidationError(
            f"Confirmação obrigatória para {what}. Repita a chamada com confirm=true."
        )


def require_super_admin(actor_role: str, *, what: str) -> None:
    if actor_role != "super_admin":
        raise ForbiddenError(f"Apenas o super admin pode {what}.")


def block_if_referenced(count: int, *, entity: str, by: str, hint: str) -> None:
    """Impede a exclusão quando há registros dependentes."""
    if count:
        raise ConflictError(
            f"Não é possível excluir {entity}: {count} {by} dependem dele. {hint}"
        )
