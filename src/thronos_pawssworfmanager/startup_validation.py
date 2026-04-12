"""Minimal startup validation for data-root/path existence."""

from __future__ import annotations

import os
from pathlib import Path

from .types import ValidationResult


_REQUIRED_PATH_ENV = (
    "SERVICE_DATA_ROOT",
    "PATH_BLOBS",
    "PATH_MANIFESTS",
    "PATH_TOMBSTONES",
    "PATH_EXPORTS",
    "PATH_IMPORTS",
    "PATH_LOGS",
    "PATH_AUDIT",
)


def validate_data_paths() -> ValidationResult:
    for name in _REQUIRED_PATH_ENV:
        value = os.getenv(name)
        if not value:
            return ValidationResult(False, "missing_env", f"missing env: {name}")
        path = Path(value)
        if not path.exists():
            return ValidationResult(False, "missing_path", f"path not found: {value}")
    return ValidationResult(True)
