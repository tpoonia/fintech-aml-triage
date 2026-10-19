"""Capture git state, package versions and hardware for run manifests."""

from __future__ import annotations

import json
import os
import platform
import secrets
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from qtrace.records.manifest import EnvironmentInfo, GitState, HardwareInfo, RunManifest

CORE_PACKAGES: tuple[str, ...] = (
    "numpy",
    "scipy",
    "pandas",
    "pyarrow",
    "pyyaml",
    "pydantic",
    "scikit-learn",
    "qiskit",
    "qiskit-aer",
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_run_id(now: datetime | None = None) -> str:
    """Timestamped unique run id. Identifiers only; never used as a random seed."""
    stamp = (now or utc_now()).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{secrets.token_hex(4)}"


def _git(repo: Path, *args: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def capture_git_state(repo: str | Path) -> GitState:
    repo = Path(repo)
    if _git(repo, "rev-parse", "--is-inside-work-tree") != "true":
        raise RuntimeError(f"{repo} is not inside a git work tree")
    status = _git(repo, "status", "--porcelain")
    return GitState(
        commit=_git(repo, "rev-parse", "HEAD"),
        branch=_git(repo, "symbolic-ref", "--short", "HEAD"),
        dirty=bool(status),
    )


def capture_environment(packages: tuple[str, ...] = CORE_PACKAGES) -> EnvironmentInfo:
    versions: dict[str, str] = {}
    for name in packages:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return EnvironmentInfo(
        python_version=platform.python_version(),
        platform=platform.platform(),
        packages=versions,
    )


def _cpu_model() -> str:
    if sys.platform == "darwin":
        proc = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text().splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def _memory_bytes() -> int | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        return None


def capture_hardware() -> HardwareInfo:
    return HardwareInfo(
        machine=platform.machine(),
        cpu_model=_cpu_model(),
        cpu_count=os.cpu_count(),
        memory_bytes=_memory_bytes(),
    )


def assert_reportable(git: GitState) -> None:
    if git.commit is None or git.dirty:
        raise RuntimeError("reported runs require a committed, clean git tree")


def write_json(path: str | Path, obj: Any) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def write_manifest(manifest: RunManifest, out_dir: str | Path) -> Path:
    return write_json(Path(out_dir) / "manifest.json", manifest.model_dump(mode="json"))
