"""Phase 4 figures A-E, drawn only from the committed aggregate tables.

Usage: uv run python scripts/make_p4_figures.py

Palette: reference categorical slots in fixed order, one per action (A1 readout,
A2 ZNE, A3 combined, RM3 shot-matched None, RM9 exposure-matched None); A0 (None)
is neutral ink. Validated 5-slot adjacent (scripts/validate_palette.js, light
surface). Low-contrast slots carry legends and marker shapes; negative-control
cells are drawn hollow; the CSVs are the table view.
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
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
ACTIONS = {  # vector -> (label, color, marker)
    "A0": ("A0 None", INK2, "o"),
    "A1": ("A1 Readout mitigation", BLUE, "s"),
    "A2": ("A2 ZNE (linear)", ORANGE, "D"),
    "A3": ("A3 Combined", AQUA, "^"),
    "RM3": ("RM3 None, 3x shots", YELLOW, "v"),
    "RM9": ("RM9 None, 9x shots", MAGENTA, "P"),
}
NAMES = {
    "clean": "clean",
    "ro-sym-high": "sym. readout high",
    "ar-020": "synth. asym. readout med.",
    "ar-050": "synth. asym. readout high",
    "dep-high": "depolarizing high",
    "th-high": "thermal high",
    "comb-medium": "combined medium",
    "comb-high": "combined high",
}
ARMS = {"s1024": "1,024 shots/circuit", "s4096": "4,096 shots/circuit"}

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


def _labels(tables):
    m = pd.read_csv(tables / "p4_noise_action_matrix.csv").set_index("condition")
    return {(c, a): m.loc[c, f"{a}_label"] for c in m.index for a in ("A1", "A2", "A3")}


def _delta_panel(ax, d, pairs, conds, labels, metric):
    offsets = np.linspace(-0.27, 0.27, len(pairs))
    for off, (a, ref) in zip(offsets, pairs, strict=True):
        label, color, marker = ACTIONS[a]
        for i, cond in enumerate(conds):
            r = d[
                (d.condition == cond)
                & (d.action == a)
                & (d.comparator == ref)
                & (d.metric == metric)
            ]
            if r.empty:
                continue
            r = r.iloc[0]
            y = i + off
            ax.hlines(y, r.ci_low, r.ci_high, color=color, linewidth=1.6)
            hollow = labels.get((cond, a)) == "negative_control"
            ax.plot(
                r.mean_delta,
                y,
                marker,
                color=color,
                markersize=7,
                markerfacecolor=SURFACE if hollow else color,
                markeredgewidth=1.4,
            )
        ax.plot([], [], marker, color=color, label=f"{label} − {ref}")
    ax.axvline(0, color=AXIS, linewidth=1)
    ax.set_yticks(range(len(conds)), [NAMES[c] for c in conds])
    ax.invert_yaxis()


def fig_a(tables, figures):
    d = pd.read_csv(tables / "p4_deltas_vs_none_s1024.csv")
    rm = pd.read_csv(tables / "p4_resource_matched.csv")
    labels = _labels(tables)
    conds = list(NAMES)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.4), sharey=True)
    da = d[d.arm == "s1024"]
    _delta_panel(
        axes[0],
        da,
        [("A1", "A0"), ("A2", "A0"), ("A3", "A0"), ("RM3", "A0")],
        conds,
        labels,
        "auprc",
    )
    axes[0].set_title("vs None (A0), same per-circuit shots", loc="left")
    _delta_panel(
        axes[1],
        rm[rm.arm == "s1024"],
        [("A1", "A0"), ("A2", "RM3"), ("A3", "RM3")],
        conds,
        labels,
        "auprc",
    )
    axes[1].set_title("vs resource-matched None (shot-matched)", loc="left")
    for ax in axes:
        ax.set_xlabel("ΔAUPRC (mean of 20 replicates; bar: two-stage 95% interval)")
        ax.legend(loc="upper left", bbox_to_anchor=(0, -0.12), fontsize=8.5, ncol=2)
    axes[1].text(
        1.0,
        -0.33,
        "hollow marker = negative-control cell",
        transform=axes[1].transAxes,
        ha="right",
        color=MUTED,
        fontsize=8.5,
    )
    _title(
        fig,
        "A. Mitigation effect on AUPRC by noise condition (P3A-R, vqc_val, 1,024 shots/circuit)",
    )
    return _save(fig, figures / "p4_a_auprc.png")


def fig_b(tables, figures):
    s = pd.read_csv(tables / "p4_summary.csv")
    ex = pd.read_csv(tables / "p4_exact_diagnostics.csv")
    clean = ex[(ex.condition == "clean") & (ex.vector == "A0")].iloc[0]
    s = s[s.arm == "s1024"]
    conds = list(NAMES)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.0), sharey=True)
    offsets = dict(zip(("A0", "A1", "A2", "A3"), np.linspace(-0.27, 0.27, 4), strict=True))
    for ax, metric in zip(axes, ("brier", "ece"), strict=True):
        for i, cond in enumerate(conds):
            g = s[s.condition == cond].set_index("vector")
            for v, off in offsets.items():
                label, color, marker = ACTIONS[v]
                ax.plot(
                    [g.loc["A0", metric], g.loc[v, metric]],
                    [i + off] * 2,
                    color=GRID,
                    linewidth=1.2,
                    zorder=1,
                )
                ax.plot(
                    g.loc[v, metric],
                    i + off,
                    marker,
                    color=color,
                    markersize=7,
                    zorder=2,
                    markeredgecolor=SURFACE,
                    label=label if i == 0 else None,
                )
        ax.axvline(clean[metric], color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
        ax.text(
            clean[metric],
            len(conds) - 0.35,
            f" exact clean {clean[metric]:.3f}",
            color=MUTED,
            fontsize=8,
            va="bottom",
        )
        ax.set_xscale("log")
        ax.set_xlabel(
            f"{metric.upper() if metric == 'ece' else 'Brier'} (mean of 20 replicates, log)"
        )
    axes[0].set_yticks(range(len(conds)), [NAMES[c] for c in conds])
    axes[0].invert_yaxis()
    axes[0].legend(loc="upper left", bbox_to_anchor=(0, -0.12), ncol=4, fontsize=8.5)
    axes[0].set_title("Brier score", loc="left")
    axes[1].set_title("Expected calibration error (10 bins)", loc="left")
    _title(fig, "B. Calibration before vs after mitigation (1,024 shots/circuit; lower is better)")
    return _save(fig, figures / "p4_b_calibration.png")


def fig_c(tables, figures):
    s = pd.read_csv(tables / "p4_summary.csv")
    conds = ["ro-sym-high", "ar-050", "dep-high", "comb-high"]
    fig, axes = plt.subplots(2, len(conds), figsize=(15, 7.2), sharex=True)
    for j, cond in enumerate(conds):
        for i, metric in enumerate(("auprc", "brier")):
            ax = axes[i, j]
            for arm, fill in (("s1024", True), ("s4096", False)):
                g = s[(s.condition == cond) & (s.arm == arm)].set_index("vector")
                none = g.loc[["A0", "RM3", "RM9"]]
                ax.plot(
                    none.shots_per_inference,
                    none[metric],
                    color=MUTED,
                    linestyle="-" if fill else (0, (3, 2)),
                    linewidth=1.2,
                    zorder=1,
                )
                for v, (_, color, marker) in ACTIONS.items():
                    ax.plot(
                        g.loc[v, "shots_per_inference"],
                        g.loc[v, metric],
                        marker,
                        color=color,
                        markersize=8,
                        markerfacecolor=color if fill else SURFACE,
                        markeredgewidth=1.5,
                        zorder=2,
                    )
            ax.set_xscale("log", base=2)
            if metric == "brier":
                ax.set_yscale("log")
            if i == 0:
                ax.set_title(NAMES[cond], loc="left")
            if j == 0:
                ax.set_ylabel(
                    "AUPRC (higher is better)"
                    if metric == "auprc"
                    else "Brier (log; lower is better)"
                )
            if i == 1:
                ax.set_xlabel("total shots per logical inference (log₂)")
    for label, color, marker in ACTIONS.values():
        axes[0, 0].plot([], [], marker, color=color, label=label)
    axes[0, 0].plot(
        [], [], "o", color=INK2, markerfacecolor=INK2, label="filled: 1,024 shots/circuit"
    )
    axes[0, 0].plot(
        [], [], "o", color=INK2, markerfacecolor=SURFACE, label="hollow: 4,096 shots/circuit"
    )
    axes[0, 0].plot([], [], color=MUTED, label="grey line: None at 1x, 3x, 9x shots")
    fig.legend(
        *axes[0, 0].get_legend_handles_labels(),
        loc="lower center",
        ncol=5,
        fontsize=8.5,
        bbox_to_anchor=(0.5, -0.06),
    )
    _title(
        fig, "C. Downstream performance vs quantum cost (means of 20 replicates; P3A-R, vqc_val)"
    )
    return _save(fig, figures / "p4_c_cost.png")


def fig_d(tables, figures):
    rm = pd.read_csv(tables / "p4_resource_matched.csv")
    rm = rm[(rm.comparison_role == "primary") & (rm.applicability != "negative_control")]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    for ax, metric, title in zip(
        axes,
        ("auprc", "brier"),
        ("ΔAUPRC vs resource-matched None", "ΔBrier vs resource-matched None"),
        strict=True,
    ):
        d = rm[rm.metric == metric]
        lo = min(d.mean_delta.min(), 0)
        hi = max(d.mean_delta.max(), 0)
        pad = 0.08 * (hi - lo + 1e-9)
        ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color=AXIS, linewidth=1)
        ax.axhline(0, color=GRID, linewidth=1)
        ax.axvline(0, color=GRID, linewidth=1)
        labelled: set[str] = set()
        for a in ("A1", "A2", "A3"):
            label, color, marker = ACTIONS[a]
            x = d[(d.action == a) & (d.arm == "s1024")].set_index("condition").mean_delta
            y = d[(d.action == a) & (d.arm == "s4096")].set_index("condition").mean_delta
            common = x.index.intersection(y.index)
            ax.plot(
                x[common],
                y[common],
                marker,
                color=color,
                markersize=8,
                markeredgecolor=SURFACE,
                label=label,
                linestyle="none",
            )
            for c in common:
                if c in labelled:
                    continue
                if abs(x[c]) == abs(x).max() or abs(y[c]) == abs(y).max():
                    labelled.add(c)
                    ax.annotate(
                        NAMES[c],
                        (x[c], y[c]),
                        textcoords="offset points",
                        xytext=(6, 4),
                        fontsize=8,
                        color=INK2,
                    )
        ax.set_xlabel("1,024 shots per circuit")
        ax.set_ylabel("4,096 shots per circuit")
        ax.set_title(title, loc="left")
    axes[0].legend(loc="upper left", fontsize=8.5)
    _title(
        fig,
        "D. Mitigation benefit at 1,024 vs 4,096 shots per circuit "
        "(applicable and partial cells; diagonal = equal benefit)",
    )
    return _save(fig, figures / "p4_d_shot_budget.png")


def fig_e(tables, figures):
    cal = pd.read_csv(tables / "p4_calibration_bins.csv")
    hist = pd.read_csv(tables / "p4_score_histogram.csv")
    meta = json.loads((tables / "p4_metadata.json").read_text())
    tau = meta["frozen_tau"]
    conds = list(dict.fromkeys(c for c in cal.condition if c != "clean"))
    fig, axes = plt.subplots(2, len(conds), figsize=(14, 7.2))
    c0 = cal[cal.condition == "clean"]
    h0 = hist[hist.condition == "clean"]
    centers = (h0.bin_lower + h0.bin_upper) / 2
    for j, cond in enumerate(conds):
        top, bottom = axes[0, j], axes[1, j]
        top.step(
            centers,
            h0.legit_count / h0.legit_count.sum(),
            where="mid",
            color=MUTED,
            linestyle=(0, (4, 2)),
            linewidth=1.8,
            label="exact clean",
        )
        bottom.plot([0, 1], [0, 1], color=AXIS, linewidth=1)
        bottom.plot(
            c0.mean_predicted,
            c0.fraction_positive,
            color=MUTED,
            linestyle=(0, (4, 2)),
            marker="o",
            markersize=4,
            linewidth=1.6,
            label="exact clean",
        )
        styles = {
            "A0": ("-", 3.2),
            "A1": ("-", 3.2),
            "A2": ((0, (4, 2)), 1.6),
            "A3": ((0, (1, 1.2)), 2.0),
        }
        shares = {}
        for v in ("A0", "A1", "A2", "A3"):
            label, color, marker = ACTIONS[v]
            style, width = styles[v]
            h = hist[(hist.condition == cond) & (hist.vector == v)]
            shares[v] = (h.legit_count / h.legit_count.sum()).to_numpy()
            top.step(
                centers,
                shares[v],
                where="mid",
                color=color,
                linestyle=style,
                linewidth=width,
                label=label,
            )
            k = cal[(cal.condition == cond) & (cal.vector == v)]
            bottom.plot(
                k.mean_predicted,
                k.fraction_positive,
                color=color,
                marker=marker,
                markersize=5,
                linestyle=style,
                linewidth=width * 0.8,
                label=label,
            )
        clean_share = (h0.legit_count / h0.legit_count.sum()).to_numpy()
        if np.allclose(shares["A1"], clean_share) and np.allclose(shares["A2"], shares["A0"]):
            top.text(
                0.98,
                0.62,
                "exact: A1 = A3 = clean\nA2 = A0 (folding does not\ntouch readout noise)",
                transform=top.transAxes,
                ha="right",
                fontsize=8,
                color=INK2,
            )
        top.axvline(tau, color=INK2, linewidth=0.8, linestyle=":")
        top.set_title(NAMES[cond] + " (exact)", loc="left")
        top.set_xlim(0, 0.7)
        bottom.set_xlim(0, 1)
        bottom.set_ylim(-0.02, 1.02)
        bottom.set_xlabel("score p = (1 − z)/2")
    axes[0, 0].set_ylabel("share of legitimate rows in bin")
    axes[1, 0].set_ylabel("observed fraud rate (10 bins)")
    fig.legend(
        *axes[0, 0].get_legend_handles_labels(),
        loc="lower center",
        ncol=5,
        fontsize=8.5,
        bbox_to_anchor=(0.5, -0.04),
    )
    _title(
        fig,
        "E. Exact score distributions (top; dotted: frozen τ) and reliability (bottom), "
        "before and after mitigation",
    )
    return _save(fig, figures / "p4_e_distributions.png")


def main() -> int:
    root = repo_root()
    tables, figures = root / "results" / "tables", root / "results" / "figures"
    for fn in (fig_a, fig_b, fig_c, fig_d, fig_e):
        print(fn(tables, figures).relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
