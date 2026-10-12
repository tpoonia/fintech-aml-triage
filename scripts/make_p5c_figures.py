"""Phase 5C figures from committed tables only (deterministic).

Usage: uv run python scripts/make_p5c_figures.py

Figure A (registered design) needs only results/tables/p5c_design.csv and can be drawn before
any outcome exists. The outcome figures are drawn when the registered analysis tables exist.
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from qtrace.config import repo_root

ROOT = Path(os.environ.get("QTRACE_FIG_ROOT", repo_root()))  # override only for tests
T, F = ROOT / "results" / "tables", ROOT / "results" / "figures"
REGION_COLOR = {
    "near_clean": "#9aa5b1",
    "readout_dominated": "#2f6fb0",
    "gate_dominated": "#c0612b",
    "mixed": "#6b4fa0",
}
REGION_LABEL = {
    "near_clean": "near-clean",
    "readout_dominated": "readout-dominated",
    "gate_dominated": "gate-dominated",
    "mixed": "mixed",
}


def figure_design(design: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    plots = design.groupby("gate_plot")[["s_dep", "s_th"]].first()
    ax = axes[0]
    ax.fill_between([0, 1], 0, 1, color="#e8ecf0", zorder=0, label="both below the low anchor")
    ax.scatter(plots.s_dep, plots.s_th, s=70, color="#444", zorder=3)
    for pid, r in plots.iterrows():
        ax.annotate(pid, (r.s_dep, r.s_th), xytext=(5, 4), textcoords="offset points", fontsize=8)
    for v in (1, 2, 3):
        ax.axvline(v, color="#ccc", lw=0.8, zorder=1)
        ax.axhline(v, color="#ccc", lw=0.8, zorder=1)
    ax.set(
        xlim=(-0.1, 3.1),
        ylim=(-0.1, 3.1),
        xlabel="depolarizing severity s_dep (1/2/3 = low/medium/high anchor)",
        ylabel="thermal severity s_th",
        title="A. 17 gate-noise plots (16 maximin LHS + gate-free)",
    )
    ax = axes[1]
    for reg in REGION_COLOR:
        g = design[design.region == reg]
        ax.scatter(
            g.s_ro, g.alpha, s=36, color=REGION_COLOR[reg], label=f"{REGION_LABEL[reg]} ({len(g)})"
        )
    ax.axvline(1, color="#ccc", lw=0.8)
    ax.set(
        xlim=(-0.1, 3.1),
        ylim=(-0.02, 0.52),
        xlabel="readout severity s_ro (mean error 0 / 0.005 / 0.02 / 0.05)",
        ylabel="readout asymmetry α (synthetic component)",
        title="B. 68 noise points: 4 readout settings per gate plot",
    )
    ax.legend(
        title="region (true severities; offline label)",
        fontsize=8,
        title_fontsize=8,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=4,
        frameon=False,
    )
    axes[0].legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16), frameon=False)
    fig.suptitle("Phase 5C registered continuous mixed-noise design (anchor-severity scale)", y=1.0)
    fig.tight_layout()
    fig.savefig(F / "p5c_a_design.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


ACTION_COLOR = {
    "A0": "#9aa5b1",
    "A1": "#2f6fb0",
    "A4": "#d9a400",
    "A2": "#c0612b",
    "A3": "#6b4fa0",
}
ACTION_LABEL = {
    "A0": "A0 none",
    "A1": "A1 readout",
    "A4": "A4 extra shots",
    "A2": "A2 ZNE",
    "A3": "A3 combined",
}
ARMS = ("s256", "s1024", "s4096")


def figure_preferred_map(by_point: dict[str, pd.DataFrame]) -> None:
    """B: majority preferred action over the noise space; marker size = majority share."""
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), sharex=True, sharey=True)
    for i, split in enumerate(("train", "val")):
        d = by_point[split]
        for j, arm in enumerate(ARMS):
            ax = axes[i, j]
            g = d[d.arm == arm]
            gate = np.maximum(g.s_dep, g.s_th)
            for a, col in ACTION_COLOR.items():
                k = g.majority == a
                ax.scatter(
                    g.s_ro[k],
                    gate[k],
                    s=20 + 140 * g.majority_share[k],
                    color=col,
                    edgecolor="white",
                    linewidth=0.6,
                    label=ACTION_LABEL[a],
                )
            mixed = g.distinct_actions > 1
            ax.scatter(
                g.s_ro[mixed],
                gate[mixed],
                s=8,
                color="black",
                marker="x",
                linewidth=0.8,
                label="models disagree",
            )
            ax.set_title(f"{split} models, {arm}", fontsize=10)
            if i == 1:
                ax.set_xlabel("readout severity s_ro")
            if j == 0:
                ax.set_ylabel("gate severity max(s_dep, s_th)")
    from matplotlib.lines import Line2D

    handles = [
        Line2D([], [], ls="", marker="o", ms=9, color=col, label=ACTION_LABEL[a])
        for a, col in ACTION_COLOR.items()
    ]
    handles.append(Line2D([], [], ls="", marker="x", ms=6, color="black", label="models disagree"))
    fig.legend(handles=handles, loc="lower center", ncol=6, frameon=False, fontsize=9)
    fig.suptitle(
        "B. Cost-aware preferred action (Oracle, eps = 0.10) by noise point: majority over models;"
        " larger = more agreement",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fig.savefig(F / "p5c_b_preferred_map.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


POLICY_ORDER = [
    "always_A0",
    "always_A1",
    "always_A4",
    "always_A2",
    "always_A3",
    "R_cat",
    "R_thr",
    "R_obs",
    "oracle",
]


def figure_policies(pe: pd.DataFrame) -> None:
    """C: validation failure, material failure and total shots per policy (all budgets)."""
    d = pe[(pe.split == "val") & (pe.arm == "all")].set_index("policy").loc[POLICY_ORDER]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    x = np.arange(len(d))
    for ax, col, title in (
        (axes[0], "failure", "failure (choice != p*)"),
        (axes[1], "material_failure", "material failure"),
    ):
        ax.bar(x, d[col], color="#6b7f99")
        lo = "fail_ci_lo" if col == "failure" else "material_ci_lo"
        hi = lo.replace("_lo", "_hi")
        if lo in d:
            ok = d[lo].notna()
            ax.errorbar(
                x[ok.to_numpy()],
                d[col][ok],
                yerr=[d[col][ok] - d[lo][ok], d[hi][ok] - d[col][ok]],
                fmt="none",
                color="black",
                capsize=3,
            )
        ax.set_title(f"{title} (val)", fontsize=10)
        ax.set_ylim(0, 1)
    axes[2].bar(
        x,
        d.mean_total_shots_per_inference / d.mean_total_shots_per_inference["always_A0"],
        color="#9a7b4f",
    )
    axes[2].set_title("total shots per inference / A0 (incl. probes)", fontsize=10)
    for ax in axes:
        ax.set_xticks(x, [p.replace("always_", "") for p in POLICY_ORDER], rotation=45, ha="right")
    fig.suptitle(
        "C. Policies on held-out validation models (95% two-stage cluster CIs)", fontsize=11
    )
    fig.tight_layout()
    fig.savefig(F / "p5c_c_policies.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def figure_residual(ss: pd.DataFrame, meta: dict) -> None:
    """D: model dependence at fixed noise (noise-only ceiling per structure) and label noise."""
    d = ss[(ss.arm == "all") & ss.noise_only_miss.notna()].sort_values(["split", "struct_id"])
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [3, 1.3]})
    ax = axes[0]
    colors = d.split.map({"train": "#6b7f99", "val": "#c0612b"})
    ax.bar(np.arange(len(d)), d.noise_only_miss, color=colors)
    ax.axhline(0.05, color="black", lw=0.8, ls="--")
    ax.set_xticks(np.arange(len(d)), d.struct_id, rotation=60, ha="right", fontsize=8)
    ax.set_ylabel("share of contexts where p* differs\nfrom the best action at that noise point")
    ax.set_title(
        "model dependence at a fixed noise point, per structure (grey train, orange val)",
        fontsize=10,
    )
    ax = axes[1]
    m = meta["g3c"]["metrics"]
    vals = {
        "best rule\nfailure": m["best_rule_failure_val"],
        "best rule\nmaterial": m["best_rule_material_failure_val"],
        "noise-only\nceiling": m["noise_only_failure_val"],
        "label\ninstability": m["label_instability_val"],
    }
    ax.bar(
        range(len(vals)), list(vals.values()), color=["#6b7f99", "#4a5a70", "#c0612b", "#9aa5b1"]
    )
    ax.set_xticks(range(len(vals)), list(vals), fontsize=8)
    ax.set_title("validation residual vs replicate noise", fontsize=10)
    fig.suptitle(f"D. Residual decision structure (G3C = {meta['g3c']['verdict']})", fontsize=11)
    fig.tight_layout()
    fig.savefig(F / "p5c_d_residual.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def figure_sensitivity(eps: pd.DataFrame, budget: pd.DataFrame) -> None:
    """E: tolerance sensitivity of shares and rule failures; between-budget disagreement."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    d = eps[eps.split == "val"].sort_values("eps")
    for a, col in ACTION_COLOR.items():
        axes[0].plot(d.eps, d[f"share_{a}"], marker="o", color=col, label=ACTION_LABEL[a])
    for r, ls in (("R_cat", ":"), ("R_thr", "--"), ("R_obs", "-.")):
        axes[0].plot(d.eps, d[f"{r}_failure"], ls=ls, color="black", label=f"{r} failure")
    axes[0].set(
        xlabel="tolerance eps",
        ylabel="share / failure (val)",
        title="preferred-action shares and rule failure vs eps",
    )
    axes[0].legend(fontsize=7, ncol=2)
    b = budget.copy()
    b["pair"] = b.arm_a + " vs " + b.arm_b
    piv = b.pivot_table(index="pair", columns="split", values="disagreement")
    piv.plot.bar(ax=axes[1], color={"train": "#6b7f99", "val": "#c0612b"}, rot=0)
    axes[1].set(ylabel="share of (model, point) pairs", title="p* changes with the shot budget")
    fig.suptitle("E. Sensitivity: tolerance and shot budget", fontsize=11)
    fig.tight_layout()
    fig.savefig(F / "p5c_e_sensitivity.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    design = pd.read_csv(T / "p5c_design.csv")
    figure_design(design)
    if not (T / "p5c_metadata.json").exists():
        print("p5c_a_design.png written; outcome figures wait for the registered analysis")
        return 0
    import json

    meta = json.loads((T / "p5c_metadata.json").read_text())
    by_point = {s: pd.read_csv(T / f"p5c_preferred_by_point_{s}.csv") for s in ("train", "val")}
    figure_preferred_map(by_point)
    figure_policies(pd.read_csv(T / "p5c_policy_eval.csv"))
    figure_residual(pd.read_csv(T / "p5c_structure_summary.csv"), meta)
    figure_sensitivity(
        pd.read_csv(T / "p5c_eps_sensitivity.csv"), pd.read_csv(T / "p5c_budget_effect.csv")
    )
    print("figures A-E written")
    return 0


if __name__ == "__main__":
    np.seterr(all="ignore")
    raise SystemExit(main())
