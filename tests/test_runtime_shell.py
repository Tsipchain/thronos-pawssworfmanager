import os
import tempfile
import unittest
from pathlib import Path

from thronos_pawssworfmanager import create_app, create_runtime_shell
from thronos_pawssworfmanager.error_model import (
    ERR_INVALID_API_VERSION,
    ERR_READINESS_FAILED,
    ERR_ROUTE_NOT_FOUND,
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

    def test_health_route_contract_shape(self):
        shell = create_runtime_shell()
        resp = shell.handle("GET", "/healthz")
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.body["status"], "success")
        self.assertEqual(resp.body["code"], "ok")
        self.assertIn("api_version", resp.body)
        self.assertIn("request_id", resp.body)
        self.assertIsNone(resp.body["error"])

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
                self.assertEqual(resp.body["status"], "success")
                self.assertTrue(resp.body["data"]["ready"])
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
            self.assertEqual(resp.body["status"], "error")
            self.assertEqual(resp.body["code"], ERR_READINESS_FAILED)
        finally:
            if old is not None:
                os.environ["SERVICE_DATA_ROOT"] = old

    def test_capabilities_route_honest_disabled_flags(self):
        shell = create_runtime_shell()
        resp = shell.handle("GET", "/v1/capabilities")
        self.assertEqual(resp.status, 200)
        body = resp.body["data"]
        disabled = body["sensitive_features"]
        self.assertFalse(disabled["auth_runtime"])
        self.assertFalse(disabled["blockchain_writes"])
        self.assertFalse(disabled["vault_operations"])
        self.assertEqual(body["negotiation"]["selected_api_version"], "v1")

    def test_config_route_non_sensitive_metadata(self):
        shell = create_runtime_shell()
        resp = shell.handle("GET", "/v1/config")
        self.assertEqual(resp.status, 200)
        data = resp.body["data"]
        self.assertIn("hash_policy", data)
        self.assertIn("manifest_required_fields", data)

    def test_metadata_route_contract(self):
        shell = create_runtime_shell()
        resp = shell.handle("GET", "/v1/metadata")
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.body["data"]["api_default_version"], "v1")

    def test_not_found_route_uses_error_model(self):
        shell = create_runtime_shell()
        resp = shell.handle("GET", "/does-not-exist")
        self.assertEqual(resp.status, 404)
        self.assertEqual(resp.body["code"], ERR_ROUTE_NOT_FOUND)

    def test_invalid_api_version(self):
        shell = create_runtime_shell()
        resp = shell.handle("GET", "/v2/config")
        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.body["code"], ERR_INVALID_API_VERSION)

    def test_create_app_reports_runtime_shell_and_disabled_features(self):
        app = create_app(validate_paths=False)
        self.assertIn("service-contract-layer", app["capabilities"])
        self.assertIn("blockchain-writes", app["disabled_sensitive_features"])
        self.assertIn("GET /v1/metadata", app["routes"])
