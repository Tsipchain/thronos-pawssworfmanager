import math
import unittest

from thronos_pawssworfmanager.canonical_manifest import canonicalize_manifest, validate_manifest_schema
from thronos_pawssworfmanager.deterministic_vectors import load_vector_set


class TestCanonicalManifest(unittest.TestCase):
    def test_pass_vector_categories(self):
        for case in load_vector_set("canonical_encoding"):
            out = canonicalize_manifest(case["manifest"]).decode("utf-8")
            self.assertEqual(out, case["expected_canonical"])

    def test_numeric_normalization_boundaries_are_deterministic(self):
        manifest = {
            "vault_id": "num-boundary",
            "version": 1,
            "entries": [{"small": 1e-06, "large": 1e12, "neg_zero": -0.0}],
        }
        out1 = canonicalize_manifest(manifest)
        out2 = canonicalize_manifest(manifest)
        self.assertEqual(out1, out2)

    def test_failure_missing_required_fields(self):
        with self.assertRaises(ValueError):
            canonicalize_manifest({"vault_id": "x", "version": 1})

    def test_failure_wrong_field_types(self):
        result = validate_manifest_schema({"vault_id": "x", "version": "1", "entries": []})
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_version")

    def test_failure_version_bool_not_allowed(self):
        result = validate_manifest_schema({"vault_id": "x", "version": True, "entries": []})
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_version")

    def test_failure_entries_not_list(self):
        result = validate_manifest_schema({"vault_id": "x", "version": 1, "entries": {}})
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_entries")

    def test_failure_non_canonicalizable_values(self):
        with self.assertRaises(ValueError):
            canonicalize_manifest({"vault_id": "x", "version": 1, "entries": [set([1, 2])]})

    def test_failure_nan_not_allowed(self):
        with self.assertRaises(ValueError):
            canonicalize_manifest({"vault_id": "x", "version": 1, "entries": [{"v": math.nan}]})

    def test_failure_pos_inf_not_allowed(self):
        with self.assertRaises(ValueError):
            canonicalize_manifest({"vault_id": "x", "version": 1, "entries": [{"v": math.inf}]})

    def test_failure_neg_inf_not_allowed(self):
        with self.assertRaises(ValueError):
            canonicalize_manifest({"vault_id": "x", "version": 1, "entries": [{"v": -math.inf}]})
