"""XChaCha20-Poly1305 envelope format validation (metadata only)."""

from __future__ import annotations

from collections.abc import Sequence

from .types import ValidationResult


_REQUIRED_FIELDS = ("version", "nonce_len", "tag_len", "kdf_profile")
_SUPPORTED_VERSION = "xchacha20poly1305-v1"


def envelope_version_id() -> str:
    return _SUPPORTED_VERSION


def required_envelope_fields() -> Sequence[str]:
    return _REQUIRED_FIELDS


def validate_envelope_header(header: dict) -> ValidationResult:
    for field in _REQUIRED_FIELDS:
        if field not in header:
            return ValidationResult(False, "missing_header_field", f"missing field: {field}")

    if header["version"] != _SUPPORTED_VERSION:
        return ValidationResult(False, "unsupported_envelope_version", "unsupported version")

    if header["nonce_len"] != 24:
        return ValidationResult(False, "invalid_nonce_len", "nonce_len must be 24")

    if header["tag_len"] != 16:
        return ValidationResult(False, "invalid_tag_len", "tag_len must be 16")

    if header["kdf_profile"] != "argon2id-v1":
        return ValidationResult(False, "unsupported_kdf_profile", "unsupported kdf profile")

    return ValidationResult(True)
