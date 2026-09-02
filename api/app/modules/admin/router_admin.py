"""Rotas administrativas: auth, usuários, módulos, dashboard, settings gerais."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
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


class _MfaVerifyIn(BaseModel):
    mfa_token: str
    code: str


class _CodeIn(BaseModel):
    code: str


class _PasswordIn(BaseModel):
    password: str


class _ProfileIn(BaseModel):
    name: str | None = None
    email: str | None = None


# ---------------------------------------------------------------- auth
@router.post("/auth/login")
async def login(
    body: AdminLoginIn,
    db: DbDep,
    _rl: Annotated[None, Depends(rate_limit("10/minute", scope="admin-login"))],
):
    admin = await service.verify_credentials(db, body.email, body.password)
    if admin.totp_enabled:
        return {"mfa_required": True, "mfa_token": service.mfa_challenge_token(str(admin.id))}
    pair = await service.issue_session(db, admin)
    return {"mfa_required": False, **TokenOut(**pair).model_dump()}


@router.post("/auth/2fa/verify", response_model=TokenOut)
async def mfa_verify(
    body: _MfaVerifyIn,
    db: DbDep,
    _rl: Annotated[None, Depends(rate_limit("10/minute", scope="admin-login"))],
):
    _, pair = await service.resolve_mfa_challenge(db, body.mfa_token, body.code)
    return TokenOut(**pair)


@router.post("/auth/2fa/start")
async def mfa_start(db: DbDep, admin: CurrentAdmin) -> dict:
    return await service.start_2fa(db, admin)


@router.post("/auth/2fa/confirm")
async def mfa_confirm(body: _CodeIn, db: DbDep, admin: CurrentAdmin) -> dict:
    codes = await service.confirm_2fa(db, admin, body.code)
    return {"recovery_codes": codes}


@router.post("/auth/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def mfa_disable(body: _PasswordIn, db: DbDep, admin: CurrentAdmin) -> None:
    await service.disable_2fa(db, admin, body.password)


@router.patch("/auth/me", response_model=AdminUserOut)
async def update_me(body: _ProfileIn, db: DbDep, admin: CurrentAdmin):
    updated = await service.update_own_profile(db, admin, body.name, body.email)
    return AdminUserOut.model_validate({**updated.__dict__, "id": str(updated.id)})


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
    metric: str = "revenue",
):
    from datetime import UTC, datetime, timedelta

    from app.modules.orders.models import Order, OrderItem, OrderNumberCounter

    now = datetime.now(UTC)
    if metric not in ("revenue", "canceled", "refunded"):
        metric = "revenue"

    # "AAAA-MM-DD" é interpretado como dia no FUSO DA LOJA e convertido para
    # UTC (início/fim do dia). Sem isso, o "Até" cortava o dia e pedidos da
    # noite caíam no dia errado — o filtro de datas não batia com a lista.
    from app.shared.timez import parse_day_bound as _parse_bound

    def _parse(raw: str | None, *, end: bool) -> datetime | None:
        return _parse_bound(raw, end=end)

    # Janela: filtro informado, senão os últimos 30 dias.
    win_start = _parse(date_from, end=False)
    win_end = _parse(date_to, end=True)
    if win_start is None and win_end is None:
        win_end = now
        win_start = now - timedelta(days=30)
    elif win_start is None:
        win_start = win_end - timedelta(days=30)
    elif win_end is None:
        win_end = now
    window_days = max(1, (win_end - win_start).days or 1)

    def _in_window(col):
        return [col >= win_start, col <= win_end]

    orders_period = await db.scalar(
        select(func.count()).select_from(Order).where(*_in_window(Order.placed_at))
    )
    orders_pending = await db.scalar(
        select(func.count()).select_from(Order).where(Order.status == "pending_payment")
    )
    orders_canceled = await db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.status == "canceled", *_in_window(Order.created_at))
    )
    orders_refunded = await db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.status == "refunded", *_in_window(Order.created_at))
    )
    revenue_period = await db.scalar(
        select(func.coalesce(func.sum(Order.grand_total_cents), 0)).where(
            Order.payment_status == "paid", *_in_window(Order.placed_at)
        )
    )

    _to_ship_status = ("paid", "processing", "tracking_available")
    orders_to_ship = await db.scalar(
        select(func.count()).select_from(Order).where(Order.status.in_(_to_ship_status))
    )
    orders_late = await db.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.status.in_(_to_ship_status),
            Order.placed_at < now - timedelta(days=2),
        )
    )
    # total histórico de pedidos — contador monotônico por ano, nunca diminui.
    total_all_time = await db.scalar(
        select(func.coalesce(func.sum(OrderNumberCounter.last_seq), 0))
    )

    # --- série temporal: período atual x período anterior (mesma duração) --
    span = max(win_end - win_start, timedelta(hours=1))
    if span <= timedelta(days=2):
        step = timedelta(hours=1)
    else:
        days = span.days + 1
        step = timedelta(days=max(1, days // 31 + (1 if days % 31 else 0)))
    n_buckets = max(1, min(60, int(span / step) + 1))

    async def _series(anchor_start):
        pts = []
        for i in range(n_buckets):
            b0 = anchor_start + step * i
            b1 = b0 + step
            if metric == "revenue":
                val = await db.scalar(
                    select(func.coalesce(func.sum(Order.grand_total_cents), 0)).where(
                        Order.payment_status == "paid",
                        Order.placed_at >= b0,
                        Order.placed_at < b1,
                    )
                )
            else:
                st = "canceled" if metric == "canceled" else "refunded"
                val = await db.scalar(
                    select(func.count())
                    .select_from(Order)
                    .where(Order.status == st, Order.created_at >= b0, Order.created_at < b1)
                )
            label = b0.strftime("%d/%m") if step >= timedelta(days=1) else b0.strftime("%d/%m %Hh")
            pts.append({"label": label, "cents": int(val or 0)})
        return pts

    series_current = await _series(win_start)
    series_previous = await _series(win_start - step * n_buckets)

    # --- curva ABC + top 10 (por receita dos itens de pedidos pagos) -------
    item_conds = [
        Order.payment_status == "paid",
        Order.placed_at >= win_start,
        Order.placed_at <= win_end,
    ]

    agg_rows = (
        await db.execute(
            select(
                func.coalesce(OrderItem.name, "—").label("name"),
                func.min(OrderItem.sku).label("sku"),
                func.sum(OrderItem.quantity).label("units"),
                func.sum(OrderItem.total_cents).label("revenue"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(*item_conds)
            .group_by(OrderItem.name)
            .order_by(func.sum(OrderItem.total_cents).desc())
        )
    ).all()

    total_rev = sum(int(r.revenue or 0) for r in agg_rows) or 1
    abc_curve = []
    running = 0
    for r in agg_rows:
        rev = int(r.revenue or 0)
        running += rev
        cum = running / total_rev * 100
        cls = "A" if cum <= 80 else "B" if cum <= 95 else "C"
        abc_curve.append(
            {"name": r.name, "revenue_cents": rev, "cum_pct": round(cum, 1), "cls": cls}
        )

    top_products = [
        {
            "name": r.name,
            "sku": r.sku or "",
            "units": int(r.units or 0),
            "revenue_cents": int(r.revenue or 0),
        }
        for r in agg_rows[:10]
    ]

    return DashboardOut(
        window_days=window_days,
        orders_period=int(orders_period or 0),
        orders_pending=int(orders_pending or 0),
        orders_late=int(orders_late or 0),
        orders_to_ship=int(orders_to_ship or 0),
        orders_canceled=int(orders_canceled or 0),
        orders_refunded=int(orders_refunded or 0),
        revenue_period_cents=int(revenue_period or 0),
        total_orders_all_time=int(total_all_time or 0),
        series_metric=metric,
        series_current=series_current,
        series_previous=series_previous,
        abc_curve=abc_curve,
        top_products=top_products,
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
        return {"host": None, "configured": False, "password_set": False}
    return {
        "host": row.host,
        "port": row.port,
        "username": row.username,
        "use_tls": row.use_tls,
        "use_ssl": row.use_ssl,
        "from_email": row.from_email,
        "from_name": row.from_name,
        "configured": bool(row.host),
        # nunca devolve a senha; só diz se há uma salva (o painel mostra •••• fixo)
        "password_set": bool(row.password_enc),
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
    # o painel manda a senha só quando o usuário realmente digitou outra; o
    # placeholder de bolinhas nunca chega aqui como senha nova.
    pwd = payload.get("password")
    if pwd and pwd.strip() and set(pwd) != {"•"}:
        row.password_enc = pwd  # TODO F9: cifrar em repouso
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return {"ok": True, "password_set": bool(row.password_enc)}


@router.post("/smtp/test")
async def test_smtp(
    payload: dict, db: DbDep, _: Annotated[AdminUser, Depends(require_role("admin"))]
):
    from app.shared import mailer

    to = payload.get("to")
    if not to:
        raise ValidationError("Informe o e-mail de destino.")
    res = await mailer.send_test(db, to)
    await db.commit()
    if not res["ok"]:
        raise ValidationError(f"SMTP recusou o envio: {res['error']}")
    return {"sent": True}
