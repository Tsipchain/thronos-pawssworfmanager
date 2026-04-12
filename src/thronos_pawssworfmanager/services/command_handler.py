"""Pure deterministic command execution pipeline (no side effects)."""

from __future__ import annotations

import base64

from ..canonical_manifest import canonicalize_manifest
from ..state_hash import compute_manifest_hash
from ..version_chain import build_chain_node, validate_chain_transition
from ..commands import add_entry, create_vault, delete_entry, export_vault, update_entry

_COMMANDS = {
    "create_vault": create_vault.to_manifest,
    "add_entry": add_entry.to_manifest,
    "update_entry": update_entry.to_manifest,
    "delete_entry": delete_entry.to_manifest,
    "export_vault": export_vault.to_manifest,
}


def supported_commands() -> list[str]:
    return sorted(_COMMANDS.keys())


def _previous_node_from_payload(payload: dict, version: int):
    if version == 1:
        return None

    prev = payload.get("prev_chain_node")
    if not isinstance(prev, dict):
        raise ValueError("missing_prev_chain_node")

    prev_version = prev.get("version")
    prev_manifest_hash = prev.get("manifest_hash")
    prev_parent_hash = prev.get("parent_hash")

    if prev_version != version - 1:
        raise ValueError("invalid_prev_chain_version")
    if not isinstance(prev_manifest_hash, str) or not prev_manifest_hash:
        raise ValueError("invalid_prev_manifest_hash")

    return build_chain_node(prev_version, prev_manifest_hash, prev_parent_hash)


def handle_command(command: str, payload: dict) -> dict:
    builder = _COMMANDS.get(command)
    if builder is None:
        raise ValueError("unsupported_command")

    if "parent_hash" in payload:
        raise ValueError("external_parent_hash_not_allowed")

    manifest = builder(payload)
    canonical_bytes = canonicalize_manifest(manifest)
    manifest_hash = compute_manifest_hash(canonical_bytes)

    version = manifest["version"]
    prev = _previous_node_from_payload(payload, version)
    parent_hash = None if prev is None else prev.manifest_hash
    chain_node = build_chain_node(version, manifest_hash, parent_hash)

    transition = validate_chain_transition(prev, chain_node)
    if not transition.ok:
        raise ValueError(f"invalid_chain_transition:{transition.code}")

    return {
        "manifest": manifest,
        "canonical_bytes": base64.b64encode(canonical_bytes).decode("ascii"),
        "canonical_bytes_encoding": "base64",
        "manifest_hash": manifest_hash,
        "chain_node": {
            "version": chain_node.version,
            "manifest_hash": chain_node.manifest_hash,
            "parent_hash": chain_node.parent_hash,
        },
    }
