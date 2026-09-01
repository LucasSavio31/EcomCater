"""DTOs do módulo `analytics`."""
from __future__ import annotations

from pydantic import BaseModel


class AnalyticsPublicConfig(BaseModel):
    """O que a loja precisa para injetar as tags no `<head>` (sem segredos)."""

    gtm_enabled: bool
    gtm_container_id: str | None

    ga4_enabled: bool
    ga4_measurement_id: str | None

    google_ads_enabled: bool
    google_ads_conversion_id: str | None
    google_ads_purchase_label: str | None

    meta_pixel_enabled: bool
    meta_pixel_id: str | None


class AnalyticsAdminConfig(AnalyticsPublicConfig):
    meta_capi_enabled: bool
    meta_test_event_code: str | None
    meta_capi_token_set: bool
    ga4_api_secret_set: bool


class AnalyticsUpdateIn(BaseModel):
    gtm_enabled: bool | None = None
    gtm_container_id: str | None = None

    ga4_enabled: bool | None = None
    ga4_measurement_id: str | None = None
    # string vazia limpa o api_secret; None (ausente) mantém o atual
    ga4_api_secret: str | None = None

    google_ads_enabled: bool | None = None
    google_ads_conversion_id: str | None = None
    google_ads_purchase_label: str | None = None

    meta_pixel_enabled: bool | None = None
    meta_pixel_id: str | None = None

    meta_capi_enabled: bool | None = None
    meta_test_event_code: str | None = None
    # string vazia limpa o token; None (ausente) mantém o atual
    meta_capi_access_token: str | None = None
