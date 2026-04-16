"""create_vault_intent transformation."""

from __future__ import annotations

from ..services.manifest_builder import base_manifest


def to_manifest(payload: dict) -> dict:
    vault_id = payload.get("vault_id")
    if not vault_id:
        raise ValueError("missing_vault_id")
    initial_entries = payload.get("initial_entries", [])
    if not isinstance(initial_entries, list):
        raise ValueError("invalid_initial_entries")

    return base_manifest(
        vault_id=vault_id,
        version=1,
        action="create_vault_intent",
        entries=initial_entries,
        metadata={"note": payload.get("note", "")},
    )
