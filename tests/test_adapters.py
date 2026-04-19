import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError

from thronos_pawssworfmanager.adapters.attestation import (
    AttestationAdapterError,
    AttestationPayload,
    DryRunChainAttestationAdapter,
    FakeAttestationAdapter,
    GenericRpcAttestationAdapter,
    RealThronosAttestationAdapter,
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
    def _payload(
        manifest_hash: str = "abcdef123",
        target_backend_type: str = "fake",
        target_network: str = "none",
        metadata: dict[str, str] | None = None,
    ) -> AttestationPayload:
        return AttestationPayload(
            manifest_hash=manifest_hash,
            manifest_version=1,
            attestation_schema_version="v1",
            source_system="test-suite",
            target_backend_type=target_backend_type,
            target_network=target_network,
            metadata=(
                {
                    "attestor_signature": "sig-test",
                    "tenant_id": "tenant-test",
                    "artifact_type": "vault_manifest",
                    "created_at": "2026-01-01T00:00:00Z",
                    "service": "test-suite",
                }
                if metadata is None
                else metadata
            ),
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

    def test_real_thronos_attestation_adapter_disabled_gate_blocks_submission(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=False,
            rpc_post_fn=lambda *_args, **_kwargs: {"jsonrpc": "2.0", "result": {"tx_hash": "0x" + "1" * 64}},
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.submit_attestation(self._payload(target_backend_type="thronos_network", target_network="thronos-mainnet"))
        self.assertEqual(err.exception.code, "attestation_execution_disabled")
        caps = a.capabilities()
        self.assertTrue(caps["polling_supported"])
        self.assertTrue(caps["reconciliation_tuple_enforced"])
        self.assertTrue(caps["poll_result_type_validation_enforced"])

    def test_real_thronos_attestation_adapter_executes_when_enabled(self):
        captured: dict[str, object] = {}

        def _submit(url: str, body: dict) -> dict:
            captured["url"] = url
            captured["body"] = body
            return {"status": "accepted", "tx_hash": "0x" + "a" * 64, "attestation_id": "att-real-1"}

        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            submit_post_fn=_submit,
        )
        submission = a.submit_attestation(
            self._payload(target_backend_type="thronos_network", target_network="thronos-mainnet")
        )
        self.assertEqual(submission["status"], "submitted")
        self.assertEqual(submission["lifecycle_state"], "submitted_not_finalized")
        self.assertEqual(submission["tx_hash"], "0x" + "a" * 64)
        self.assertTrue(submission["submission_id"].startswith("sub_"))
        self.assertEqual(submission["confirmation_status"], "not_polled")
        self.assertEqual(submission["finality_status"], "not_finalized")
        self.assertTrue(submission["reconciliation_id"].startswith("thronos-mainnet:0x"))
        self.assertFalse(submission["dry_run"])
        self.assertEqual(captured["url"], "https://rpc.example")
        body = captured["body"]
        self.assertEqual(body["tx_type"], "AI_ATTESTATION")
        self.assertEqual(body["service"], "test-suite")
        self.assertEqual(body["artifact_type"], "vault_manifest")
        self.assertEqual(body["tenant_id"], "tenant-test")
        self.assertEqual(body["created_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(body["payload"]["manifest_hash"], "abcdef123")
        self.assertEqual(body["payload"]["manifest_version"], 1)
        self.assertEqual(body["payload"]["attestation_schema_version"], "v1")
        self.assertEqual(body["attestor_pubkey"], "ref://signer")
        self.assertEqual(body["attestor_signature"], "sig-test")
        self.assertNotIn("pubkey", body)
        self.assertNotIn("signature", body)
        self.assertNotIn("jsonrpc", body)
        self.assertNotIn("method", body)
        self.assertNotIn("params", body)

    def test_real_thronos_attestation_adapter_rejects_malformed_rest_response(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            submit_post_fn=lambda *_args, **_kwargs: [],
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.submit_attestation(self._payload(target_backend_type="thronos_network", target_network="thronos-mainnet"))
        self.assertEqual(err.exception.code, "attestation_submit_malformed_response")

    def test_real_thronos_attestation_adapter_maps_400_malformed_request_to_permanent(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            submit_post_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                HTTPError("https://rpc.example", 400, "Bad Request", hdrs=None, fp=None)
            ),
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.submit_attestation(self._payload(target_backend_type="thronos_network", target_network="thronos-mainnet"))
        self.assertEqual(err.exception.code, "attestation_submit_bad_request")
        self.assertEqual(err.exception.lifecycle_state, "submission_failed_permanent")

    def test_real_thronos_attestation_adapter_rejects_missing_required_attestor_signature(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="pubkey-only",
            network="thronos-mainnet",
            exec_enabled=True,
            submit_post_fn=lambda *_args, **_kwargs: {"status": "accepted", "tx_hash": "0x" + "a" * 64},
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.submit_attestation(
                self._payload(
                    target_backend_type="thronos_network",
                    target_network="thronos-mainnet",
                    metadata={},
                )
            )
        self.assertEqual(err.exception.code, "attestation_missing_attestor_fields")

    def test_real_thronos_attestation_adapter_uses_signer_ref_pubkey_signature_pair(self):
        captured: dict[str, object] = {}

        def _submit(_url: str, body: dict) -> dict:
            captured["body"] = body
            return {"status": "accepted", "tx_hash": "0x" + "a" * 64}

        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="pubkey-1::sig-from-ref",
            network="thronos-mainnet",
            exec_enabled=True,
            submit_post_fn=_submit,
        )
        a.submit_attestation(
            self._payload(
                target_backend_type="thronos_network",
                target_network="thronos-mainnet",
                metadata={"tenant_id": "tenant-test"},
            )
        )
        body = captured["body"]
        self.assertEqual(body["attestor_pubkey"], "pubkey-1")
        self.assertEqual(body["attestor_signature"], "sig-from-ref")
        self.assertIn("payload", body)

    def test_real_thronos_attestation_adapter_rejects_missing_required_tenant_id(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            submit_post_fn=lambda *_args, **_kwargs: {"status": "accepted", "tx_hash": "0x" + "a" * 64},
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.submit_attestation(
                self._payload(
                    target_backend_type="thronos_network",
                    target_network="thronos-mainnet",
                    metadata={"attestor_signature": "sig-only"},
                )
            )
        self.assertEqual(err.exception.code, "attestation_missing_required_submit_fields")

    def test_real_thronos_attestation_adapter_rejects_missing_tx_hash(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            submit_post_fn=lambda *_args, **_kwargs: {"status": "accepted"},
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.submit_attestation(self._payload(target_backend_type="thronos_network", target_network="thronos-mainnet"))
        self.assertEqual(err.exception.code, "attestation_invalid_tx_hash")

    def test_real_thronos_attestation_adapter_rejected_status_is_permanent(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            submit_post_fn=lambda *_args, **_kwargs: {"status": "rejected", "tx_hash": "0x" + "c" * 64},
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.submit_attestation(self._payload(target_backend_type="thronos_network", target_network="thronos-mainnet"))
        self.assertEqual(err.exception.code, "attestation_submission_rejected")
        self.assertEqual(err.exception.lifecycle_state, "submission_rejected")

    def test_real_thronos_polling_status_classification(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            rpc_post_fn=lambda _url, method, _params: {
                "jsonrpc": "2.0",
                "result": {"status": "finalized", "confirmation_id": "conf-1"},
            }
            if method == "thronos_getAttestationStatus"
            else {"jsonrpc": "2.0", "result": {"status": "accepted", "tx_hash": "0x" + "a" * 64}},
        )
        poll = a.poll_attestation("sub_abc", "0x" + "a" * 64, "thronos-mainnet:0x" + "a" * 64)
        self.assertEqual(poll["confirmation_status"], "confirmed")
        self.assertEqual(poll["finality_status"], "finalized")
        self.assertEqual(poll["lifecycle_state"], "confirmed_finalized")
        self.assertEqual(poll["confirmation_id"], "conf-1")

    def test_real_thronos_polling_unknown_status_classification(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            rpc_post_fn=lambda _url, method, _params: {
                "jsonrpc": "2.0",
                "result": {"status": "mystery"},
            }
            if method == "thronos_getAttestationStatus"
            else {"jsonrpc": "2.0", "result": {"status": "accepted", "tx_hash": "0x" + "a" * 64}},
        )
        poll = a.poll_attestation("sub_abc", "0x" + "a" * 64, "thronos-mainnet:0x" + "a" * 64)
        self.assertEqual(poll["confirmation_status"], "unknown")
        self.assertEqual(poll["finality_status"], "unknown")
        self.assertEqual(poll["lifecycle_state"], "submission_unknown")

    def test_real_thronos_polling_pending_status_classification(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            rpc_post_fn=lambda _url, method, _params: {
                "jsonrpc": "2.0",
                "result": {"status": "pending"},
            }
            if method == "thronos_getAttestationStatus"
            else {"jsonrpc": "2.0", "result": {"status": "accepted", "tx_hash": "0x" + "a" * 64}},
        )
        poll = a.poll_attestation("sub_abc", "0x" + "a" * 64, "thronos-mainnet:0x" + "a" * 64)
        self.assertEqual(poll["confirmation_status"], "still_pending")
        self.assertEqual(poll["finality_status"], "not_finalized")
        self.assertEqual(poll["lifecycle_state"], "submitted_not_finalized")

    def test_real_thronos_polling_rejected_status_classification(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            rpc_post_fn=lambda _url, method, _params: {
                "jsonrpc": "2.0",
                "result": {"status": "dropped"},
            }
            if method == "thronos_getAttestationStatus"
            else {"jsonrpc": "2.0", "result": {"status": "accepted", "tx_hash": "0x" + "a" * 64}},
        )
        poll = a.poll_attestation("sub_abc", "0x" + "a" * 64, "thronos-mainnet:0x" + "a" * 64)
        self.assertEqual(poll["confirmation_status"], "rejected_or_dropped")
        self.assertEqual(poll["finality_status"], "rejected")
        self.assertEqual(poll["lifecycle_state"], "submission_rejected")

    def test_real_thronos_polling_rejects_mismatched_reconciliation_ids(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            rpc_post_fn=lambda _url, _method, _params: {"jsonrpc": "2.0", "result": {"status": "pending"}},
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.poll_attestation(
                "sub_abc",
                "0x" + "a" * 64,
                "thronos-mainnet:0x" + "b" * 64,
            )
        self.assertEqual(err.exception.code, "attestation_poll_id_mismatch")

    def test_real_thronos_polling_accepts_tx_hash_from_reconciliation_id(self):
        captured = {}

        def _rpc_post(_url, _method, params):
            captured["params"] = params
            return {"jsonrpc": "2.0", "result": {"status": "pending"}}

        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            rpc_post_fn=_rpc_post,
        )
        rid = "thronos-mainnet:0x" + "a" * 64
        poll = a.poll_attestation("sub_abc", None, rid)
        self.assertEqual(poll["confirmation_status"], "still_pending")
        self.assertEqual(captured["params"][0]["tx_hash"], "0x" + "a" * 64)

    def test_real_thronos_polling_rejects_non_string_status(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            rpc_post_fn=lambda _url, _method, _params: {"jsonrpc": "2.0", "result": {"status": 42}},
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.poll_attestation("sub_abc", "0x" + "a" * 64, "thronos-mainnet:0x" + "a" * 64)
        self.assertEqual(err.exception.code, "attestation_poll_malformed_result")

    def test_real_thronos_polling_rejects_non_string_confirmation_id(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            rpc_post_fn=lambda _url, _method, _params: {
                "jsonrpc": "2.0",
                "result": {"status": "confirmed", "confirmation_id": 99},
            },
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.poll_attestation("sub_abc", "0x" + "a" * 64, "thronos-mainnet:0x" + "a" * 64)
        self.assertEqual(err.exception.code, "attestation_poll_malformed_result")

    def test_real_thronos_attestation_adapter_rejects_invalid_tx_hash(self):
        a = RealThronosAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="111",
            contract_address="0xabc",
            signer_ref="ref://signer",
            network="thronos-mainnet",
            exec_enabled=True,
            rpc_post_fn=lambda *_args, **_kwargs: {"jsonrpc": "2.0", "result": {"status": "accepted", "tx_hash": "0x1234"}},
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.submit_attestation(self._payload(target_backend_type="thronos_network", target_network="thronos-mainnet"))
        self.assertEqual(err.exception.code, "attestation_invalid_tx_hash")

    def test_generic_rpc_attestation_adapter_contract_prepared_with_execution_capability(self):
        a = GenericRpcAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="1",
            network="generic-mainnet",
            backend_label="evm_generic",
            rpc_submit_method="eth_sendRawTransaction",
            rpc_poll_method="eth_getTransactionReceipt",
            exec_enabled=False,
        )
        submission = a.submit_attestation(self._payload(target_backend_type="rpc_generic", target_network="generic-mainnet"))
        self.assertEqual(submission["status"], "prepared_dry_run")
        self.assertEqual(submission["confirmation_status"], "not_polled")
        self.assertEqual(submission["finality_status"], "not_finalized")
        caps = a.capabilities()
        self.assertTrue(caps["real_submission_supported"])
        self.assertTrue(caps["rpc_generic_contract_prepared"])

    def test_generic_rpc_attestation_adapter_executes_when_enabled(self):
        a = GenericRpcAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="1",
            network="generic-mainnet",
            backend_label="evm_generic",
            rpc_submit_method="eth_sendRawTransaction",
            rpc_poll_method="eth_getTransactionReceipt",
            exec_enabled=True,
            rpc_post_fn=lambda *_args, **_kwargs: {
                "jsonrpc": "2.0",
                "result": {"tx_hash": "0x" + "d" * 64, "submission_id": "sub-rpc-1", "attestation_id": "att-rpc-1"},
            },
        )
        out = a.submit_attestation(self._payload(target_backend_type="rpc_generic", target_network="generic-mainnet"))
        self.assertEqual(out["status"], "submitted")
        self.assertEqual(out["tx_hash"], "0x" + "d" * 64)
        self.assertEqual(out["execution_mode"], "execute")
        self.assertFalse(out["dry_run"])

    def test_generic_rpc_attestation_adapter_rejects_malformed_response(self):
        a = GenericRpcAttestationAdapter(
            rpc_url="https://rpc.example",
            chain_id="1",
            network="generic-mainnet",
            backend_label="evm_generic",
            rpc_submit_method="eth_sendRawTransaction",
            rpc_poll_method="eth_getTransactionReceipt",
            exec_enabled=True,
            rpc_post_fn=lambda *_args, **_kwargs: {"jsonrpc": "2.0", "result": {"status": "accepted"}},
        )
        with self.assertRaises(AttestationAdapterError) as err:
            a.submit_attestation(self._payload(target_backend_type="rpc_generic", target_network="generic-mainnet"))
        self.assertEqual(err.exception.code, "rpc_generic_invalid_tx_hash")

    def test_static_identity(self):
        i = StaticIdentity()
        self.assertEqual(i.resolve_actor({}), "anonymous")
