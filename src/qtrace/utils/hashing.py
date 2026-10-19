"""Canonical hashing for configs, artifacts and files.

Hashes identify *what* was run. They must be stable across machines and
Python sessions, so everything is serialized to canonical JSON first.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def canonical_json(obj: Any) -> str:
    """Serialize ``obj`` deterministically: sorted keys, no whitespace, no NaN/inf."""
    if isinstance(obj, BaseModel):
        obj = obj.model_dump(mode="json")
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def stable_hash(obj: Any) -> str:
    """SHA-256 of the canonical JSON form of ``obj`` (a dict, list or pydantic model)."""
    return sha256_hex(canonical_json(obj))


def file_sha256(path: str | Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()
