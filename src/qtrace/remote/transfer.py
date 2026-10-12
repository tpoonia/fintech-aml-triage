"""Guarded transfer between the authoritative local repository and a remote runtime (Colab).

Rules enforced here (docs/REMOTE_COMPUTE.md):

- **Outbound:** only code at a pinned, pushed commit (cloned by the remote) and, when a job
  needs data, an *exported subset* of allowed partitions. ``ctrl_test`` rows, anything under
  ``results/lockbox/`` and sealed counterfactual test files are never exported.
- **Inbound:** the remote returns one zip with ``manifest.json`` (job id, commit, platform,
  SHA-256 of every file). The local import verifies every hash, that the commit exists in
  local history, that no path escapes the job directory or touches sealed material, and
  writes only under ``results/remote/<job_id>/``; it never overwrites an existing path. Frozen
  artifacts and committed tables can only change through a local, reviewed, committed step.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

import pandas as pd

SEALED_PARTITIONS = frozenset({"ctrl_test"})
SEALED_PATTERNS = (
    re.compile(r"(^|/)results/lockbox(/|$)"),
    re.compile(r"(^|/)lockbox(/|$)"),
    re.compile(r"(^|/)(counterfactual|mixed)_test\.parquet$"),
    re.compile(r"(^|/)data/raw(/|$)"),
)
JOB_ID = re.compile(r"^[a-z0-9][a-z0-9_\-]{2,63}$")
INBOUND_ROOT = Path("results/remote")


class TransferError(RuntimeError):
    """A transfer would break isolation, integrity or the no-overwrite rule."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def is_sealed(relpath: str) -> bool:
    return any(p.search(relpath) for p in SEALED_PATTERNS)


# ---------------------------------------------------------------- outbound (local -> remote)


def export_partitions(root: Path, dataset_id: str, partitions: tuple[str, ...], out: Path) -> dict:
    """Write a data subset holding ONLY ``partitions`` (never ctrl_test) plus preprocessing.

    The remote places it at the same relative paths; the unchanged Phase 1 verification
    (per-partition row-id hashes against committed metadata) then passes for those partitions.
    """
    bad = SEALED_PARTITIONS & set(partitions)
    if bad:
        raise TransferError(f"sealed partitions may not leave the machine: {sorted(bad)}")
    from qtrace.data.duplicates import row_ids_sha256

    src = root / "data" / "processed" / dataset_id
    frame = pd.read_parquet(
        src / "features_preprocessed.parquet", filters=[("partition", "in", list(partitions))]
    )
    seen = set(frame.partition.unique())
    if seen != set(partitions):
        raise TransferError(f"export read {sorted(seen)}, expected {sorted(partitions)}")
    meta = json.loads(
        (root / "results" / "tables" / f"{dataset_id}_phase1_metadata.json").read_text()
    )
    expected = {p["partition"]: p["row_ids_sha256"] for p in meta["partitions"]}
    hashes = {p: row_ids_sha256(frame.loc[frame.partition == p, "row_id"]) for p in partitions}
    if any(hashes[p] != expected[p] for p in partitions):
        raise TransferError("exported partition row ids differ from Phase 1 metadata")
    dest = out / "data" / "processed" / dataset_id
    dest.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(dest / "features_preprocessed.parquet", index=False)
    shutil.copy2(src / "preprocessing.json", dest / "preprocessing.json")
    files = {str(PurePosixPath(p.relative_to(out))): sha256_file(p) for p in sorted(dest.iterdir())}
    manifest = {
        "dataset_id": dataset_id,
        "partitions": list(partitions),
        "partition_row_ids_sha256": hashes,
        "files": files,
    }
    (out / "inputs_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


# ---------------------------------------------------------------- remote side


def pack_results(job_dir: Path, job_id: str, commit: str, platform: dict, zip_path: Path) -> dict:
    """On the remote: hash every file under ``job_dir`` into a manifest and zip them."""
    if not JOB_ID.match(job_id):
        raise TransferError(f"invalid job id {job_id!r}")
    files = {}
    for p in sorted(job_dir.rglob("*")):
        if p.is_file():
            rel = str(PurePosixPath(p.relative_to(job_dir)))
            if is_sealed(rel):
                raise TransferError(f"sealed material in remote outputs: {rel}")
            files[rel] = sha256_file(p)
    manifest = {"job_id": job_id, "commit": commit, "platform": platform, "files": files}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        for rel in files:
            z.write(job_dir / rel, f"files/{rel}")
    return manifest


# ---------------------------------------------------------------- inbound (remote -> local)


def _commit_known(root: Path, commit: str) -> bool:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        return False
    r = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root, capture_output=True
    )
    return r.returncode == 0


def import_results(root: Path, zip_path: Path) -> dict:
    """Verify a remote bundle and copy it to ``results/remote/<job_id>/`` (never overwriting)."""
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        for n in names:
            pp = PurePosixPath(n)
            if pp.is_absolute() or ".." in pp.parts:
                raise TransferError(f"unsafe path in bundle: {n}")
        if "manifest.json" not in names:
            raise TransferError("bundle has no manifest.json")
        z.extractall(tmp)
        manifest = json.loads((Path(tmp) / "manifest.json").read_text())
        job_id, commit = manifest.get("job_id", ""), manifest.get("commit", "")
        if not JOB_ID.match(job_id):
            raise TransferError(f"invalid job id {job_id!r}")
        if not _commit_known(root, commit):
            raise TransferError(f"commit {commit!r} is not in the local history")
        files = manifest.get("files", {})
        payload = {
            n[len("files/") :] for n in names if n.startswith("files/") and not n.endswith("/")
        }
        if payload != set(files):
            raise TransferError("bundle files and manifest disagree")
        for rel, digest in files.items():
            if is_sealed(rel):
                raise TransferError(f"sealed material in bundle: {rel}")
            if sha256_file(Path(tmp) / "files" / rel) != digest:
                raise TransferError(f"hash mismatch: {rel}")
        dest = root / INBOUND_ROOT / job_id
        if dest.exists():
            raise TransferError(f"{dest.relative_to(root)} exists; remote imports never overwrite")
        dest.mkdir(parents=True)
        for rel in files:
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(tmp) / "files" / rel, target)
        (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return {"job_id": job_id, "commit": commit, "files": len(files), "dest": str(dest)}
