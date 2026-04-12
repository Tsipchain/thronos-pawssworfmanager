"""Blob storage adapter contracts with dry-run and local filesystem implementations."""

from __future__ import annotations

from pathlib import Path
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
    """Provider-shaped adapter for future cloud backends (simulated only)."""

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


class LocalFileBlobStorage:
    """First real blob adapter (filesystem-backed), strictly gate-controlled."""

    def __init__(self, root_path: str, exec_enabled: bool) -> None:
        self.root = Path(root_path)
        self.root.mkdir(parents=True, exist_ok=True)
        self.exec_enabled = exec_enabled

    def _path_for(self, blob_id: str) -> Path:
        return self.root / f"{blob_id}.blob"

    def put_blob(self, blob_id: str, data: bytes) -> None:
        if not self.exec_enabled:
            raise RuntimeError("blob_execution_gate_closed")
        self._path_for(blob_id).write_bytes(data)

    def get_blob(self, blob_id: str) -> bytes:
        return self._path_for(blob_id).read_bytes()

    def delete_blob(self, blob_id: str) -> None:
        path = self._path_for(blob_id)
        if path.exists():
            path.unlink()

    def capabilities(self) -> dict:
        return {
            "backend": "local_fs",
            "provider_family": "filesystem",
            "dry_run_supported": True,
            "exec_enabled": self.exec_enabled,
            "root_path_configured": str(self.root),
        }
