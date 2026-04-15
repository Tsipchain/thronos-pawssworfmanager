"""Attestation adapter contracts and dry-run-capable provider stubs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class AttestationPayload:
    manifest_hash: str
    manifest_version: int
    attestation_schema_version: str
    source_system: str
    target_backend_type: str
    target_network: str
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "manifest_hash": self.manifest_hash,
            "manifest_version": self.manifest_version,
            "attestation_schema_version": self.attestation_schema_version,
            "source_system": self.source_system,
            "target_backend_type": self.target_backend_type,
            "target_network": self.target_network,
            "metadata": dict(self.metadata),
        }


class AttestationAdapter(Protocol):
    def submit_attestation(self, payload: AttestationPayload) -> dict: ...

    def get_attestation(self, attestation_id: str) -> dict: ...

    def capabilities(self) -> dict: ...


class FakeAttestationAdapter:
    def submit_attestation(self, payload: AttestationPayload) -> dict:
        att_id = f"att_{payload.manifest_hash[:8]}"
        return {
            "status": "confirmed",
            "attestation_id": att_id,
            "network": "none",
            "tx_hash": None,
            "execution_mode": "dry_run",
            "dry_run": True,
        }

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

    def __init__(
        self,
        backend: str,
        network: str,
        exec_enabled: bool = False,
        simulate_failure: bool = False,
    ) -> None:
        self.backend = backend
        self.network = network
        self.exec_enabled = exec_enabled
        self.simulate_failure = simulate_failure

    def submit_attestation(self, payload: AttestationPayload) -> dict:
        if self.exec_enabled:
            raise RuntimeError("real_attestation_submission_disabled")
        if self.simulate_failure:
            raise TimeoutError("simulated_attestation_provider_timeout")
        return {
            "status": "simulated_confirmed",
            "attestation_id": f"dryrun_{self.backend}_{payload.manifest_hash[:8]}",
            "network": self.network,
            "tx_hash": None,
            "execution_mode": "dry_run",
            "dry_run": True,
        }

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
            "network": self.network,
            "provider_family": "chain",
            "dry_run_supported": True,
            "exec_enabled": self.exec_enabled,
        }
