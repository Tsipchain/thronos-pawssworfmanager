import unittest
import uuid

from thronos_pawssworfmanager.command_validation import build_command_result, validate_internal_command
from thronos_pawssworfmanager.internal_commands import (
    InternalCommand,
    RequestIdentity,
    WriteIntent,
    command_schema_summary,
)


class TestInternalCommands(unittest.TestCase):
    def _valid_command(self) -> InternalCommand:
        return InternalCommand(
            api_version="v1",
            identity=RequestIdentity(
                request_id=str(uuid.uuid4()),
                idempotency_key="idem-key-1234",
                actor_ref="actor:test",
            ),
            intent=WriteIntent(
                intent_id=str(uuid.uuid4()),
                command_type="vault.prepare_write_intent",
                vault_id="vault-1",
                manifest_hash="abcd",
                parent_hash="prev",
                expected_version=2,
            ),
            payload={"note": "future-write-intent"},
        )

    def test_schema_summary_execution_disabled(self):
        summary = command_schema_summary()
        self.assertFalse(summary["execution"]["enabled"])
        self.assertIn("vault.prepare_write_intent", summary["command_types"])

    def test_validate_internal_command_pass(self):
        result = validate_internal_command(self._valid_command())
        self.assertTrue(result.ok)

    def test_validate_internal_command_reject_bad_type(self):
        cmd = self._valid_command()
        cmd = InternalCommand(
            api_version=cmd.api_version,
            identity=cmd.identity,
            intent=WriteIntent(
                intent_id=cmd.intent.intent_id,
                command_type="vault.execute_write",
                vault_id=cmd.intent.vault_id,
                manifest_hash=cmd.intent.manifest_hash,
                parent_hash=cmd.intent.parent_hash,
                expected_version=cmd.intent.expected_version,
            ),
            payload=cmd.payload,
        )
        result = validate_internal_command(cmd)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_command_type")

    def test_validate_internal_command_reject_bad_idempotency_key(self):
        cmd = self._valid_command()
        cmd = InternalCommand(
            api_version=cmd.api_version,
            identity=RequestIdentity(
                request_id=cmd.identity.request_id,
                idempotency_key="bad key",
                actor_ref=cmd.identity.actor_ref,
            ),
            intent=cmd.intent,
            payload=cmd.payload,
        )
        result = validate_internal_command(cmd)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_idempotency_key")

    def test_validate_internal_command_reject_missing_actor(self):
        cmd = self._valid_command()
        cmd = InternalCommand(
            api_version=cmd.api_version,
            identity=RequestIdentity(
                request_id=cmd.identity.request_id,
                idempotency_key=cmd.identity.idempotency_key,
                actor_ref="",
            ),
            intent=cmd.intent,
            payload=cmd.payload,
        )
        result = validate_internal_command(cmd)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "missing_actor_ref")

    def test_validate_internal_command_reject_invalid_expected_version(self):
        cmd = self._valid_command()
        cmd = InternalCommand(
            api_version=cmd.api_version,
            identity=cmd.identity,
            intent=WriteIntent(
                intent_id=cmd.intent.intent_id,
                command_type=cmd.intent.command_type,
                vault_id=cmd.intent.vault_id,
                manifest_hash=cmd.intent.manifest_hash,
                parent_hash=cmd.intent.parent_hash,
                expected_version=0,
            ),
            payload=cmd.payload,
        )
        result = validate_internal_command(cmd)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_expected_version")

    def test_build_command_result_rejection_behavior(self):
        cmd = self._valid_command()
        result = build_command_result(cmd)
        self.assertTrue(result["accepted"])
        self.assertFalse(result["executed"])
        self.assertEqual(result["code"], "command_execution_disabled")
