import json
import os
import tempfile
import unittest
from pathlib import Path

from thronos_pawssworfmanager.http_service import wsgi_app


class TestHttpService(unittest.TestCase):
    def _call(self, method: str, path: str):
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        body = b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": method,
                    "PATH_INFO": path,
                },
                start_response,
            )
        )
        captured["body"] = json.loads(body.decode("utf-8"))
        return captured

    def test_healthz(self):
        res = self._call("GET", "/healthz")
        self.assertTrue(res["status"].startswith("200"))
        self.assertEqual(res["body"]["status"], "success")

    def test_metadata(self):
        res = self._call("GET", "/v1/metadata")
        self.assertTrue(res["status"].startswith("200"))
        self.assertEqual(res["body"]["data"]["api_default_version"], "v1")

    def test_readyz(self):
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
                res = self._call("GET", "/readyz")
                self.assertTrue(res["status"].startswith("200"))
            finally:
                for k, v in old.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
