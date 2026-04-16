"""add_entry_intent transformation."""

from __future__ import annotations

from ..services.manifest_builder import base_manifest


def to_manifest(payload: dict) -> dict:
    vault_id = payload.get("vault_id")
    version = payload.get("version")
    entry = payload.get("entry")
    entries = payload.get("entries", [])
    if not vault_id:
        raise ValueError("missing_vault_id")
    if not isinstance(version, int) or version < 1:
        raise ValueError("invalid_version")
    if not isinstance(entry, dict):
        raise ValueError("invalid_entry")
    if not isinstance(entries, list):
        raise ValueError("invalid_entries")

    return base_manifest(
        vault_id=vault_id,
        version=version,
        action="add_entry_intent",
        entries=[*entries, entry],
        metadata={"entry_id": entry.get("id", "")},
    )
