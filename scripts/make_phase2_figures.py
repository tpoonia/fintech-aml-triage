"""Phase 2 presentation figures, drawn only from the committed aggregate tables.

Usage: uv run python scripts/make_phase2_figures.py

Colors: reference categorical slots 1-4 (validated: CVD dE >= 9.1, normal-vision
dE >= 22.9; aqua/yellow are < 3:1 on the surface, so every series also has a
legend entry and a direct label, and the CSVs in results/tables are the table view).
"""

from __future__ import annotations

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
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # fixed order, never cycled
MODELS = {"logreg": "Logistic regression", "rf": "Random forest", "hgb": "Hist. gradient boosting"}
REPS = {
    "full": "All 30 features",
    "top4-fclassif": "Top-4 (ANOVA F)",
    "pca4-std": "PCA-4 (standardized)",
    "pca4": "PCA-4",
}
TICKS = ["All 30\nfeatures", "Top-4\n(ANOVA F)", "PCA-4\n(standardized)", "PCA-4"]

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


def auprc_by_representation(tables, figures):
    m = pd.read_csv(tables / "phase2_classical_metrics.csv")
    m = m[m["draw"] == 0]
    panels = [
        ("a-full", "Trained on full vqc_train (127,677 rows, class-weighted)"),
        ("b-lpf4", "Trained on a VQC-scale subset (1,065 rows: 213 fraud + 852 legit)"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    offsets = [-0.2, 0.0, 0.2]
    for ax, (regime, title) in zip(axes, panels, strict=True):
        for i, (model, label) in enumerate(MODELS.items()):
            rows = m[(m["regime"] == regime) & (m["model"] == model)].set_index("representation")
            rows = rows.loc[list(REPS)]
            x = [k + offsets[i] for k in range(len(REPS))]
            ax.errorbar(
                x,
                rows["auprc"],
                yerr=[rows["auprc"] - rows["auprc_ci_low"], rows["auprc_ci_high"] - rows["auprc"]],
                fmt="o",
                color=SERIES[i],
                markersize=7,
                elinewidth=2,
                capsize=0,
                markeredgecolor=SURFACE,
                markeredgewidth=1.5,
                label=label,
            )
        ax.axhline(0.00166, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
        ax.text(
            len(REPS) - 0.55,
            0.02,
            "chance (prevalence 0.17%)",
            color=MUTED,
            fontsize=8.5,
            ha="right",
            va="bottom",
        )
        ax.set_xticks(range(len(REPS)), TICKS)
        ax.set_ylim(0, 1)
        ax.set_title(title, loc="left")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("AUPRC on vqc_val (47 frauds)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=3, fontsize=9, bbox_to_anchor=(0.99, 1.07))
    fig.suptitle(
        "Validation AUPRC with 95% stratified-bootstrap intervals",
        x=0.01,
        ha="left",
        color=INK,
        fontsize=12,
        y=1.07,
    )
    return _save(fig, figures / "phase2_auprc_by_representation.png")


def pr_curves(tables, figures):
    pr = pd.read_csv(tables / "phase2_pr_curves.csv")
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9), sharey=True)
    for ax, (model, title) in zip(axes, MODELS.items(), strict=True):
        for j, (rep, label) in enumerate(REPS.items()):
            c = pr[(pr["model"] == model) & (pr["representation"] == rep)]
            ax.step(
                c["recall"],
                c["interpolated_precision"],
                where="post",
                color=SERIES[j],
                linewidth=2,
                label=label,
                solid_capstyle="round",
            )
        ax.set_title(title, loc="left")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.02)
        ax.set_xlabel("Recall")
    axes[0].set_ylabel("Interpolated precision")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=4, fontsize=9, bbox_to_anchor=(0.99, 1.09))
    fig.suptitle(
        "Precision–recall on vqc_val, full-partition training (interpolated, 51 recall points)",
        x=0.01,
        ha="left",
        color=INK,
        fontsize=12,
        y=1.09,
    )
    return _save(fig, figures / "phase2_pr_curves.png")


def calibration(tables, figures):
    """Small multiples; markers only (bins are not a continuum), each labelled with its count."""
    cal = pd.read_csv(tables / "phase2_calibration_bins.csv")
    cal = cal[cal["strategy"] == "uniform"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.0), sharey=True)
    for i, (ax, (model, title)) in enumerate(zip(axes, MODELS.items(), strict=True)):
        ax.plot([0, 1], [0, 1], color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
        c = cal[cal["model"] == model]
        ax.plot(
            c["mean_predicted"],
            c["fraction_positive"],
            linestyle="none",
            marker="o",
            markersize=7,
            color=SERIES[i],
            markeredgecolor=SURFACE,
            markeredgewidth=1.5,
        )
        for _, b in c.iterrows():
            ax.annotate(
                f"n={int(b['count']):,}",
                (b["mean_predicted"], b["fraction_positive"]),
                textcoords="offset points",
                xytext=(0, 7),
                fontsize=7.5,
                color=INK2,
                rotation=90,
                ha="center",
                va="bottom",
            )
        ax.set_title(title, loc="left")
        ax.set_xlim(-0.04, 1.06)
        ax.set_ylim(-0.03, 1.32)
        ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_xlabel("Mean predicted probability")
    axes[0].set_ylabel("Observed fraud rate in bin")
    axes[0].text(
        0.62,
        0.5,
        "perfect calibration",
        color=MUTED,
        fontsize=8,
        rotation=38,
        ha="left",
        va="bottom",
    )
    fig.suptitle(
        "Reliability on vqc_val: full features, full partition "
        "(10 equal-width bins; bins with few rows are unreliable)",
        x=0.01,
        ha="left",
        color=INK,
        fontsize=12,
        y=1.04,
    )
    return _save(fig, figures / "phase2_calibration.png")


def main() -> int:
    root = repo_root()
    tables, figures = root / "results" / "tables", root / "results" / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    for fn in (auprc_by_representation, pr_curves, calibration):
        print(fn(tables, figures).relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
