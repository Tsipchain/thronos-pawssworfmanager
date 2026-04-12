"""Blob storage adapter contracts with dry-run-capable provider stubs."""

from __future__ import annotations

from typing import Protocol


class BlobStorageAdapter(Protocol):
    def put_blob(self, blob_id: str, data: bytes) -> None: ...

    def get_blob(self, blob_id: str) -> bytes: ...

    def delete_blob(self, blob_id: str) -> None: ...

    def capabilities(self) -> dict: ...


class InMemoryBlobStorage:
    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def put_blob(self, blob_id: str, data: bytes) -> None:
        self._store[blob_id] = data

    def get_blob(self, blob_id: str) -> bytes:
        return self._store[blob_id]

    def delete_blob(self, blob_id: str) -> None:
        del self._store[blob_id]

    def capabilities(self) -> dict:
        return {
            "backend": "in_memory",
            "provider_family": "memory",
            "dry_run_supported": True,
            "exec_enabled": False,
        }


class DryRunBlobStorageProvider:
    """Provider-shaped adapter for future real backends.

    This class intentionally never performs real writes. It only simulates
    provider call paths and errors for integration dry-runs.
    """

    def __init__(self, backend: str, exec_enabled: bool = False) -> None:
        self.backend = backend
        self.exec_enabled = exec_enabled
        self._simulated_objects: dict[str, bytes] = {}

    def put_blob(self, blob_id: str, data: bytes) -> None:
        if self.exec_enabled:
            raise RuntimeError("real_blob_write_disabled")
        self._simulated_objects[blob_id] = data

    def get_blob(self, blob_id: str) -> bytes:
        return self._simulated_objects[blob_id]

    def delete_blob(self, blob_id: str) -> None:
        self._simulated_objects.pop(blob_id, None)

    def capabilities(self) -> dict:
        return {
            "backend": self.backend,
            "provider_family": "object_storage",
            "dry_run_supported": True,
            "exec_enabled": self.exec_enabled,
        }
