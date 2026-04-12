"""Canonical manifest encoding using JCS-style deterministic JSON output."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .types import ValidationResult

REQUIRED_TOP_LEVEL_FIELDS = ("vault_id", "version", "entries")


def validate_manifest_schema(manifest: Mapping[str, Any]) -> ValidationResult:
    if not isinstance(manifest, Mapping):
        return ValidationResult(False, "manifest_not_mapping", "manifest must be a mapping")

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in manifest:
            return ValidationResult(False, "missing_required_field", f"missing required field: {field}")

    if not isinstance(manifest["vault_id"], str) or not manifest["vault_id"]:
        return ValidationResult(False, "invalid_vault_id", "vault_id must be a non-empty string")

    if not isinstance(manifest["version"], int) or manifest["version"] < 1:
        return ValidationResult(False, "invalid_version", "version must be integer >= 1")

    if not isinstance(manifest["entries"], list):
        return ValidationResult(False, "invalid_entries", "entries must be a list")

    return ValidationResult(True)


def canonicalize_manifest(manifest: Mapping[str, Any]) -> bytes:
    schema = validate_manifest_schema(manifest)
    if not schema.ok:
        raise ValueError(f"{schema.code}: {schema.detail}")

    try:
        canonical = json.dumps(
            manifest,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"manifest_not_canonicalizable: {exc}") from exc

    return canonical.encode("utf-8")
