"""Phase 5B figures A-F, drawn only from the committed aggregate tables (train/val; test sealed).

Usage: uv run python scripts/make_p5b_figures.py

Palette: actions use the validated reference slots in fixed order (A1 blue, A2 orange,
A3 aqua, A4 yellow); A0 (no intervention) is a neutral grey. Low-contrast slots carry
legends; the CSVs are the table view. Condition labels appear only in figures (offline
metadata), never as controller features.
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

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
ACTIONS = ["A0", "A1", "A2", "A3", "A4"]
COLOR = {"A0": "#d6d5ce", "A1": BLUE, "A2": ORANGE, "A3": AQUA, "A4": YELLOW, "RM9": MAGENTA}
LABEL = {
    "A0": "A0 none",
    "A1": "A1 readout",
    "A2": "A2 ZNE",
    "A3": "A3 combined",
    "A4": "A4 extra shots (3×)",
    "RM9": "RM9 (9×, diagnostic)",
}
MARK = {"A0": "o", "A1": "s", "A2": "D", "A3": "^", "A4": "v", "RM9": "P"}
CONDS = [
    "clean",
    "ro-sym-high",
    "ar-020",
    "ar-050",
    "dep-high",
    "th-high",
    "comb-medium",
    "comb-high",
]

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


def _legend(fig, keys, y=-0.05, ncol=5):
    for k in keys:
        plt.plot([], [], "s", color=COLOR[k], label=LABEL[k])
    fig.legend(loc="lower center", ncol=ncol, fontsize=8.5, bbox_to_anchor=(0.5, y))


def _outcomes(tables):
    parts = [
        pd.read_csv(tables / f)
        for f in (
            "p5b_context_outcomes_train_s1024.csv",
            "p5b_context_outcomes_train_s4096.csv",
            "p5b_context_outcomes_val.csv",
        )
    ]
    split = ["train", "train", "val"]
    return pd.concat([p.assign(split=s) for p, s in zip(parts, split, strict=True)])


def _pref(tables):
    return pd.concat(
        [
            pd.read_csv(tables / f"p5b_preferred_actions_{s}.csv").assign(split=s)
            for s in ("train", "val")
        ]
    )


def fig_a(tables, figures):
    p = _pref(tables)
    static = pd.read_csv(tables / "p5b_static_features.csv").set_index("model_id")
    p["col"] = p.condition + " | " + p.arm
    cols = [f"{c} | {a}" for a in ("s1024", "s4096") for c in CONDS]
    order = (
        p[["model_id", "split"]]
        .drop_duplicates()
        .assign(struct=lambda d: d.model_id.map(static.struct_id))
        .sort_values(
            ["split", "struct", "model_id"],
            key=lambda s: s.map({"train": 0, "val": 1}) if s.name == "split" else s,
        )
    )
    mat = p.pivot_table(index="model_id", columns="col", values="preferred", aggfunc="first")
    mat = mat.loc[order.model_id, cols]
    codes = mat.replace({a: i for i, a in enumerate(ACTIONS)}).to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(13, 12))
    ax.imshow(
        codes,
        cmap=ListedColormap([COLOR[a] for a in ACTIONS]),
        vmin=-0.5,
        vmax=4.5,
        aspect="auto",
        interpolation="nearest",
    )
    ax.set_xticks(range(len(cols)), [c.replace(" | ", "\n") for c in cols], fontsize=7, rotation=90)
    ax.set_yticks(range(len(mat)), [m.replace("p5a-", "") for m in mat.index], fontsize=6)
    ax.axvline(7.5, color=INK, linewidth=1.2)
    n_train = int((order.split == "train").sum())
    ax.axhline(n_train - 0.5, color=INK, linewidth=1.2)
    ax.text(16.2, n_train / 2, "train (ctrl_train)", rotation=90, va="center", color=INK2)
    ax.text(
        16.2,
        n_train + (len(mat) - n_train) / 2,
        "val (ctrl_val)",
        rotation=90,
        va="center",
        color=INK2,
    )
    ax.grid(False)
    _legend(fig, ACTIONS, y=-0.03)
    _title(
        fig,
        "A. Preferred action (cost-aware Oracle, Brier) per model × context; "
        "test structures sealed",
        y=0.92,
    )
    return _save(fig, figures / "p5b_a_preferred_heatmap.png")


def fig_b(tables, figures):
    o = _outcomes(tables)
    b = o.pivot_table(
        index=["split", "model_id", "condition", "arm"], columns="action", values="brier"
    ).reset_index()
    fig, axes = plt.subplots(2, 2, figsize=(14, 7.5), sharey=False)
    rng = np.random.default_rng(0)  # plotting jitter only
    for ax, a in zip(axes.ravel(), ACTIONS[1:], strict=True):
        for i, c in enumerate(CONDS):
            for arm, off, fill in (("s1024", -0.17, True), ("s4096", 0.17, False)):
                d = b[(b.condition == c) & (b.arm == arm)]
                rel = (d[a] - d["A0"]) / d["A0"]
                ax.scatter(
                    i + off + rng.uniform(-0.07, 0.07, len(d)),
                    rel,
                    s=12,
                    color=COLOR[a] if fill else SURFACE,
                    edgecolor=COLOR[a],
                    linewidth=0.8,
                    zorder=2,
                )
        ax.axhline(0, color=AXIS, linewidth=1)
        ax.axhline(-0.10, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
        ax.set_xticks(range(len(CONDS)), CONDS, fontsize=8, rotation=20)
        ax.set_title(f"{LABEL[a]} vs A0", loc="left")
        ax.set_ylabel("relative ΔBrier (context mean)")
    axes[0, 0].plot([], [], "o", color=MUTED, label="filled: 1,024 shots; hollow: 4,096")
    axes[0, 0].plot([], [], color=MUTED, linestyle=(0, (3, 3)), label="−10% (preference tolerance)")
    axes[0, 0].legend(loc="lower left", fontsize=8)
    _title(
        fig,
        "B. Brier change by action and condition across models "
        "(train + val contexts; each dot = one model)",
    )
    fig.tight_layout()
    return _save(fig, figures / "p5b_b_delta_brier.png")


def fig_c(tables, figures):
    par = pd.read_csv(tables / "p5b_pareto.csv")
    par = par[(par.split == "train")]
    fig, axes = plt.subplots(2, 4, figsize=(15, 7.2), sharex=True)
    for ax, c in zip(axes.ravel(), CONDS, strict=True):
        for arm, fill in (("s1024", True), ("s4096", False)):
            d = par[(par.condition == c) & (par.arm == arm)].set_index("action")
            for a in ACTIONS:
                ax.plot(
                    d.loc[a, "shots_per_inference"],
                    d.loc[a, "brier"],
                    MARK[a],
                    color=COLOR[a] if a != "A0" else INK2,
                    markersize=8,
                    markerfacecolor=(COLOR[a] if a != "A0" else INK2) if fill else SURFACE,
                    markeredgewidth=1.5,
                )
            front = d[d.pareto_optimal].sort_values("shots_per_inference")
            ax.plot(
                front.shots_per_inference,
                front.brier,
                color=MUTED,
                linestyle="-" if fill else (0, (3, 2)),
                linewidth=1,
                zorder=0,
            )
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_title(c, loc="left")
    for ax in axes[1]:
        ax.set_xlabel("shots per logical inference (log₂)")
    for ax in axes[:, 0]:
        ax.set_ylabel("mean Brier over train models (log)")
    for a in ACTIONS:
        axes[0, 0].plot([], [], MARK[a], color=COLOR[a] if a != "A0" else INK2, label=LABEL[a])
    axes[0, 0].plot([], [], color=MUTED, label="Pareto front (filled 1,024 / dashed 4,096)")
    fig.legend(
        *axes[0, 0].get_legend_handles_labels(),
        loc="lower center",
        ncol=6,
        fontsize=8.5,
        bbox_to_anchor=(0.5, -0.05),
    )
    _title(fig, "C. Reliability vs quantum cost (train contexts; probe cost excluded)")
    fig.tight_layout()
    return _save(fig, figures / "p5b_c_pareto.png")


def fig_d(tables, figures):
    f = pd.concat([pd.read_csv(tables / f"p5b_context_features_{s}.csv") for s in ("train", "val")])
    o = _outcomes(tables)
    b = o.pivot_table(
        index=["model_id", "condition", "arm"], columns="action", values="brier"
    ).reset_index()
    m = f.merge(b, on=["model_id", "condition", "arm"])
    cmap = dict(
        zip(
            CONDS,
            ["#d6d5ce", BLUE, "#8fb9ea", "#16467e", ORANGE, YELLOW, AQUA, "#0b6b49"],
            strict=True,
        )
    )
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    specs = [
        ("probe_readout_error_mean_mean", "A1", "readout probe: mean error p̂"),
        ("probe_gate_contraction_mean", "A2", "gate probe: contraction |O|₃ / |O|₁"),
        ("probe_gate_contraction_mean", "A4", "gate probe: contraction |O|₃ / |O|₁"),
    ]
    for ax, (feat, a, xl) in zip(axes, specs, strict=True):
        for c in CONDS:
            d = m[m.condition == c]
            ax.scatter(
                d[feat],
                (d[a] - d["A0"]) / d["A0"],
                s=12,
                color=cmap[c],
                edgecolor=SURFACE,
                linewidth=0.4,
                label=c,
            )
        ax.axhline(0, color=AXIS, linewidth=1)
        ax.set_xlabel(xl)
        ax.set_ylabel(f"relative ΔBrier, {LABEL[a]} vs A0")
    axes[0].legend(
        loc="lower left",
        fontsize=7.5,
        ncol=2,
        title="condition (offline label)",
        title_fontsize=7.5,
    )
    _title(fig, "D. Pre-action probe features vs realised benefit (context means; train + val)")
    fig.tight_layout()
    return _save(fig, figures / "p5b_d_probes_vs_benefit.png")


def _stacked(ax, frame, keycol, keys):
    left = np.zeros(len(keys))
    for a in ACTIONS:
        vals = np.array(
            [frame[(frame[keycol] == k) & (frame.action == a)].share_preferred.sum() for k in keys]
        )
        ax.barh(
            range(len(keys)),
            vals,
            left=left,
            color=COLOR[a],
            edgecolor=SURFACE,
            linewidth=1,
            height=0.7,
        )
        left += vals
    ax.set_yticks(range(len(keys)), keys)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)


def fig_e(tables, figures):
    fam = pd.read_csv(tables / "p5b_preferred_by_family.csv")
    fam = fam[fam.split == "train"]
    axes_list = ["feature_set", "encoding_family", "ansatz", "ansatz_reps", "readout_observable"]
    fig, axes = plt.subplots(
        1, len(axes_list), figsize=(18, 3.6), sharex=True, gridspec_kw={"wspace": 0.75}
    )
    for ax, axis in zip(axes, axes_list, strict=True):
        d = fam[fam.axis == axis]
        keys = list(dict.fromkeys(d.level))
        _stacked(ax, d.rename(columns={"level": "key"}), "key", keys)
        ax.set_title(axis.replace("_", " "), loc="left")
        ax.set_xlabel("share of contexts")
    _legend(fig, ACTIONS, y=-0.12)
    _title(fig, "E. Preferred-action frequencies by structural family (train contexts)", y=1.05)
    return _save(fig, figures / "p5b_e_family.png")


def fig_f(tables, figures):
    e = pd.read_csv(tables / "p5b_preferred_by_condition.csv")
    e = e[e.split == "train"]
    agree = pd.read_csv(tables / "p5b_preferred_by_arm.csv")
    agree = agree[agree.model_condition_pairs.notna()].set_index("split")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for ax, arm in zip(axes, ("s1024", "s4096"), strict=True):
        d = e[e.arm == arm]
        _stacked(ax, d, "condition", CONDS)
        ax.set_title(f"{arm.replace('s', '')} shots per circuit", loc="left")
        ax.set_xlabel("share of train models")
    tr = agree.loc["train", "same_preferred_both_arms"]
    axes[1].text(
        1.0,
        -0.18,
        f"same preferred action at both budgets: {tr:.0%} of (model, condition) pairs (train)",
        transform=axes[1].transAxes,
        ha="right",
        color=INK2,
        fontsize=9,
    )
    _legend(fig, ACTIONS, y=-0.1)
    _title(fig, "F. Preferred action at 1,024 vs 4,096 shots per circuit (train contexts)")
    return _save(fig, figures / "p5b_f_shot_budget.png")


def main() -> int:
    root = repo_root()
    tables, figures = root / "results" / "tables", root / "results" / "figures"
    meta = json.loads((tables / "p5b_metadata.json").read_text())
    print("G3B:", meta["g3b"]["verdict"])
    for fn in (fig_a, fig_b, fig_c, fig_d, fig_e, fig_f):
        print(fn(tables, figures).relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
