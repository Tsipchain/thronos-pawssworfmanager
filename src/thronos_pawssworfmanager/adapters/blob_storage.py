"""Blob storage adapter contracts with dry-run and local filesystem implementations."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Protocol


class BlobStorageError(Exception):
    def __init__(self, code: str, failure_class: str, message: str):
        super().__init__(message)
        self.code = code
        self.failure_class = failure_class


class BlobStorageAdapter(Protocol):
    def put_blob(self, blob_id: str, data: bytes) -> str: ...

    def get_blob(self, blob_id: str) -> bytes: ...

    def delete_blob(self, blob_id: str) -> None: ...

    def capabilities(self) -> dict: ...


class InMemoryBlobStorage:
    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def put_blob(self, blob_id: str, data: bytes) -> str:
        if blob_id in self._store:
            if self._store[blob_id] == data:
                return "duplicate"
            self._store[blob_id] = data
            return "overwritten"
        self._store[blob_id] = data
        return "created"

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

    def put_blob(self, blob_id: str, data: bytes) -> str:
        if self.exec_enabled:
            raise RuntimeError("real_blob_write_disabled")
        if blob_id in self._simulated_objects and self._simulated_objects[blob_id] == data:
            return "duplicate"
        status = "created" if blob_id not in self._simulated_objects else "overwritten"
        self._simulated_objects[blob_id] = data
        return status

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

    _BLOB_ID = re.compile(r"^[A-Za-z0-9._-]+$")

    def __init__(self, root_path: str, exec_enabled: bool, max_blob_bytes: int | None = None) -> None:
        self.root = Path(root_path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.exec_enabled = exec_enabled
        self.max_blob_bytes = max_blob_bytes if max_blob_bytes is not None else int(os.getenv("MAX_BLOB_BYTES", "1048576"))

    def _path_for(self, blob_id: str) -> Path:
        if not self._BLOB_ID.match(blob_id):
            raise BlobStorageError("invalid_blob_id", "permanent", "blob id format invalid")
        candidate = (self.root / f"{blob_id}.blob").resolve()
        if candidate.parent != self.root:
            raise BlobStorageError("path_escape", "permanent", "blob path escapes root")
        return candidate

    def put_blob(self, blob_id: str, data: bytes) -> str:
        if not self.exec_enabled:
            raise BlobStorageError("execution_gate_closed", "permanent", "blob execution gate closed")
        if len(data) > self.max_blob_bytes:
            raise BlobStorageError("blob_too_large", "permanent", "blob exceeds max size")

        path = self._path_for(blob_id)
        if path.exists():
            existing = path.read_bytes()
            if existing == data:
                return "duplicate"
            status = "overwritten"
        else:
            status = "created"

        fd, temp_name = tempfile.mkstemp(prefix=".tmp_blob_", dir=str(self.root))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return status

    def get_blob(self, blob_id: str) -> bytes:
        path = self._path_for(blob_id)
        if not path.exists():
            raise BlobStorageError("blob_not_found", "permanent", "blob not found")
        return path.read_bytes()

    def delete_blob(self, blob_id: str) -> None:
        path = self._path_for(blob_id)
        if not path.exists():
            raise BlobStorageError("blob_not_found", "permanent", "blob not found")
        path.unlink()

    def capabilities(self) -> dict:
        return {
            "backend": "local_fs",
            "provider_family": "filesystem",
            "dry_run_supported": True,
            "exec_enabled": self.exec_enabled,
            "root_path_configured": str(self.root),
            "max_blob_bytes": self.max_blob_bytes,
            "atomic_write": True,
            "overwrite_semantics": "duplicate_or_overwritten",
        }
