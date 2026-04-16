"""Deterministic manifest/state hashing."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from .canonical_manifest import canonicalize_manifest
from .hash_policy import HASH_ALGORITHM, HASH_HEX_LENGTH


def hash_algorithm_id() -> str:
    """Return the centralized hash policy identifier for deterministic core."""
    return HASH_ALGORITHM


def compute_manifest_hash(canonical_bytes: bytes) -> str:
    if canonical_bytes is None or len(canonical_bytes) == 0:
        raise ValueError("invalid_canonical_bytes")

    if HASH_ALGORITHM != "sha256":
        raise ValueError("unsupported_hash_policy")

    digest = hashlib.sha256(canonical_bytes).hexdigest()
    if len(digest) != HASH_HEX_LENGTH:
        raise ValueError("invalid_hash_length")
    return digest


def compute_state_hash(manifest: Mapping[str, Any]) -> str:
    canonical = canonicalize_manifest(manifest)
    return compute_manifest_hash(canonical)
