"""Application scaffold.

This intentionally provides only a health response and no vault logic.
"""

from .startup_validation import validate_data_paths


def create_app(validate_paths: bool = False) -> dict:
    """Return minimal application metadata for bootstrapping tests/integration."""
    path_validation = validate_data_paths() if validate_paths else None
    return {
        "service": "thronos-pawssworfmanager",
        "phase": "phase1-deterministic-core",
        "capabilities": [
            "canonical-manifest",
            "state-hash",
            "version-chain",
            "argon2id-policy",
        ],
        "path_validation": {
            "checked": bool(validate_paths),
            "ok": None if path_validation is None else path_validation.ok,
            "code": None if path_validation is None else path_validation.code,
        },
    }


if __name__ == "__main__":
    print(create_app())
