"""Rotas administrativas: auth, usuários, módulos, dashboard, settings gerais."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.core.module_registry import all_specs
from app.core.ratelimit import rate_limit
from app.modules.admin import service
from app.modules.admin.models import AdminUser, ModuleRow, StoreSettings
from app.modules.admin.schemas import (
    AdminLoginIn,
    AdminUserCreateIn,
    AdminUserOut,
    AdminUserUpdateIn,
    ChangePasswordIn,
    DashboardOut,
    ModuleOut,
    ModuleUpdateIn,
    RefreshIn,
    TokenOut,
)

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentAdmin = Annotated[AdminUser, Depends(get_current_admin)]


# ---------------------------------------------------------------- auth
@router.post("/auth/login", response_model=TokenOut)
async def login(
    body: AdminLoginIn,
    db: DbDep,
    _rl: Annotated[None, Depends(rate_limit("10/minute", scope="admin-login"))],
):
    _, pair = await service.authenticate(db, body.email, body.password)
    return TokenOut(**pair)


@router.post("/auth/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, db: DbDep):
    pair = await service.refresh(db, body.refresh_token)
    return TokenOut(**pair)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshIn, db: DbDep):
    await service.logout(db, body.refresh_token)


@router.get("/auth/me", response_model=AdminUserOut)
async def me(admin: CurrentAdmin):
    return AdminUserOut.model_validate({**admin.__dict__, "id": str(admin.id)})


@router.post("/auth/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: ChangePasswordIn, db: DbDep, admin: CurrentAdmin):
    await service.change_password(db, admin, body.current_password, body.new_password)


# ---------------------------------------------------------------- usuários admin
@router.get("/users", response_model=list[AdminUserOut])
async def list_users(db: DbDep, _: Annotated[AdminUser, Depends(require_role("admin"))]):
    rows = await service.list_admins(db)
    return [AdminUserOut.model_validate({**r.__dict__, "id": str(r.id)}) for r in rows]


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: AdminUserCreateIn,
    db: DbDep,
    actor: Annotated[AdminUser, Depends(require_role("super_admin"))],
):
    admin = await service.create_admin(
        db, actor=actor, email=body.email, name=body.name,
        password=body.password, role=body.role,
    )
    return AdminUserOut.model_validate({**admin.__dict__, "id": str(admin.id)})


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: str,
    body: AdminUserUpdateIn,
    db: DbDep,
    actor: Annotated[AdminUser, Depends(require_role("super_admin"))],
):
    admin = await service.update_admin(
        db, actor=actor, admin_id=user_id, data=body.model_dump(exclude_unset=True)
    )
    return AdminUserOut.model_validate({**admin.__dict__, "id": str(admin.id)})


# ---------------------------------------------------------------- módulos
@router.get("/modules", response_model=list[ModuleOut])
async def list_modules(db: DbDep, _: CurrentAdmin):
    rows = {r.slug: r for r in await db.scalars(select(ModuleRow))}
    out: list[ModuleOut] = []
    for spec in all_specs():
        row = rows.get(spec.slug)
        out.append(
            ModuleOut(
                slug=spec.slug,
                label=spec.label,
                kind=spec.kind,
                toggleable=spec.toggleable,
                enabled=row.enabled if row else spec.default_enabled,
                config=dict(row.config_json) if row and row.config_json else dict(spec.default_config),
            )
        )
    return out


@router.patch("/modules/{slug}", response_model=ModuleOut)
async def update_module(
    slug: str,
    body: ModuleUpdateIn,
    db: DbDep,
    _: Annotated[AdminUser, Depends(require_role("admin"))],
):
    from app.core.errors import NotFoundError, ValidationError
    from app.core.module_registry import get_spec

    spec = get_spec(slug)
    if not spec:
        raise NotFoundError("Módulo não encontrado.")
    row = await db.get(ModuleRow, slug)
    if row is None:
        row = ModuleRow(slug=slug, enabled=spec.default_enabled, config_json=dict(spec.default_config))
        db.add(row)
    if body.enabled is not None:
        if not spec.toggleable and body.enabled is False:
            raise ValidationError(f"O módulo '{slug}' não pode ser desabilitado.")
        row.enabled = body.enabled
    if body.config is not None:
        row.config_json = {**dict(row.config_json or {}), **body.config}
    await db.flush()
    return ModuleOut(
        slug=slug, label=spec.label, kind=spec.kind, toggleable=spec.toggleable,
        enabled=row.enabled, config=dict(row.config_json or {}),
    )


# ---------------------------------------------------------------- dashboard / settings
@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(db: DbDep, _: CurrentAdmin):
    # Implementação completa na Fase 7/8; agora retorna zeros seguros.
    from app.modules.orders.models import Order

    orders_pending = await db.scalar(
        select(func.count()).select_from(Order).where(Order.status == "pending_payment")
    )
    return DashboardOut(
        orders_today=0,
        orders_pending=int(orders_pending or 0),
        revenue_month_cents=0,
        low_stock_count=0,
        recent_orders=[],
    )


@router.get("/settings")
async def get_settings(db: DbDep, _: CurrentAdmin):
    row = await db.get(StoreSettings, 1)
    if not row:
        return {}
    return {c.name: getattr(row, c.name) for c in StoreSettings.__table__.columns}
