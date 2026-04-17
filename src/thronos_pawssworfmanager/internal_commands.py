"""Internal command and write-intent contract layer (no execution)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .api_versioning import DEFAULT_API_VERSION

ALLOWED_COMMAND_TYPES = (
    "vault.prepare_write_intent",
    "vault.prepare_export_intent",
    "vault.prepare_import_intent",
)


@dataclass(frozen=True)
class RequestIdentity:
    request_id: str
    idempotency_key: str
    actor_ref: str


@dataclass(frozen=True)
class WriteIntent:
    intent_id: str
    command_type: str
    vault_id: str
    manifest_hash: str | None
    parent_hash: str | None
    expected_version: int | None


@dataclass(frozen=True)
class InternalCommand:
    api_version: str
    identity: RequestIdentity
    intent: WriteIntent
    payload: dict[str, Any]


def command_schema_summary() -> dict[str, Any]:
    return {
        "api_version": DEFAULT_API_VERSION,
        "command_types": list(ALLOWED_COMMAND_TYPES),
        "identity_fields": ["request_id", "idempotency_key", "actor_ref"],
        "intent_fields": [
            "intent_id",
            "command_type",
            "vault_id",
            "manifest_hash",
            "parent_hash",
            "expected_version",
        ],
        "execution": {
            "enabled": False,
            "reason": "sensitive_features_disabled",
        },
    }
