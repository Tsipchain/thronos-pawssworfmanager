"""Adapter configuration contracts, execution policy matrix, and startup refusal rules."""

from __future__ import annotations

from dataclasses import asdict, dataclass


_ALLOWED_MANIFEST_STORE = {"in_memory"}
_ALLOWED_BLOB_STORAGE = {"in_memory", "local_fs", "s3", "gcs", "azure_blob"}
_ALLOWED_ATTESTATION = {"fake", "thronos_network", "rpc_generic"}
_ALLOWED_IDENTITY = {"static"}
_ALLOWED_EXECUTION_MODES = {"dry_run", "execute"}
_CLOUD_LIKE_BLOB = {"s3", "gcs", "azure_blob"}


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


def _policy_matrix() -> dict[str, dict[str, bool]]:
    return {
        "blob_storage": {
            "in_memory+dry_run": True,
            "in_memory+execute": True,
            "local_fs+dry_run": True,
            "local_fs+execute": True,
            "cloud_like+dry_run": True,
            "cloud_like+execute": False,
        },
        "attestation": {
            "fake+dry_run": True,
            "fake+execute": True,
            "thronos_network+dry_run": True,
            "thronos_network+execute": True,
            "rpc_generic+dry_run": True,
            "rpc_generic+execute": True,
        },
    }


def _blob_policy_allowed(blob_backend: str, execution_mode: str) -> bool:
    if blob_backend == "in_memory":
        return execution_mode in {"dry_run", "execute"}
    if blob_backend == "local_fs":
        return execution_mode in {"dry_run", "execute"}
    if blob_backend in _CLOUD_LIKE_BLOB:
        return execution_mode == "dry_run"
    return False


def _attestation_policy_allowed(attestation_backend: str, execution_mode: str) -> bool:
    if attestation_backend == "fake":
        return execution_mode in {"dry_run", "execute"}
    if attestation_backend == "thronos_network":
        return execution_mode in {"dry_run", "execute"}
    if attestation_backend == "rpc_generic":
        return execution_mode in {"dry_run", "execute"}
    return False


def execution_policy_status(config: AdapterConfig) -> dict:
    blob_allowed = _blob_policy_allowed(config.blob_storage_backend, config.execution_mode)
    att_allowed = _attestation_policy_allowed(config.attestation_backend, config.execution_mode)
    return {
        "matrix": _policy_matrix(),
        "blob_pair": f"{config.blob_storage_backend}+{config.execution_mode}",
        "blob_allowed": blob_allowed,
        "attestation_pair": f"{config.attestation_backend}+{config.execution_mode}",
        "attestation_allowed": att_allowed,
        "startup_allowed": blob_allowed and att_allowed,
        "enforcement": "fail_closed",
    }


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

    config = AdapterConfig(
        manifest_store_backend=manifest_store,
        blob_storage_backend=blob_storage,
        attestation_backend=attestation,
        identity_backend=identity,
        execution_mode=execution_mode,
    )

    status = execution_policy_status(config)
    if not status["startup_allowed"]:
        raise ValueError("forbidden_backend_execution_combination")

    return config
