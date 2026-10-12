from __future__ import annotations

import numpy as np
import pytest

from qtrace.config.schemas import SeedConfig
from qtrace.utils.seeds import STREAMS, derive_seed, derive_seeds, make_rng


def test_deterministic():
    assert derive_seed(2307, "model", "ra-r1", 3) == derive_seed(2307, "model", "ra-r1", 3)


def test_streams_are_separated():
    seeds = {derive_seed(1, stream, "unit", 0) for stream in STREAMS}
    assert len(seeds) == len(STREAMS)


def test_keys_and_masters_change_seed():
    base = derive_seed(9011, "shots", "ctx", 0)
    assert derive_seed(9011, "shots", "ctx", 1) != base
    assert derive_seed(9012, "shots", "ctx", 0) != base


def test_type_tagging_prevents_collisions():
    assert derive_seed(1, "model", 1) != derive_seed(1, "model", "1")
    assert derive_seed(1, "model", True) != derive_seed(1, "model", 1)
    # Length-prefixing: ("ab", "c") must differ from ("a", "bc").
    assert derive_seed(1, "model", "ab", "c") != derive_seed(1, "model", "a", "bc")


def test_order_independent_derivation():
    keys = [("ra-r1", i) for i in range(10)]
    forward = derive_seeds(2307, "model", keys)
    backward = derive_seeds(2307, "model", list(reversed(keys)))
    assert forward == backward
    # Adding a unit (A06: larger pools) must not change existing seeds.
    extended = derive_seeds(2307, "model", [*keys, ("ra-r1", 10)])
    assert all(extended[k] == forward[k] for k in keys)


def test_make_rng_reproducible():
    a = make_rng(1701, "split", "ulb_v1").random(5)
    b = make_rng(1701, "split", "ulb_v1").random(5)
    np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize("bad", [-1, True])
def test_invalid_master(bad):
    with pytest.raises(ValueError):
        derive_seed(bad, "model", "x")


def test_unknown_stream_rejected():
    with pytest.raises(ValueError, match="unknown seed stream"):
        derive_seed(1, "global", "x")


def test_seed_config_matches_streams():
    assert set(SeedConfig.model_fields) == set(STREAMS)
