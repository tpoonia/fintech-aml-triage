"""Remote-transfer guards: sealed material never leaves or enters; imports verify hashes and
the commit, stay inside results/remote/<job_id>/ and never overwrite."""

from __future__ import annotations

import json
import subprocess
import zipfile

import pytest

from qtrace.config import repo_root
from qtrace.remote import transfer as TR

ROOT = repo_root()
HEAD = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
).stdout.strip()


@pytest.mark.parametrize(
    "path",
    [
        "results/lockbox/phase5c/mixed_test.parquet",
        "lockbox/x.json",
        "out/mixed_test.parquet",
        "results/processed/phase5b/counterfactual_test.parquet",
        "data/raw/creditcard.csv",
    ],
)
def test_sealed_paths_are_recognised(path):
    assert TR.is_sealed(path)


@pytest.mark.parametrize(
    "path", ["bench/bench_colab-t4.json", "results/remote/x/mixed_val.parquet"]
)
def test_ordinary_paths_pass(path):
    assert not TR.is_sealed(path)


def test_ctrl_test_is_never_exported(tmp_path):
    with pytest.raises(TR.TransferError, match="sealed partitions"):
        TR.export_partitions(ROOT, "ulb_v1", ("ctrl_train", "ctrl_test"), tmp_path)


def _job(tmp_path, files: dict[str, bytes]):
    job = tmp_path / "job"
    for rel, data in files.items():
        (job / rel).parent.mkdir(parents=True, exist_ok=True)
        (job / rel).write_bytes(data)
    return job


def test_pack_refuses_sealed_outputs(tmp_path):
    job = _job(tmp_path, {"results/lockbox/a.parquet": b"x"})
    with pytest.raises(TR.TransferError, match="sealed"):
        TR.pack_results(job, "bench-1", HEAD, {}, tmp_path / "b.zip")


def test_round_trip_import_and_no_overwrite(tmp_path):
    job = _job(tmp_path, {"bench/bench_x.json": b"{}\n", "bench/ref.npz": b"\x00\x01"})
    zp = tmp_path / "b.zip"
    TR.pack_results(job, "bench-colab-t4", HEAD, {"gpu": "T4"}, zp)
    root = tmp_path / "repo"
    subprocess.run(["git", "clone", "-q", "--no-checkout", str(ROOT), str(root)], check=True)
    out = TR.import_results(root, zp)
    assert out["files"] == 2
    dest = root / "results/remote/bench-colab-t4"
    assert (dest / "bench/bench_x.json").read_bytes() == b"{}\n"
    assert json.loads((dest / "manifest.json").read_text())["commit"] == HEAD
    with pytest.raises(TR.TransferError, match="never overwrite"):
        TR.import_results(root, zp)


def test_import_rejects_tampering_unknown_commit_and_traversal(tmp_path):
    job = _job(tmp_path, {"a.json": b"1"})
    good = tmp_path / "good.zip"
    TR.pack_results(job, "job-ok", HEAD, {}, good)
    root = tmp_path / "repo"
    subprocess.run(["git", "clone", "-q", "--no-checkout", str(ROOT), str(root)], check=True)

    def rewrite(name, mutate):
        bad = tmp_path / name
        with zipfile.ZipFile(good) as zin, zipfile.ZipFile(bad, "w") as zout:
            for item in zin.namelist():
                data = zin.read(item)
                item, data = mutate(item, data)
                zout.writestr(item, data)
        return bad

    tampered = rewrite("t.zip", lambda n, d: (n, b"2" if n == "files/a.json" else d))
    with pytest.raises(TR.TransferError, match="hash mismatch"):
        TR.import_results(root, tampered)

    def other_commit(n, d):
        if n != "manifest.json":
            return n, d
        m = json.loads(d)
        m["commit"] = "0" * 40
        return n, json.dumps(m).encode()

    with pytest.raises(TR.TransferError, match="not in the local history"):
        TR.import_results(root, rewrite("c.zip", other_commit))
    with pytest.raises(TR.TransferError, match="unsafe path"):
        TR.import_results(
            root, rewrite("p.zip", lambda n, d: ("../x" if n == "files/a.json" else n, d))
        )


@pytest.mark.skipif(
    not (ROOT / "data/processed/ulb_v1/features_preprocessed.parquet").exists(),
    reason="Phase 1 data not present locally",
)
def test_export_holds_only_requested_partitions_and_verifies(tmp_path):
    import pandas as pd

    m = TR.export_partitions(ROOT, "ulb_v1", ("ctrl_train",), tmp_path)
    frame = pd.read_parquet(tmp_path / "data/processed/ulb_v1/features_preprocessed.parquet")
    assert set(frame.partition) == {"ctrl_train"} and len(frame) == 42_559
    assert set(m["files"]) == {
        "data/processed/ulb_v1/features_preprocessed.parquet",
        "data/processed/ulb_v1/preprocessing.json",
    }
