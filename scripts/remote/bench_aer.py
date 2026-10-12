"""CPU/GPU benchmark of the Q-TRACE simulation hot path (synthetic bindings; no data needed).

Usage (local or Colab, from the repository root at a pinned commit):
    uv run python scripts/remote/bench_aer.py --tag mac-m5pro
    .venv/bin/python scripts/remote/bench_aer.py --tag colab-t4 --rows 2048,8192,32768

Writes results/remote/bench/bench_<tag>.json and reference_<tag>.npz (the smallest row count).
GPU variants run only when Aer reports a GPU device (qiskit-aer-gpu on Linux + NVIDIA).
"""

from __future__ import annotations

import argparse
import json

from qtrace.config import repo_root
from qtrace.remote.bench import VARIANTS, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True, help="platform label, e.g. mac-m5pro, colab-t4")
    parser.add_argument("--rows", default="2048,8192", help="comma-separated binding counts")
    parser.add_argument("--variants", default=",".join(VARIANTS), help="comma-separated variants")
    parser.add_argument("--out", default="results/remote/bench")
    args = parser.parse_args(argv)
    rows = tuple(int(x) for x in args.rows.split(","))
    variants = tuple(v for v in args.variants.split(",") if v)
    unknown = set(variants) - set(VARIANTS)
    if unknown:
        parser.error(f"unknown variants: {sorted(unknown)}")
    report = run(rows, variants, repo_root() / args.out, args.tag)
    for r in report["exact"]:
        print(
            f"{r['rows']:>6} {r['plot']} {r['variant']:<28} {r['seconds']:8.2f} s"
            f"  {r['ms_per_row_all_factors']:.3f} ms/row"
            f"  max|dp| {r['max_abs_dp_vs_reference']:.1e}"
        )
    for r in report["finite_shot"]:
        print(
            f"finite-shot replicate at {r['rows']} rows: {r['total_per_replicate_context_s']:.3f} s"
        )
    for s in report["skipped"]:
        print("skipped:", json.dumps(s))
    print(f"total {report['total_seconds']:.1f} s; peak RSS {report['peak_rss_mb']:.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
