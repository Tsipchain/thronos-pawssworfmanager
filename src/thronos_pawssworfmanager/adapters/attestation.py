"""Attestation adapter contracts and dry-run-capable provider stubs."""

from __future__ import annotations

from typing import Protocol


class AttestationAdapter(Protocol):
    def submit_attestation(self, manifest_hash: str) -> str: ...

    def get_attestation(self, attestation_id: str) -> dict: ...

    def capabilities(self) -> dict: ...


class FakeAttestationAdapter:
    def submit_attestation(self, manifest_hash: str) -> str:
        return f"att_{manifest_hash[:8]}"

    def get_attestation(self, attestation_id: str) -> dict:
        return {
            "status": "confirmed",
            "attestation_id": attestation_id,
            "mode": "dry_run",
        }

    def capabilities(self) -> dict:
        return {
            "backend": "fake",
            "provider_family": "mock_chain",
            "dry_run_supported": True,
            "exec_enabled": False,
        }


class DryRunChainAttestationAdapter:
    """Provider-shaped chain adapter that never submits real transactions."""

    def __init__(self, backend: str, exec_enabled: bool = False, simulate_failure: bool = False) -> None:
        self.backend = backend
        self.exec_enabled = exec_enabled
        self.simulate_failure = simulate_failure

    def submit_attestation(self, manifest_hash: str) -> str:
        if self.exec_enabled:
            raise RuntimeError("real_attestation_submission_disabled")
        if self.simulate_failure:
            raise TimeoutError("simulated_attestation_provider_timeout")
        return f"dryrun_{self.backend}_{manifest_hash[:8]}"

    def get_attestation(self, attestation_id: str) -> dict:
        return {
            "status": "simulated_confirmed",
            "attestation_id": attestation_id,
            "backend": self.backend,
            "mode": "dry_run",
        }

    def capabilities(self) -> dict:
        return {
            "backend": self.backend,
            "provider_family": "chain",
            "dry_run_supported": True,
            "exec_enabled": self.exec_enabled,
        }
