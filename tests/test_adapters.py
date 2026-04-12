import tempfile
import unittest

from thronos_pawssworfmanager.adapters.attestation import DryRunChainAttestationAdapter, FakeAttestationAdapter
from thronos_pawssworfmanager.adapters.blob_storage import (
    BlobStorageError,
    DryRunBlobStorageProvider,
    InMemoryBlobStorage,
    LocalFileBlobStorage,
)
from thronos_pawssworfmanager.adapters.identity import StaticIdentity
from thronos_pawssworfmanager.adapters.manifest_store import InMemoryManifestStore


class TestAdapters(unittest.TestCase):
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
            self.assertEqual(read_err.exception.code, "blob_not_found")
            self.assertEqual(read_err.exception.failure_class, "permanent")

            with self.assertRaises(BlobStorageError) as del_err:
                s.delete_blob("missing")
            self.assertEqual(del_err.exception.code, "blob_not_found")
            self.assertEqual(del_err.exception.failure_class, "permanent")

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
        att_id = a.submit_attestation("abcdef123")
        self.assertTrue(att_id.startswith("att_"))
        receipt = a.get_attestation(att_id)
        self.assertEqual(receipt["status"], "confirmed")

    def test_chain_attestation_dry_run_provider(self):
        a = DryRunChainAttestationAdapter("thronos_chain")
        att_id = a.submit_attestation("abcdef123")
        self.assertTrue(att_id.startswith("dryrun_thronos_chain_"))
        receipt = a.get_attestation(att_id)
        self.assertEqual(receipt["status"], "simulated_confirmed")
        caps = a.capabilities()
        self.assertEqual(caps["backend"], "thronos_chain")
        self.assertFalse(caps["exec_enabled"])

    def test_chain_attestation_dry_run_failure_simulation(self):
        a = DryRunChainAttestationAdapter("thronos_chain", simulate_failure=True)
        with self.assertRaises(TimeoutError):
            a.submit_attestation("abcdef123")

    def test_static_identity(self):
        i = StaticIdentity()
        self.assertEqual(i.resolve_actor({}), "anonymous")
