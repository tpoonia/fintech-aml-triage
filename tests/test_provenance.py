from __future__ import annotations

import json
import subprocess

import pytest

from qtrace.records import RunManifest
from qtrace.utils.provenance import (
    CORE_PACKAGES,
    assert_reportable,
    capture_environment,
    capture_git_state,
    capture_hardware,
    new_run_id,
    utc_now,
    write_manifest,
)


def _commit(repo, name="f.txt"):
    (repo / name).write_text("x")
    subprocess.run(["git", "-C", str(repo), "add", name], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "c"], check=True, capture_output=True)


def test_git_state_before_first_commit(git_repo):
    state = capture_git_state(git_repo)
    assert state.commit is None and state.branch == "main"
    with pytest.raises(RuntimeError):
        assert_reportable(state)


def test_git_state_clean_then_dirty(git_repo):
    _commit(git_repo)
    clean = capture_git_state(git_repo)
    assert clean.commit and len(clean.commit) == 40 and not clean.dirty
    assert_reportable(clean)
    (git_repo / "untracked.txt").write_text("y")
    dirty = capture_git_state(git_repo)
    assert dirty.dirty and dirty.commit == clean.commit
    with pytest.raises(RuntimeError):
        assert_reportable(dirty)


def test_not_a_repo(tmp_path):
    with pytest.raises(RuntimeError):
        capture_git_state(tmp_path)


def test_environment_and_hardware_capture():
    env = capture_environment()
    assert set(env.packages) == set(CORE_PACKAGES)
    assert env.packages["qiskit"] != "not-installed"
    hw = capture_hardware()
    assert hw.cpu_count and hw.cpu_count >= 1 and hw.machine


def test_run_ids_unique_and_timestamped():
    ids = {new_run_id() for _ in range(50)}
    assert len(ids) == 50 and all(i[8] == "T" and i.endswith(i[-8:]) for i in ids)


def test_manifest_round_trip(git_repo, tmp_path):
    _commit(git_repo)
    now = utc_now()
    manifest = RunManifest(
        run_id=new_run_id(now),
        experiment_id="smoke_env",
        protocol_version="0.2",
        reporting="dev",
        status="completed",
        command=["pytest"],
        resolved_config={"a": 1},
        config_hash="b" * 64,
        component_hashes={},
        git=capture_git_state(git_repo),
        environment=capture_environment(),
        hardware=capture_hardware(),
        seeds={"shots": 9011},
        started_utc=now,
        finished_utc=now,
    )
    path = write_manifest(manifest, tmp_path / "out")
    loaded = RunManifest.model_validate(json.loads(path.read_text()))
    assert loaded == manifest
