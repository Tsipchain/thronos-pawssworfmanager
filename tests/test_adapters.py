import unittest

from thronos_pawssworfmanager.adapters.attestation import FakeAttestationAdapter
from thronos_pawssworfmanager.adapters.blob_storage import InMemoryBlobStorage
from thronos_pawssworfmanager.adapters.identity import StaticIdentity
from thronos_pawssworfmanager.adapters.manifest_store import InMemoryManifestStore


class TestAdapters(unittest.TestCase):
    def test_blob_storage_in_memory(self):
        s = InMemoryBlobStorage()
        s.put_blob("b1", b"abc")
        self.assertEqual(s.get_blob("b1"), b"abc")
        s.delete_blob("b1")
        with self.assertRaises(KeyError):
            s.get_blob("b1")

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

    def test_static_identity(self):
        i = StaticIdentity()
        self.assertEqual(i.resolve_actor({}), "anonymous")
