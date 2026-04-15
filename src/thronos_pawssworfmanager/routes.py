"""Route registration layout for runtime skeleton."""

from __future__ import annotations

import os

from .adapters.attestation import DryRunChainAttestationAdapter, FakeAttestationAdapter
from .adapters.blob_storage import DryRunBlobStorageProvider, InMemoryBlobStorage, LocalFileBlobStorage
from .adapters.config import backend_selection_policy, execution_policy_status, resolve_adapter_config
from .adapters.execution_gating import evaluate_execution_gates
from .adapters.identity import StaticIdentity
from .adapters.manifest_store import InMemoryManifestStore
from .adapters.provider_config import load_provider_config_boundary
from .api_versioning import DEFAULT_API_VERSION, SUPPORTED_API_VERSIONS
from .canonical_manifest import REQUIRED_TOP_LEVEL_FIELDS
from .contracts import error_contract, success_contract
from .error_model import (
    ERR_COMMAND_PIPELINE_FAILED,
    ERR_COMMAND_VALIDATION_FAILED,
    ERR_READINESS_FAILED,
    ERR_UNSUPPORTED_COMMAND,
)
from .hash_policy import hash_policy_id
from .internal_commands import command_schema_summary
from .runtime import RouteResponse, RuntimeShell
from .services.command_handler import handle_command, supported_commands
from .services.orchestrator import CommandOrchestrator
from .startup_validation import validate_data_paths

_ADAPTER_CONFIG = resolve_adapter_config(os.environ)
_SELECTION_POLICY = backend_selection_policy()
_EXECUTION_POLICY = execution_policy_status(_ADAPTER_CONFIG)
_PROVIDER_CONFIG = load_provider_config_boundary(os.environ, _ADAPTER_CONFIG)
_ENABLE_REAL_EXECUTION = os.getenv("ENABLE_REAL_EXECUTION", "false").lower() == "true"
_EXECUTION_GATES = evaluate_execution_gates(
    enable_real_execution=_ENABLE_REAL_EXECUTION,
    execution_mode=_ADAPTER_CONFIG.execution_mode,
    policy_allows=bool(_EXECUTION_POLICY.get("startup_allowed")),
    provider_config_complete=True,
    secrets_boundary_satisfied=True,
)
if _ENABLE_REAL_EXECUTION and not _EXECUTION_GATES.execution_enabled:
    raise ValueError(f"real_execution_gate_denied:{','.join(_EXECUTION_GATES.denial_reasons)}")
_MANIFEST_STORE = InMemoryManifestStore()
if _ADAPTER_CONFIG.blob_storage_backend == "in_memory":
    _BLOB_STORAGE = InMemoryBlobStorage()
elif _ADAPTER_CONFIG.blob_storage_backend == "local_fs":
    _local_root = _PROVIDER_CONFIG.blob.local_root_path
    if not _local_root:
        raise ValueError("blob_local_root_required")
    _BLOB_STORAGE = LocalFileBlobStorage(_local_root, exec_enabled=_EXECUTION_GATES.execution_enabled)
else:
    _BLOB_STORAGE = DryRunBlobStorageProvider(
        _ADAPTER_CONFIG.blob_storage_backend,
        exec_enabled=not _ADAPTER_CONFIG.dry_run_enabled,
    )
_ATTESTATION = (
    FakeAttestationAdapter()
    if _ADAPTER_CONFIG.attestation_backend == "fake"
    else DryRunChainAttestationAdapter(
        _ADAPTER_CONFIG.attestation_backend,
        network=_PROVIDER_CONFIG.attestation.target_network or _PROVIDER_CONFIG.attestation.chain_id or "unknown",
        exec_enabled=not _ADAPTER_CONFIG.dry_run_enabled,
        simulate_failure=os.getenv("SIMULATE_ATTESTATION_FAILURE", "0") == "1",
    )
)
_IDENTITY = StaticIdentity()
_ORCHESTRATOR = CommandOrchestrator(
    _MANIFEST_STORE,
    _ATTESTATION,
    blob_storage=_BLOB_STORAGE,
    manifest_backend=_ADAPTER_CONFIG.manifest_store_backend,
    blob_backend=_ADAPTER_CONFIG.blob_storage_backend,
    attestation_backend=_ADAPTER_CONFIG.attestation_backend,
    idempotency_scope=_ADAPTER_CONFIG.idempotency_scope,
    execution_enabled=_EXECUTION_GATES.execution_enabled,
)


