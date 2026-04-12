import math
import unittest

from thronos_pawssworfmanager.canonical_manifest import canonicalize_manifest, validate_manifest_schema
from thronos_pawssworfmanager.deterministic_vectors import load_vector_set


class TestCanonicalManifest(unittest.TestCase):
    def test_pass_vector_categories(self):
        for case in load_vector_set("canonical_encoding"):
            out = canonicalize_manifest(case["manifest"]).decode("utf-8")
            self.assertEqual(out, case["expected_canonical"])

    def test_failure_missing_required_fields(self):
        with self.assertRaises(ValueError):
            canonicalize_manifest({"vault_id": "x", "version": 1})

    def test_failure_wrong_field_types(self):
        result = validate_manifest_schema({"vault_id": "x", "version": "1", "entries": []})
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_version")

    def test_failure_non_canonicalizable_values(self):
        with self.assertRaises(ValueError):
            canonicalize_manifest({"vault_id": "x", "version": 1, "entries": [set([1, 2])]})

    def test_failure_nan_not_allowed(self):
        with self.assertRaises(ValueError):
            canonicalize_manifest({"vault_id": "x", "version": 1, "entries": [{"v": math.nan}]})
