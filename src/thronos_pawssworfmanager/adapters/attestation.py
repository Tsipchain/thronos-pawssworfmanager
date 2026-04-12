"""Attestation adapter contracts and fake implementation."""

from __future__ import annotations

from typing import Protocol


class AttestationAdapter(Protocol):
    def submit_attestation(self, manifest_hash: str) -> str: ...

    def get_attestation(self, attestation_id: str) -> dict: ...


class FakeAttestationAdapter:
    def submit_attestation(self, manifest_hash: str) -> str:
        return f"att_{manifest_hash[:8]}"

    def get_attestation(self, attestation_id: str) -> dict:
        return {
            "status": "confirmed",
            "attestation_id": attestation_id,
        }
