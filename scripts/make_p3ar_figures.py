"""Phase 3A-R figures, drawn only from the committed aggregate tables.

Usage: uv run python scripts/make_p3ar_figures.py

Palette: reference categorical slots in fixed order (LR, RF, HGB as before; the
P3A-original VQC keeps slot 4; P3A-R takes slot 5). Validated 5-slot adjacent:
CVD dE >= 9.1, normal-vision dE >= 19.6. Low-contrast slots get legends, the VQC
lines carry secondary encoding (dashed / heavier), and the CSVs are the table view.
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
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
MODELS = {
    "logreg": ("Logistic regression", BLUE, "-", 2.0),
    "rf": ("Random forest", ORANGE, "-", 2.0),
    "hgb": ("Hist. gradient boosting", AQUA, "-", 2.0),
    "p3a_original": ("P3A-original VQC", YELLOW, (0, (5, 2)), 2.2),
    "p3a_r": ("P3A-R VQC (repaired)", MAGENTA, "-", 3.0),
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


def cv_candidates(tables, figures):
    s = pd.read_csv(tables / "p3ar_cv_summary.csv")
    sel = pd.read_json(tables / "p3ar_selection.json", typ="series")["selection"]["selected"]
    s = s.iloc[::-1].reset_index(drop=True)  # matrix order top-to-bottom
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    for i, row in s.iterrows():
        color = BLUE if row["eligible"] else MUTED
        ax.plot(
            [row["cv_auprc_min"], row["cv_auprc_max"]],
            [i, i],
            color=color,
            linewidth=2,
            solid_capstyle="round",
        )
        ax.plot(
            row["cv_auprc_mean"],
            i,
            "o",
            color=color,
            markersize=8,
            markeredgecolor=SURFACE,
            markeredgewidth=1.5,
        )
        label = f"{row['cv_auprc_mean']:.3f}" + ("  (selected)" if row["cand_id"] == sel else "")
        ax.text(
            row["cv_auprc_max"] + 0.015,
            i,
            label,
            va="center",
            fontsize=8.5,
            color=INK if row["cand_id"] == sel else INK2,
        )
    ax.set_yticks(range(len(s)), s["cand_id"])
    ax.set_xlim(0, 0.92)
    ax.set_xlabel("Held-out-fold AUPRC (dot: mean of 5 folds; bar: fold min–max)")
    ax.plot([], [], "o", color=BLUE, label="eligible (pre-registered rule)")
    ax.plot([], [], "o", color=MUTED, label="control / ineligible")
    ax.legend(loc="lower right", fontsize=8.5)
    ax.set_title(
        "Phase 3A-R: pre-registered candidates, 5-fold CV inside vqc_train only\n"
        "e0 = original ±3,[-π,π]; e1 = ±3,[-π/4,π/4]; e2 = ±5; e3 = ±15 "
        "(e1–e3 in [-π/4,π/4])",
        loc="left",
    )
    return _save(fig, figures / "p3ar_cv_candidates.png")


def pr_comparison(tables, figures):
    pr = pd.read_csv(tables / "p3ar_pr_curves.csv")
    cmp_ = pd.read_csv(tables / "p3ar_validation_comparison.csv").set_index("model")
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    for key, (label, color, style, width) in MODELS.items():
        c = pr[pr["model"] == key]
        ax.step(
            c["recall"],
            c["interpolated_precision"],
            where="post",
            color=color,
            linestyle=style,
            linewidth=width,
            label=f"{label} (AUPRC {cmp_.loc[key, 'auprc']:.2f})",
        )
    ax.axhline(0.00166, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(0.04, 0.025, "chance (prevalence 0.17%)", color=MUTED, fontsize=8.5)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Interpolated precision")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, -0.13), ncol=2, fontsize=8.5)
    ax.set_title(
        "One-time vqc_val evaluation (47 frauds): same 1,065 training rows;\n"
        "classical models use the P3A-R (e3) angles",
        loc="left",
    )
    return _save(fig, figures / "p3ar_pr_comparison.png")


def score_distribution(tables, figures):
    h = pd.read_csv(tables / "p3ar_score_histogram.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    for ax, key in zip(axes, ("p3a_original", "p3a_r"), strict=True):
        d = h[h["model"] == key]
        centers = (d["bin_lower"] + d["bin_upper"]) / 2
        for col, label, color in (
            ("legit_count", "Legitimate", BLUE),
            ("fraud_count", "Fraud", ORANGE),
        ):
            ax.step(
                centers,
                d[col] / d[col].sum(),
                where="mid",
                color=color,
                linewidth=2,
                label=f"{label} (n={int(d[col].sum()):,})",
            )
        ax.set_xlim(0, 1)
        ax.set_title(MODELS[key][0], loc="left")
        ax.set_xlabel("VQC fraud score p = (1 - z) / 2")
    axes[0].set_ylabel("Share of class in bin")
    axes[0].legend(loc="upper left", fontsize=8.5)
    fig.suptitle(
        "Score distributions on vqc_val (raw scores; trained at 20% prevalence)",
        x=0.01,
        ha="left",
        color=INK,
        fontsize=12,
        y=1.03,
    )
    return _save(fig, figures / "p3ar_score_distribution.png")


def main() -> int:
    root = repo_root()
    tables, figures = root / "results" / "tables", root / "results" / "figures"
    for fn in (cv_candidates, pr_comparison, score_distribution):
        print(fn(tables, figures).relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
