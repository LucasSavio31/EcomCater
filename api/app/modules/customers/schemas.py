"""DTOs do módulo `customers`."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class CustomerOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    phone: str | None = None
    cpf: str | None = None

    model_config = {"from_attributes": True}


class CustomerUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = None
    cpf: str | None = Field(default=None, min_length=11, max_length=11)
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class AddressIn(BaseModel):
    label: str = "Endereço"
    recipient_name: str
    zip: str = Field(min_length=8, max_length=8)
    street: str
    number: str
    complement: str | None = None
    district: str
    city: str
    state: str = Field(min_length=2, max_length=2)
    is_default: bool = False


class AddressOut(AddressIn):
    id: str

    model_config = {"from_attributes": True}
