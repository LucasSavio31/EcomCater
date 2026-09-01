"""Regra de negócio do módulo `analytics`."""
from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.modules.analytics.models import AnalyticsSettings

_ID_PATTERNS = {
    "gtm_container_id": re.compile(r"^GTM-[A-Z0-9]{4,10}$", re.I),
    "ga4_measurement_id": re.compile(r"^G-[A-Z0-9]{6,12}$", re.I),
    "google_ads_conversion_id": re.compile(r"^AW-\d{6,13}$", re.I),
    "meta_pixel_id": re.compile(r"^\d{6,20}$"),
}

_STR_FIELDS = {
    "gtm_container_id",
    "ga4_measurement_id",
    "google_ads_conversion_id",
    "google_ads_purchase_label",
    "meta_pixel_id",
    "meta_test_event_code",
}
_BOOL_FIELDS = {
    "gtm_enabled",
    "ga4_enabled",
    "google_ads_enabled",
    "meta_pixel_enabled",
    "meta_capi_enabled",
}


async def get_settings(db: AsyncSession) -> AnalyticsSettings:
    row = await db.get(AnalyticsSettings, 1)
    if not row:
        row = AnalyticsSettings(id=1)
        db.add(row)
        await db.flush()
    return row


def _clean_id(field: str, value: str) -> str:
    value = value.strip()
    pat = _ID_PATTERNS.get(field)
    if pat and value and not pat.fullmatch(value):
        raise ValidationError(f"Formato inválido para '{field}': {value!r}.")
    # normaliza o prefixo em maiúsculas (GTM-, G-, AW-)
    for prefix in ("GTM-", "G-", "AW-"):
        if value.upper().startswith(prefix):
            return prefix + value[len(prefix):]
    return value


async def update_settings(db: AsyncSession, data: dict) -> AnalyticsSettings:
    row = await get_settings(db)

    for key in _BOOL_FIELDS:
        if data.get(key) is not None:
            setattr(row, key, bool(data[key]))

    for key in _STR_FIELDS:
        if key in data and data[key] is not None:
            raw = str(data[key]).strip()
            setattr(row, key, _clean_id(key, raw) if raw else None)

    # segredos: "" limpa, ausente/None mantém
    token = data.get("meta_capi_access_token")
    if token is not None:
        row.meta_capi_access_token = token.strip() or None
    ga4_secret = data.get("ga4_api_secret")
    if ga4_secret is not None:
        row.ga4_api_secret = ga4_secret.strip() or None

    # coerência: não dá pra ligar a CAPI sem token nem sem pixel
    if row.meta_capi_enabled and not (row.meta_capi_access_token and row.meta_pixel_id):
        raise ValidationError(
            "Para ativar a API de Conversões da Meta informe o ID do Pixel e o token da API."
        )
    for flag, ident in (
        ("gtm_enabled", "gtm_container_id"),
        ("ga4_enabled", "ga4_measurement_id"),
        ("google_ads_enabled", "google_ads_conversion_id"),
        ("meta_pixel_enabled", "meta_pixel_id"),
    ):
        if getattr(row, flag) and not getattr(row, ident):
            raise ValidationError(f"Preencha '{ident}' para ativar essa integração.")

    row.updated_at = datetime.now(UTC)
    await db.flush()
    return row


def to_public(row: AnalyticsSettings) -> dict:
    return {
        "gtm_enabled": row.gtm_enabled,
        "gtm_container_id": row.gtm_container_id,
        "ga4_enabled": row.ga4_enabled,
        "ga4_measurement_id": row.ga4_measurement_id,
        "google_ads_enabled": row.google_ads_enabled,
        "google_ads_conversion_id": row.google_ads_conversion_id,
        "google_ads_purchase_label": row.google_ads_purchase_label,
        "meta_pixel_enabled": row.meta_pixel_enabled,
        "meta_pixel_id": row.meta_pixel_id,
    }


def to_admin(row: AnalyticsSettings) -> dict:
    return {
        **to_public(row),
        "meta_capi_enabled": row.meta_capi_enabled,
        "meta_test_event_code": row.meta_test_event_code,
        "meta_capi_token_set": bool(row.meta_capi_access_token),
        "ga4_api_secret_set": bool(row.ga4_api_secret),
    }
