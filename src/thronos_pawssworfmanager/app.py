"""Application scaffold and runtime shell wiring."""

from __future__ import annotations

from .routes import register_runtime_routes
from .runtime import RuntimeShell
from .startup_validation import validate_data_paths


def create_runtime_shell() -> RuntimeShell:
    shell = RuntimeShell()
    register_runtime_routes(shell)
    return shell


def create_app(validate_paths: bool = False) -> dict:
    """Return minimal application metadata for bootstrapping tests/integration."""
    path_validation = validate_data_paths() if validate_paths else None
    shell = create_runtime_shell()

    return {
        "service": "thronos-pawssworfmanager",
        "phase": "m4-internal-command-contract",
        "capabilities": [
            "canonical-manifest",
            "state-hash",
            "version-chain",
            "argon2id-policy",
            "runtime-shell",
            "service-contract-layer",
            "internal-command-contract-layer",
            "deterministic-command-pipeline",
        ],
        "disabled_sensitive_features": [
            "auth-runtime",
            "blob-storage-runtime",
            "encryption-runtime",
            "blockchain-writes",
            "database-integration",
            "export-import-runtime",
            "vault-operations",
            "vault-command-execution-side-effects",
        ],
        "routes": [f"{method} {path}" for method, path in shell.routes()],
        "path_validation": {
            "checked": bool(validate_paths),
            "ok": None if path_validation is None else path_validation.ok,
            "code": None if path_validation is None else path_validation.code,
        },
    }


if __name__ == "__main__":
    print(create_app())
