import unittest

from thronos_pawssworfmanager.services.command_handler import handle_command, supported_commands


class TestCommandHandler(unittest.TestCase):
    def test_supported_commands(self):
        self.assertIn("create_vault", supported_commands())
        self.assertIn("add_entry", supported_commands())
        self.assertIn("export_vault", supported_commands())

    def test_create_vault_pipeline(self):
        result = handle_command(
            "create_vault",
            {
                "vault_id": "vault-1",
                "initial_entries": [],
            },
        )
        self.assertIn("manifest", result)
        self.assertIn("canonical_bytes", result)
        self.assertIn("manifest_hash", result)
        self.assertIn("chain_node", result)
        self.assertEqual(result["chain_node"]["version"], 1)
        self.assertEqual(result["canonical_bytes_encoding"], "base64")

    def test_add_entry_pipeline_with_prev_chain_node(self):
        result = handle_command(
            "add_entry",
            {
                "vault_id": "vault-1",
                "version": 2,
                "prev_chain_node": {"version": 1, "manifest_hash": "h1", "parent_hash": None},
                "entries": [{"id": "e1", "value": "old"}],
                "entry": {"id": "e2", "value": "new"},
            },
        )
        self.assertEqual(result["manifest"]["version"], 2)
        self.assertEqual(result["chain_node"]["parent_hash"], "h1")

    def test_reject_unsupported_command(self):
        with self.assertRaises(ValueError):
            handle_command("unknown", {})

    def test_reject_external_parent_hash_input(self):
        with self.assertRaises(ValueError):
            handle_command(
                "add_entry",
                {
                    "vault_id": "vault-1",
                    "version": 2,
                    "parent_hash": "danger",
                    "entries": [],
                    "entry": {"id": "e1"},
                    "prev_chain_node": {"version": 1, "manifest_hash": "h1", "parent_hash": None},
                },
            )
