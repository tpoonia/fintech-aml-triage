"""The Colab notebook stays safe: valid nbformat, no secrets, pinned commit, no push, no
sealed or transaction data, and it removes the git remote after the read-only clone."""

from __future__ import annotations

import json

from qtrace.config import repo_root

NB = repo_root() / "notebooks" / "colab_qtrace_benchmark.ipynb"


def _source() -> str:
    nb = json.loads(NB.read_text())
    assert nb["nbformat"] == 4 and nb["cells"]
    assert all(not c.get("outputs") for c in nb["cells"] if c["cell_type"] == "code")
    return "\n".join("".join(c["source"]) for c in nb["cells"])


def test_notebook_is_safe():
    src = _source()
    assert 'userdata.get("GITHUB_TOKEN")' in src  # token only from Colab Secrets
    assert "ghp_" not in src and "github_pat_" not in src
    assert "git push" not in src and '"remote", "remove", "origin"' in src
    assert 'PINNED_COMMIT = "REPLACE_WITH_40_CHAR_COMMIT"' in src
    assert "[0-9a-f]{40}" in src  # refuses to run without a full commit
    code = "\n".join(
        "".join(c["source"])
        for c in json.loads(NB.read_text())["cells"]
        if c["cell_type"] == "code"
    )
    for sealed in ("lockbox", "ctrl_test", "data/raw", "creditcard", "export_inputs"):
        assert sealed not in code
