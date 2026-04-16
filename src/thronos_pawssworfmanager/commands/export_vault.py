"""export_vault_intent transformation (manifest only, no export execution)."""

from __future__ import annotations

from ..services.manifest_builder import base_manifest


def to_manifest(payload: dict) -> dict:
    vault_id = payload.get("vault_id")
    version = payload.get("version")
    entries = payload.get("entries", [])

    if not vault_id:
        raise ValueError("missing_vault_id")
    if not isinstance(version, int) or version < 1:
        raise ValueError("invalid_version")
    if not isinstance(entries, list):
        raise ValueError("invalid_entries")

    return base_manifest(
        vault_id=vault_id,
        version=version,
        action="export_vault_intent",
        entries=entries,
        metadata={"export": "intent_only_no_runtime"},
    )
