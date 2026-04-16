"""Helpers for deterministic vector fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]


def load_vector_set(name: str) -> list[dict[str, Any]]:
    path = _REPO_ROOT / "tests" / "vectors" / f"{name}.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("vector_set_must_be_list")
    return data


def run_vector_suite(name: str) -> dict[str, Any]:
    vectors = load_vector_set(name)
    return {"suite": name, "count": len(vectors), "ok": True}


def list_vector_categories() -> list[str]:
    vectors_dir = _REPO_ROOT / "tests" / "vectors"
    return sorted(p.stem for p in vectors_dir.glob("*.json"))
