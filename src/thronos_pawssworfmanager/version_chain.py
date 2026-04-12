"""Parent-hash version-chain validation."""

from __future__ import annotations

from collections.abc import Sequence

from .types import ChainNode, ValidationResult


def build_chain_node(version: int, manifest_hash: str, parent_hash: str | None) -> ChainNode:
    return ChainNode(version=version, manifest_hash=manifest_hash, parent_hash=parent_hash)


def validate_chain_transition(prev: ChainNode | None, curr: ChainNode) -> ValidationResult:
    if curr.version < 1:
        return ValidationResult(False, "invalid_version", "version must be >=1")

    if prev is None:
        if curr.version != 1:
            return ValidationResult(False, "invalid_genesis_version", "genesis version must be 1")
        if curr.parent_hash is not None:
            return ValidationResult(False, "invalid_genesis_parent", "genesis parent_hash must be None")
        return ValidationResult(True)

    if curr.version != prev.version + 1:
        return ValidationResult(False, "non_monotonic_version", "version must increase by 1")

    if curr.parent_hash != prev.manifest_hash:
        return ValidationResult(False, "parent_hash_mismatch", "parent hash must match previous manifest hash")

    return ValidationResult(True)


def verify_chain(nodes: Sequence[ChainNode]) -> ValidationResult:
    prev = None
    seen_versions: dict[int, str] = {}
    for node in nodes:
        if node.version in seen_versions and seen_versions[node.version] != node.manifest_hash:
            return ValidationResult(False, "fork_detected", "same version has different hash")
        seen_versions[node.version] = node.manifest_hash
        valid = validate_chain_transition(prev, node)
        if not valid.ok:
            return valid
        prev = node
    return ValidationResult(True)
