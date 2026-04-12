import unittest

from thronos_pawssworfmanager.adapters.config import (
    AdapterConfig,
    backend_selection_policy,
    execution_policy_status,
    resolve_adapter_config,
)
from thronos_pawssworfmanager.adapters.provider_config import load_provider_config_boundary
from thronos_pawssworfmanager.services.retry_semantics import RetryPolicy, classify_failure, is_retryable


class TestAdapterBoundaryContracts(unittest.TestCase):
    def test_backend_selection_policy_is_allowlist_and_fail_closed(self):
        policy = backend_selection_policy()
        self.assertEqual(policy.mode, "allowlist")
        self.assertTrue(policy.fail_closed)
        self.assertIn("in_memory", policy.allowed_manifest_store_backends)
        self.assertIn("s3", policy.allowed_blob_storage_backends)
        self.assertIn("dry_run", policy.allowed_execution_modes)

    def test_execution_policy_matrix_includes_required_pairs(self):
        status = execution_policy_status(
            AdapterConfig(
                manifest_store_backend="in_memory",
                blob_storage_backend="in_memory",
                attestation_backend="fake",
                identity_backend="static",
                execution_mode="dry_run",
            )
        )
        matrix = status["matrix"]
        self.assertTrue(matrix["blob_storage"]["in_memory+dry_run"])
        self.assertTrue(matrix["blob_storage"]["in_memory+execute"])
        self.assertTrue(matrix["blob_storage"]["real_like+dry_run"])
        self.assertFalse(matrix["blob_storage"]["real_like+execute"])
        self.assertTrue(matrix["attestation"]["fake+dry_run"])
        self.assertTrue(matrix["attestation"]["fake+execute"])
        self.assertTrue(matrix["attestation"]["chain_like+dry_run"])
        self.assertFalse(matrix["attestation"]["chain_like+execute"])

    def test_resolve_adapter_config_allows_in_memory_dry_run_and_execute(self):
        cfg_a = resolve_adapter_config({"BLOB_STORAGE_BACKEND": "in_memory", "ADAPTER_EXECUTION_MODE": "dry_run"})
        cfg_b = resolve_adapter_config({"BLOB_STORAGE_BACKEND": "in_memory", "ADAPTER_EXECUTION_MODE": "execute"})
        self.assertTrue(cfg_a.dry_run_enabled)
        self.assertEqual(cfg_b.execution_mode, "execute")

    def test_resolve_adapter_config_allows_real_blob_only_in_dry_run(self):
        cfg = resolve_adapter_config({"BLOB_STORAGE_BACKEND": "s3", "ADAPTER_EXECUTION_MODE": "dry_run"})
        self.assertEqual(cfg.blob_storage_backend, "s3")
        with self.assertRaises(ValueError):
            resolve_adapter_config({"BLOB_STORAGE_BACKEND": "s3", "ADAPTER_EXECUTION_MODE": "execute"})

    def test_resolve_adapter_config_allows_fake_attestation_dry_run_and_execute(self):
        cfg_a = resolve_adapter_config({"ATTESTATION_BACKEND": "fake", "ADAPTER_EXECUTION_MODE": "dry_run"})
        cfg_b = resolve_adapter_config({"ATTESTATION_BACKEND": "fake", "ADAPTER_EXECUTION_MODE": "execute"})
        self.assertEqual(cfg_a.attestation_backend, "fake")
        self.assertEqual(cfg_b.execution_mode, "execute")

    def test_resolve_adapter_config_allows_chain_attestation_only_in_dry_run(self):
        cfg = resolve_adapter_config({"ATTESTATION_BACKEND": "thronos_chain", "ADAPTER_EXECUTION_MODE": "dry_run"})
        self.assertEqual(cfg.attestation_backend, "thronos_chain")
        with self.assertRaises(ValueError):
            resolve_adapter_config({"ATTESTATION_BACKEND": "thronos_chain", "ADAPTER_EXECUTION_MODE": "execute"})

    def test_resolve_adapter_config_rejects_unsupported_backend(self):
        with self.assertRaises(ValueError):
            resolve_adapter_config({"MANIFEST_STORE_BACKEND": "sqlite"})

    def test_retry_failure_classification(self):
        self.assertEqual(classify_failure(TimeoutError("x")), "transient")
        self.assertEqual(classify_failure(ValueError("x")), "permanent")
        self.assertEqual(classify_failure(RuntimeError("x")), "unknown")

    def test_retryability_by_policy(self):
        policy = RetryPolicy(max_attempts=2)
        self.assertTrue(is_retryable(TimeoutError("x"), policy))
        self.assertFalse(is_retryable(ValueError("x"), policy))

    def test_provider_config_boundary_requires_shape_for_real_backends(self):
        cfg = resolve_adapter_config(
            {"BLOB_STORAGE_BACKEND": "s3", "ATTESTATION_BACKEND": "thronos_chain", "ADAPTER_EXECUTION_MODE": "dry_run"}
        )
        with self.assertRaises(ValueError):
            load_provider_config_boundary({}, cfg)

        boundary = load_provider_config_boundary(
            {
                "BLOB_PROVIDER": "aws",
                "BLOB_BUCKET": "bucket-a",
                "BLOB_REGION": "us-east-1",
                "ATTESTATION_RPC_URL": "https://rpc.example",
                "ATTESTATION_CHAIN_ID": "42",
            },
            cfg,
        )
        self.assertEqual(boundary.blob.bucket, "bucket-a")
        self.assertEqual(boundary.attestation.chain_id, "42")

    def test_provider_config_boundary_rejects_plaintext_secrets(self):
        cfg = resolve_adapter_config({})
        with self.assertRaises(ValueError):
            load_provider_config_boundary({"BLOB_ACCESS_KEY": "raw-secret"}, cfg)

    def test_provider_config_boundary_redacts_refs(self):
        cfg = resolve_adapter_config({})
        boundary = load_provider_config_boundary(
            {
                "BLOB_ACCESS_KEY_REF": "env://blob-access",
                "BLOB_SECRET_KEY_REF": "env://blob-secret",
                "ATTESTATION_SIGNER_KEY_REF": "env://chain-signer",
            },
            cfg,
        )
        redacted = boundary.to_redacted_dict()
        self.assertEqual(redacted["blob"]["access_key_ref"], "<redacted:set>")
        self.assertEqual(redacted["blob"]["secret_key_ref"], "<redacted:set>")
        self.assertEqual(redacted["attestation"]["signer_key_ref"], "<redacted:set>")
