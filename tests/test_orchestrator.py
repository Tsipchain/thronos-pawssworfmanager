import base64
import tempfile
import unittest

from thronos_pawssworfmanager.adapters.attestation import AttestationAdapterError, FakeAttestationAdapter, RealThronosAttestationAdapter
from thronos_pawssworfmanager.adapters.blob_storage import LocalFileBlobStorage
from thronos_pawssworfmanager.adapters.manifest_store import InMemoryManifestStore
from thronos_pawssworfmanager.state_hash import compute_manifest_hash
from thronos_pawssworfmanager.services.orchestrator import CommandOrchestrator
from thronos_pawssworfmanager.services.retry_semantics import RetryPolicy


class FlakyAttestationAdapter(FakeAttestationAdapter):
    def __init__(self):
        self.calls = 0

    def submit_attestation(self, payload) -> dict:
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("temporary network")
        return super().submit_attestation(payload)


class BrokenAttestationAdapter(FakeAttestationAdapter):
    def submit_attestation(self, payload) -> dict:
        raise ValueError("invalid payload")


class TransientAttestationAdapter(FakeAttestationAdapter):
    def __init__(self):
        self.calls = 0

    def submit_attestation(self, payload) -> dict:
        self.calls += 1
        if self.calls == 1:
            raise AttestationAdapterError("attestation_rpc_timeout", "transient", "timeout", "submission_failed_retryable")
        return super().submit_attestation(payload)


class PermanentAttestationAdapter(FakeAttestationAdapter):
    def submit_attestation(self, payload) -> dict:
        raise AttestationAdapterError("attestation_invalid_tx_hash", "permanent", "invalid tx", "submission_failed_permanent")


class TamperingBlobStorage(LocalFileBlobStorage):
    def get_blob(self, blob_id: str) -> bytes:
        return b"tampered"


class CapturingAttestationAdapter(FakeAttestationAdapter):
    def __init__(self):
        self.last_payload = None

    def submit_attestation(self, payload) -> dict:
        self.last_payload = payload
        return super().submit_attestation(payload)


class PollingAttestationAdapter(FakeAttestationAdapter):
    def __init__(self, poll_status: str, lifecycle_state: str):
        self.poll_status = poll_status
        self.lifecycle_state = lifecycle_state

    def poll_attestation(self, submission_id: str, tx_hash: str | None, reconciliation_id: str | None) -> dict:
        return {
            "confirmation_status": self.poll_status,
            "finality_status": "finalized" if self.poll_status == "confirmed" else "not_finalized",
            "lifecycle_state": self.lifecycle_state,
            "confirmation_id": "conf-123" if self.poll_status == "confirmed" else None,
            "confirmation_proof": {"proof_source": "test", "proof_kind": "status_attestation"},
            "polling_supported": True,
        }


class FailingPollAttestationAdapter(FakeAttestationAdapter):
    def poll_attestation(self, submission_id: str, tx_hash: str | None, reconciliation_id: str | None) -> dict:
        raise AttestationAdapterError(
            "attestation_poll_failed",
            "permanent",
            "poll failed",
            "submission_unknown",
        )


class CountingPollAttestationAdapter(FakeAttestationAdapter):
    def __init__(self):
        self.poll_calls = 0

    def poll_attestation(self, submission_id: str, tx_hash: str | None, reconciliation_id: str | None) -> dict:
        self.poll_calls += 1
        return {
            "confirmation_status": "still_pending",
            "finality_status": "not_finalized",
            "lifecycle_state": "submitted_not_finalized",
            "confirmation_id": None,
            "confirmation_proof": {"proof_source": "test", "proof_kind": "status_attestation"},
            "polling_supported": True,
        }


