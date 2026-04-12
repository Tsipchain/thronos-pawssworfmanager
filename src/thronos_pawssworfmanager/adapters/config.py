"""Adapter configuration contracts and backend selection rules."""

from __future__ import annotations

from dataclasses import asdict, dataclass


_ALLOWED_MANIFEST_STORE = {"in_memory"}
_ALLOWED_ATTESTATION = {"fake"}
_ALLOWED_IDENTITY = {"static"}


@dataclass(frozen=True)
class BackendSelectionPolicy:
    mode: str
    fail_closed: bool
    allowed_manifest_store_backends: tuple[str, ...]
    allowed_attestation_backends: tuple[str, ...]
    allowed_identity_backends: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AdapterConfig:
    manifest_store_backend: str
    attestation_backend: str
    identity_backend: str
    idempotency_scope: str = "single_instance_memory"


_POLICY = BackendSelectionPolicy(
    mode="allowlist",
    fail_closed=True,
    allowed_manifest_store_backends=tuple(sorted(_ALLOWED_MANIFEST_STORE)),
    allowed_attestation_backends=tuple(sorted(_ALLOWED_ATTESTATION)),
    allowed_identity_backends=tuple(sorted(_ALLOWED_IDENTITY)),
)


def backend_selection_policy() -> BackendSelectionPolicy:
    return _POLICY


def resolve_adapter_config(env: dict[str, str]) -> AdapterConfig:
    manifest_store = env.get("MANIFEST_STORE_BACKEND", "in_memory")
    attestation = env.get("ATTESTATION_BACKEND", "fake")
    identity = env.get("IDENTITY_BACKEND", "static")

    if manifest_store not in _ALLOWED_MANIFEST_STORE:
        raise ValueError("unsupported_manifest_store_backend")
    if attestation not in _ALLOWED_ATTESTATION:
        raise ValueError("unsupported_attestation_backend")
    if identity not in _ALLOWED_IDENTITY:
        raise ValueError("unsupported_identity_backend")

    return AdapterConfig(
        manifest_store_backend=manifest_store,
        attestation_backend=attestation,
        identity_backend=identity,
    )
