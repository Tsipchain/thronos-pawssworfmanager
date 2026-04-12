"""Identity adapter contracts and static implementation."""

from __future__ import annotations

from typing import Protocol


class IdentityAdapter(Protocol):
    def resolve_actor(self, request: dict) -> str: ...


class StaticIdentity:
    def resolve_actor(self, request: dict) -> str:
        return "anonymous"