class TestOrchestrator(unittest.TestCase):
    def test_orchestrator_persists_manifest_and_returns_attestation(self):
        store = InMemoryManifestStore()
        att = FakeAttestationAdapter()
        orch = CommandOrchestrator(store, att)

        command_result = {
            "manifest": {"vault_id": "v1", "version": 1, "entries": []},
            "canonical_bytes": "ignored",
            "canonical_bytes_encoding": "base64",
            "manifest_hash": "abcd1234",
            "chain_node": {"version": 1, "manifest_hash": "abcd1234", "parent_hash": None},
        }
        out = orch.execute(command_result)
        self.assertEqual(out["manifest_hash"], "abcd1234")
        self.assertTrue(out["attestation_id"].startswith("att_"))
        self.assertEqual(out["storage_write"], "created")
        self.assertEqual(out["blob_receipt"]["status"], "not_configured")
        self.assertEqual(out["persistence_receipt"]["operation"], "manifest_persist")
        self.assertEqual(out["attestation_receipt"]["operation"], "attestation_submit")
        self.assertEqual(store.get_manifest("abcd1234")["vault_id"], "v1")

    def test_orchestrator_idempotent_over_same_hash(self):
        store = InMemoryManifestStore()
        att = FakeAttestationAdapter()
        orch = CommandOrchestrator(store, att)

        command_result = {
            "manifest": {"vault_id": "v1", "version": 1, "entries": []},
            "canonical_bytes": "ignored",
            "canonical_bytes_encoding": "base64",
            "manifest_hash": "samehash",
            "chain_node": {"version": 1, "manifest_hash": "samehash", "parent_hash": None},
        }
        a = orch.execute(command_result)
        b = orch.execute(command_result)
        self.assertEqual(a["manifest_hash"], b["manifest_hash"])
        self.assertEqual(a["storage_write"], "created")
        self.assertEqual(b["storage_write"], "duplicate")
        self.assertEqual(b["persistence_receipt"]["idempotency_scope"], "single_instance_memory")
        self.assertEqual(store.get_manifest("samehash")["version"], 1)

    def test_blob_write_skipped_when_execution_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InMemoryManifestStore()
            att = FakeAttestationAdapter()
            blob = LocalFileBlobStorage(tmp, exec_enabled=False)
            orch = CommandOrchestrator(store, att, blob_storage=blob, blob_backend="local_fs", execution_enabled=False)
            payload = base64.b64encode(b"hello").decode("utf-8")
            out = orch.execute(
                {
                    "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                    "canonical_bytes": payload,
                    "canonical_bytes_encoding": "base64",
                    "manifest_hash": "h1",
                    "chain_node": {"version": 1, "manifest_hash": "h1", "parent_hash": None},
                }
            )
            self.assertEqual(out["blob_receipt"]["status"], "skipped_gate")

    def test_blob_write_occurs_when_execution_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InMemoryManifestStore()
            att = FakeAttestationAdapter()
            blob = LocalFileBlobStorage(tmp, exec_enabled=True)
            orch = CommandOrchestrator(store, att, blob_storage=blob, blob_backend="local_fs", execution_enabled=True)
            raw = b"hello"
            payload = base64.b64encode(raw).decode("utf-8")
            manifest_hash = compute_manifest_hash(raw)
            out = orch.execute(
                {
                    "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                    "canonical_bytes": payload,
                    "canonical_bytes_encoding": "base64",
                    "manifest_hash": manifest_hash,
                    "chain_node": {"version": 1, "manifest_hash": manifest_hash, "parent_hash": None},
                }
            )
            self.assertEqual(out["blob_receipt"]["status"], "created")
            self.assertEqual(blob.get_blob(manifest_hash), b"hello")
            self.assertTrue(out["blob_receipt"]["verified"])
            self.assertEqual(out["blob_receipt"]["blob_hash"], out["blob_receipt"]["blob_id"])

    def test_blob_write_failure_receipt_contains_error_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InMemoryManifestStore()
            att = FakeAttestationAdapter()
            blob = LocalFileBlobStorage(tmp, exec_enabled=True, max_blob_bytes=2)
            orch = CommandOrchestrator(store, att, blob_storage=blob, blob_backend="local_fs", execution_enabled=True)
            raw = b"hello"
            payload = base64.b64encode(raw).decode("utf-8")
            manifest_hash = compute_manifest_hash(raw)
            out = orch.execute(
                {
                    "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                    "canonical_bytes": payload,
                    "canonical_bytes_encoding": "base64",
                    "manifest_hash": manifest_hash,
                    "chain_node": {"version": 1, "manifest_hash": manifest_hash, "parent_hash": None},
                }
            )
            self.assertEqual(out["blob_receipt"]["status"], "failed")
            self.assertEqual(out["blob_receipt"]["error_code"], "size_limit_exceeded")
            self.assertEqual(out["blob_receipt"]["failure_class"], "permanent")

    def test_blob_id_is_deterministic_from_canonical_bytes_hash(self):
        store = InMemoryManifestStore()
        att = FakeAttestationAdapter()
        orch = CommandOrchestrator(store, att, blob_storage=None, execution_enabled=False)
        raw = b"deterministic"
        payload = base64.b64encode(raw).decode("utf-8")
        manifest_hash = compute_manifest_hash(raw)
        receipt = orch._maybe_write_blob(
            {
                "canonical_bytes": payload,
                "manifest_hash": manifest_hash,
            }
        )
        self.assertEqual(receipt.status, "not_configured")

        with tempfile.TemporaryDirectory() as tmp:
            blob = LocalFileBlobStorage(tmp, exec_enabled=True)
            orch = CommandOrchestrator(store, att, blob_storage=blob, blob_backend="local_fs", execution_enabled=True)
            out1 = orch.execute(
                {
                    "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                    "canonical_bytes": payload,
                    "canonical_bytes_encoding": "base64",
                    "manifest_hash": manifest_hash,
                    "chain_node": {"version": 1, "manifest_hash": manifest_hash, "parent_hash": None},
                }
            )
            out2 = orch.execute(
                {
                    "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                    "canonical_bytes": payload,
                    "canonical_bytes_encoding": "base64",
                    "manifest_hash": manifest_hash,
                    "chain_node": {"version": 1, "manifest_hash": manifest_hash, "parent_hash": None},
                }
            )
            self.assertEqual(out1["blob_receipt"]["blob_id"], out2["blob_receipt"]["blob_id"])

    def test_blob_hash_mismatch_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InMemoryManifestStore()
            att = FakeAttestationAdapter()
            blob = LocalFileBlobStorage(tmp, exec_enabled=True)
            orch = CommandOrchestrator(store, att, blob_storage=blob, blob_backend="local_fs", execution_enabled=True)
            payload = base64.b64encode(b"hello").decode("utf-8")
            out = orch.execute(
                {
                    "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                    "canonical_bytes": payload,
                    "canonical_bytes_encoding": "base64",
                    "manifest_hash": "not_the_real_hash",
                    "chain_node": {"version": 1, "manifest_hash": "not_the_real_hash", "parent_hash": None},
                }
            )
            self.assertEqual(out["error"]["stage"], "integrity_binding")
            self.assertEqual(out["error"]["error_code"], "blob_hash_mismatch")
            self.assertFalse(out["error"]["retryable"])
            self.assertNotIn("persistence_receipt", out)
            self.assertNotIn("blob_receipt", out)
            with self.assertRaises(KeyError):
                store.get_manifest("not_the_real_hash")

    def test_blob_tampering_detected_during_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InMemoryManifestStore()
            att = FakeAttestationAdapter()
            blob = TamperingBlobStorage(tmp, exec_enabled=True)
            orch = CommandOrchestrator(store, att, blob_storage=blob, blob_backend="local_fs", execution_enabled=True)
            payload = base64.b64encode(b"hello").decode("utf-8")
            manifest_hash = compute_manifest_hash(b"hello")
            out = orch.execute(
                {
                    "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                    "canonical_bytes": payload,
                    "canonical_bytes_encoding": "base64",
                    "manifest_hash": manifest_hash,
                    "chain_node": {"version": 1, "manifest_hash": manifest_hash, "parent_hash": None},
                }
            )
            self.assertEqual(out["blob_receipt"]["status"], "failed")
            self.assertEqual(out["blob_receipt"]["error_code"], "blob_hash_mismatch")
            self.assertFalse(out["blob_receipt"]["verified"])

    def test_orchestrator_retries_transient_attestation_failure(self):
        store = InMemoryManifestStore()
        att = FlakyAttestationAdapter()
        orch = CommandOrchestrator(store, att, retry_policy=RetryPolicy(max_attempts=2))

        command_result = {
            "manifest": {"vault_id": "v1", "version": 1, "entries": []},
            "canonical_bytes": "ignored",
            "canonical_bytes_encoding": "base64",
            "manifest_hash": "retryhash",
            "chain_node": {"version": 1, "manifest_hash": "retryhash", "parent_hash": None},
        }
        out = orch.execute(command_result)
        self.assertEqual(att.calls, 2)
        self.assertEqual(out["attestation_receipt"]["attempts"], 2)

    def test_attestation_receipt_real_thronos_submission_shape(self):
        store = InMemoryManifestStore()
        att = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            rpc_post_fn=lambda *_args, **_kwargs: {
                "jsonrpc": "2.0",
                "result": {"status": "accepted", "tx_hash": "0x" + "a" * 64, "attestation_id": "att-real-1"},
            },
        )
        orch = CommandOrchestrator(store, att, attestation_backend="thronos_network")
        command_result = {
            "manifest": {"vault_id": "v1", "version": 1, "entries": []},
            "canonical_bytes": "ignored",
            "canonical_bytes_encoding": "base64",
            "manifest_hash": "abcd1234",
            "chain_node": {"version": 1, "manifest_hash": "abcd1234", "parent_hash": None},
        }
        out = orch.execute(command_result)
        receipt = out["attestation_receipt"]
        self.assertEqual(receipt["backend"], "thronos_network")
        self.assertEqual(receipt["network"], "thronos-mainnet")
        self.assertEqual(receipt["status"], "submitted")
        self.assertEqual(receipt["lifecycle_state"], "submitted_not_finalized")
        self.assertEqual(receipt["tx_hash"], "0x" + "a" * 64)
        self.assertTrue(receipt["submission_id"].startswith("sub_"))
        self.assertIsNone(receipt["confirmation_id"])
        self.assertEqual(receipt["confirmation_status"], "not_polled")
        self.assertEqual(receipt["finality_status"], "not_finalized")
        self.assertTrue(receipt["reconciliation_id"].startswith("thronos-mainnet:0x"))
        self.assertEqual(receipt["replay_state"], "not_checked")
        self.assertEqual(receipt["replay_observation_count"], 0)
        self.assertEqual(receipt["execution_mode"], "execute")
        self.assertFalse(receipt["dry_run"])

    def test_attestation_payload_shape_excludes_sensitive_content(self):
        store = InMemoryManifestStore()
        att = CapturingAttestationAdapter()
        orch = CommandOrchestrator(store, att)
        command_result = {
            "manifest": {"vault_id": "v1", "version": 3, "entries": [{"id": "entry1", "secret": "hidden"}]},
            "canonical_bytes": "ignored",
            "canonical_bytes_encoding": "base64",
            "manifest_hash": "payloadhash",
            "chain_node": {"version": 3, "manifest_hash": "payloadhash", "parent_hash": "old"},
        }
        orch.execute(command_result)
        payload = att.last_payload
        self.assertIsNotNone(payload)
        self.assertEqual(payload.manifest_hash, "payloadhash")
        self.assertEqual(payload.manifest_version, 3)
        self.assertEqual(payload.attestation_schema_version, "v1")
        self.assertEqual(payload.source_system, "thronos-pawssworfmanager")
        self.assertFalse(hasattr(payload, "entries"))
        self.assertFalse(hasattr(payload, "canonical_bytes"))

    def test_orchestrator_reports_permanent_attestation_failure(self):
        store = InMemoryManifestStore()
        att = BrokenAttestationAdapter()
        orch = CommandOrchestrator(store, att, retry_policy=RetryPolicy(max_attempts=2))

        command_result = {
            "manifest": {"vault_id": "v1", "version": 1, "entries": []},
            "canonical_bytes": "ignored",
            "canonical_bytes_encoding": "base64",
            "manifest_hash": "brokenhash",
            "chain_node": {"version": 1, "manifest_hash": "brokenhash", "parent_hash": None},
        }
        out = orch.execute(command_result)
        self.assertEqual(out["error"]["stage"], "attestation")
        self.assertEqual(out["error"]["failure_class"], "permanent")
        self.assertFalse(out["error"]["retryable"])

    def test_orchestrator_retries_transient_adapter_error(self):
        store = InMemoryManifestStore()
        att = TransientAttestationAdapter()
        orch = CommandOrchestrator(store, att, retry_policy=RetryPolicy(max_attempts=2))
        out = orch.execute(
            {
                "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                "canonical_bytes": "ignored",
                "canonical_bytes_encoding": "base64",
                "manifest_hash": "retryhash2",
                "chain_node": {"version": 1, "manifest_hash": "retryhash2", "parent_hash": None},
            }
        )
        self.assertEqual(att.calls, 2)
        self.assertEqual(out["attestation_receipt"]["attempts"], 2)

    def test_orchestrator_surfaces_lifecycle_for_transient_attestation_failure(self):
        store = InMemoryManifestStore()

        class AlwaysTransient(FakeAttestationAdapter):
            def submit_attestation(self, payload) -> dict:
                raise AttestationAdapterError("attestation_rpc_timeout", "transient", "timeout", "submission_failed_retryable")

        orch = CommandOrchestrator(store, AlwaysTransient(), retry_policy=RetryPolicy(max_attempts=1))
        out = orch.execute(
            {
                "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                "canonical_bytes": "ignored",
                "canonical_bytes_encoding": "base64",
                "manifest_hash": "thash",
                "chain_node": {"version": 1, "manifest_hash": "thash", "parent_hash": None},
            }
        )
        self.assertEqual(out["error"]["error_code"], "attestation_rpc_timeout")
        self.assertEqual(out["error"]["lifecycle_state"], "submission_failed_retryable")

    def test_orchestrator_returns_attestation_error_code_for_permanent_adapter_error(self):
        store = InMemoryManifestStore()
        att = PermanentAttestationAdapter()
        orch = CommandOrchestrator(store, att, retry_policy=RetryPolicy(max_attempts=2))
        out = orch.execute(
            {
                "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                "canonical_bytes": "ignored",
                "canonical_bytes_encoding": "base64",
                "manifest_hash": "permanenthash",
                "chain_node": {"version": 1, "manifest_hash": "permanenthash", "parent_hash": None},
            }
        )
        self.assertEqual(out["error"]["stage"], "attestation")
        self.assertEqual(out["error"]["error_code"], "attestation_invalid_tx_hash")
        self.assertEqual(out["error"]["lifecycle_state"], "submission_failed_permanent")
        self.assertFalse(out["error"]["retryable"])

    def test_dry_run_attestation_receipt_exposes_future_finality_fields(self):
        store = InMemoryManifestStore()
        att = FakeAttestationAdapter()
        orch = CommandOrchestrator(store, att)
        out = orch.execute(
            {
                "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                "canonical_bytes": "ignored",
                "canonical_bytes_encoding": "base64",
                "manifest_hash": "futurefields",
                "chain_node": {"version": 1, "manifest_hash": "futurefields", "parent_hash": None},
            }
        )
        receipt = out["attestation_receipt"]
        self.assertIn("submission_id", receipt)
        self.assertIn("confirmation_id", receipt)
        self.assertIn("confirmation_status", receipt)
        self.assertIn("reconciliation_id", receipt)
        self.assertEqual(receipt["confirmation_status"], "not_polled")
        self.assertEqual(receipt["finality_status"], "not_finalized")

    def test_reconcile_attestation_receipt_confirmed_transition(self):
        store = InMemoryManifestStore()
        att = PollingAttestationAdapter("confirmed", "confirmed_finalized")
        orch = CommandOrchestrator(store, att)
        out = orch.reconcile_attestation_receipt(
            {
                "confirmation_status": "still_pending",
                "lifecycle_state": "submitted_not_finalized",
                "submission_id": "sub_abc",
                "tx_hash": "0x" + "a" * 64,
                "reconciliation_id": "thronos-mainnet:0x" + "a" * 64,
            }
        )
        self.assertEqual(out["attestation_receipt"]["confirmation_status"], "confirmed")
        self.assertEqual(out["attestation_receipt"]["lifecycle_state"], "confirmed_finalized")
        self.assertEqual(out["attestation_receipt"]["confirmation_id"], "conf-123")
        self.assertEqual(out["attestation_receipt"]["replay_state"], "first_observation")

    def test_reconcile_attestation_receipt_rejected_transition(self):
        store = InMemoryManifestStore()
        att = PollingAttestationAdapter("rejected_or_dropped", "submission_rejected")
        orch = CommandOrchestrator(store, att)
        out = orch.reconcile_attestation_receipt(
            {
                "confirmation_status": "still_pending",
                "lifecycle_state": "submitted_not_finalized",
                "submission_id": "sub_abc",
                "tx_hash": "0x" + "a" * 64,
                "reconciliation_id": "thronos-mainnet:0x" + "a" * 64,
            }
        )
        self.assertEqual(out["attestation_receipt"]["confirmation_status"], "rejected_or_dropped")
        self.assertEqual(out["attestation_receipt"]["lifecycle_state"], "submission_rejected")
        self.assertEqual(out["attestation_receipt"]["finality_status"], "not_finalized")

    def test_reconcile_attestation_receipt_still_pending_transition(self):
        store = InMemoryManifestStore()
        att = PollingAttestationAdapter("still_pending", "submitted_not_finalized")
        orch = CommandOrchestrator(store, att)
        out = orch.reconcile_attestation_receipt(
            {
                "confirmation_status": "not_polled",
                "lifecycle_state": "submitted_not_finalized",
                "submission_id": "sub_abc",
                "tx_hash": "0x" + "a" * 64,
                "reconciliation_id": "thronos-mainnet:0x" + "a" * 64,
            }
        )
        self.assertEqual(out["attestation_receipt"]["confirmation_status"], "still_pending")
        self.assertEqual(out["attestation_receipt"]["lifecycle_state"], "submitted_not_finalized")
        self.assertIsNone(out["attestation_receipt"]["confirmation_id"])

    def test_reconcile_attestation_receipt_unknown_transition(self):
        store = InMemoryManifestStore()
        att = PollingAttestationAdapter("unknown", "submission_unknown")
        orch = CommandOrchestrator(store, att)
        out = orch.reconcile_attestation_receipt(
            {
                "confirmation_status": "not_polled",
                "lifecycle_state": "submitted_not_finalized",
                "submission_id": "sub_abc",
                "tx_hash": "0x" + "a" * 64,
                "reconciliation_id": "thronos-mainnet:0x" + "a" * 64,
            }
        )
        self.assertEqual(out["attestation_receipt"]["confirmation_status"], "unknown")
        self.assertEqual(out["attestation_receipt"]["lifecycle_state"], "submission_unknown")
        self.assertIsNone(out["attestation_receipt"]["confirmation_id"])

    def test_reconcile_attestation_receipt_is_deterministic_across_repeated_observations(self):
        store = InMemoryManifestStore()
        att = PollingAttestationAdapter("confirmed", "confirmed_finalized")
        orch = CommandOrchestrator(store, att)
        seed = {
            "confirmation_status": "still_pending",
            "finality_status": "not_finalized",
            "lifecycle_state": "submitted_not_finalized",
            "submission_id": "sub_abc",
            "tx_hash": "0x" + "a" * 64,
            "reconciliation_id": "thronos-mainnet:0x" + "a" * 64,
            "replay_observation_count": 0,
            "replay_key": None,
        }
        first = orch.reconcile_attestation_receipt(seed)["attestation_receipt"]
        second = orch.reconcile_attestation_receipt(first)["attestation_receipt"]
        self.assertEqual(first["confirmation_status"], second["confirmation_status"])
        self.assertEqual(first["finality_status"], second["finality_status"])
        self.assertEqual(second["replay_state"], "repeated_observation_consistent")

    def test_reconcile_attestation_receipt_invalid_transition_is_rejected(self):
        store = InMemoryManifestStore()
        att = PollingAttestationAdapter("still_pending", "submitted_not_finalized")
        orch = CommandOrchestrator(store, att)
        out = orch.reconcile_attestation_receipt(
            {
                "confirmation_status": "confirmed",
                "lifecycle_state": "confirmed_finalized",
                "submission_id": "sub_abc",
                "tx_hash": "0x" + "a" * 64,
                "reconciliation_id": "thronos-mainnet:0x" + "a" * 64,
            }
        )
        self.assertEqual(out["error"]["error_code"], "invalid_confirmation_transition")

    def test_reconcile_attestation_receipt_maps_adapter_poll_errors(self):
        store = InMemoryManifestStore()
        att = FailingPollAttestationAdapter()
        orch = CommandOrchestrator(store, att)
        out = orch.reconcile_attestation_receipt(
            {
                "confirmation_status": "not_polled",
                "lifecycle_state": "submitted_not_finalized",
                "submission_id": "sub_abc",
                "tx_hash": "0x" + "a" * 64,
                "reconciliation_id": "thronos-mainnet:0x" + "a" * 64,
            }
        )
        self.assertEqual(out["error"]["stage"], "attestation_reconciliation")
        self.assertEqual(out["error"]["error_code"], "attestation_poll_failed")
        self.assertEqual(out["error"]["lifecycle_state"], "submission_unknown")

    def test_reconcile_attestation_receipt_rejects_missing_submission_id(self):
        store = InMemoryManifestStore()
        att = CountingPollAttestationAdapter()
        orch = CommandOrchestrator(store, att)
        out = orch.reconcile_attestation_receipt(
            {
                "confirmation_status": "not_polled",
                "lifecycle_state": "submitted_not_finalized",
                "submission_id": None,
                "tx_hash": "0x" + "a" * 64,
                "reconciliation_id": "thronos-mainnet:0x" + "a" * 64,
            }
        )
        self.assertEqual(out["error"]["error_code"], "invalid_reconciliation_tuple")
        self.assertEqual(att.poll_calls, 0)

    def test_reconcile_attestation_receipt_requires_tx_hash_or_reconciliation_id(self):
        store = InMemoryManifestStore()
        att = CountingPollAttestationAdapter()
        orch = CommandOrchestrator(store, att)
        out = orch.reconcile_attestation_receipt(
            {
                "confirmation_status": "not_polled",
                "lifecycle_state": "submitted_not_finalized",
                "submission_id": "sub_abc",
                "tx_hash": None,
                "reconciliation_id": None,
            }
        )
        self.assertEqual(out["error"]["error_code"], "invalid_reconciliation_tuple")
        self.assertEqual(att.poll_calls, 0)
