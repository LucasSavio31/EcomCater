"""2FA (TOTP) — helpers de segredo, QR e verificação."""
from __future__ import annotations

import hashlib
import io
import secrets

import pyotp
import segno

_ISSUER = "Loja — Admin"


def new_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, account: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account, issuer_name=_ISSUER)


def qr_svg(uri: str) -> str:
    buf = io.BytesIO()
    segno.make(uri, error="m").save(buf, kind="svg", scale=4, border=2, dark="#111111")
    return buf.getvalue().decode("utf-8")


def verify_totp(secret: str | None, code: str) -> bool:
    if not secret:
        return False
    code = "".join(ch for ch in (code or "") if ch.isdigit())
    if len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def hash_code(raw: str) -> str:
    return hashlib.sha256(raw.strip().upper().encode()).hexdigest()


def gen_recovery_codes(n: int = 8) -> list[str]:
    # formato XXXX-XXXX, fácil de digitar
    return [
        f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}" for _ in range(n)
    ]
