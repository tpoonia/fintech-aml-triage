"""One-time unlock of the sealed controller-test outcomes (protocol §17; completion brief).

The sealed test files may be read only after the final-test protocol is committed AND pushed
(HEAD contained in ``origin/main``), on a clean tree, and the first read is recorded in
``results/lockbox/UNLOCK_RECORD.json`` (gitignored; its content is copied into the committed
final results). A second *unlock* is refused. Re-reading for byte-for-byte reproduction of the
frozen evaluation is allowed only after the unlock, at a commit that descends from the unlock
commit, and every read is appended to ``results/lockbox/ACCESS_LOG.jsonl``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

RECORD = Path("results/lockbox/UNLOCK_RECORD.json")
ACCESS_LOG = Path("results/lockbox/ACCESS_LOG.jsonl")


class SealError(RuntimeError):
    """The sealed test may not be read in the current state."""


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state(root: Path, protocol: str) -> dict:
    """Facts the unlock depends on (no side effects)."""
    head = _git(root, "rev-parse", "HEAD")
    dirty = bool(_git(root, "status", "--porcelain"))
    tracked = bool(_git(root, "ls-files", protocol))
    try:
        remote = _git(root, "branch", "-r", "--contains", head)
    except subprocess.CalledProcessError:
        remote = ""
    return {
        "head": head,
        "dirty": dirty,
        "protocol_tracked": tracked,
        "pushed": "origin/main" in remote.split(),
        "protocol_sha256": _sha(root / protocol) if (root / protocol).is_file() else None,
    }


def unlock(root: Path, protocol: str, purpose: str) -> dict:
    """Record the single unlock; refuse unless the frozen protocol is committed and pushed."""
    if (root / RECORD).exists():
        raise SealError(f"the sealed test was already unlocked: {(root / RECORD).read_text()}")
    s = state(root, protocol)
    if s["dirty"]:
        raise SealError("refusing to unlock on a dirty tree")
    if not s["protocol_tracked"]:
        raise SealError(f"the final-test protocol {protocol} is not committed")
    if not s["pushed"]:
        raise SealError("the commit holding the final-test protocol is not on origin/main")
    record = {
        "unlocked_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": s["head"],
        "protocol": protocol,
        "protocol_sha256": s["protocol_sha256"],
        "purpose": purpose,
    }
    (root / RECORD).parent.mkdir(parents=True, exist_ok=True)
    (root / RECORD).write_text(json.dumps(record, indent=2) + "\n")
    return record


def read_sealed(root: Path, relpath: str, reader, purpose: str):
    """Read a sealed file after the unlock; every read is logged."""
    if not (root / RECORD).exists():
        raise SealError("the sealed test has not been unlocked (final protocol first)")
    record = json.loads((root / RECORD).read_text())
    head = _git(root, "rev-parse", "HEAD")
    try:
        _git(root, "merge-base", "--is-ancestor", record["commit"], head)
    except subprocess.CalledProcessError as exc:
        raise SealError("HEAD does not descend from the unlock commit") from exc
    with (root / ACCESS_LOG).open("a") as log:
        log.write(
            json.dumps(
                {
                    "utc": datetime.now(UTC).isoformat(timespec="seconds"),
                    "commit": head,
                    "file": relpath,
                    "purpose": purpose,
                }
            )
            + "\n"
        )
    return reader(root / relpath)
