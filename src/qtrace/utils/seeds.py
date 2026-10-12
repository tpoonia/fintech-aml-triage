"""Deterministic, stream-separated, order-independent seed derivation (E04).

Every source of randomness belongs to exactly one *stream*. A per-unit seed is
derived from ``(master seed, stream, stable unit key)`` by hashing, so:

* the same inputs always give the same seed (determinism);
* different streams never share seeds even with equal master values;
* adding or removing units (e.g. model #41) never changes other units' seeds,
  because nothing depends on enumeration order.
"""

from __future__ import annotations

import hashlib
from collections.abc import Hashable

import numpy as np

STREAMS: frozenset[str] = frozenset(
    {"split", "model", "undersample", "noise", "shots", "policy", "bootstrap"}
)

KeyPart = str | int | bool


def _encode_part(part: KeyPart) -> bytes:
    # Type-tagged so that 1, "1" and True can never collide.
    if isinstance(part, bool):
        return b"b:" + (b"1" if part else b"0")
    if isinstance(part, int):
        return b"i:" + str(part).encode()
    if isinstance(part, str):
        return b"s:" + part.encode("utf-8")
    raise TypeError(f"seed key parts must be str, int or bool, got {type(part).__name__}")


def derive_seed(master: int, stream: str, *key: KeyPart) -> int:
    """Return a 64-bit seed for one unit of one stream."""
    if stream not in STREAMS:
        raise ValueError(f"unknown seed stream {stream!r}; allowed: {sorted(STREAMS)}")
    if not isinstance(master, int) or isinstance(master, bool) or master < 0:
        raise ValueError("master seed must be a non-negative int")
    parts = [_encode_part(master), _encode_part(stream), *(_encode_part(k) for k in key)]
    # Length-prefix each part so concatenation is unambiguous.
    payload = b"".join(len(p).to_bytes(4, "big") + p for p in parts)
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def make_rng(master: int, stream: str, *key: KeyPart) -> np.random.Generator:
    """NumPy generator seeded from :func:`derive_seed`."""
    return np.random.default_rng(np.random.SeedSequence(derive_seed(master, stream, *key)))


def derive_seeds(master: int, stream: str, keys: list[Hashable]) -> dict[Hashable, int]:
    """Seeds for many units at once; the result does not depend on ``keys`` order."""
    out: dict[Hashable, int] = {}
    for key in keys:
        parts = key if isinstance(key, tuple) else (key,)
        out[key] = derive_seed(master, stream, *parts)
    return out
