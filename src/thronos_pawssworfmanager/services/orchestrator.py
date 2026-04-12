"""Command orchestrator for controlled side effects."""

from __future__ import annotations

import base64

from ..adapters.attestation import AttestationAdapter
from ..adapters.blob_storage import BlobStorageAdapter, BlobStorageError
from ..adapters.manifest_store import ManifestStoreAdapter
from ..adapters.schemas import AttestationReceipt, BlobWriteReceipt, PersistenceReceipt
from .retry_semantics import RetryPolicy, classify_failure, is_retryable


class CommandOrchestrator:
    def __init__(
        self,
        manifest_store: ManifestStoreAdapter,
        attestation: AttestationAdapter,
        blob_storage: BlobStorageAdapter | None = None,
        retry_policy: RetryPolicy | None = None,
        manifest_backend: str = "in_memory",
        blob_backend: str = "in_memory",
        attestation_backend: str = "fake",
        idempotency_scope: str = "single_instance_memory",
        execution_enabled: bool = False,
    ):
        self.manifest_store = manifest_store
        self.attestation = attestation
        self.blob_storage = blob_storage
        self.retry_policy = retry_policy or RetryPolicy()
        self.manifest_backend = manifest_backend
        self.blob_backend = blob_backend
        self.attestation_backend = attestation_backend
        self.idempotency_scope = idempotency_scope
        self.execution_enabled = execution_enabled

    def execute(self, command_result: dict) -> dict:
        manifest = command_result["manifest"]
        manifest_hash = command_result["manifest_hash"]

        persistence_or_error = self._persist_with_policy(manifest_hash, manifest)
        if "error" in persistence_or_error:
            return persistence_or_error
        persistence = persistence_or_error["persistence_receipt"]

        blob_receipt = self._maybe_write_blob(command_result)

        attestation_or_error = self._attest_with_policy(manifest_hash)
        if "error" in attestation_or_error:
            return {
                "manifest_hash": manifest_hash,
                "persistence_receipt": persistence.to_dict(),
                "blob_receipt": blob_receipt.to_dict(),
                "error": attestation_or_error["error"],
            }
        attestation = attestation_or_error["attestation_receipt"]

        return {
            "manifest_hash": manifest_hash,
            "attestation_id": attestation.attestation_id,
            "attestation": self.attestation.get_attestation(attestation.attestation_id or ""),
            "manifest": manifest,
            "chain_node": command_result["chain_node"],
            "canonical_bytes": command_result["canonical_bytes"],
            "canonical_bytes_encoding": command_result["canonical_bytes_encoding"],
            "storage_write": persistence.status,
            "persistence_receipt": persistence.to_dict(),
            "blob_receipt": blob_receipt.to_dict(),
            "attestation_receipt": attestation.to_dict(),
        }

    def _maybe_write_blob(self, command_result: dict) -> BlobWriteReceipt:
        blob_id = command_result["manifest_hash"]
        if self.blob_storage is None:
            return BlobWriteReceipt(
                operation="blob_write",
                status="not_configured",
                backend=self.blob_backend,
                blob_id=blob_id,
                execution_enabled=self.execution_enabled,
                failure_class=None,
                error_code=None,
            )
        if not self.execution_enabled:
            return BlobWriteReceipt(
                operation="blob_write",
                status="skipped_gate",
                backend=self.blob_backend,
                blob_id=blob_id,
                execution_enabled=False,
                failure_class=None,
                error_code=None,
            )

        try:
            raw = base64.b64decode(command_result["canonical_bytes"].encode("utf-8"))
            status = self.blob_storage.put_blob(blob_id, raw)
            return BlobWriteReceipt(
                operation="blob_write",
                status=status,
                backend=self.blob_backend,
                blob_id=blob_id,
                execution_enabled=True,
                failure_class=None,
                error_code=None,
            )
        except BlobStorageError as exc:
            return BlobWriteReceipt(
                operation="blob_write",
                status="failed",
                backend=self.blob_backend,
                blob_id=blob_id,
                execution_enabled=True,
                failure_class=exc.failure_class,
                error_code=exc.code,
            )
        except Exception as exc:
            return BlobWriteReceipt(
                operation="blob_write",
                status="failed",
                backend=self.blob_backend,
                blob_id=blob_id,
                execution_enabled=True,
                failure_class=classify_failure(exc),
                error_code="blob_write_failed",
            )

    def _persist_with_policy(self, manifest_hash: str, manifest: dict) -> dict:
        attempts = 0
        while attempts < self.retry_policy.max_attempts:
            attempts += 1
            try:
                created = self.manifest_store.put_manifest_if_absent(manifest_hash, manifest)
                return {
                    "persistence_receipt": PersistenceReceipt(
                        operation="manifest_persist",
                        status="created" if created else "duplicate",
                        backend=self.manifest_backend,
                        manifest_hash=manifest_hash,
                        attempts=attempts,
                        max_attempts=self.retry_policy.max_attempts,
                        retryable=False,
                        failure_class=None,
                        error_code=None,
                        idempotency_scope=self.idempotency_scope,
                    )
                }
            except Exception as exc:  # controlled boundary mapping
                retryable = is_retryable(exc, self.retry_policy)
                if retryable and attempts < self.retry_policy.max_attempts:
                    continue
                return {
                    "manifest_hash": manifest_hash,
                    "error": {
                        "stage": "persistence",
                        "retryable": retryable,
                        "failure_class": classify_failure(exc),
                        "attempts": attempts,
                        "max_attempts": self.retry_policy.max_attempts,
                        "message": str(exc),
                    },
                }
        raise RuntimeError("unreachable_persist_loop")

    def _attest_with_policy(self, manifest_hash: str) -> dict:
        attempts = 0
        while attempts < self.retry_policy.max_attempts:
            attempts += 1
            try:
                att_id = self.attestation.submit_attestation(manifest_hash)
                return {
                    "attestation_receipt": AttestationReceipt(
                        operation="attestation_submit",
                        status="confirmed",
                        backend=self.attestation_backend,
                        attestation_id=att_id,
                        attempts=attempts,
                        max_attempts=self.retry_policy.max_attempts,
                        retryable=False,
                        failure_class=None,
                        error_code=None,
                    )
                }
            except Exception as exc:  # controlled boundary mapping
                retryable = is_retryable(exc, self.retry_policy)
                if retryable and attempts < self.retry_policy.max_attempts:
                    continue
                return {
                    "error": {
                        "stage": "attestation",
                        "retryable": retryable,
                        "failure_class": classify_failure(exc),
                        "attempts": attempts,
                        "max_attempts": self.retry_policy.max_attempts,
                        "message": str(exc),
                    }
                }
        raise RuntimeError("unreachable_attest_loop")
