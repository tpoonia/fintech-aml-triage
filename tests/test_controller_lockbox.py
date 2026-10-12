"""The one-time sealed-test unlock refuses every unsafe state and logs every later read."""

from __future__ import annotations

import json
import subprocess

import pytest

from qtrace.controller import lockbox as LB


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    _git(tmp_path, "clone", str(origin), str(work))
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        _git(work, "config", k, v)
    (work / ".gitignore").write_text("results/lockbox/\n")
    (work / "README").write_text("x\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "init")
    _git(work, "push", "-u", "origin", "main")
    (work / "results" / "lockbox").mkdir(parents=True)
    (work / "results" / "lockbox" / "sealed.txt").write_text("secret\n")
    return work


def _commit_protocol(repo, push: bool):
    (repo / "docs").mkdir(exist_ok=True)
    (repo / "docs" / "FINAL.md").write_text("frozen\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "protocol")
    if push:
        _git(repo, "push")


def test_refuses_before_protocol_dirty_or_unpushed(repo):
    with pytest.raises(LB.SealError, match="not been unlocked"):
        LB.read_sealed(repo, "results/lockbox/sealed.txt", lambda p: p.read_text(), "x")
    with pytest.raises(LB.SealError, match="not committed"):
        LB.unlock(repo, "docs/FINAL.md", "final")
    _commit_protocol(repo, push=False)
    with pytest.raises(LB.SealError, match="origin/main"):
        LB.unlock(repo, "docs/FINAL.md", "final")
    _git(repo, "push")
    (repo / "scratch.txt").write_text("dirty\n")
    with pytest.raises(LB.SealError, match="dirty"):
        LB.unlock(repo, "docs/FINAL.md", "final")


def test_unlocks_once_and_logs_reads(repo):
    _commit_protocol(repo, push=True)
    rec = LB.unlock(repo, "docs/FINAL.md", "final evaluation")
    assert rec["protocol_sha256"] and len(rec["commit"]) == 40
    with pytest.raises(LB.SealError, match="already unlocked"):
        LB.unlock(repo, "docs/FINAL.md", "again")
    text = LB.read_sealed(repo, "results/lockbox/sealed.txt", lambda p: p.read_text(), "eval")
    assert text == "secret\n"
    log = [json.loads(x) for x in (repo / LB.ACCESS_LOG).read_text().splitlines()]
    assert len(log) == 1 and log[0]["purpose"] == "eval"
