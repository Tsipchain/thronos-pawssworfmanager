"""delete_entry_intent transformation."""

from __future__ import annotations

from ..services.manifest_builder import base_manifest


def to_manifest(payload: dict) -> dict:
    vault_id = payload.get("vault_id")
    version = payload.get("version")
    entry_id = payload.get("entry_id")
    entries = payload.get("entries", [])

    if not vault_id:
        raise ValueError("missing_vault_id")
    if not isinstance(version, int) or version < 1:
        raise ValueError("invalid_version")
    if not entry_id:
        raise ValueError("missing_entry_id")
    if not isinstance(entries, list):
        raise ValueError("invalid_entries")

    filtered = [e for e in entries if not (isinstance(e, dict) and e.get("id") == entry_id)]
    if len(filtered) == len(entries):
        raise ValueError("entry_not_found")

    return base_manifest(
        vault_id=vault_id,
        version=version,
        action="delete_entry_intent",
        entries=filtered,
        metadata={"entry_id": entry_id},
    )
