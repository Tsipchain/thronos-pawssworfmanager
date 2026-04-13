import base64
import tempfile
import unittest

from thronos_pawssworfmanager.adapters.attestation import FakeAttestationAdapter
from thronos_pawssworfmanager.adapters.blob_storage import LocalFileBlobStorage
from thronos_pawssworfmanager.adapters.manifest_store import InMemoryManifestStore
from thronos_pawssworfmanager.services.orchestrator import CommandOrchestrator
from thronos_pawssworfmanager.services.retry_semantics import RetryPolicy


class FlakyAttestationAdapter(FakeAttestationAdapter):
    def __init__(self):
        self.calls = 0

    def submit_attestation(self, manifest_hash: str) -> str:
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("temporary network")
        return super().submit_attestation(manifest_hash)


class BrokenAttestationAdapter(FakeAttestationAdapter):
    def submit_attestation(self, manifest_hash: str) -> str:
        raise ValueError("invalid payload")


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
            payload = base64.b64encode(b"hello").decode("utf-8")
            out = orch.execute(
                {
                    "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                    "canonical_bytes": payload,
                    "canonical_bytes_encoding": "base64",
                    "manifest_hash": "h2",
                    "chain_node": {"version": 1, "manifest_hash": "h2", "parent_hash": None},
                }
            )
            self.assertEqual(out["blob_receipt"]["status"], "created")
            self.assertEqual(blob.get_blob("h2"), b"hello")

    def test_blob_write_failure_receipt_contains_error_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InMemoryManifestStore()
            att = FakeAttestationAdapter()
            blob = LocalFileBlobStorage(tmp, exec_enabled=True, max_blob_bytes=2)
            orch = CommandOrchestrator(store, att, blob_storage=blob, blob_backend="local_fs", execution_enabled=True)
            payload = base64.b64encode(b"hello").decode("utf-8")
            out = orch.execute(
                {
                    "manifest": {"vault_id": "v1", "version": 1, "entries": []},
                    "canonical_bytes": payload,
                    "canonical_bytes_encoding": "base64",
                    "manifest_hash": "h3",
                    "chain_node": {"version": 1, "manifest_hash": "h3", "parent_hash": None},
                }
            )
            self.assertEqual(out["blob_receipt"]["status"], "failed")
            self.assertEqual(out["blob_receipt"]["error_code"], "size_limit_exceeded")
            self.assertEqual(out["blob_receipt"]["failure_class"], "permanent")

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
