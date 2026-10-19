"""Phase 5A figures A-D, drawn only from the committed aggregate tables.

Usage: uv run python scripts/make_p5a_figures.py

Palette: reference categorical slots in fixed order for the three feature sets
(top4, next4, pca4); ansatz family is a secondary encoding (marker shape). The
heatmap uses one sequential hue. The CSVs are the table view.
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.transforms import blended_transform_factory  # noqa: E402

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
FEATURES = {
    "top4": ("top-4 ANOVA", BLUE),
    "next4": ("ANOVA ranks 5-8", ORANGE),
    "pca4": ("PCA-4", AQUA),
}
FAMILY_MARKER = {"real_amplitudes": "o", "efficient_su2": "s"}
FAMILY_NAME = {"real_amplitudes": "RealAmplitudes", "efficient_su2": "EfficientSU2"}

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


def _title(fig, text, y=1.02):
    fig.suptitle(text, x=0.01, ha="left", color=INK, fontsize=12, y=y)


def _load(tables):
    cand = pd.read_csv(tables / "p5a_candidates.csv")
    met = pd.read_csv(tables / "p5a_pool_metrics.csv")
    pool = met[met.role == "candidate"].merge(
        cand[["model_id", "features", "encoding", "ansatz", "family", "reps", "readout"]],
        on="model_id",
    )
    ref = met[met.role.isin(["anchor", "control"])]
    meta = json.loads((tables / "p5a_metadata.json").read_text())
    return cand, pool, ref, meta


def _ref_lines(ax, ref, meta, horizontal=False):
    prev = meta["context"]["prevalence"]
    lines = [(10 * prev, "qualification floor: 10× prevalence (on CI low)", MUTED, (0, (2, 2)))]
    for _, r in ref.iterrows():
        name = "P3A-R anchor" if r.role == "anchor" else r.model_id
        lines.append((r.auprc, name, INK2 if r.role == "anchor" else MUTED, (0, (5, 3))))
    for v, label, color, style in lines:
        if horizontal:
            ax.axhline(v, color=color, linewidth=1, linestyle=style)
            ax.text(
                ax.get_xlim()[1],
                v,
                f" {label} {v:.3f}",
                color=color,
                fontsize=7.5,
                va="center",
                ha="left",
            )
        else:
            ax.axvline(v, color=color, linewidth=1, linestyle=style)


def fig_a(tables, figures):
    _, pool, ref, meta = _load(tables)
    pool = pool.sort_values("auprc").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    for f, (label, color) in FEATURES.items():
        for fam, marker in FAMILY_MARKER.items():
            d = pool[(pool.features == f) & (pool.family == fam)]
            ax.vlines(
                d.index, d.auprc_ci_low, d.auprc_ci_high, color=color, alpha=0.35, linewidth=1
            )
            ax.plot(
                d.index,
                d.auprc,
                marker,
                color=color,
                markersize=6,
                markeredgecolor=SURFACE,
                linestyle="none",
                label=f"{label}, {FAMILY_NAME[fam]}",
            )
    ax.set_xlim(-1, len(pool) + 0.5)
    ax.set_xticks([])
    ax.set_xlabel(f"qualified pool models, sorted by clean AUPRC (n = {len(pool)})")
    ax.set_ylabel("clean vqc_val AUPRC (bar: 95% bootstrap CI)")
    _ref_lines(ax, ref, meta, horizontal=True)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    _title(fig, "A. Clean AUPRC across the frozen Phase 5A pool (47 frauds in vqc_val)")
    return _save(fig, figures / "p5a_a_auprc.png")


def fig_b(tables, figures):
    mat = pd.read_csv(tables / "p5a_spearman_matrix.csv").set_index("model_id")
    cand = pd.read_csv(tables / "p5a_candidates.csv").set_index("model_id")
    ids = list(mat.index)
    cmap = LinearSegmentedColormap.from_list("seq_blue", ["#f3f7fc", "#9cc3ec", BLUE, "#123d70"])
    fig = plt.figure(figsize=(11, 10))
    ax = fig.add_axes([0.12, 0.08, 0.72, 0.8])
    strip = fig.add_axes([0.12, 0.885, 0.72, 0.02])
    im = ax.imshow(
        mat.to_numpy(),
        cmap=cmap,
        vmin=float(np.nanmin(mat.to_numpy())),
        vmax=1,
        interpolation="nearest",
    )
    ax.set_xticks([])
    ax.set_yticks(range(len(ids)), [i.replace("p5a-", "") for i in ids], fontsize=5.5)
    ax.grid(False)
    colors = [FEATURES[cand.loc[i, "features"]][1] if i in cand.index else INK for i in ids]
    strip.imshow([[matplotlib.colors.to_rgb(c) for c in colors]], aspect="auto")
    strip.set_xticks([])
    strip.set_yticks([])
    strip.set_title("feature set (black = P3A-R anchor)", loc="left", fontsize=8.5, color=INK2)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("Spearman ρ of clean vqc_val scores", color=INK2)
    for label, color in FEATURES.values():
        ax.plot([], [], "s", color=color, label=label)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 0.12), fontsize=8)
    fig.suptitle(
        "B. Pairwise prediction correlation, average-linkage clustered on 1 − ρ",
        x=0.12,
        ha="left",
        color=INK,
        fontsize=12,
        y=0.95,
    )
    return _save(fig, figures / "p5a_b_correlation.png")


def fig_c(tables, figures):
    _, pool, ref, meta = _load(tables)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), sharey=True)
    rng = np.random.default_rng(0)  # plotting jitter only
    for ax, col, label in zip(
        axes,
        ("trainable_parameters", "noisy_depth"),
        ("trainable parameters", "noisy-gate depth of the transpiled circuit"),
        strict=True,
    ):
        for f, (_, color) in FEATURES.items():
            for fam, marker in FAMILY_MARKER.items():
                d = pool[(pool.features == f) & (pool.family == fam)]
                ax.plot(
                    d[col] + rng.uniform(-0.25, 0.25, len(d)),
                    d.auprc,
                    marker,
                    color=color,
                    markersize=6,
                    markeredgecolor=SURFACE,
                    alpha=0.9,
                    linestyle="none",
                )
        ax.set_xlabel(label)
    axes[0].set_ylabel("clean vqc_val AUPRC")
    for flab, color in FEATURES.values():
        axes[0].plot([], [], "o", color=color, label=flab)
    axes[0].plot([], [], "o", color=MUTED, label="RealAmplitudes")
    axes[0].plot([], [], "s", color=MUTED, label="EfficientSU2")
    axes[0].legend(loc="upper left", fontsize=8)
    _title(fig, "C. Circuit complexity vs clean performance (qualified pool; jittered)")
    return _save(fig, figures / "p5a_c_complexity.png")


def fig_d(tables, figures):
    _, pool, ref, meta = _load(tables)
    pool = pool.assign(ansatz_depth=pool.ansatz)
    axes_def = [
        ("features", ["top4", "next4", "pca4"]),
        ("encoding", ["e3", "e2", "s5"]),
        ("ansatz_depth", ["ra1", "ra2", "esu1", "esu2"]),
        ("readout", ["parity", "mean_z"]),
    ]
    fig, axes = plt.subplots(
        1, 4, figsize=(14, 4.4), sharey=True, gridspec_kw={"width_ratios": [3, 3, 4, 2]}
    )
    rng = np.random.default_rng(1)  # plotting jitter only
    for ax, (axis, levels) in zip(axes, axes_def, strict=True):
        for i, lvl in enumerate(levels):
            d = pool[pool[axis] == lvl]
            colors = [FEATURES[f][1] for f in d.features]
            ax.scatter(
                i + rng.uniform(-0.18, 0.18, len(d)),
                d.auprc,
                s=22,
                c=colors,
                edgecolor=SURFACE,
                linewidth=0.6,
                zorder=2,
            )
            if len(d):
                ax.hlines(d.auprc.median(), i - 0.3, i + 0.3, color=INK, linewidth=2, zorder=3)
                ax.text(
                    i,
                    0.99,
                    f"n={len(d)}",
                    transform=blended_transform_factory(ax.transData, ax.transAxes),
                    ha="center",
                    va="top",
                    fontsize=7.5,
                    color=MUTED,
                )
        ax.set_xticks(range(len(levels)), levels)
        ax.set_title(axis.replace("_", " "), loc="left", pad=14)
        ax.set_xlim(-0.6, len(levels) - 0.4)
    axes[0].set_ylabel("clean vqc_val AUPRC (bar: median)")
    for flab, color in FEATURES.values():
        axes[-1].plot([], [], "o", color=color, label=flab)
    fig.legend(
        *axes[-1].get_legend_handles_labels(),
        loc="lower center",
        ncol=3,
        fontsize=8.5,
        bbox_to_anchor=(0.5, -0.08),
    )
    _title(
        fig, "D. Structural family vs clean performance (qualified pool; dot colour = feature set)"
    )
    return _save(fig, figures / "p5a_d_families.png")


def main() -> int:
    root = repo_root()
    tables, figures = root / "results" / "tables", root / "results" / "figures"
    for fn in (fig_a, fig_b, fig_c, fig_d):
        print(fn(tables, figures).relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
