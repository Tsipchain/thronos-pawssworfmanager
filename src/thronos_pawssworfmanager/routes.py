"""Route registration layout for runtime skeleton."""

from __future__ import annotations

import os

from .api_versioning import DEFAULT_API_VERSION, SUPPORTED_API_VERSIONS
from .canonical_manifest import REQUIRED_TOP_LEVEL_FIELDS
from .contracts import error_contract, success_contract
from .error_model import ERR_READINESS_FAILED
from .hash_policy import hash_policy_id
from .runtime import RouteResponse, RuntimeShell
from .startup_validation import validate_data_paths


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
        "phase": "m3-service-contract",
        "api_default_version": DEFAULT_API_VERSION,
        "api_supported_versions": list(SUPPORTED_API_VERSIONS),
    }


def register_runtime_routes(shell: RuntimeShell) -> None:
    shell.register(
        "GET",
        "/healthz",
        lambda: RouteResponse(200, success_contract({"status": "ok", **_service_metadata()})),
    )

    shell.register(
        "GET",
        "/readyz",
        lambda: _readiness_response(),
    )

    shell.register(
        "GET",
        "/v1/config",
        lambda: RouteResponse(
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
                }
            ),
        ),
    )

    shell.register(
        "GET",
        "/v1/capabilities",
        lambda: RouteResponse(200, success_contract(_capability_report())),
    )

    shell.register(
        "GET",
        "/v1/metadata",
        lambda: RouteResponse(200, success_contract(_service_metadata())),
    )


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
