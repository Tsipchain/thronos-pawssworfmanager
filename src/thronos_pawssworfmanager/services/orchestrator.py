"""Command orchestrator for controlled side effects."""

from __future__ import annotations

import base64
import hashlib

from ..adapters.attestation import AttestationAdapter, AttestationAdapterError, AttestationPayload
from ..adapters.blob_storage import BlobStorageAdapter, BlobStorageError
from ..adapters.manifest_store import ManifestStoreAdapter
from ..adapters.schemas import AttestationReceipt, BlobWriteReceipt, PersistenceReceipt
from ..state_hash import compute_manifest_hash
from .retry_semantics import RetryPolicy, classify_failure, is_retryable


class CommandOrchestrator:
    _ALLOWED_CONFIRMATION_TRANSITIONS = {
        "not_polled": {"still_pending", "confirmed", "rejected_or_dropped", "unknown"},
        "still_pending": {"still_pending", "confirmed", "rejected_or_dropped", "unknown"},
        "unknown": {"still_pending", "confirmed", "rejected_or_dropped", "unknown"},
        "confirmed": {"confirmed"},
        "rejected_or_dropped": {"rejected_or_dropped"},
    }

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
        if self.blob_storage is not None and self.execution_enabled:
            integrity_error = self._validate_manifest_binding(command_result)
            if integrity_error is not None:
                return integrity_error

        persistence_or_error = self._persist_with_policy(manifest_hash, manifest)
        if "error" in persistence_or_error:
            return persistence_or_error
        persistence = persistence_or_error["persistence_receipt"]

        blob_receipt = self._maybe_write_blob(command_result)

        attestation_or_error = self._attest_with_policy(manifest_hash, manifest.get("version", 1))
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

    def reconcile_attestation_receipt(self, attestation_receipt: dict) -> dict:
        submission_id = attestation_receipt.get("submission_id")
        tx_hash = attestation_receipt.get("tx_hash")
        reconciliation_id = attestation_receipt.get("reconciliation_id")
        current_status = attestation_receipt.get("confirmation_status", "not_polled")
        if not submission_id:
            return {
                "error": {
                    "stage": "attestation_reconciliation",
                    "retryable": False,
                    "failure_class": "permanent",
                    "error_code": "invalid_reconciliation_tuple",
                    "lifecycle_state": "submission_unknown",
                    "message": "submission_id is required for reconciliation",
                }
            }
        if tx_hash is None and reconciliation_id is None:
            return {
                "error": {
                    "stage": "attestation_reconciliation",
                    "retryable": False,
                    "failure_class": "permanent",
                    "error_code": "invalid_reconciliation_tuple",
                    "lifecycle_state": "submission_unknown",
                    "message": "either tx_hash or reconciliation_id is required for reconciliation",
                }
            }

        try:
            poll = self.attestation.poll_attestation(submission_id, tx_hash, reconciliation_id)
        except AttestationAdapterError as exc:
            return {
                "error": {
                    "stage": "attestation_reconciliation",
                    "retryable": exc.failure_class == "transient",
                    "failure_class": exc.failure_class,
                    "error_code": exc.code,
                    "lifecycle_state": exc.lifecycle_state,
                    "message": str(exc),
                }
            }
        except Exception as exc:
            return {
                "error": {
                    "stage": "attestation_reconciliation",
                    "retryable": False,
                    "failure_class": "unknown",
                    "error_code": "attestation_reconciliation_failed",
                    "lifecycle_state": "submission_unknown",
                    "message": str(exc),
                }
            }
        next_status = poll.get("confirmation_status", "unknown")
        allowed = self._ALLOWED_CONFIRMATION_TRANSITIONS.get(current_status, {"unknown"})
        if next_status not in allowed:
            return {
                "error": {
                    "stage": "attestation_reconciliation",
                    "retryable": False,
                    "failure_class": "permanent",
                    "error_code": "invalid_confirmation_transition",
                    "lifecycle_state": "submission_unknown",
                    "message": f"invalid transition {current_status}->{next_status}",
                }
            }

        updated = dict(attestation_receipt)
        updated["confirmation_status"] = next_status
        updated["lifecycle_state"] = poll.get("lifecycle_state", updated.get("lifecycle_state", "submission_unknown"))
        updated["confirmation_id"] = poll.get("confirmation_id")
        return {"attestation_receipt": updated}

    def _validate_manifest_binding(self, command_result: dict) -> dict | None:
        try:
            raw = base64.b64decode(command_result["canonical_bytes"].encode("utf-8"))
            computed = compute_manifest_hash(raw)
            expected = command_result["manifest_hash"]
            if expected != computed:
                return {
                    "manifest_hash": expected,
                    "error": {
                        "stage": "integrity_binding",
                        "retryable": False,
                        "failure_class": "permanent",
                        "error_code": "blob_hash_mismatch",
                        "message": "manifest hash does not match canonical bytes hash",
                    },
                }
        except Exception as exc:
            return {
                "manifest_hash": command_result.get("manifest_hash"),
                "error": {
                    "stage": "integrity_binding",
                    "retryable": False,
                    "failure_class": "permanent",
                    "error_code": "integrity_check_failed",
                    "message": str(exc),
                },
            }
        return None

    def _maybe_write_blob(self, command_result: dict) -> BlobWriteReceipt:
        blob_id = command_result["manifest_hash"]
        if self.blob_storage is None:
            return BlobWriteReceipt(
                operation="blob_write",
                status="not_configured",
                backend=self.blob_backend,
                blob_id=blob_id,
                blob_hash=None,
                verified=None,
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
                blob_hash=None,
                verified=None,
                execution_enabled=False,
                failure_class=None,
                error_code=None,
            )

        try:
            raw = base64.b64decode(command_result["canonical_bytes"].encode("utf-8"))
            blob_hash = hashlib.sha256(raw).hexdigest()
            expected_hash = command_result.get("manifest_hash")
            if expected_hash and expected_hash != blob_hash:
                return BlobWriteReceipt(
                    operation="blob_write",
                    status="failed",
                    backend=self.blob_backend,
                    blob_id=blob_hash,
                    blob_hash=blob_hash,
                    verified=False,
                    execution_enabled=True,
                    failure_class="permanent",
                    error_code="blob_hash_mismatch",
                )

            blob_id = blob_hash
            status = self.blob_storage.put_blob(blob_id, raw)
            verify_raw = self.blob_storage.get_blob(blob_id)
            verified = hashlib.sha256(verify_raw).hexdigest() == blob_hash
            if not verified:
                return BlobWriteReceipt(
                    operation="blob_write",
                    status="failed",
                    backend=self.blob_backend,
                    blob_id=blob_id,
                    blob_hash=blob_hash,
                    verified=False,
                    execution_enabled=True,
                    failure_class="permanent",
                    error_code="blob_hash_mismatch",
                )
            return BlobWriteReceipt(
                operation="blob_write",
                status=status,
                backend=self.blob_backend,
                blob_id=blob_id,
                blob_hash=blob_hash,
                verified=True,
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
                blob_hash=None,
                verified=False,
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
                blob_hash=None,
                verified=False,
                execution_enabled=True,
                failure_class=classify_failure(exc),
                error_code="write_failed",
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

    def _attest_with_policy(self, manifest_hash: str, manifest_version: int) -> dict:
        attempts = 0
        while attempts < self.retry_policy.max_attempts:
            attempts += 1
            try:
                payload = AttestationPayload(
                    manifest_hash=manifest_hash,
                    manifest_version=manifest_version,
                    attestation_schema_version="v1",
                    source_system="thronos-pawssworfmanager",
                    target_backend_type=self.attestation_backend,
                    target_network=self.attestation.capabilities().get("network", "none"),
                    metadata={"idempotency_scope": self.idempotency_scope},
                )
                submission = self.attestation.submit_attestation(payload)
                return {
                    "attestation_receipt": AttestationReceipt(
                        operation="attestation_submit",
                        backend=self.attestation_backend,
                        network=submission.get("network", "unknown"),
                        status=submission.get("status", "unknown"),
                        lifecycle_state=submission.get("lifecycle_state", "submission_unknown"),
                        attestation_id=submission.get("attestation_id"),
                        submission_id=submission.get("submission_id"),
                        tx_hash=submission.get("tx_hash"),
                        confirmation_id=submission.get("confirmation_id"),
                        confirmation_status=submission.get("confirmation_status", "not_polled"),
                        reconciliation_id=submission.get("reconciliation_id"),
                        submitted_at=None,
                        attempts=attempts,
                        max_attempts=self.retry_policy.max_attempts,
                        retryable=False,
                        failure_class=None,
                        error_code=None,
                        execution_mode=submission.get("execution_mode", "dry_run"),
                        dry_run=bool(submission.get("dry_run", True)),
                    )
                }
            except AttestationAdapterError as exc:
                retryable = exc.failure_class == "transient"
                if retryable and attempts < self.retry_policy.max_attempts:
                    continue
                return {
                    "error": {
                        "stage": "attestation",
                        "retryable": retryable,
                        "failure_class": exc.failure_class,
                        "error_code": exc.code,
                        "lifecycle_state": exc.lifecycle_state,
                        "attempts": attempts,
                        "max_attempts": self.retry_policy.max_attempts,
                        "message": str(exc),
                    }
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
                        "error_code": "attestation_submit_failed",
                        "lifecycle_state": "submission_unknown",
                        "attempts": attempts,
                        "max_attempts": self.retry_policy.max_attempts,
                        "message": str(exc),
                    }
                }
        raise RuntimeError("unreachable_attest_loop")
