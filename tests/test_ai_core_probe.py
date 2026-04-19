import unittest

from thronos_pawssworfmanager.ai_core_probe import classify_submit_probe


class TestAiCoreProbe(unittest.TestCase):
    def test_classifies_service_suspended(self):
        result = classify_submit_probe(503, "<html>Service Suspended</html>")
        self.assertEqual(result.classification, "upstream_service_suspended")

    def test_classifies_method_forbidden(self):
        result = classify_submit_probe(403, "Method forbidden")
        self.assertEqual(result.classification, "edge_method_forbidden")

    def test_classifies_registry_unregistered(self):
        result = classify_submit_probe(400, '{"error":"UNREGISTERED_SERVICE"}')
        self.assertEqual(result.classification, "registry_unregistered_service")

    def test_classifies_registry_scope_missing(self):
        result = classify_submit_probe(400, '{"error":"MISSING_SCOPE","scope":"ai:attest"}')
        self.assertEqual(result.classification, "registry_missing_scope")

    def test_classifies_submit_receipt_shape(self):
        result = classify_submit_probe(200, '{"tx_hash":"0x' + 'a' * 64 + '"}')
        self.assertEqual(result.classification, "attestation_submitted")

    def test_classifies_unknown_fallback(self):
        result = classify_submit_probe(418, "teapot")
        self.assertEqual(result.classification, "unknown")


if __name__ == "__main__":
    unittest.main()
