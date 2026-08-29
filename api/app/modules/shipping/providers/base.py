"""Interface abstrata de provedores de frete.

Adicionar uma transportadora nova = implementar `ShippingProvider` e registrar
em `shipping/module.py`. Nada mais no sistema muda.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Package:
    weight_grams: int
    length_mm: int
    width_mm: int
    height_mm: int
    insurance_cents: int = 0
    quantity: int = 1


@dataclass(slots=True)
class ShippingRate:
    id: str                 # id da opção (service id do provedor)
    service: str            # nome do serviço (ex.: "SEDEX", "PAC", ".Package")
    carrier: str            # transportadora (ex.: "Correios", "Jadlog")
    price_cents: int
    delivery_days: int
    provider: str = "melhor_envio"
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "service": self.service,
            "carrier": self.carrier,
            "price_cents": self.price_cents,
            "delivery_days": self.delivery_days,
            "provider": self.provider,
            **({"extra": self.extra} if self.extra else {}),
        }


@dataclass(slots=True)
class TrackingUpdate:
    provider_shipment_id: str
    status: str            # POSTADO | EM_TRANSITO | ENTREGUE  (normalizado)
    raw_status: str
    tracking_code: str | None = None
    occurred_at: str | None = None


class ShippingProvider(ABC):
    slug: str = "base"

    @abstractmethod
    async def quote(
        self, *, origin_zip: str, dest_zip: str, packages: list[Package]
    ) -> list[ShippingRate]:
        ...

    def parse_webhook(self, headers: dict[str, str], body: dict) -> TrackingUpdate | None:
        """Traduz um evento de rastreio do provedor para `TrackingUpdate`.

        Retorna None se o evento não for relevante para o status do pedido.
        """
        return None

    def verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool:
        return True
