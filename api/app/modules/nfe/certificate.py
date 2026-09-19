"""Validação do certificado digital A1 (.pfx/.p12) usado pra assinar as
NF-e. Só valida e extrai metadados aqui -- a assinatura de verdade acontece
em `sefaz_client.py`, na hora de emitir.
"""
from __future__ import annotations

from cryptography.hazmat.primitives.serialization import pkcs12

from app.core.errors import ValidationError


class CertificateInfo:
    def __init__(self, titular: str, validade_iso: str, is_expired: bool) -> None:
        self.titular = titular
        self.validade_iso = validade_iso
        self.is_expired = is_expired


def inspect_pfx(pfx_bytes: bytes, senha: str) -> CertificateInfo:
    """Abre o .pfx com a senha informada e extrai titular (CN) + validade.
    Levanta `ValidationError` com mensagem clara se a senha estiver errada ou
    o arquivo não for um certificado válido."""
    try:
        _key, cert, _extra_certs = pkcs12.load_key_and_certificates(
            pfx_bytes, senha.encode("utf-8")
        )
    except ValueError as exc:
        raise ValidationError(
            "Não foi possível abrir o certificado — confira o arquivo .pfx e a senha."
        ) from exc

    if cert is None:
        raise ValidationError("Arquivo não contém um certificado válido.")

    from datetime import UTC, datetime

    subject = cert.subject
    cn_attrs = subject.get_attributes_for_oid(_CN_OID())
    titular = cn_attrs[0].value if cn_attrs else "?"

    not_after = cert.not_valid_after_utc
    is_expired = not_after < datetime.now(UTC)

    return CertificateInfo(
        titular=titular,
        validade_iso=not_after.date().isoformat(),
        is_expired=is_expired,
    )


def _CN_OID():
    from cryptography.x509.oid import NameOID

    return NameOID.COMMON_NAME
