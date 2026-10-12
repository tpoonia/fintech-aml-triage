"""Phase 5A pre-registration: the pool study config is complete and internally consistent."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from qtrace.config import load_component, load_experiment
from qtrace.config.schemas import PoolEncodingConfig, PoolStudyConfig
from qtrace.data.access import PartitionAccessError, check_access


@pytest.fixture(scope="module")
def study():
    return load_component("pool_study", "p5a_v1")


def test_registered_grid(study):
    assert len(study.structures) == 16 and study.seeds_per_structure == 4
    main = [s for s in study.structures if s.encoding == "e3" and s.readout == "parity"]
    assert len(main) == 12
    assert {s.features for s in main} == {"top4", "next4", "pca4"}
    assert {s.ansatz for s in main} == {"ra1", "ra2", "esu1", "esu2"}
    assert {s.readout for s in study.structures} == {"parity", "mean_z"}
    assert {s.encoding for s in study.structures} == {"e3", "e2", "s5"}
    assert all(e.half_width < math.pi / 2 for e in study.encodings)
    assert "ra0" not in {s.ansatz for s in study.structures}  # shallow ansatz is a control only


def test_protocol_matches_p3a_r(study):
    assert study.optimizer.max_evaluations == 1000 and study.restarts == 3
    assert study.subset_legit_per_fraud == 4
    p3b = load_component("noise_study", "p3b_v1")
    assert study.anchor == next(m for m in p3b.models if m.model_id == "p3a_r")
    assert {c.control_id for c in study.controls} == {"ctrl-p3a-original", "ctrl-shallow"}
    assert load_experiment("phase5a_pool").spec.protocol_version == "0.10"


def test_phase5a_access_is_vqc_only():
    assert check_access("phase5a", ["vqc_train", "vqc_val"]) == ("vqc_train", "vqc_val")
    for bad in ("ctrl_train", "ctrl_val", "ctrl_test"):
        with pytest.raises(PartitionAccessError):
            check_access("phase5a", ["vqc_train", bad])


def test_schema_rejects_unregistered_designs(study):
    with pytest.raises(ValidationError):
        PoolEncodingConfig(enc_id="e0", kind="clip_linear", scale=3, half_width=math.pi)
    data = study.model_dump()
    bad = dict(data, structures=[dict(data["structures"][0], struct_id="wrong")])
    with pytest.raises(ValidationError):
        PoolStudyConfig.model_validate(bad)
    bad = dict(data, structures=[dict(data["structures"][0], ansatz="ra9")])
    with pytest.raises(ValidationError):
        PoolStudyConfig.model_validate(bad)
    with pytest.raises(ValidationError):
        PoolStudyConfig.model_validate(dict(data, seed_keys={"subset": "x"}))
