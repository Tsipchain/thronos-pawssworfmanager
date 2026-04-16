"""Centralized hash policy for deterministic core."""

HASH_ALGORITHM = "sha256"
HASH_HEX_LENGTH = 64


def hash_policy_id() -> str:
    return HASH_ALGORITHM
