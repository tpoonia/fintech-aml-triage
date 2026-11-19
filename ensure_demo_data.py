"""Generate a deterministic demo queue when the configured queue is absent."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DEFAULT_CSV = ROOT / "data" / "processed" / "aml_prioritized_alerts.csv"
DEFAULT_PARQUET = ROOT / "data" / "processed" / "aml_prioritized_alerts.parquet"


def main():
    configured = os.environ.get("AML_ALERTS_DATA_PATH")
    requested = Path(configured).expanduser() if configured else DEFAULT_CSV
    if not requested.is_absolute():
        requested = ROOT / requested
    if requested.exists():
        print(f"Demo data already available: {requested}")
        return

    output_format = "parquet" if requested.suffix.lower() == ".parquet" else "csv"
    generated = DEFAULT_PARQUET if output_format == "parquet" else DEFAULT_CSV
    subprocess.run(
        [sys.executable, str(ROOT / "run_pipeline.py"), "--demo", "--output-format", output_format],
        cwd=ROOT,
        check=True,
    )
    if requested != generated:
        requested.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(generated, requested)
    print(f"Demo data ready: {requested}")


if __name__ == "__main__":
    main()
