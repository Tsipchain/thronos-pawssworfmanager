"""Response schema helpers for normalized runtime contracts."""

from __future__ import annotations

import uuid
from typing import Any

from .api_versioning import DEFAULT_API_VERSION


def _request_id() -> str:
    return str(uuid.uuid4())


def success_contract(data: dict[str, Any], status: int = 200) -> dict[str, Any]:
    return {
        "api_version": DEFAULT_API_VERSION,
        "request_id": _request_id(),
        "status": "success",
        "code": "ok",
        "data": data,
        "error": None,
        "http_status": status,
    }


def error_contract(code: str, message: str, status: int) -> dict[str, Any]:
    return {
        "api_version": DEFAULT_API_VERSION,
        "request_id": _request_id(),
        "status": "error",
        "code": code,
        "data": None,
        "error": {
            "message": message,
            "retryable": status >= 500,
        },
        "http_status": status,
    }
