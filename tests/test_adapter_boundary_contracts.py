import unittest

from thronos_pawssworfmanager.adapters.config import backend_selection_policy, resolve_adapter_config
from thronos_pawssworfmanager.services.retry_semantics import RetryPolicy, classify_failure, is_retryable


class TestAdapterBoundaryContracts(unittest.TestCase):
    def test_backend_selection_policy_is_allowlist_and_fail_closed(self):
        policy = backend_selection_policy()
        self.assertEqual(policy.mode, "allowlist")
        self.assertTrue(policy.fail_closed)
        self.assertIn("in_memory", policy.allowed_manifest_store_backends)

    def test_resolve_adapter_config_defaults(self):
        cfg = resolve_adapter_config({})
        self.assertEqual(cfg.manifest_store_backend, "in_memory")
        self.assertEqual(cfg.attestation_backend, "fake")
        self.assertEqual(cfg.identity_backend, "static")
        self.assertEqual(cfg.idempotency_scope, "single_instance_memory")

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
