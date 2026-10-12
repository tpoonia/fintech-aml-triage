"""Import a remote job's result zip into results/remote/<job_id>/ (verified; never overwrites).

Usage: uv run python scripts/remote/import_results.py ~/Downloads/bench-colab-t4.zip
"""

from __future__ import annotations

import argparse
from pathlib import Path

from qtrace.config import repo_root
from qtrace.remote.transfer import import_results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip", type=Path)
    args = parser.parse_args(argv)
    out = import_results(repo_root(), args.zip)
    print(f"imported {out['files']} files from commit {out['commit']} into {out['dest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
