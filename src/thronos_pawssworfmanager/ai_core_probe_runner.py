"""Active probe runner for upstream AI Core submit diagnostics."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Optional
from urllib import error, request

from .ai_core_probe import SubmitProbeClassification, classify_submit_probe


@dataclass(frozen=True)
class ProbeObservation:
    method: str
    status: int
    body: str
    classification: SubmitProbeClassification


@dataclass(frozen=True)
class UpstreamDiagnostics:
    submit_url: str
    get_probe: ProbeObservation
    post_probe: ProbeObservation
    attestor_pubkey_input: Optional[str]
    attestor_pubkey_lowercase: Optional[str]
    registry_presence: str
    summary: str


def run_upstream_diagnostics(submit_url: str, attestor_pubkey: Optional[str] = None) -> UpstreamDiagnostics:
    get_probe = _probe(submit_url, "GET")
    post_probe = _probe(submit_url, "POST", "{}")

    normalized = attestor_pubkey.lower() if attestor_pubkey else None

    registry_presence = "unknown_requires_upstream_registry_access"
    summary = _build_summary(get_probe.classification.classification, post_probe.classification.classification)

    return UpstreamDiagnostics(
        submit_url=submit_url,
        get_probe=get_probe,
        post_probe=post_probe,
        attestor_pubkey_input=attestor_pubkey,
        attestor_pubkey_lowercase=normalized,
        registry_presence=registry_presence,
        summary=summary,
    )


def diagnostics_to_json(diagnostics: UpstreamDiagnostics) -> str:
    return json.dumps(asdict(diagnostics), indent=2, sort_keys=True)


def _probe(url: str, method: str, body: Optional[str] = None) -> ProbeObservation:
    payload = body.encode("utf-8") if body is not None else None
    req = request.Request(
        url,
        data=payload,
        method=method,
        headers={"content-type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            status = int(resp.status)
            raw = resp.read()
    except error.HTTPError as err:
        status = int(err.code)
        raw = err.read()
    except error.URLError as err:
        status = 0
        raw = str(err).encode("utf-8")

    body_text = raw.decode("utf-8", errors="replace")
    classification = classify_submit_probe(status, body_text)
    return ProbeObservation(method=method, status=status, body=body_text, classification=classification)


def _build_summary(get_classification: str, post_classification: str) -> str:
    if get_classification in {"upstream_service_suspended", "upstream_unavailable"}:
        return "upstream_availability_incident"
    if post_classification == "edge_method_forbidden":
        return "upstream_gateway_method_policy_or_route_mapping"
    if post_classification in {"registry_unregistered_service", "registry_missing_scope"}:
        return "registry_prerequisite_not_met"
    if post_classification == "attestation_submitted":
        return "submit_path_healthy"
    return "needs_manual_upstream_triage"
