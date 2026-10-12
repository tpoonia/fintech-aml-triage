"""Phase 5B registered analysis (train/val only; the test split stays sealed).

Usage: uv run python scripts/analyze_counterfactual_5b.py

Reads results/processed/phase5b (gitignored) and the committed build records; writes the
committed analysis tables (Tables A-I support, preferred actions, heterogeneity,
predictability) and p5b_metadata.json with the G3B verdict. Deterministic.
"""

from __future__ import annotations

from qtrace.config import repo_root
from qtrace.counterfactual.report import render_report, run_report


def main() -> int:
    root = repo_root()
    rep = run_report(root)
    for rel, text in render_report(rep).items():
        (root / rel).write_text(text, encoding="utf-8")
    g = rep["an"]["g3b"]
    print("G3B:", g["verdict"])
    print("fail conditions:", g["fail_conditions"])
    print("pass criteria:", g["pass_criteria"])
    print(
        "metrics:", {k: round(v, 4) if isinstance(v, float) else v for k, v in g["metrics"].items()}
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
