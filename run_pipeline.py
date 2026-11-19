"""Run the synthetic AML triage pipeline from data generation through queue build."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
STEPS = (
    "src/data/generate_customers.py",
    "src/data/generate_transactions.py",
    "src/data/generate_alerts.py",
    "src/data/build_ml_dataset.py",
    "src/models/train_model.py",
    "src/scoring/risk_scoring.py",
    "src/explainability/explain_alerts.py",
    "src/prioritization/prioritize_alerts.py",
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Use a small dataset for a quick product demo.")
    parser.add_argument("--n-customers", type=int, help="Number of synthetic customers (default: 10,000).")
    parser.add_argument("--n-transactions", type=int, help="Number of base transactions (default: 20 per customer).")
    parser.add_argument("--seed", type=int, default=42, help="Reproducible random seed (default: 42).")
    parser.add_argument(
        "--output-format",
        choices=("csv", "trimmed-csv", "parquet"),
        default="csv",
        help="Prioritized queue format.",
    )
    args = parser.parse_args(argv)
    if args.n_customers is None:
        args.n_customers = 200 if args.demo else 10_000
    if args.n_transactions is None:
        args.n_transactions = args.n_customers * 20
    if args.n_customers < 20 or args.n_transactions < 1:
        parser.error("--n-customers must be at least 20 and --n-transactions must be positive")
    return args


def main(argv=None):
    args = parse_args(argv)
    env = os.environ.copy()
    env.update(
        AML_N_CUSTOMERS=str(args.n_customers),
        AML_N_TRANSACTIONS=str(args.n_transactions),
        AML_SEED=str(args.seed),
        AML_QUEUE_FORMAT=args.output_format,
    )
    started = time.monotonic()
    print(
        f"AML pipeline starting: customers={args.n_customers:,}, "
        f"base_transactions={args.n_transactions:,}, seed={args.seed}, "
        f"queue_format={args.output_format}",
        flush=True,
    )
    for index, step in enumerate(STEPS, start=1):
        print(f"\n[{index}/{len(STEPS)}] {step}", flush=True)
        subprocess.run([sys.executable, str(ROOT / step)], cwd=ROOT, env=env, check=True)
    print(f"\nPipeline completed in {time.monotonic() - started:.2f}s.", flush=True)


if __name__ == "__main__":
    main()
