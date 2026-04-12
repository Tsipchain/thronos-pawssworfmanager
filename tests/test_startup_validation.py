import os
import tempfile
import unittest
from pathlib import Path

from thronos_pawssworfmanager.startup_validation import validate_data_paths


class TestStartupValidation(unittest.TestCase):
    def test_paths_exist(self):
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
            for v in paths.values():
                Path(v).mkdir(parents=True, exist_ok=True)
            old = {k: os.getenv(k) for k in paths}
            try:
                os.environ.update(paths)
                result = validate_data_paths()
                self.assertTrue(result.ok)
            finally:
                for k, v in old.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
