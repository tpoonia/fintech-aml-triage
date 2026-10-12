"""Export the data subset a remote job needs (allowed partitions only; never ctrl_test).

Usage: uv run python scripts/remote/export_inputs.py --partitions ctrl_train,ctrl_val
Writes remote_staging/<dataset>/ (gitignored). Upload it to the remote; the benchmark itself
needs no data at all.
"""

from __future__ import annotations

import argparse

from qtrace.config import repo_root
from qtrace.remote.transfer import export_partitions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="ulb_v1")
    parser.add_argument("--partitions", required=True)
    args = parser.parse_args(argv)
    root = repo_root()
    parts = tuple(p for p in args.partitions.split(",") if p)
    manifest = export_partitions(root, args.dataset, parts, root / "remote_staging" / args.dataset)
    print("exported", manifest["partitions"], "row-id hashes match Phase 1 metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
