"""Rotas administrativas: auth, usuários, módulos, dashboard, settings gerais."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.core.errors import ValidationError
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
async def dashboard(
    db: DbDep,
    _: CurrentAdmin,
    date_from: str | None = None,
    date_to: str | None = None,
):
    from datetime import UTC, date, datetime, time

    from app.modules.orders.models import Order
    from app.modules.products.models import ProductVariant

    now = datetime.now(UTC)

    def _parse(raw: str | None, *, end: bool) -> datetime | None:
        """Aceita ISO completo (com fuso, vindo do navegador) ou só a data."""
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            pass
        try:
            d = date.fromisoformat(raw)
            return datetime.combine(d, time.max if end else time.min, tzinfo=UTC)
        except ValueError:
            return None

    # janela de análise: filtro informado, senão "hoje" (contagem) e "mês" (receita)
    win_start = _parse(date_from, end=False)
    win_end = _parse(date_to, end=True)

    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ranged = win_start is not None or win_end is not None

    count_start = win_start if ranged else start_day
    rev_start = win_start if ranged else start_month

    def _between(col):
        conds = []
        if count_start is not None:
            conds.append(col >= count_start)
        if win_end is not None:
            conds.append(col <= win_end)
        return conds

    orders_today = await db.scalar(
        select(func.count()).select_from(Order).where(*_between(Order.placed_at))
    )
    orders_pending = await db.scalar(
        select(func.count()).select_from(Order).where(Order.status == "pending_payment")
    )
    rev_conds = [Order.payment_status == "paid"]
    if rev_start is not None:
        rev_conds.append(Order.placed_at >= rev_start)
    if win_end is not None:
        rev_conds.append(Order.placed_at <= win_end)
    revenue_month = await db.scalar(
        select(func.coalesce(func.sum(Order.grand_total_cents), 0)).where(*rev_conds)
    )
    low_stock = await db.scalar(
        select(func.count()).select_from(ProductVariant).where(
            ProductVariant.is_active.is_(True), ProductVariant.stock_qty <= 3
        )
    )
    recent_stmt = select(Order)
    if ranged:
        recent_stmt = recent_stmt.where(*_between(Order.placed_at))
    recent = await db.scalars(
        recent_stmt.order_by(Order.placed_at.desc().nullslast()).limit(10)
    )
    return DashboardOut(
        orders_today=int(orders_today or 0),
        orders_pending=int(orders_pending or 0),
        revenue_month_cents=int(revenue_month or 0),
        low_stock_count=int(low_stock or 0),
        recent_orders=[
            {
                "number": o.number,
                "status": o.status,
                "payment_status": o.payment_status,
                "total_cents": o.grand_total_cents,
                "email": o.email,
                "placed_at": o.placed_at.isoformat() if o.placed_at else None,
            }
            for o in recent
        ],
    )


@router.get("/settings")
async def get_settings(db: DbDep, _: CurrentAdmin):
    row = await db.get(StoreSettings, 1)
    if not row:
        return {}
    return {c.name: getattr(row, c.name) for c in StoreSettings.__table__.columns}


@router.put("/settings")
async def update_settings(payload: dict, db: DbDep, _: Annotated[AdminUser, Depends(require_role("admin"))]):
    from datetime import UTC, datetime

    row = await db.get(StoreSettings, 1)
    if not row:
        row = StoreSettings(id=1)
        db.add(row)
    allowed = {c.name for c in StoreSettings.__table__.columns} - {"id"}
    for k, v in payload.items():
        if k in allowed:
            setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return {c.name: getattr(row, c.name) for c in StoreSettings.__table__.columns}


# ---------------------------------------------------------------- SMTP
@router.get("/smtp")
async def get_smtp(db: DbDep, _: Annotated[AdminUser, Depends(require_role("admin"))]):
    from app.modules.admin.models import SmtpSettings

    row = await db.get(SmtpSettings, 1)
    if not row:
        return {"host": None, "configured": False}
    return {
        "host": row.host,
        "port": row.port,
        "username": row.username,
        "use_tls": row.use_tls,
        "use_ssl": row.use_ssl,
        "from_email": row.from_email,
        "from_name": row.from_name,
        "configured": bool(row.host),
    }


@router.put("/smtp")
async def update_smtp(payload: dict, db: DbDep, _: Annotated[AdminUser, Depends(require_role("admin"))]):
    from datetime import UTC, datetime

    from app.modules.admin.models import SmtpSettings

    row = await db.get(SmtpSettings, 1)
    if not row:
        row = SmtpSettings(id=1)
        db.add(row)
    for k in ("host", "port", "username", "use_tls", "use_ssl", "from_email", "from_name"):
        if k in payload:
            setattr(row, k, payload[k])
    if payload.get("password"):
        row.password_enc = payload["password"]  # TODO F9: cifrar em repouso
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return {"ok": True}


@router.post("/smtp/test")
async def test_smtp(
    payload: dict, db: DbDep, _: Annotated[AdminUser, Depends(require_role("admin"))]
):
    from app.shared import mailer

    to = payload.get("to")
    if not to:
        raise ValidationError("Informe o e-mail de destino.")
    ok = await mailer.send_test(db, to)
    return {"sent": ok}