def _capability_report() -> dict:
    return {
        "deterministic_core": {
            "enabled": True,
            "modules": [
                "canonical_manifest",
                "state_hash",
                "version_chain",
                "argon2id_policy",
            ],
        },
        "internal_command_layer": {
            "enabled": True,
            "execution_enabled": False,
            "supported_commands": supported_commands(),
        },
        "adapters": {
            "manifest_store": _ADAPTER_CONFIG.manifest_store_backend,
            "blob_storage": _ADAPTER_CONFIG.blob_storage_backend,
            "attestation": _ADAPTER_CONFIG.attestation_backend,
            "supported_attestation_backends": ["fake", "thronos_network", "rpc_generic"],
            "selected_attestation_backend": _ADAPTER_CONFIG.attestation_backend,
            "identity": _ADAPTER_CONFIG.identity_backend,
            "execution_mode": _ADAPTER_CONFIG.execution_mode,
            "dry_run_enabled": _ADAPTER_CONFIG.dry_run_enabled,
            "selection_policy": _SELECTION_POLICY.to_dict(),
            "execution_policy": _EXECUTION_POLICY,
            "idempotency_scope": _ADAPTER_CONFIG.idempotency_scope,
            "blob_capabilities": _BLOB_STORAGE.capabilities(),
            "attestation_capabilities": _ATTESTATION.capabilities(),
            "provider_config_boundary": _PROVIDER_CONFIG.to_redacted_dict(),
            "execution_gates": _EXECUTION_GATES.to_dict(),
            "execution_ready": _EXECUTION_GATES.execution_ready,
            "execution_enabled": _EXECUTION_GATES.execution_enabled,
            "attestation_execution_ready": _EXECUTION_GATES.execution_ready and _EXECUTION_POLICY["attestation_allowed"],
            "attestation_execution_enabled": _EXECUTION_GATES.execution_enabled and _EXECUTION_POLICY["attestation_allowed"],
        },
        "negotiation": {
            "server_supported_api_versions": list(SUPPORTED_API_VERSIONS),
            "selected_api_version": DEFAULT_API_VERSION,
        },
        "sensitive_features": {
            "auth_runtime": False,
            "blob_storage_runtime": False,
            "encryption_runtime": False,
            "blockchain_writes": False,
            "database_integration": False,
            "export_import_runtime": False,
            "vault_operations": False,
        },
    }


def _service_metadata() -> dict:
    return {
        "service": "thronos-pawssworfmanager",
        "phase": "m9-chain-agnostic-attestation-prep",
        "api_default_version": DEFAULT_API_VERSION,
        "api_supported_versions": list(SUPPORTED_API_VERSIONS),
        "execution_policy_enforced": _EXECUTION_POLICY["startup_allowed"],
        "secret_policy_enforced": True,
        "secret_backed_adapters": ["blob_storage", "attestation"],
        "execution_ready": _EXECUTION_GATES.execution_ready,
        "execution_enabled": _EXECUTION_GATES.execution_enabled,
        "attestation_execution_ready": _EXECUTION_GATES.execution_ready and _EXECUTION_POLICY["attestation_allowed"],
        "attestation_execution_enabled": _EXECUTION_GATES.execution_enabled and _EXECUTION_POLICY["attestation_allowed"],
    }


def register_runtime_routes(shell: RuntimeShell) -> None:
    shell.register(
        "GET",
        "/healthz",
        lambda _req: RouteResponse(200, success_contract({"status": "ok", **_service_metadata()})),
    )

    shell.register(
        "GET",
        "/readyz",
        lambda _req: _readiness_response(),
    )

    shell.register(
        "GET",
        "/v1/config",
        lambda _req: RouteResponse(
            200,
            success_contract(
                {
                    **_service_metadata(),
                    "env": os.getenv("SERVICE_ENV", "unknown"),
                    "port": os.getenv("SERVICE_PORT", "8080"),
                    "data_root": os.getenv("SERVICE_DATA_ROOT", ""),
                    "hash_policy": hash_policy_id(),
                    "manifest_required_fields": list(REQUIRED_TOP_LEVEL_FIELDS),
                    "routes": [f"{method} {path}" for method, path in shell.routes()],
                    "provider_config": _PROVIDER_CONFIG.to_redacted_dict(),
                    "execution_gates": _EXECUTION_GATES.to_dict(),
                }
            ),
        ),
    )

    shell.register(
        "GET",
        "/v1/capabilities",
        lambda _req: RouteResponse(200, success_contract(_capability_report())),
    )

    shell.register(
        "GET",
        "/v1/metadata",
        lambda _req: RouteResponse(200, success_contract(_service_metadata())),
    )

    shell.register(
        "GET",
        "/v1/contracts/internal",
        lambda _req: RouteResponse(200, success_contract(command_schema_summary())),
    )

    shell.register(
        "POST",
        "/v1/commands/execute",
        lambda req: _execute_command(req),
    )


def _execute_command(request: dict) -> RouteResponse:
    command = request.get("command")
    payload = request.get("payload")

    if not isinstance(command, str) or not command:
        return RouteResponse(422, error_contract(ERR_COMMAND_VALIDATION_FAILED, "missing command", 422))
    if command not in supported_commands():
        return RouteResponse(422, error_contract(ERR_UNSUPPORTED_COMMAND, f"unsupported command: {command}", 422))
    if not isinstance(payload, dict):
        return RouteResponse(422, error_contract(ERR_COMMAND_VALIDATION_FAILED, "payload must be object", 422))

    try:
        deterministic_result = handle_command(command, payload)
        orchestrated = _ORCHESTRATOR.execute(deterministic_result)
        orchestrated["actor_ref"] = _IDENTITY.resolve_actor(request)
    except ValueError as exc:
        return RouteResponse(422, error_contract(ERR_COMMAND_PIPELINE_FAILED, str(exc), 422))

    return RouteResponse(200, success_contract(orchestrated))


def _readiness_response() -> RouteResponse:
    result = validate_data_paths()
    if result.ok:
        return RouteResponse(
            200,
            success_contract(
                {
                    "ready": True,
                    "checks": ["env_paths_exist", "env_paths_are_directories"],
                    **_service_metadata(),
                }
            ),
        )
    return RouteResponse(503, error_contract(ERR_READINESS_FAILED, result.detail or result.code, 503))
