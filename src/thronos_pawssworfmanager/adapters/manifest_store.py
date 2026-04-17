"""Manifest persistence adapter contracts and in-memory implementation."""

from __future__ import annotations

from typing import Protocol


class ManifestStoreAdapter(Protocol):
    def put_manifest(self, manifest_hash: str, manifest: dict) -> None: ...

    def put_manifest_if_absent(self, manifest_hash: str, manifest: dict) -> bool: ...

    def get_manifest(self, manifest_hash: str) -> dict: ...


class InMemoryManifestStore:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def put_manifest(self, manifest_hash: str, manifest: dict) -> None:
        self._store[manifest_hash] = manifest

    def put_manifest_if_absent(self, manifest_hash: str, manifest: dict) -> bool:
        if manifest_hash in self._store:
            return False
        self._store[manifest_hash] = manifest
        return True

    def get_manifest(self, manifest_hash: str) -> dict:
        return self._store[manifest_hash]
