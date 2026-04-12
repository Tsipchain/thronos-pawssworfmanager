"""Provider config schemas, secret source policy, redaction, and validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import AdapterConfig


@dataclass(frozen=True)
class SecretSourcePolicy:
    allowed_sources: tuple[str, ...]
    forbidden_plaintext_env_keys: tuple[str, ...]


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

    def to_redacted_dict(self) -> dict:
        return {
            "secret_source_policy": asdict(self.secret_source_policy),
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
        forbidden_plaintext_env_keys=(
            "BLOB_ACCESS_KEY",
            "BLOB_SECRET_KEY",
            "ATTESTATION_SIGNER_KEY",
        ),
    )

    for forbidden in policy.forbidden_plaintext_env_keys:
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
    boundary.validate_completeness()
    return boundary


def _redact_ref(value: str | None) -> str | None:
    if not value:
        return None
    return "<redacted:set>"
