"""Provider config schemas, field classification, redaction matrix, and validation."""

from __future__ import annotations

from dataclasses import dataclass

from .config import AdapterConfig


_FORBIDDEN_RAW_SECRET_ENV_KEYS = (
    "BLOB_ACCESS_KEY",
    "BLOB_SECRET_KEY",
    "ATTESTATION_SIGNER_KEY",
)

_BLOB_CLASSIFICATION = {
    "provider": "public",
    "bucket": "public",
    "region": "public",
    "endpoint_url": "public",
    "access_key_ref": "sensitive_ref",
    "secret_key_ref": "sensitive_ref",
    "access_key_raw": "forbidden_raw",
    "secret_key_raw": "forbidden_raw",
}

_ATTESTATION_CLASSIFICATION = {
    "rpc_url": "public",
    "chain_id": "public",
    "contract_address": "public",
    "signer_key_ref": "sensitive_ref",
    "signer_key_raw": "forbidden_raw",
}

_REDACTION_MATRIX = {
    "public": "report_as_is",
    "sensitive_ref": "report_redacted_if_set",
    "forbidden_raw": "never_report_and_refuse_startup_if_set",
}


@dataclass(frozen=True)
class SecretSourcePolicy:
    allowed_sources: tuple[str, ...]
    forbidden_raw_inputs: bool


@dataclass(frozen=True)
class BlobProviderConfig:
    backend: str
    provider: str | None
    bucket: str | None
    region: str | None
    endpoint_url: str | None
    access_key_ref: str | None
    secret_key_ref: str | None


@dataclass(frozen=True)
class AttestationProviderConfig:
    backend: str
    rpc_url: str | None
    chain_id: str | None
    contract_address: str | None
    signer_key_ref: str | None


@dataclass(frozen=True)
class ProviderConfigBoundary:
    secret_source_policy: SecretSourcePolicy
    blob: BlobProviderConfig
    attestation: AttestationProviderConfig
    required_for_future_execute: dict[str, tuple[str, ...]]

    def validate_completeness(self) -> None:
        # Required when real-like backends are selected even in dry-run, to verify shape.
        if self.blob.backend != "in_memory":
            missing = [f for f in ("provider", "bucket", "region") if not getattr(self.blob, f)]
            if missing:
                raise ValueError(f"incomplete_blob_provider_config:{','.join(missing)}")
        if self.attestation.backend != "fake":
            missing = [f for f in ("rpc_url", "chain_id") if not getattr(self.attestation, f)]
            if missing:
                raise ValueError(f"incomplete_attestation_provider_config:{','.join(missing)}")

    def validate_consistency(self) -> None:
        blob_any = any(
            [
                self.blob.provider,
                self.blob.bucket,
                self.blob.region,
                self.blob.endpoint_url,
                self.blob.access_key_ref,
                self.blob.secret_key_ref,
            ]
        )
        if self.blob.backend == "in_memory" and blob_any:
            raise ValueError("contradictory_blob_config_for_in_memory")

        att_any = any(
            [
                self.attestation.rpc_url,
                self.attestation.chain_id,
                self.attestation.contract_address,
                self.attestation.signer_key_ref,
            ]
        )
        if self.attestation.backend == "fake" and att_any:
            raise ValueError("contradictory_attestation_config_for_fake")

        if (self.blob.access_key_ref is None) != (self.blob.secret_key_ref is None):
            raise ValueError("incomplete_blob_secret_ref_pair")

        if (self.attestation.contract_address is None) != (self.attestation.signer_key_ref is None):
            raise ValueError("incomplete_attestation_signer_pair")

    def to_redacted_dict(self) -> dict:
        return {
            "secret_source_policy": {
                "allowed_sources": self.secret_source_policy.allowed_sources,
                "forbidden_raw_inputs": self.secret_source_policy.forbidden_raw_inputs,
            },
            "field_classification": {
                "blob": dict(_BLOB_CLASSIFICATION),
                "attestation": dict(_ATTESTATION_CLASSIFICATION),
            },
            "redaction_matrix": dict(_REDACTION_MATRIX),
            "required_for_future_execute": self.required_for_future_execute,
            "blob": {
                "backend": self.blob.backend,
                "provider": self.blob.provider,
                "bucket": self.blob.bucket,
                "region": self.blob.region,
                "endpoint_url": self.blob.endpoint_url,
                "access_key_ref": _redact_ref(self.blob.access_key_ref),
                "secret_key_ref": _redact_ref(self.blob.secret_key_ref),
            },
            "attestation": {
                "backend": self.attestation.backend,
                "rpc_url": self.attestation.rpc_url,
                "chain_id": self.attestation.chain_id,
                "contract_address": self.attestation.contract_address,
                "signer_key_ref": _redact_ref(self.attestation.signer_key_ref),
            },
        }


def load_provider_config_boundary(env: dict[str, str], config: AdapterConfig) -> ProviderConfigBoundary:
    policy = SecretSourcePolicy(
        allowed_sources=("env_ref",),
        forbidden_raw_inputs=True,
    )

    for forbidden in _FORBIDDEN_RAW_SECRET_ENV_KEYS:
        if env.get(forbidden):
            raise ValueError(f"forbidden_plaintext_secret:{forbidden}")

    blob = BlobProviderConfig(
        backend=config.blob_storage_backend,
        provider=env.get("BLOB_PROVIDER"),
        bucket=env.get("BLOB_BUCKET"),
        region=env.get("BLOB_REGION"),
        endpoint_url=env.get("BLOB_ENDPOINT_URL"),
        access_key_ref=env.get("BLOB_ACCESS_KEY_REF"),
        secret_key_ref=env.get("BLOB_SECRET_KEY_REF"),
    )

    attestation = AttestationProviderConfig(
        backend=config.attestation_backend,
        rpc_url=env.get("ATTESTATION_RPC_URL"),
        chain_id=env.get("ATTESTATION_CHAIN_ID"),
        contract_address=env.get("ATTESTATION_CONTRACT_ADDRESS"),
        signer_key_ref=env.get("ATTESTATION_SIGNER_KEY_REF"),
    )

    boundary = ProviderConfigBoundary(
        secret_source_policy=policy,
        blob=blob,
        attestation=attestation,
        required_for_future_execute={
            "blob": ("provider", "bucket", "region", "access_key_ref", "secret_key_ref"),
            "attestation": ("rpc_url", "chain_id", "contract_address", "signer_key_ref"),
        },
    )
    boundary.validate_consistency()
    boundary.validate_completeness()
    return boundary


def _redact_ref(value: str | None) -> str | None:
    if not value:
        return None
    return "<redacted:set>"
