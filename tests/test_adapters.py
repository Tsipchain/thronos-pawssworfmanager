import tempfile
import unittest
from unittest import mock

from thronos_pawssworfmanager.adapters.attestation import (
    AttestationPayload,
    DryRunChainAttestationAdapter,
    FakeAttestationAdapter,
)
from thronos_pawssworfmanager.adapters.blob_storage import (
    BlobStorageError,
    DryRunBlobStorageProvider,
    InMemoryBlobStorage,
    LocalFileBlobStorage,
)
from thronos_pawssworfmanager.adapters.identity import StaticIdentity
from thronos_pawssworfmanager.adapters.manifest_store import InMemoryManifestStore


class TestAdapters(unittest.TestCase):
    @staticmethod
    def _payload(manifest_hash: str = "abcdef123") -> AttestationPayload:
        return AttestationPayload(
            manifest_hash=manifest_hash,
            manifest_version=1,
            attestation_schema_version="v1",
            source_system="test-suite",
            target_backend_type="fake",
            target_network="none",
            metadata={},
        )

    def test_blob_storage_in_memory(self):
        s = InMemoryBlobStorage()
        self.assertEqual(s.put_blob("b1", b"abc"), "created")
        self.assertEqual(s.put_blob("b1", b"abc"), "duplicate")
        self.assertEqual(s.put_blob("b1", b"zzz"), "overwritten")
        self.assertEqual(s.get_blob("b1"), b"zzz")
        s.delete_blob("b1")
        with self.assertRaises(KeyError):
            s.get_blob("b1")

    def test_blob_storage_dry_run_provider(self):
        s = DryRunBlobStorageProvider("s3")
        self.assertEqual(s.put_blob("b1", b"abc"), "created")
        self.assertEqual(s.put_blob("b1", b"abc"), "duplicate")
        self.assertEqual(s.put_blob("b1", b"def"), "overwritten")
        self.assertEqual(s.get_blob("b1"), b"def")
        caps = s.capabilities()
        self.assertEqual(caps["backend"], "s3")
        self.assertTrue(caps["dry_run_supported"])
        self.assertFalse(caps["exec_enabled"])

    def test_blob_storage_local_fs_real_write_and_overwrite_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = LocalFileBlobStorage(tmp, exec_enabled=True)
            self.assertEqual(s.put_blob("b2", b"xyz"), "created")
            self.assertEqual(s.put_blob("b2", b"xyz"), "duplicate")
            self.assertEqual(s.put_blob("b2", b"qqq"), "overwritten")
            self.assertEqual(s.get_blob("b2"), b"qqq")
            s.delete_blob("b2")

    def test_blob_storage_local_fs_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = LocalFileBlobStorage(tmp, exec_enabled=True)
            with self.assertRaises(BlobStorageError):
                s.put_blob("../escape", b"bad")

    def test_blob_storage_local_fs_size_limit_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = LocalFileBlobStorage(tmp, exec_enabled=True, max_blob_bytes=4)
            with self.assertRaises(BlobStorageError):
                s.put_blob("b3", b"12345")

    def test_blob_storage_local_fs_read_delete_error_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = LocalFileBlobStorage(tmp, exec_enabled=True)
            with self.assertRaises(BlobStorageError) as read_err:
                s.get_blob("missing")
            self.assertEqual(read_err.exception.code, "read_not_found")
            self.assertEqual(read_err.exception.failure_class, "permanent")

            with self.assertRaises(BlobStorageError) as del_err:
                s.delete_blob("missing")
            self.assertEqual(del_err.exception.code, "delete_not_found")
            self.assertEqual(del_err.exception.failure_class, "permanent")

    def test_blob_storage_local_fs_atomic_replace_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = LocalFileBlobStorage(tmp, exec_enabled=True)
            with mock.patch("thronos_pawssworfmanager.adapters.blob_storage.os.replace") as replace_mock:
                self.assertEqual(s.put_blob("atomic", b"v1"), "created")
                replace_mock.assert_called_once()

    def test_blob_storage_local_fs_write_error_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = LocalFileBlobStorage(tmp, exec_enabled=True)
            with mock.patch("thronos_pawssworfmanager.adapters.blob_storage.os.replace", side_effect=OSError("disk io")):
                with self.assertRaises(BlobStorageError) as write_err:
                    s.put_blob("w1", b"bytes")
            self.assertEqual(write_err.exception.code, "write_failed")
            self.assertEqual(write_err.exception.failure_class, "transient")

    def test_manifest_store_in_memory(self):
        s = InMemoryManifestStore()
        m = {"vault_id": "v1", "version": 1, "entries": []}
        s.put_manifest("h1", m)
        self.assertEqual(s.get_manifest("h1"), m)

    def test_manifest_store_idempotent_insert(self):
        s = InMemoryManifestStore()
        m = {"vault_id": "v1", "version": 1, "entries": []}
        self.assertTrue(s.put_manifest_if_absent("h1", m))
        self.assertFalse(s.put_manifest_if_absent("h1", m))

    def test_fake_attestation(self):
        a = FakeAttestationAdapter()
        submission = a.submit_attestation(self._payload())
        self.assertTrue(submission["attestation_id"].startswith("att_"))
        receipt = a.get_attestation(submission["attestation_id"])
        self.assertEqual(receipt["status"], "confirmed")

    def test_chain_attestation_dry_run_provider(self):
        a = DryRunChainAttestationAdapter("thronos_network", network="thronos-mainnet")
        submission = a.submit_attestation(self._payload())
        self.assertTrue(submission["attestation_id"].startswith("dryrun_thronos_network_"))
        receipt = a.get_attestation(submission["attestation_id"])
        self.assertEqual(receipt["status"], "simulated_confirmed")
        caps = a.capabilities()
        self.assertEqual(caps["backend"], "thronos_network")
        self.assertEqual(caps["network"], "thronos-mainnet")
        self.assertFalse(caps["exec_enabled"])

    def test_chain_attestation_dry_run_failure_simulation(self):
        a = DryRunChainAttestationAdapter("thronos_network", network="thronos-mainnet", simulate_failure=True)
        with self.assertRaises(TimeoutError):
            a.submit_attestation(self._payload())

    def test_static_identity(self):
        i = StaticIdentity()
        self.assertEqual(i.resolve_actor({}), "anonymous")
