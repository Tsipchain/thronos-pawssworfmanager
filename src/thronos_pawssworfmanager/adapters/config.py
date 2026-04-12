"""Adapter configuration contracts and backend selection rules."""

from __future__ import annotations

from dataclasses import asdict, dataclass


_ALLOWED_MANIFEST_STORE = {"in_memory"}
_ALLOWED_BLOB_STORAGE = {"in_memory", "s3", "gcs", "azure_blob"}
_ALLOWED_ATTESTATION = {"fake", "thronos_chain"}
_ALLOWED_IDENTITY = {"static"}
_ALLOWED_EXECUTION_MODES = {"dry_run", "execute"}


@dataclass(frozen=True)
class BackendSelectionPolicy:
    mode: str
    fail_closed: bool
    allowed_manifest_store_backends: tuple[str, ...]
    allowed_blob_storage_backends: tuple[str, ...]
    allowed_attestation_backends: tuple[str, ...]
    allowed_identity_backends: tuple[str, ...]
    allowed_execution_modes: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AdapterConfig:
    manifest_store_backend: str
    blob_storage_backend: str
    attestation_backend: str
    identity_backend: str
    execution_mode: str
    idempotency_scope: str = "single_instance_memory"

    @property
    def dry_run_enabled(self) -> bool:
        return self.execution_mode == "dry_run"


_POLICY = BackendSelectionPolicy(
    mode="allowlist",
    fail_closed=True,
    allowed_manifest_store_backends=tuple(sorted(_ALLOWED_MANIFEST_STORE)),
    allowed_blob_storage_backends=tuple(sorted(_ALLOWED_BLOB_STORAGE)),
    allowed_attestation_backends=tuple(sorted(_ALLOWED_ATTESTATION)),
    allowed_identity_backends=tuple(sorted(_ALLOWED_IDENTITY)),
    allowed_execution_modes=tuple(sorted(_ALLOWED_EXECUTION_MODES)),
)


def backend_selection_policy() -> BackendSelectionPolicy:
    return _POLICY


def resolve_adapter_config(env: dict[str, str]) -> AdapterConfig:
    manifest_store = env.get("MANIFEST_STORE_BACKEND", "in_memory")
    blob_storage = env.get("BLOB_STORAGE_BACKEND", "in_memory")
    attestation = env.get("ATTESTATION_BACKEND", "fake")
    identity = env.get("IDENTITY_BACKEND", "static")
    execution_mode = env.get("ADAPTER_EXECUTION_MODE", "dry_run")

    if manifest_store not in _ALLOWED_MANIFEST_STORE:
        raise ValueError("unsupported_manifest_store_backend")
    if blob_storage not in _ALLOWED_BLOB_STORAGE:
        raise ValueError("unsupported_blob_storage_backend")
    if attestation not in _ALLOWED_ATTESTATION:
        raise ValueError("unsupported_attestation_backend")
    if identity not in _ALLOWED_IDENTITY:
        raise ValueError("unsupported_identity_backend")
    if execution_mode not in _ALLOWED_EXECUTION_MODES:
        raise ValueError("unsupported_adapter_execution_mode")

    # M5 hard stop: execute mode is blocked for real providers.
    if execution_mode == "execute" and (blob_storage != "in_memory" or attestation != "fake"):
        raise ValueError("real_execution_mode_not_allowed")

    return AdapterConfig(
        manifest_store_backend=manifest_store,
        blob_storage_backend=blob_storage,
        attestation_backend=attestation,
        identity_backend=identity,
        execution_mode=execution_mode,
    )
