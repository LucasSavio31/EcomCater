"""DTOs do módulo `domains`."""
from __future__ import annotations

from pydantic import BaseModel, Field


class DomainsConfigIn(BaseModel):
    aapanel_url: str | None = None
    aapanel_api_key: str | None = None
    cloudflare_api_token: str | None = None
    server_ip: str | None = None


class DomainIn(BaseModel):
    hostname: str = Field(min_length=3, max_length=255)


class DomainOut(BaseModel):
    id: str
    hostname: str
    is_primary: bool
    status: str
    dns_managed_by_cloudflare: bool
    ssl_status: str
    last_error: str | None
    last_checked_at: str | None
    admin_hostname: str
    api_hostname: str
    cloudflare_nameservers: list[str] | None
    dns_confirmed: bool
