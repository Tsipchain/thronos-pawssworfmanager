"""Attestation adapter contracts and dry-run-capable provider stubs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AttestationAdapterError(Exception):
    def __init__(self, code: str, failure_class: str, message: str, lifecycle_state: str):
        super().__init__(message)
        self.code = code
        self.failure_class = failure_class
        self.lifecycle_state = lifecycle_state


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

    def poll_attestation(self, submission_id: str, tx_hash: str | None, reconciliation_id: str | None) -> dict: ...

    def capabilities(self) -> dict: ...


class FakeAttestationAdapter:
    def submit_attestation(self, payload: AttestationPayload) -> dict:
        att_id = f"att_{payload.manifest_hash[:8]}"
        return {
            "status": "confirmed",
            "lifecycle_state": "submitted_not_finalized",
            "attestation_id": att_id,
            "submission_id": f"sub_{att_id}",
            "network": "none",
            "tx_hash": None,
            "confirmation_id": None,
            "confirmation_status": "not_polled",
            "finality_status": "not_finalized",
            "confirmation_proof": None,
            "reconciliation_id": None,
            "execution_mode": "dry_run",
            "dry_run": True,
        }

    def get_attestation(self, attestation_id: str) -> dict:
        return {
            "status": "confirmed",
            "attestation_id": attestation_id,
            "mode": "dry_run",
        }

    def poll_attestation(self, submission_id: str, tx_hash: str | None, reconciliation_id: str | None) -> dict:
        return {
            "confirmation_status": "unknown",
            "finality_status": "unknown",
            "lifecycle_state": "submission_unknown",
            "confirmation_id": None,
            "confirmation_proof": None,
            "polling_supported": False,
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
            "lifecycle_state": "submitted_not_finalized",
            "attestation_id": f"dryrun_{self.backend}_{payload.manifest_hash[:8]}",
            "submission_id": f"sub_dryrun_{self.backend}_{payload.manifest_hash[:8]}",
            "network": self.network,
            "tx_hash": None,
            "confirmation_id": None,
            "confirmation_status": "not_polled",
            "finality_status": "not_finalized",
            "confirmation_proof": None,
            "reconciliation_id": None,
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

    def poll_attestation(self, submission_id: str, tx_hash: str | None, reconciliation_id: str | None) -> dict:
        return {
            "confirmation_status": "still_pending",
            "finality_status": "not_finalized",
            "lifecycle_state": "submitted_not_finalized",
            "confirmation_id": None,
            "confirmation_proof": None,
            "polling_supported": True,
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
        submit_auth_header_name: str | None = None,
        submit_auth_header_ref: str | None = None,
        submit_auth_header_prefix: str | None = None,
        submit_post_fn: Callable[..., dict] | None = None,
    ) -> None:
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.contract_address = contract_address
        self.signer_ref = signer_ref
        self.network = network
        self.exec_enabled = exec_enabled
        self.submit_auth_header_name = submit_auth_header_name
        self.submit_auth_header_ref = submit_auth_header_ref
        self.submit_auth_header_prefix = submit_auth_header_prefix
        self._rpc_post = rpc_post_fn or _json_rpc_post
        if submit_post_fn is not None:
            self._submit_post = lambda url, body, headers: _invoke_submit_post(submit_post_fn, url, body, headers)
        elif rpc_post_fn is not None:
            self._submit_post = lambda url, body, _headers: rpc_post_fn(url, body)  # type: ignore[misc,call-arg]
        else:
            self._submit_post = _json_http_post

    def submit_attestation(self, payload: AttestationPayload) -> dict:
        if not self.exec_enabled:
            raise AttestationAdapterError(
                "attestation_execution_disabled",
                "permanent",
                "real attestation gate closed",
                "submission_failed_permanent",
            )
        if payload.target_backend_type != "thronos_network":
            raise AttestationAdapterError(
                "invalid_backend_type",
                "permanent",
                "payload backend type mismatch",
                "submission_failed_permanent",
            )

        attestor_pubkey = self.signer_ref
        attestor_signature = payload.metadata.get("attestor_signature")
        if "::" in self.signer_ref:
            parsed_pubkey, parsed_signature = self.signer_ref.split("::", 1)
            attestor_pubkey = parsed_pubkey
            attestor_signature = attestor_signature or parsed_signature
        if not attestor_pubkey or not attestor_signature:
            raise AttestationAdapterError(
                "attestation_missing_attestor_fields",
                "permanent",
                "attestor_pubkey/attestor_signature required for AI_ATTESTATION submit",
                "submission_failed_permanent",
            )
        tenant_id = payload.metadata.get("tenant_id")
        if not tenant_id:
            raise AttestationAdapterError(
                "attestation_missing_required_submit_fields",
                "permanent",
                "tenant_id required for AI_ATTESTATION submit",
                "submission_failed_permanent",
            )
        artifact_type = payload.metadata.get("artifact_type") or "vault_manifest"
        created_at = payload.metadata.get("created_at") or _utc_now_iso8601()
        service = payload.metadata.get("service") or payload.source_system

        request_body = {
            "tx_type": "AI_ATTESTATION",
            "service": service,
            "artifact_type": artifact_type,
            "tenant_id": tenant_id,
            "created_at": created_at,
            "payload": {
                "chain_id": self.chain_id,
                "contract_address": self.contract_address,
                "manifest_hash": payload.manifest_hash,
                "manifest_version": payload.manifest_version,
                "attestation_schema_version": payload.attestation_schema_version,
                "source_system": payload.source_system,
                "target_network": payload.target_network,
                "metadata": payload.metadata,
            },
            "pubkey": attestor_pubkey,
            "signature": attestor_signature,
        }
        submit_headers: dict[str, str] = {}
        if self.submit_auth_header_name and self.submit_auth_header_ref:
            auth_value = self.submit_auth_header_ref
            if self.submit_auth_header_prefix:
                auth_value = f"{self.submit_auth_header_prefix} {auth_value}"
            submit_headers[self.submit_auth_header_name] = auth_value
        try:
            submit_doc = self._submit_post(self.rpc_url, request_body, submit_headers)
        except HTTPError as exc:
            if exc.code == 400:
                raise AttestationAdapterError(
                    "attestation_submit_bad_request",
                    "permanent",
                    "thronos submit endpoint rejected request body",
                    "submission_failed_permanent",
                ) from exc
            if 400 <= exc.code < 500:
                raise AttestationAdapterError(
                    "attestation_submission_rejected",
                    "permanent",
                    f"submit http status: {exc.code}",
                    "submission_rejected",
                ) from exc
            raise AttestationAdapterError(
                "attestation_rpc_unreachable",
                "transient",
                str(exc),
                "submission_failed_retryable",
            ) from exc
        except TimeoutError as exc:
            raise AttestationAdapterError(
                "attestation_rpc_timeout",
                "transient",
                str(exc),
                "submission_failed_retryable",
            ) from exc
        except URLError as exc:
            raise AttestationAdapterError(
                "attestation_rpc_unreachable",
                "transient",
                str(exc),
                "submission_failed_retryable",
            ) from exc
        except Exception as exc:
            raise AttestationAdapterError(
                "attestation_submit_failed",
                "unknown",
                str(exc),
                "submission_unknown",
            ) from exc

        result = _validate_rest_submission_result(submit_doc)
        tx_hash = result["tx_hash"]
        attestation_id = result.get("attestation_id") or f"thronos_{tx_hash[:10]}"
        submission_id = result.get("submission_id") or f"sub_{payload.manifest_hash[:8]}_{tx_hash[2:10]}"
        return {
            "status": "submitted",
            "lifecycle_state": "submitted_not_finalized",
            "attestation_id": attestation_id,
            "submission_id": submission_id,
            "network": self.network,
            "tx_hash": tx_hash,
            "confirmation_id": None,
            "confirmation_status": "not_polled",
            "finality_status": "not_finalized",
            "confirmation_proof": None,
            "reconciliation_id": f"{self.network}:{tx_hash}",
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

    def poll_attestation(self, submission_id: str, tx_hash: str | None, reconciliation_id: str | None) -> dict:
        if not self.exec_enabled:
            raise AttestationAdapterError(
                "attestation_polling_disabled",
                "permanent",
                "thronos polling gate closed",
                "submission_unknown",
            )
        if not submission_id:
            raise AttestationAdapterError(
                "attestation_poll_missing_submission_id",
                "permanent",
                "submission_id required for polling",
                "submission_unknown",
            )
        normalized_tx_hash = tx_hash
        if tx_hash is not None:
            if not isinstance(tx_hash, str) or not re.fullmatch(r"0x[a-fA-F0-9]{64}", tx_hash):
                raise AttestationAdapterError(
                    "attestation_poll_invalid_tx_hash",
                    "permanent",
                    "poll tx hash invalid",
                    "submission_unknown",
                )

        if reconciliation_id is not None:
            if not isinstance(reconciliation_id, str):
                raise AttestationAdapterError(
                    "attestation_poll_invalid_reconciliation_id",
                    "permanent",
                    "reconciliation_id must be string",
                    "submission_unknown",
                )
            prefix = f"{self.network}:"
            if not reconciliation_id.startswith(prefix):
                raise AttestationAdapterError(
                    "attestation_poll_invalid_reconciliation_id",
                    "permanent",
                    "reconciliation_id network mismatch",
                    "submission_unknown",
                )
            rid_tx_hash = reconciliation_id[len(prefix) :]
            if not re.fullmatch(r"0x[a-fA-F0-9]{64}", rid_tx_hash):
                raise AttestationAdapterError(
                    "attestation_poll_invalid_reconciliation_id",
                    "permanent",
                    "reconciliation_id tx hash invalid",
                    "submission_unknown",
                )
            if normalized_tx_hash is None:
                normalized_tx_hash = rid_tx_hash
            elif normalized_tx_hash.lower() != rid_tx_hash.lower():
                raise AttestationAdapterError(
                    "attestation_poll_id_mismatch",
                    "permanent",
                    "tx_hash does not match reconciliation_id",
                    "submission_unknown",
                )
        params = [
            {
                "chain_id": self.chain_id,
                "submission_id": submission_id,
                "tx_hash": normalized_tx_hash,
                "reconciliation_id": reconciliation_id,
            }
        ]
        try:
            rpc_doc = self._rpc_post(self.rpc_url, "thronos_getAttestationStatus", params)
        except TimeoutError as exc:
            raise AttestationAdapterError(
                "attestation_poll_timeout",
                "transient",
                str(exc),
                "submission_failed_retryable",
            ) from exc
        except URLError as exc:
            raise AttestationAdapterError(
                "attestation_poll_unreachable",
                "transient",
                str(exc),
                "submission_failed_retryable",
            ) from exc
        except Exception as exc:
            raise AttestationAdapterError(
                "attestation_poll_failed",
                "unknown",
                str(exc),
                "submission_unknown",
            ) from exc
        return _validate_rpc_poll_result(rpc_doc)

    def capabilities(self) -> dict:
        return {
            "backend": "thronos_network",
            "network": self.network,
            "provider_family": "chain",
            "dry_run_supported": True,
            "exec_enabled": self.exec_enabled,
            "real_submission_supported": True,
            "polling_supported": True,
            "reconciliation_tuple_enforced": True,
            "poll_result_type_validation_enforced": True,
        }


class GenericRpcAttestationAdapter:
    """Generic RPC attestation adapter with gate-controlled real execution."""

    def __init__(
        self,
        rpc_url: str,
        chain_id: str,
        network: str,
        backend_label: str,
        rpc_submit_method: str,
        rpc_poll_method: str,
        exec_enabled: bool = False,
        rpc_post_fn: Callable[[str, str, list[dict]], dict] | None = None,
    ) -> None:
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.network = network
        self.backend_label = backend_label
        self.rpc_submit_method = rpc_submit_method
        self.rpc_poll_method = rpc_poll_method
        self.exec_enabled = exec_enabled
        self._rpc_post = rpc_post_fn or _json_rpc_post

    def submit_attestation(self, payload: AttestationPayload) -> dict:
        if self.exec_enabled:
            params = [
                {
                    "chain_id": self.chain_id,
                    "backend_label": self.backend_label,
                    "manifest_hash": payload.manifest_hash,
                    "manifest_version": payload.manifest_version,
                    "attestation_schema_version": payload.attestation_schema_version,
                    "source_system": payload.source_system,
                    "target_network": payload.target_network,
                    "metadata": payload.metadata,
                }
            ]
            try:
                rpc_doc = self._rpc_post(self.rpc_url, self.rpc_submit_method, params)
            except TimeoutError as exc:
                raise AttestationAdapterError(
                    "rpc_generic_timeout",
                    "transient",
                    str(exc),
                    "submission_failed_retryable",
                ) from exc
            except URLError as exc:
                raise AttestationAdapterError(
                    "rpc_generic_unreachable",
                    "transient",
                    str(exc),
                    "submission_failed_retryable",
                ) from exc
            except Exception as exc:
                raise AttestationAdapterError(
                    "rpc_generic_submit_failed",
                    "unknown",
                    str(exc),
                    "submission_unknown",
                ) from exc
            result = _validate_rpc_generic_submission_result(rpc_doc)
            tx_hash = result["tx_hash"]
            submission_id = result.get("submission_id") or f"sub_rpcg_{payload.manifest_hash[:8]}_{tx_hash[2:10]}"
            attestation_id = result.get("attestation_id") or f"rpc_generic_{tx_hash[2:10]}"
            return {
                "status": "submitted",
                "lifecycle_state": "submitted_not_finalized",
                "attestation_id": attestation_id,
                "submission_id": submission_id,
                "network": self.network,
                "tx_hash": tx_hash,
                "confirmation_id": None,
                "confirmation_status": "not_polled",
                "finality_status": "not_finalized",
                "confirmation_proof": None,
                "reconciliation_id": f"{self.backend_label}:{tx_hash}",
                "execution_mode": "execute",
                "dry_run": False,
            }
        return {
            "status": "prepared_dry_run",
            "lifecycle_state": "submitted_not_finalized",
            "attestation_id": f"rpc_generic_{payload.manifest_hash[:8]}",
            "submission_id": f"sub_rpcg_{payload.manifest_hash[:8]}",
            "network": self.network,
            "tx_hash": None,
            "confirmation_id": None,
            "confirmation_status": "not_polled",
            "finality_status": "not_finalized",
            "confirmation_proof": None,
            "reconciliation_id": f"{self.backend_label}:{payload.manifest_hash[:8]}",
            "execution_mode": "dry_run",
            "dry_run": True,
        }

    def get_attestation(self, attestation_id: str) -> dict:
        return {
            "status": "prepared_dry_run",
            "attestation_id": attestation_id,
            "backend": "rpc_generic",
            "mode": "dry_run",
        }

    def poll_attestation(self, submission_id: str, tx_hash: str | None, reconciliation_id: str | None) -> dict:
        return {
            "confirmation_status": "unknown",
            "finality_status": "unknown",
            "lifecycle_state": "submission_unknown",
            "confirmation_id": None,
            "confirmation_proof": {
                "proof_source": "thronos_rpc",
                "proof_kind": "status_attestation",
                "provider_status": "generic_rpc_unavailable",
                "confirmation_id": None,
            },
            "polling_supported": False,
        }

    def capabilities(self) -> dict:
        return {
            "backend": "rpc_generic",
            "network": self.network,
            "provider_family": "chain",
            "dry_run_supported": True,
            "exec_enabled": self.exec_enabled,
            "real_submission_supported": True,
            "rpc_generic_contract_prepared": True,
            "rpc_submit_method": self.rpc_submit_method,
            "rpc_poll_method": self.rpc_poll_method,
            "backend_label": self.backend_label,
        }


def _json_rpc_post(rpc_url: str, method: str, params: list[dict]) -> dict:
    payload = {"jsonrpc": "2.0", "id": "pawssworfmanager", "method": method, "params": params}
    body = json.dumps(payload).encode("utf-8")
    req = Request(rpc_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _json_http_post(url: str, body: dict, extra_headers: dict[str, str] | None = None) -> dict:
    encoded = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    req = Request(url, data=encoded, headers=headers, method="POST")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _utc_now_iso8601() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _invoke_submit_post(fn: Callable[..., dict], url: str, body: dict, headers: dict[str, str]) -> dict:
    try:
        return fn(url, body, headers)
    except TypeError:
        return fn(url, body)


def _validate_rpc_generic_submission_result(doc: dict) -> dict:
    if not isinstance(doc, dict) or doc.get("jsonrpc") != "2.0":
        raise AttestationAdapterError(
            "rpc_generic_malformed_envelope",
            "permanent",
            "rpc generic envelope invalid",
            "submission_unknown",
        )
    if "error" in doc:
        raise AttestationAdapterError(
            "rpc_generic_rpc_error",
            "permanent",
            f"rpc generic error: {doc['error']}",
            "submission_failed_permanent",
        )
    result = doc.get("result")
    if not isinstance(result, dict):
        raise AttestationAdapterError(
            "rpc_generic_malformed_result",
            "permanent",
            "rpc generic result invalid",
            "submission_unknown",
        )
    tx_hash = result.get("tx_hash")
    if not isinstance(tx_hash, str) or not re.fullmatch(r"0x[a-fA-F0-9]{64}", tx_hash):
        raise AttestationAdapterError(
            "rpc_generic_invalid_tx_hash",
            "permanent",
            "rpc generic tx hash missing or invalid",
            "submission_unknown",
        )
    for optional in ("submission_id", "attestation_id"):
        value = result.get(optional)
        if value is not None and not isinstance(value, str):
            raise AttestationAdapterError(
                "rpc_generic_malformed_result",
                "permanent",
                f"{optional} must be string",
                "submission_unknown",
            )
    return result


def _validate_rest_submission_result(doc: dict) -> dict:
    if not isinstance(doc, dict):
        raise AttestationAdapterError(
            "attestation_submit_malformed_response",
            "permanent",
            "submit response is not an object",
            "submission_unknown",
        )
    result = doc.get("data") if isinstance(doc.get("data"), dict) else doc
    status = result.get("status")
    if status == "rejected":
        raise AttestationAdapterError(
            "attestation_submission_rejected",
            "permanent",
            "submission explicitly rejected by backend",
            "submission_rejected",
        )
    if status is not None and status not in {"accepted", "submitted", "ok", "success"}:
        raise AttestationAdapterError(
            "attestation_submission_rejected",
            "permanent",
            f"submission status: {status}",
            "submission_rejected",
        )

    tx_hash = result.get("tx_hash") or result.get("txHash")
    if not isinstance(tx_hash, str) or not re.fullmatch(r"0x[a-fA-F0-9]{64}", tx_hash):
        raise AttestationAdapterError(
            "attestation_invalid_tx_hash",
            "permanent",
            "tx hash missing or invalid",
            "submission_unknown",
        )

    attestation_id = result.get("attestation_id") or result.get("attestationId")
    if attestation_id is not None and not isinstance(attestation_id, str):
        raise AttestationAdapterError(
            "attestation_malformed_attestation_id",
            "permanent",
            "attestation_id must be string",
            "submission_unknown",
        )
    submission_id = result.get("submission_id") or result.get("submissionId")
    if submission_id is not None and not isinstance(submission_id, str):
        raise AttestationAdapterError(
            "attestation_submit_malformed_response",
            "permanent",
            "submission_id must be string",
            "submission_unknown",
        )
    return {"tx_hash": tx_hash, "attestation_id": attestation_id, "submission_id": submission_id}


def _validate_rpc_poll_result(doc: dict) -> dict:
    if not isinstance(doc, dict) or doc.get("jsonrpc") != "2.0":
        raise AttestationAdapterError(
            "attestation_poll_malformed_envelope",
            "permanent",
            "poll rpc envelope invalid",
            "submission_unknown",
        )
    if "error" in doc:
        raise AttestationAdapterError(
            "attestation_poll_rpc_error",
            "permanent",
            f"poll rpc error: {doc['error']}",
            "submission_unknown",
        )
    result = doc.get("result")
    if not isinstance(result, dict):
        raise AttestationAdapterError(
            "attestation_poll_malformed_result",
            "permanent",
            "poll rpc result invalid",
            "submission_unknown",
        )
    status = result.get("status")
    if status is not None and not isinstance(status, str):
        raise AttestationAdapterError(
            "attestation_poll_malformed_result",
            "permanent",
            "poll status must be string",
            "submission_unknown",
        )
    confirmation_id = result.get("confirmation_id")
    if confirmation_id is not None and not isinstance(confirmation_id, str):
        raise AttestationAdapterError(
            "attestation_poll_malformed_result",
            "permanent",
            "confirmation_id must be string",
            "submission_unknown",
        )
    if status in {"confirmed", "finalized"}:
        finality_status = "finalized" if status == "finalized" else "not_finalized"
        lifecycle_state = "confirmed_finalized" if status == "finalized" else "confirmed_not_finalized"
        return {
            "confirmation_status": "confirmed",
            "finality_status": finality_status,
            "lifecycle_state": lifecycle_state,
            "confirmation_id": confirmation_id,
            "confirmation_proof": {
                "proof_source": "thronos_rpc",
                "proof_kind": "status_attestation",
                "provider_status": status,
                "confirmation_id": confirmation_id,
            },
            "polling_supported": True,
        }
    if status in {"pending", "submitted"}:
        return {
            "confirmation_status": "still_pending",
            "finality_status": "not_finalized",
            "lifecycle_state": "submitted_not_finalized",
            "confirmation_id": None,
            "confirmation_proof": {
                "proof_source": "thronos_rpc",
                "proof_kind": "status_attestation",
                "provider_status": status,
            },
            "polling_supported": True,
        }
    if status in {"rejected", "dropped"}:
        return {
            "confirmation_status": "rejected_or_dropped",
            "finality_status": "rejected",
            "lifecycle_state": "submission_rejected",
            "confirmation_id": None,
            "confirmation_proof": {
                "proof_source": "thronos_rpc",
                "proof_kind": "status_attestation",
                "provider_status": status,
            },
            "polling_supported": True,
        }
    return {
        "confirmation_status": "unknown",
        "finality_status": "unknown",
        "lifecycle_state": "submission_unknown",
        "confirmation_id": None,
        "confirmation_proof": {
            "proof_source": "thronos_rpc",
            "proof_kind": "status_attestation",
            "provider_status": status,
        },
        "polling_supported": True,
    }
