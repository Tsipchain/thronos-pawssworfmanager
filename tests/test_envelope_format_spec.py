import unittest

from thronos_pawssworfmanager.deterministic_vectors import load_vector_set
from thronos_pawssworfmanager.envelope_format_spec import (
    envelope_version_id,
    required_envelope_fields,
    validate_envelope_header,
)


class TestEnvelopeFormatSpec(unittest.TestCase):
    def test_pass_vector(self):
        case = load_vector_set("envelope_format")[0]
        result = validate_envelope_header(case["header"])
        self.assertTrue(result.ok)

    def test_version_and_fields(self):
        self.assertEqual(envelope_version_id(), "xchacha20poly1305-v1")
        self.assertIn("nonce_len", required_envelope_fields())

    def test_failure_missing_field(self):
        result = validate_envelope_header({"version": "xchacha20poly1305-v1", "nonce_len": 24, "tag_len": 16})
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "missing_header_field")

    def test_failure_bad_version(self):
        result = validate_envelope_header({
            "version": "bad-v",
            "nonce_len": 24,
            "tag_len": 16,
            "kdf_profile": "argon2id-v1",
        })
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "unsupported_envelope_version")

    def test_failure_bad_nonce_tag_lengths(self):
        result = validate_envelope_header({
            "version": "xchacha20poly1305-v1",
            "nonce_len": 12,
            "tag_len": 16,
            "kdf_profile": "argon2id-v1",
        })
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_nonce_len")
