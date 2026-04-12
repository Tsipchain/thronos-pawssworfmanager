"""Validation boundaries for internal future-sensitive commands."""

from __future__ import annotations

import re
from uuid import UUID

from .api_versioning import DEFAULT_API_VERSION
from .error_model import ERR_COMMAND_EXECUTION_DISABLED, ERR_COMMAND_VALIDATION_FAILED
from .internal_commands import ALLOWED_COMMAND_TYPES, InternalCommand
from .types import ValidationResult

_IDEMPOTENCY_RE = re.compile(r"^[A-Za-z0-9_.:-]{8,128}$")



def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def validate_internal_command(command: InternalCommand) -> ValidationResult:
    if command.api_version != DEFAULT_API_VERSION:
        return ValidationResult(False, "invalid_api_version", "command api_version not supported")

    if command.intent.command_type not in ALLOWED_COMMAND_TYPES:
        return ValidationResult(False, "invalid_command_type", "command type is not allowed")

    if not _is_uuid(command.identity.request_id):
        return ValidationResult(False, "invalid_request_id", "request_id must be uuid")

    if not _IDEMPOTENCY_RE.match(command.identity.idempotency_key):
        return ValidationResult(False, "invalid_idempotency_key", "idempotency_key format invalid")

    if not command.identity.actor_ref:
        return ValidationResult(False, "missing_actor_ref", "actor_ref is required")

    if not command.intent.vault_id:
        return ValidationResult(False, "missing_vault_id", "vault_id is required")

    if command.intent.expected_version is not None and command.intent.expected_version < 1:
        return ValidationResult(False, "invalid_expected_version", "expected_version must be >= 1")

    return ValidationResult(True)


def build_command_result(command: InternalCommand) -> dict:
    validation = validate_internal_command(command)
    if not validation.ok:
        return {
            "accepted": False,
            "executed": False,
            "code": ERR_COMMAND_VALIDATION_FAILED,
            "validation_code": validation.code,
            "detail": validation.detail,
        }

    return {
        "accepted": True,
        "executed": False,
        "code": ERR_COMMAND_EXECUTION_DISABLED,
        "detail": "command validated but execution is disabled in current milestone",
    }
