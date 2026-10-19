"""On the remote runtime: hash and zip a job's outputs for return to the local repository.

Usage: python scripts/remote/pack_results.py --job-dir results/remote/bench --job-id bench-colab-t4
Refuses sealed material. The zip is downloaded and imported locally with import_results.py.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from qtrace.remote.bench import hardware
from qtrace.remote.transfer import pack_results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--zip", default=None)
    args = parser.parse_args(argv)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    zip_path = Path(args.zip or f"{args.job_id}.zip")
    m = pack_results(Path(args.job_dir), args.job_id, commit, hardware(), zip_path)
    print(f"{zip_path}: {len(m['files'])} files, commit {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
