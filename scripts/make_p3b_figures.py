"""Phase 3B figures A-E, drawn only from the committed aggregate tables.

Usage: uv run python scripts/make_p3b_figures.py

Palette: reference categorical slots in fixed order, one per noise family
(depolarizing, thermal, combined, synthetic asymmetric readout, symmetric-readout
negative control). Validated 5-slot adjacent (scripts/validate_palette.js, light
surface). Low-contrast slots (aqua, yellow) carry legends and secondary encoding
(markers / dashes); the CSVs are the table view.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, LogNorm  # noqa: E402

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
FAMILIES = {  # g1_family -> (label, color, marker, linestyle)
    "depolarizing": ("Depolarizing", BLUE, "o", "-"),
    "thermal": ("Thermal relaxation", ORANGE, "s", "-"),
    "combined": ("Combined (dep + thermal + sym. readout)", AQUA, "D", "-"),
    "synthetic_asymmetric_readout": ("Synthetic asym. readout stress test", YELLOW, "^", "-"),
    "symmetric_readout_negative_control": (
        "Symmetric readout (negative control)",
        MAGENTA,
        "v",
        (0, (4, 2)),
    ),
}
SEVERITIES = ("low", "medium", "high")
NAMES = {
    "clean": "clean",
    "ro-sym-high": "sym. readout high (neg. control)",
    "dep-high": "depolarizing high",
    "th-high": "thermal high",
    "comb-high": "combined high",
    "ar-050": "synthetic asym. readout high",
}
PRIMARY = "p3a_r"

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


def _primary(tables):
    m = pd.read_csv(tables / "p3b_exact_metrics.csv")
    return m[(m["model"] == PRIMARY) & (m["condition"] != "clean")]


def _by_family(ax, m, col, lo=None, hi=None, families=None):
    keys = list(FAMILIES) if families is None else families
    offsets = np.linspace(-0.16, 0.16, len(keys))
    for off, fam in zip(offsets, keys, strict=True):
        label, color, marker, style = FAMILIES[fam]
        d = m[m["g1_family"] == fam].set_index("severity").loc[list(SEVERITIES)]
        x = np.arange(3) + off
        if lo is not None:
            ax.vlines(x, d[lo], d[hi], color=color, linewidth=1.6, alpha=0.9)
        ax.plot(
            x,
            d[col],
            color=color,
            linestyle=style,
            linewidth=2,
            marker=marker,
            markersize=7,
            markeredgecolor=SURFACE,
            markeredgewidth=1.2,
            label=label,
        )
    ax.set_xticks(range(3), SEVERITIES)
    ax.set_xlabel("Registered severity")


def fig_a(tables, figures):
    m = _primary(tables)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
    for ax, name in zip(axes, ("auprc", "auroc"), strict=True):
        ax.axhline(0, color=AXIS, linewidth=1)
        _by_family(ax, m, f"delta_{name}", f"delta_{name}_ci_low", f"delta_{name}_ci_high")
        ax.set_ylabel(f"Δ{name.upper()} (exact noisy − exact clean)")
    axes[0].set_title("ΔAUPRC, paired 95% bootstrap interval", loc="left")
    axes[1].set_title("ΔAUROC, paired 95% bootstrap interval", loc="left")
    axes[0].legend(loc="upper left", bbox_to_anchor=(0.0, -0.16), ncol=3, fontsize=8.5)
    fig.suptitle(
        "A. Discrimination change under exact noise: frozen P3A-R VQC on vqc_val (47 frauds)",
        x=0.01,
        ha="left",
        color=INK,
        fontsize=12,
        y=1.02,
    )
    return _save(fig, figures / "p3b_a_delta_auprc.png")


def fig_b(tables, figures):
    m = _primary(tables).copy()
    nc = m[m["g1_family"] == "symmetric_readout_negative_control"]
    m = m[m["g1_family"] != "symmetric_readout_negative_control"]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
    for ax, col, title, rule in zip(
        axes,
        ("spearman", "kendall"),
        ("Spearman ρ vs clean scores", "Kendall τ vs clean scores"),
        (("ρ", 0.999), ("τ", 0.995)),
        strict=True,
    ):
        m[f"one_minus_{col}"] = 1 - m[col]
        _by_family(ax, m, f"one_minus_{col}", families=list(FAMILIES)[:4])
        ax.set_yscale("log")
        ax.set_title(f"1 − {title}", loc="left")
        ax.axhline(1 - rule[1], color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
        ax.text(
            -0.3,
            (1 - rule[1]) * 0.85,
            f"A13 rule: {rule[0]} = {rule[1]}",
            color=MUTED,
            fontsize=8,
            ha="left",
            va="top",
        )
    axes[0].set_ylabel("1 − rank correlation (log scale)")
    axes[0].legend(loc="upper left", bbox_to_anchor=(0.0, -0.16), ncol=2, fontsize=8.5)
    axes[1].text(
        0.0,
        -0.2,
        f"Symmetric readout (negative control, {len(nc)} conditions) not drawn: ρ = τ = 1\n"
        "to table precision (registered tolerance 1 − ρ ≤ 1e-9; exact affine contraction).",
        transform=axes[1].transAxes,
        color=INK2,
        fontsize=8.5,
        va="top",
    )
    fig.suptitle(
        "B. Ranking change under exact noise (higher = more reordering); P3A-R, vqc_val",
        x=0.01,
        ha="left",
        color=INK,
        fontsize=12,
        y=1.02,
    )
    return _save(fig, figures / "p3b_b_ranking.png")


def fig_c(tables, figures):
    h = pd.read_csv(tables / "p3b_score_hist2d.csv")
    h = h[h["model"] == PRIMARY]
    meta = pd.read_json(tables / "p3b_metadata.json", typ="series")
    tau = meta["models"][PRIMARY]["tau_frozen_clean"]
    conds = [c for c in NAMES if c != "clean"]
    edges = np.linspace(0, 1, 51)
    centers = (edges[:-1] + edges[1:]) / 2
    cmap = LinearSegmentedColormap.from_list("seq_blue", ["#dbe9f8", BLUE, "#123d70"])
    fig, axes = plt.subplots(1, len(conds), figsize=(16, 3.9), sharex=True, sharey=True)
    for ax, cond in zip(axes, conds, strict=True):
        d = h[h["condition"] == cond]
        grid = np.zeros((50, 50))
        legit = d[d["class"] == "legit"]
        grid[legit["clean_bin"], legit["noisy_bin"]] = legit["count"]
        img = np.ma.masked_equal(grid.T, 0)
        mesh = ax.pcolormesh(edges, edges, img, cmap=cmap, norm=LogNorm(1, grid.max()))
        fr = d[d["class"] == "fraud"]
        ax.scatter(
            centers[fr["clean_bin"]],
            centers[fr["noisy_bin"]],
            s=10 + 12 * fr["count"],
            color=ORANGE,
            edgecolor=SURFACE,
            linewidth=0.8,
            zorder=3,
            label="fraud",
        )
        ax.plot([0, 1], [0, 1], color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
        ax.axvline(tau, color=INK2, linewidth=0.8, linestyle=":")
        ax.axhline(tau, color=INK2, linewidth=0.8, linestyle=":")
        ax.set_title(NAMES[cond], loc="left", fontsize=9.5)
        ax.set_xlabel("clean score")
        ax.set_aspect("equal")
        ax.grid(False)
    axes[0].set_ylabel("noisy score")
    cb = fig.colorbar(mesh, ax=axes, fraction=0.012, pad=0.01)
    cb.set_label("legitimate rows per cell (log)", color=INK2)
    axes[0].legend(loc="upper left", fontsize=8.5)
    fig.suptitle(
        "C. Clean vs exact-noisy score per transaction (P3A-R, vqc_val); dotted lines: frozen τ",
        x=0.01,
        ha="left",
        color=INK,
        fontsize=12,
        y=1.04,
    )
    return _save(fig, figures / "p3b_c_clean_vs_noisy.png")


def fig_d(tables, figures):
    h = pd.read_csv(tables / "p3b_score_histogram.csv")
    cal = pd.read_csv(tables / "p3b_calibration_bins.csv")
    h, cal = h[h["model"] == PRIMARY], cal[cal["model"] == PRIMARY]
    conds = [c for c in NAMES if c != "clean"]
    fig, axes = plt.subplots(2, len(conds), figsize=(16, 6.6), sharex=True)
    c0 = h[h["condition"] == "clean"]
    centers = (c0["bin_lower"] + c0["bin_upper"]) / 2
    k0 = cal[cal["condition"] == "clean"]
    for j, cond in enumerate(conds):
        d = h[h["condition"] == cond]
        top, bottom = axes[0, j], axes[1, j]
        for frame, color, style, label in (
            (c0, MUTED, (0, (4, 2)), "clean"),
            (d, BLUE, "-", "noisy"),
        ):
            top.step(
                centers,
                frame["legit_count"].to_numpy() / frame["legit_count"].sum(),
                where="mid",
                color=color,
                linestyle=style,
                linewidth=2,
                label=f"{label} (legit)",
            )
            top.step(
                centers,
                frame["fraud_count"].to_numpy() / frame["fraud_count"].sum(),
                where="mid",
                color=ORANGE if label == "noisy" else "#b9b8b0",
                linestyle=style,
                linewidth=1.6,
                label=f"{label} (fraud)",
            )
        top.set_title(NAMES[cond], loc="left", fontsize=9.5)
        k = cal[cal["condition"] == cond]
        bottom.plot([0, 1], [0, 1], color=AXIS, linewidth=1)
        bottom.plot(
            k0["mean_predicted"],
            k0["fraction_positive"],
            color=MUTED,
            linestyle=(0, (4, 2)),
            marker="o",
            markersize=5,
            linewidth=1.6,
            label="clean",
        )
        bottom.plot(
            k["mean_predicted"],
            k["fraction_positive"],
            color=BLUE,
            marker="o",
            markersize=6,
            markeredgecolor=SURFACE,
            linewidth=2,
            label="noisy",
        )
        bottom.set_xlabel("score p = (1 − z)/2")
        bottom.set_xlim(0, 1)
        bottom.set_ylim(-0.02, 1.02)
    axes[0, 0].set_ylabel("share of class in bin")
    axes[1, 0].set_ylabel("observed fraud rate (10 bins)")
    axes[0, 0].legend(loc="upper right", fontsize=7.5)
    axes[1, 0].legend(loc="upper left", fontsize=8)
    fig.suptitle(
        "D. Score distributions (top) and reliability (bottom): clean vs exact noisy, P3A-R",
        x=0.01,
        ha="left",
        color=INK,
        fontsize=12,
        y=1.01,
    )
    return _save(fig, figures / "p3b_d_distribution_calibration.png")


def fig_e(tables, figures):
    reps = pd.read_csv(tables / "p3b_finite_shot_replicates.csv")
    m = pd.read_csv(tables / "p3b_exact_metrics.csv")
    m = m[m["model"] == PRIMARY].set_index("condition")
    noise = pd.read_csv(tables / "p3b_noise_matrix.csv").set_index("profile_id")
    conds = list(dict.fromkeys(reps["condition"]))[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.2), sharey=True)
    rng = np.random.default_rng(0)  # plotting jitter only
    for i, cond in enumerate(conds):
        fam = noise.loc[cond, "g1_family"]
        color = FAMILIES.get(fam, ("", INK2))[1]
        r = reps[reps["condition"] == cond]
        jitter = rng.uniform(-0.18, 0.18, len(r))
        axes[0].scatter(
            r["delta_auprc_vs_shot_clean"],
            i + jitter,
            s=14,
            color=color,
            alpha=0.8,
            edgecolor="none",
        )
        axes[1].scatter(
            r["spearman_vs_exact_clean"], i + jitter, s=14, color=color, alpha=0.8, edgecolor="none"
        )
        exact_d = 0.0 if cond == "clean" else m.loc[cond, "delta_auprc"]
        exact_r = 1.0 if cond == "clean" else m.loc[cond, "spearman"]
        axes[0].plot(exact_d, i, "D", color=INK, markersize=6, markeredgecolor=SURFACE)
        axes[1].plot(exact_r, i, "D", color=INK, markersize=6, markeredgecolor=SURFACE)
    axes[0].axvline(0, color=AXIS, linewidth=1)
    axes[0].set_yticks(range(len(conds)), conds)
    axes[0].set_xlabel("ΔAUPRC: finite-shot noisy − finite-shot clean (same replicate)")
    axes[1].set_xlabel("Spearman ρ of finite-shot scores vs exact clean scores")
    axes[0].plot([], [], "o", color=MUTED, label="replicate (1,024 shots), 20 per condition")
    axes[0].plot([], [], "D", color=INK, label="exact (Stage 1) value")
    axes[0].legend(loc="upper left", bbox_to_anchor=(0.0, -0.09), fontsize=8.5)
    fig.suptitle(
        "E. Finite-shot variability (O07 pilot: 1,024 shots × 20 replicates; not final protocol)",
        x=0.01,
        ha="left",
        color=INK,
        fontsize=12,
        y=1.01,
    )
    return _save(fig, figures / "p3b_e_finite_shot.png")


def main() -> int:
    root = repo_root()
    tables, figures = root / "results" / "tables", root / "results" / "figures"
    for fn in (fig_a, fig_b, fig_c, fig_d, fig_e):
        print(fn(tables, figures).relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
