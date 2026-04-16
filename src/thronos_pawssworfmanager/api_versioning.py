"""API versioning rules for runtime shell contracts."""

SUPPORTED_API_VERSIONS = ("v1",)
DEFAULT_API_VERSION = "v1"
API_PREFIX = "/v1"


def is_supported_version(version: str) -> bool:
    return version in SUPPORTED_API_VERSIONS


def is_versioned_api_path(path: str) -> bool:
    return path.startswith("/v")


def extract_version(path: str) -> str | None:
    if not is_versioned_api_path(path):
        return None
    parts = path.split("/")
    if len(parts) < 2:
        return None
    return parts[1]
