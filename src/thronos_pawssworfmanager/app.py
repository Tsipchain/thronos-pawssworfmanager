"""Application scaffold.

This intentionally provides only a health response and no vault logic.
"""


def create_app() -> dict:
    """Return minimal application metadata for bootstrapping tests/integration."""
    return {
        "service": "thronos-pawssworfmanager",
        "phase": "greenfield-security-first-scaffold",
        "capabilities": [
            "encrypted-blob-offchain-storage (draft)",
            "thronos-attestation (draft)",
        ],
    }


if __name__ == "__main__":
    print(create_app())
