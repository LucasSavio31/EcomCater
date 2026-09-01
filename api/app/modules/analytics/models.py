"""Modelo do módulo `analytics` — tags de marketing (linha única, id=1).

Guarda a configuração dos pixels/tags: Google Tag Manager, Google Analytics 4,
Google Ads e Meta (Pixel do navegador + API de Conversões server-side).

O token da API de Conversões da Meta é segredo: nunca é exposto na rota pública
nem devolvido pela rota de admin (só um booleano `meta_capi_token_set`).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    SmallInteger,
    String,
    Text,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base


class AnalyticsSettings(Base):
    __tablename__ = "analytics_settings"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)

    # Google Tag Manager
    gtm_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    gtm_container_id: Mapped[str | None] = mapped_column(String(20))  # GTM-XXXXXXX

    # Google Analytics 4
    ga4_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    ga4_measurement_id: Mapped[str | None] = mapped_column(String(20))  # G-XXXXXXXXXX
    # Measurement Protocol (server-side) — usado só para `refund` do backend.
    # Segredo: nunca exposto na rota pública/admin (só `ga4_api_secret_set`).
    ga4_api_secret: Mapped[str | None] = mapped_column(Text)

    # Google Ads
    google_ads_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    google_ads_conversion_id: Mapped[str | None] = mapped_column(String(20))  # AW-XXXXXXXXX
    google_ads_purchase_label: Mapped[str | None] = mapped_column(String(60))

    # Meta Pixel (browser)
    meta_pixel_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    meta_pixel_id: Mapped[str | None] = mapped_column(String(32))

    # Meta Conversions API (server-side)
    meta_capi_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    meta_capi_access_token: Mapped[str | None] = mapped_column(Text)
    meta_test_event_code: Mapped[str | None] = mapped_column(String(40))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
