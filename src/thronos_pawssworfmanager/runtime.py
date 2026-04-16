"""Runtime skeleton without sensitive feature behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .api_versioning import DEFAULT_API_VERSION, extract_version, is_supported_version, is_versioned_api_path
from .contracts import error_contract
from .error_model import ERR_INVALID_API_VERSION, ERR_ROUTE_NOT_FOUND


@dataclass(frozen=True)
class RouteResponse:
    status: int
    body: dict


Handler = Callable[[dict], RouteResponse]


class RuntimeShell:
    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], Handler] = {}

    def register(self, method: str, path: str, handler: Handler) -> None:
        self._routes[(method.upper(), path)] = handler

    def routes(self) -> list[tuple[str, str]]:
        return sorted(self._routes.keys())

    def handle(self, method: str, path: str, request: dict | None = None) -> RouteResponse:
        request = request or {}
        if is_versioned_api_path(path):
            version = extract_version(path)
            if version is not None and not is_supported_version(version):
                return RouteResponse(
                    400,
                    error_contract(
                        ERR_INVALID_API_VERSION,
                        f"unsupported api version '{version}', supported: {DEFAULT_API_VERSION}",
                        400,
                    ),
                )

        key = (method.upper(), path)
        handler = self._routes.get(key)
        if handler is None:
            return RouteResponse(404, error_contract(ERR_ROUTE_NOT_FOUND, f"route not found: {path}", 404))
        return handler(request)
