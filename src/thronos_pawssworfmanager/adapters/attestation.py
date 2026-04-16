"""Attestation adapter contracts and dry-run-capable provider stubs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen


class AttestationAdapterError(Exception):
    def __init__(self, code: str, failure_class: str, message: str):
        super().__init__(message)
        self.code = code
        self.failure_class = failure_class


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


class RealThronosAttestationAdapter:
    """First real Thronos attestation execution path, gate-controlled."""

    def __init__(
        self,
        rpc_url: str,
        chain_id: str,
        contract_address: str,
        signer_ref: str,
        network: str,
        exec_enabled: bool,
        rpc_post_fn: Callable[[str, str, list[dict]], dict] | None = None,
    ) -> None:
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.contract_address = contract_address
        self.signer_ref = signer_ref
        self.network = network
        self.exec_enabled = exec_enabled
        self._rpc_post = rpc_post_fn or _json_rpc_post

    def submit_attestation(self, payload: AttestationPayload) -> dict:
        if not self.exec_enabled:
            raise AttestationAdapterError("attestation_execution_disabled", "permanent", "real attestation gate closed")
        if payload.target_backend_type != "thronos_network":
            raise AttestationAdapterError("invalid_backend_type", "permanent", "payload backend type mismatch")

        params = [
            {
                "chain_id": self.chain_id,
                "contract_address": self.contract_address,
                "signer_ref": self.signer_ref,
                "manifest_hash": payload.manifest_hash,
                "manifest_version": payload.manifest_version,
                "attestation_schema_version": payload.attestation_schema_version,
                "source_system": payload.source_system,
                "target_network": payload.target_network,
                "metadata": payload.metadata,
            }
        ]
        try:
            rpc_doc = self._rpc_post(self.rpc_url, "thronos_submitAttestation", params)
        except TimeoutError as exc:
            raise AttestationAdapterError("attestation_rpc_timeout", "transient", str(exc)) from exc
        except URLError as exc:
            raise AttestationAdapterError("attestation_rpc_unreachable", "transient", str(exc)) from exc
        except Exception as exc:
            raise AttestationAdapterError("attestation_submit_failed", "unknown", str(exc)) from exc

        result = _validate_rpc_submission_result(rpc_doc)
        tx_hash = result["tx_hash"]
        attestation_id = result.get("attestation_id") or f"thronos_{tx_hash[:10]}"
        return {
            "status": "submitted",
            "attestation_id": attestation_id,
            "network": self.network,
            "tx_hash": tx_hash,
            "execution_mode": "execute",
            "dry_run": False,
        }

    def get_attestation(self, attestation_id: str) -> dict:
        return {
            "status": "submitted",
            "attestation_id": attestation_id,
            "backend": "thronos_network",
            "mode": "execute",
        }

    def capabilities(self) -> dict:
        return {
            "backend": "thronos_network",
            "network": self.network,
            "provider_family": "chain",
            "dry_run_supported": True,
            "exec_enabled": self.exec_enabled,
            "real_submission_supported": True,
        }


def _json_rpc_post(rpc_url: str, method: str, params: list[dict]) -> dict:
    payload = {"jsonrpc": "2.0", "id": "pawssworfmanager", "method": method, "params": params}
    body = json.dumps(payload).encode("utf-8")
    req = Request(rpc_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _validate_rpc_submission_result(doc: dict) -> dict:
    if not isinstance(doc, dict):
        raise AttestationAdapterError("attestation_rpc_malformed_envelope", "permanent", "rpc response is not an object")
    if doc.get("jsonrpc") != "2.0":
        raise AttestationAdapterError("attestation_rpc_malformed_envelope", "permanent", "rpc jsonrpc field invalid")
    if "error" in doc:
        raise AttestationAdapterError("attestation_rpc_error", "permanent", f"rpc error: {doc['error']}")

    result = doc.get("result")
    if not isinstance(result, dict):
        raise AttestationAdapterError("attestation_rpc_malformed_result", "permanent", "rpc result missing or invalid")

    rpc_status = result.get("status")
    if rpc_status is not None and rpc_status not in {"accepted", "submitted"}:
        raise AttestationAdapterError("attestation_submission_rejected", "permanent", f"submission status: {rpc_status}")

    tx_hash = result.get("tx_hash")
    if not isinstance(tx_hash, str) or not re.fullmatch(r"0x[a-fA-F0-9]{64}", tx_hash):
        raise AttestationAdapterError("attestation_invalid_tx_hash", "permanent", "tx hash missing or invalid")

    attestation_id = result.get("attestation_id")
    if attestation_id is not None and not isinstance(attestation_id, str):
        raise AttestationAdapterError("attestation_malformed_attestation_id", "permanent", "attestation_id must be string")
    return result
