"""Blob storage adapter contracts and in-memory implementation."""

from __future__ import annotations

from typing import Protocol


class BlobStorageAdapter(Protocol):
    def put_blob(self, blob_id: str, data: bytes) -> None: ...

    def get_blob(self, blob_id: str) -> bytes: ...

    def delete_blob(self, blob_id: str) -> None: ...


class InMemoryBlobStorage:
    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def put_blob(self, blob_id: str, data: bytes) -> None:
        self._store[blob_id] = data

    def get_blob(self, blob_id: str) -> bytes:
        return self._store[blob_id]

    def delete_blob(self, blob_id: str) -> None:
        del self._store[blob_id]
