import unittest

from thronos_pawssworfmanager.deterministic_vectors import load_vector_set
from thronos_pawssworfmanager.state_hash import compute_manifest_hash, compute_state_hash, hash_algorithm_id


class TestStateHash(unittest.TestCase):
    def test_hash_reproducible(self):
        case = load_vector_set("state_hashing")[0]
        h1 = compute_state_hash(case["manifest"])
        h2 = compute_state_hash(case["manifest"])
        self.assertEqual(h1, h2)

    def test_hash_sensitivity(self):
        case = load_vector_set("state_hashing")[1]
        h1 = compute_state_hash(case["manifest"])
        h2 = compute_state_hash(case["mutated_manifest"])
        self.assertNotEqual(h1, h2)

    def test_genesis_hash_format(self):
        case = load_vector_set("state_hashing")[2]
        h1 = compute_state_hash(case["manifest"])
        self.assertEqual(len(h1), 64)

    def test_failure_invalid_input_bytes(self):
        with self.assertRaises(ValueError):
            compute_manifest_hash(b"")

    def test_failure_unsupported_algorithm_id_check(self):
        self.assertEqual(hash_algorithm_id(), "sha256")
