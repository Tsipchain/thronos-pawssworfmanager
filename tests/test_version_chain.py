import unittest

from thronos_pawssworfmanager.deterministic_vectors import load_vector_set
from thronos_pawssworfmanager.version_chain import build_chain_node, validate_chain_transition, verify_chain


class TestVersionChain(unittest.TestCase):
    def test_valid_linear_chain(self):
        case = load_vector_set("version_chain")[0]
        nodes = [
            build_chain_node(n["version"], n["manifest_hash"], n["parent_hash"])
            for n in case["chain"]
        ]
        result = verify_chain(nodes)
        self.assertTrue(result.ok)

    def test_failure_parent_hash_mismatch(self):
        n1 = build_chain_node(1, "h1", None)
        n2 = build_chain_node(2, "h2", "wrong")
        result = validate_chain_transition(n1, n2)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "parent_hash_mismatch")

    def test_failure_non_monotonic(self):
        n1 = build_chain_node(1, "h1", None)
        n2 = build_chain_node(3, "h3", "h1")
        result = validate_chain_transition(n1, n2)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "non_monotonic_version")

    def test_failure_fork_detected(self):
        nodes = [
            build_chain_node(1, "h1", None),
            build_chain_node(2, "h2", "h1"),
            build_chain_node(2, "hX", "h1"),
        ]
        result = verify_chain(nodes)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "fork_detected")

    def test_failure_invalid_genesis(self):
        bad = build_chain_node(2, "h2", None)
        result = validate_chain_transition(None, bad)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_genesis_version")
