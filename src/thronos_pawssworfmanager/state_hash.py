"""Deterministic manifest/state hashing."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from .canonical_manifest import canonicalize_manifest

_HASH_ALGO = "sha256"


def hash_algorithm_id() -> str:
    return _HASH_ALGO


def compute_manifest_hash(canonical_bytes: bytes) -> str:
    if canonical_bytes is None or len(canonical_bytes) == 0:
        raise ValueError("invalid_canonical_bytes")
    return hashlib.sha256(canonical_bytes).hexdigest()


def compute_state_hash(manifest: Mapping[str, Any]) -> str:
    canonical = canonicalize_manifest(manifest)
    return compute_manifest_hash(canonical)
