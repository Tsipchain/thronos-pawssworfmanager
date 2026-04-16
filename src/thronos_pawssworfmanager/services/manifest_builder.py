"""Pure manifest construction utilities."""

from __future__ import annotations


def base_manifest(vault_id: str, version: int, action: str, entries: list[dict], metadata: dict | None = None) -> dict:
    return {
        "vault_id": vault_id,
        "version": version,
        "entries": entries,
        "action": action,
        "metadata": metadata or {},
    }
