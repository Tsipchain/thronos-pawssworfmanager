"""Persistence, blob, and attestation receipt schemas for adapter boundary contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PersistenceReceipt:
    operation: str
    status: str
    backend: str
    manifest_hash: str
    attempts: int
    max_attempts: int
    retryable: bool
    failure_class: str | None
    error_code: str | None
    idempotency_scope: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BlobWriteReceipt:
    operation: str
    status: str
    backend: str
    blob_id: str
    blob_hash: str | None
    verified: bool | None
    execution_enabled: bool
    failure_class: str | None
    error_code: str | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AttestationReceipt:
    operation: str
    backend: str
    network: str
    status: str
    lifecycle_state: str
    attestation_id: str | None
    tx_hash: str | None
    submitted_at: str | None
    attempts: int
    max_attempts: int
    retryable: bool
    failure_class: str | None
    error_code: str | None
    execution_mode: str
    dry_run: bool

    def to_dict(self) -> dict:
        return asdict(self)
