"""Final-evaluation figures from committed tables only (PREREG_FINAL.md §8).

Usage: uv run python scripts/make_final_figures.py
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from qtrace.config import repo_root

ROOT = repo_root()
T, F = ROOT / "results" / "tables", ROOT / "results" / "figures"
ORDER = [
    "always_A0",
    "always_A1",
    "always_A4",
    "always_A2",
    "always_A3",
    "R_cat",
    "R_thr",
    "R_obs",
    "L_logistic",
    "L_tree3",
    "L_gbt",
    "L_gbt_benefit",
    "oracle",
]
COLOR = {"always": "#9aa5b1", "R": "#2f6fb0", "L": "#c0612b", "oracle": "#444444"}


SPECIFIC = {
    "R_thr": "#173f73",
    "R_obs": "#7fa7d6",
    "R_cat": "#2f6fb0",
    "L_logistic": "#f0b27a",
    "L_tree3": "#dd8a4a",
    "L_gbt": "#b8541e",
    "L_gbt_benefit": "#7a330d",
}


def _color(p: str) -> str:
    if p in SPECIFIC:
        return SPECIFIC[p]
    return COLOR["always"] if p.startswith("always") else COLOR.get(p.split("_")[0], "#444")


def figure_policies() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.2), sharex=True)
    for i, (env, title) in enumerate(
        (
            ("5c_test", "Phase 5C test (continuous joint noise)"),
            ("5b_test", "Phase 5B test (categorical noise)"),
        )
    ):
        p = pd.read_csv(T / f"final_policies_{env}.csv")
        p = p[p.arm == "all"].set_index("policy").loc[ORDER]
        x = np.arange(len(p))
        cols = [_color(n) for n in p.index]
        for j, (col, label) in enumerate(
            (("failure", "failure (choice != p*)"), ("material_failure", "material failure"))
        ):
            ax = axes[i, j]
            ax.bar(x, p[col], color=cols)
            lo, hi = (
                ("fail_ci_lo", "fail_ci_hi") if j == 0 else ("material_ci_lo", "material_ci_hi")
            )
            ax.errorbar(
                x,
                p[col],
                yerr=[p[col] - p[lo], p[hi] - p[col]],
                fmt="none",
                color="black",
                capsize=2,
                lw=0.8,
            )
            ax.set_ylim(0, 1.02)
            ax.set_title(f"{title}: {label}", fontsize=9)
        ax = axes[i, 2]
        ax.bar(
            x,
            p.mean_total_shots_per_inference / p.loc["oracle"].mean_total_shots_per_inference,
            color=cols,
        )
        ax.axhline(1, color="black", lw=0.8, ls="--")
        ax.set_title(f"{title}: total shots / Oracle", fontsize=9)
    for ax in axes[1]:
        ax.set_xticks(
            np.arange(len(ORDER)),
            [o.replace("always_", "") for o in ORDER],
            rotation=60,
            ha="right",
            fontsize=8,
        )
    fig.suptitle(
        "A. One-time held-out evaluation of frozen policies "
        "(grey: fixed; blue: probe rules, dark = deployable R_thr; orange: learned; "
        "95% two-stage cluster CIs)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(F / "final_a_policies.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def figure_structures() -> None:
    b = pd.read_csv(T / "final_by_structure_5c_test.csv")
    pols = ["always_A3", "R_thr", "R_obs", "L_logistic", "L_tree3", "L_gbt", "L_gbt_benefit"]
    b = b[b.policy.isin(pols)]
    structs = sorted(b.struct_id.unique())
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.4), sharey=False)
    w = 0.8 / len(pols)
    for j, (col, label) in enumerate(
        (("failure", "failure"), ("material_failure", "material failure"))
    ):
        ax = axes[j]
        for k, pol in enumerate(pols):
            v = b[b.policy == pol].set_index("struct_id").loc[structs, col]
            ax.bar(
                np.arange(len(structs)) + (k - len(pols) / 2) * w + w / 2,
                v,
                width=w,
                color=_color(pol),
                label=pol,
            )
        ax.set_xticks(np.arange(len(structs)), structs, fontsize=8)
        ax.set_title(f"5C test, per held-out structure: {label}", fontsize=10)
    axes[1].legend(fontsize=7, ncol=2)
    fig.suptitle(
        "B. Per-structure results (the mean-Z structure explains R_thr's non-material "
        "overspends; R_obs absorbs them)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(F / "final_b_structures.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    figure_policies()
    figure_structures()
    print("final figures A-B written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
