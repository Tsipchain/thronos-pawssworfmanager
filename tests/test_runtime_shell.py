import os
import tempfile
import unittest
from pathlib import Path

from thronos_pawssworfmanager import create_app, create_runtime_shell
from thronos_pawssworfmanager.error_model import (
    ERR_COMMAND_PIPELINE_FAILED,
    ERR_COMMAND_VALIDATION_FAILED,
    ERR_INVALID_API_VERSION,
    ERR_READINESS_FAILED,
    ERR_ROUTE_NOT_FOUND,
    ERR_UNSUPPORTED_COMMAND,
)


class TestRuntimeShell(unittest.TestCase):
    def test_route_registration_layout(self):
        shell = create_runtime_shell()
        routes = shell.routes()
        self.assertIn(("GET", "/healthz"), routes)
        self.assertIn(("GET", "/readyz"), routes)
        self.assertIn(("GET", "/v1/config"), routes)
        self.assertIn(("GET", "/v1/capabilities"), routes)
        self.assertIn(("GET", "/v1/metadata"), routes)
        self.assertIn(("GET", "/v1/contracts/internal"), routes)
        self.assertIn(("POST", "/v1/commands/execute"), routes)

    def test_capabilities_reports_adapter_selection_policy(self):
        shell = create_runtime_shell()
        resp = shell.handle("GET", "/v1/capabilities")
        self.assertEqual(resp.status, 200)
        adapters = resp.body["data"]["adapters"]
        self.assertEqual(adapters["manifest_store"], "in_memory")
        self.assertEqual(adapters["blob_storage"], "in_memory")
        self.assertEqual(adapters["attestation"], "fake")
        self.assertEqual(adapters["execution_mode"], "dry_run")
        self.assertTrue(adapters["dry_run_enabled"])
        self.assertEqual(adapters["idempotency_scope"], "single_instance_memory")
        self.assertEqual(adapters["selection_policy"]["mode"], "allowlist")
        self.assertTrue(adapters["execution_policy"]["startup_allowed"])
        self.assertEqual(adapters["execution_policy"]["enforcement"], "fail_closed")
        self.assertTrue(adapters["blob_capabilities"]["dry_run_supported"])
        self.assertTrue(adapters["attestation_capabilities"]["dry_run_supported"])
        self.assertIn("provider_config_boundary", adapters)

    def test_config_redacts_provider_secret_refs(self):
        shell = create_runtime_shell()
        resp = shell.handle("GET", "/v1/config")
        self.assertEqual(resp.status, 200)
        provider = resp.body["data"]["provider_config"]
        self.assertIn("secret_source_policy", provider)
        self.assertNotIn("raw-secret", str(provider))
        self.assertNotIn("env://", str(provider))

    def test_command_execute_success(self):
        shell = create_runtime_shell()
        resp = shell.handle(
            "POST",
            "/v1/commands/execute",
            {
                "command": "create_vault",
                "payload": {"vault_id": "vault-1", "initial_entries": []},
            },
        )
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.body["status"], "success")
        self.assertEqual(resp.body["data"]["canonical_bytes_encoding"], "base64")
        self.assertEqual(resp.body["data"]["storage_write"], "created")

    def test_command_execute_validation_error(self):
        shell = create_runtime_shell()
        resp = shell.handle("POST", "/v1/commands/execute", {"command": "create_vault"})
        self.assertEqual(resp.status, 422)
        self.assertEqual(resp.body["code"], ERR_COMMAND_VALIDATION_FAILED)

    def test_command_execute_unsupported(self):
        shell = create_runtime_shell()
        resp = shell.handle("POST", "/v1/commands/execute", {"command": "x", "payload": {}})
        self.assertEqual(resp.status, 422)
        self.assertEqual(resp.body["code"], ERR_UNSUPPORTED_COMMAND)

    def test_command_execute_pipeline_failure(self):
        shell = create_runtime_shell()
        resp = shell.handle(
            "POST",
            "/v1/commands/execute",
            {
                "command": "add_entry",
                "payload": {"vault_id": "v1", "version": 2, "entries": [], "entry": {"id": "e1"}},
            },
        )
        self.assertEqual(resp.status, 422)
        self.assertEqual(resp.body["code"], ERR_COMMAND_PIPELINE_FAILED)

    def test_readiness_route_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = {
                "SERVICE_DATA_ROOT": tmp,
                "PATH_BLOBS": f"{tmp}/blobs",
                "PATH_MANIFESTS": f"{tmp}/manifests",
                "PATH_TOMBSTONES": f"{tmp}/tombstones",
                "PATH_EXPORTS": f"{tmp}/transfers/exports",
                "PATH_IMPORTS": f"{tmp}/transfers/imports",
                "PATH_LOGS": f"{tmp}/logs",
                "PATH_AUDIT": f"{tmp}/audit",
            }
            for p in paths.values():
                Path(p).mkdir(parents=True, exist_ok=True)
            old = {k: os.getenv(k) for k in paths}
            try:
                os.environ.update(paths)
                shell = create_runtime_shell()
                resp = shell.handle("GET", "/readyz")
                self.assertEqual(resp.status, 200)
            finally:
                for k, v in old.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

    def test_readiness_route_fail_uses_error_model(self):
        old = os.environ.pop("SERVICE_DATA_ROOT", None)
        try:
            shell = create_runtime_shell()
            resp = shell.handle("GET", "/readyz")
            self.assertEqual(resp.status, 503)
            self.assertEqual(resp.body["code"], ERR_READINESS_FAILED)
        finally:
            if old is not None:
                os.environ["SERVICE_DATA_ROOT"] = old

    def test_not_found_route_uses_error_model(self):
        shell = create_runtime_shell()
        resp = shell.handle("GET", "/does-not-exist")
        self.assertEqual(resp.status, 404)
        self.assertEqual(resp.body["code"], ERR_ROUTE_NOT_FOUND)

    def test_metadata_reports_execution_policy_enforced(self):
        shell = create_runtime_shell()
        resp = shell.handle("GET", "/v1/metadata")
        self.assertEqual(resp.status, 200)
        self.assertTrue(resp.body["data"]["execution_policy_enforced"])
        self.assertTrue(resp.body["data"]["secret_policy_enforced"])
        self.assertIn("blob_storage", resp.body["data"]["secret_backed_adapters"])

    def test_invalid_api_version(self):
        shell = create_runtime_shell()
        resp = shell.handle("GET", "/v2/config")
        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.body["code"], ERR_INVALID_API_VERSION)

    def test_create_app_reports_runtime_shell_and_disabled_features(self):
        app = create_app(validate_paths=False)
        self.assertIn("deterministic-command-pipeline", app["capabilities"])
        self.assertIn("vault-command-execution-side-effects", app["disabled_sensitive_features"])
        self.assertIn("POST /v1/commands/execute", app["routes"])
