"""Phase 3A figures, drawn only from the committed aggregate tables.

Usage: uv run python scripts/make_phase3a_figures.py

Colors: reference categorical slots in fixed order (LR, RF, HGB as in Phase 2;
the VQC takes slot 4). Validated: adjacent CVD dE >= 9.1, normal-vision dE >= 22.9.
Aqua/yellow are < 3:1 on the surface, so every series has a legend entry and the
CSVs in results/tables are the table view.
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from qtrace.config import repo_root  # noqa: E402

SURFACE, INK, INK2, MUTED, GRID, AXIS = (
    "#fcfcfb",
    "#0b0b0b",
    "#52514e",
    "#898781",
    "#e1e0d9",
    "#c3c2b7",
)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
MODELS = {
    "logreg": ("Logistic regression", SERIES[0]),
    "rf": ("Random forest", SERIES[1]),
    "hgb": ("Hist. gradient boosting", SERIES[2]),
    "vqc": ("Clean 4-qubit VQC", SERIES[3]),
}

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "axes.facecolor": SURFACE,
        "figure.facecolor": SURFACE,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK2,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlecolor": INK,
        "axes.titlesize": 10.5,
        "legend.frameon": False,
        "legend.labelcolor": INK2,
    }
)


def _save(fig, path):
    fig.savefig(path, dpi=200, metadata={"Software": None}, bbox_inches="tight")
    plt.close(fig)
    return path


def pr_comparison(tables, figures):
    pr = pd.read_csv(tables / "phase3a_pr_curves.csv")
    cmp_ = pd.read_csv(tables / "phase3a_comparison.csv").set_index("model")
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    for model, (label, color) in MODELS.items():
        c = pr[pr["model"] == model]
        auprc = cmp_.loc[model, "auprc"]
        ax.step(
            c["recall"],
            c["interpolated_precision"],
            where="post",
            color=color,
            linewidth=2.6 if model == "vqc" else 2,
            label=f"{label} (AUPRC {auprc:.2f})",
        )
    ax.axhline(0.00166, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(0.04, 0.025, "chance (prevalence 0.17%)", color=MUTED, fontsize=8.5, ha="left")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Interpolated precision")
    ax.legend(loc="lower left", bbox_to_anchor=(0.04, 0.3), fontsize=8.5)
    ax.set_title(
        "Same 4 inputs (V17, V14, V12, V10 as angles), same 1,065 training rows\n"
        "Precision–recall on vqc_val (47 frauds)",
        loc="left",
    )
    return _save(fig, figures / "phase3a_pr_comparison.png")


def optimization_trace(tables, figures):
    trace = pd.read_csv(tables / "phase3a_optimization_trace.csv")
    meta = json.loads((tables / "phase3a_metadata.json").read_text())
    floor = meta["training_diagnostics"]["constant_prevalence_bce"]
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    ax.plot(trace["evaluation"], trace["bce_loss"], color=SERIES[3], linewidth=1.6)
    ax.plot(trace["evaluation"], trace["bce_loss"].cummin(), color=INK2, linewidth=2)
    ax.axhline(floor, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(
        trace["evaluation"].max(),
        floor + 0.004,
        f"constant 20% predictor ({floor:.3f})",
        color=MUTED,
        fontsize=8.5,
        ha="right",
        va="bottom",
    )
    ax.text(
        trace["evaluation"].max(),
        trace["bce_loss"].cummin().iloc[-1] + 0.006,
        f"best so far: {trace['bce_loss'].min():.3f}",
        color=INK2,
        fontsize=8.5,
        ha="right",
        va="bottom",
    )
    ax.set_xlabel("Objective evaluation (COBYLA)")
    ax.set_ylabel("Training BCE (1,065 rows)")
    ax.set_title(
        f"VQC optimization: {len(trace)} evaluations, local convergence "
        "(trust region at its lower bound)",
        loc="left",
    )
    return _save(fig, figures / "phase3a_optimization_trace.png")


def score_distribution(tables, figures):
    h = pd.read_csv(tables / "phase3a_score_histogram.csv")
    centers = (h["bin_lower"] + h["bin_upper"]) / 2
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    for col, label, color in (
        ("legit_count", "Legitimate", SERIES[0]),
        ("fraud_count", "Fraud", SERIES[1]),
    ):
        share = h[col] / h[col].sum()
        ax.step(
            centers,
            share,
            where="mid",
            color=color,
            linewidth=2,
            label=f"{label} (n={int(h[col].sum()):,})",
        )
    ax.set_xlim(0, 1)
    ax.set_xlabel("VQC fraud score p = (1 - z) / 2, z = four-qubit parity expectation")
    ax.set_ylabel("Share of class in bin")
    ax.legend(loc="upper left", fontsize=8.5)
    peak = h["fraud_count"].idxmax()
    n_peak, n_fraud = int(h.loc[peak, "fraud_count"]), int(h["fraud_count"].sum())
    x_peak, y_peak = centers[peak], h.loc[peak, "fraud_count"] / n_fraud
    ax.annotate(
        f"{n_peak} of {n_fraud} frauds share one score:\nall four features clipped to ±π",
        xy=(x_peak, y_peak),
        xytext=(x_peak - 0.36, y_peak - 0.08),
        fontsize=8.5,
        color=INK2,
        arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 1},
    )
    ax.set_title(
        "VQC score distribution on vqc_val (raw scores; trained at 20% prevalence)", loc="left"
    )
    return _save(fig, figures / "phase3a_score_distribution.png")


def main() -> int:
    root = repo_root()
    tables, figures = root / "results" / "tables", root / "results" / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    for fn in (pr_comparison, optimization_trace, score_distribution):
        print(fn(tables, figures).relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
