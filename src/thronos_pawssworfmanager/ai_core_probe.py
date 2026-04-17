"""Operational classification helpers for AI Core submit probes."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class SubmitProbeClassification:
    classification: str
    detail: str
    recommended_action: str


def classify_submit_probe(status: int, response_text: str) -> SubmitProbeClassification:
    """Classify an AI Core submit probe response into an operational bucket."""
    lowered = (response_text or "").strip().lower()

    if status == 503 and "service suspended" in lowered:
        return SubmitProbeClassification(
            classification="upstream_service_suspended",
            detail="AI Core endpoint is reachable but currently suspended upstream.",
            recommended_action="Treat as upstream availability incident and escalate to AI Core ops.",
        )

    if status == 503:
        return SubmitProbeClassification(
            classification="upstream_unavailable",
            detail="AI Core endpoint returned HTTP 503.",
            recommended_action="Treat as upstream availability incident and retry after provider recovery.",
        )

    if status == 403 and "method forbidden" in lowered:
        return SubmitProbeClassification(
            classification="edge_method_forbidden",
            detail="Route is reachable but edge currently forbids this method.",
            recommended_action="Confirm route mapping and HTTP method policy in upstream gateway.",
        )

    if "unregistered_service" in lowered:
        return SubmitProbeClassification(
            classification="registry_unregistered_service",
            detail="Attestor pubkey identity is not registered upstream.",
            recommended_action="Run AI_SERVICE_REGISTER for the exact attestor pubkey.",
        )

    if "missing_scope" in lowered or "ai:attest" in lowered:
        return SubmitProbeClassification(
            classification="registry_missing_scope",
            detail="Attestor identity exists but required ai:attest scope is missing.",
            recommended_action="Assign ai:attest scope to the registered attestor identity.",
        )

    parsed = _parse_json(response_text)
    if status in {200, 201, 202} and isinstance(parsed, dict) and _has_receipt_shape(parsed):
        return SubmitProbeClassification(
            classification="attestation_submitted",
            detail="Response shape indicates attestation was accepted.",
            recommended_action="Continue with receipt reconciliation/finality polling.",
        )

    return SubmitProbeClassification(
        classification="unknown",
        detail="Response does not match known AI Core submit gate outcomes.",
        recommended_action="Capture response and verify upstream contract before local code changes.",
    )


def _parse_json(response_text: str):
    try:
        return json.loads(response_text)
    except (TypeError, json.JSONDecodeError):
        return None


def _has_receipt_shape(payload: dict) -> bool:
    tx_hash = payload.get("tx_hash")
    return isinstance(tx_hash, str) and tx_hash.startswith("0x") and len(tx_hash) == 66
