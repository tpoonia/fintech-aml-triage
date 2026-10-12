"""The one-time final evaluation reproduces byte for byte (slow; reads the sealed test again,
which the lockbox guard allows only after the single unlock and logs). Skipped before the
unlock or when the gitignored data are absent."""

from __future__ import annotations

import subprocess
import sys

import pytest

from qtrace.config import repo_root
from qtrace.controller import lockbox as LB

ROOT = repo_root()
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not (ROOT / LB.RECORD).exists(), reason="sealed test not unlocked here"),
]


def test_final_evaluation_reproduces_byte_for_byte():
    before = {p: p.read_bytes() for p in (ROOT / "results/tables").glob("final_*")}
    subprocess.run(
        [sys.executable, "scripts/final_test.py", "--reproduce"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    after = {p: p.read_bytes() for p in (ROOT / "results/tables").glob("final_*")}
    assert before.keys() == after.keys()
    changed = [p.name for p in before if before[p] != after[p] and p.name != "final_metadata.json"]
    assert not changed, changed
