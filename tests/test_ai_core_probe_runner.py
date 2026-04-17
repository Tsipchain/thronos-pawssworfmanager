import unittest
from unittest.mock import patch

from thronos_pawssworfmanager import ai_core_probe_runner


class TestAiCoreProbeRunner(unittest.TestCase):
    @patch("thronos_pawssworfmanager.ai_core_probe_runner._probe")
    def test_run_diagnostics_normalizes_pubkey_and_summarizes_incident(self, mock_probe):
        mock_probe.side_effect = [
            ai_core_probe_runner.ProbeObservation(
                method="GET",
                status=503,
                body="Service Suspended",
                classification=ai_core_probe_runner.classify_submit_probe(503, "Service Suspended"),
            ),
            ai_core_probe_runner.ProbeObservation(
                method="POST",
                status=403,
                body="Method forbidden",
                classification=ai_core_probe_runner.classify_submit_probe(403, "Method forbidden"),
            ),
        ]

        result = ai_core_probe_runner.run_upstream_diagnostics(
            "https://ai.thronoschain.org/tx/submit", attestor_pubkey="0xABCD"
        )

        self.assertEqual(result.attestor_pubkey_lowercase, "0xabcd")
        self.assertEqual(result.summary, "upstream_availability_incident")
        self.assertEqual(result.registry_presence, "unknown_requires_upstream_registry_access")

    def test_build_summary_registry_blocker(self):
        summary = ai_core_probe_runner._build_summary("unknown", "registry_missing_scope")
        self.assertEqual(summary, "registry_prerequisite_not_met")

    @patch("thronos_pawssworfmanager.ai_core_probe_runner._probe")
    def test_diagnostics_json_shape(self, mock_probe):
        mock_probe.side_effect = [
            ai_core_probe_runner.ProbeObservation(
                method="GET",
                status=200,
                body="ok",
                classification=ai_core_probe_runner.classify_submit_probe(200, "ok"),
            ),
            ai_core_probe_runner.ProbeObservation(
                method="POST",
                status=200,
                body='{"tx_hash":"0x' + 'a' * 64 + '"}',
                classification=ai_core_probe_runner.classify_submit_probe(200, '{"tx_hash":"0x' + 'a' * 64 + '"}'),
            ),
        ]

        result = ai_core_probe_runner.run_upstream_diagnostics("https://ai.thronoschain.org/tx/submit")
        rendered = ai_core_probe_runner.diagnostics_to_json(result)

        self.assertIn('"submit_url": "https://ai.thronoschain.org/tx/submit"', rendered)
        self.assertIn('"summary": "submit_path_healthy"', rendered)


if __name__ == "__main__":
    unittest.main()
