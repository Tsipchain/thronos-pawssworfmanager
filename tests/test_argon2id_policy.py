import unittest

from thronos_pawssworfmanager.argon2id_policy import (
    get_default_argon2id_profile,
    profile_id,
    validate_argon2id_params,
)
from thronos_pawssworfmanager.deterministic_vectors import load_vector_set
from thronos_pawssworfmanager.types import Argon2idParams


class TestArgon2idPolicy(unittest.TestCase):
    def test_pass_vectors(self):
        for case in load_vector_set("argon2id_policy"):
            params = Argon2idParams(**case["params"])
            result = validate_argon2id_params(params)
            self.assertTrue(result.ok)

    def test_default_profile(self):
        params = get_default_argon2id_profile()
        self.assertEqual(profile_id(params), "argon2id-v1")

    def test_failure_memory_too_low(self):
        params = Argon2idParams(memory_kib=1024, time_cost=3, parallelism=1)
        result = validate_argon2id_params(params)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "memory_too_low")

    def test_failure_time_too_low(self):
        params = Argon2idParams(memory_kib=65536, time_cost=1, parallelism=1)
        result = validate_argon2id_params(params)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "time_cost_too_low")

    def test_failure_parallelism_out_of_range(self):
        params = Argon2idParams(memory_kib=65536, time_cost=3, parallelism=0)
        result = validate_argon2id_params(params)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "parallelism_out_of_range")

    def test_failure_unknown_profile(self):
        params = Argon2idParams(memory_kib=65536, time_cost=3, parallelism=1, profile_version="argon2id-v2")
        result = validate_argon2id_params(params)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "unknown_profile")
