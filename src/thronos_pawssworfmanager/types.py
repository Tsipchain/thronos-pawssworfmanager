"""Core deterministic-domain types for Phase 1."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    code: str = "ok"
    detail: str = ""


@dataclass(frozen=True)
class ChainNode:
    version: int
    manifest_hash: str
    parent_hash: str | None


@dataclass(frozen=True)
class Argon2idParams:
    memory_kib: int
    time_cost: int
    parallelism: int
    salt_len: int = 16
    key_len: int = 32
    profile_version: str = "argon2id-v1"
