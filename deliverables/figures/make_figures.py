"""Publication figures for the Q-TRACE deliverables (vector PDF + PNG).

Usage (repository root): uv run python deliverables/figures/make_figures.py

Every quantitative panel reads committed tables in results/tables/ only (never sealed or
transaction-level data); the two diagrams (architecture, workflow) are schematic. Provenance
is listed in deliverables/figures/FIGURES.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / "results" / "tables"
OUT = Path(__file__).resolve().parent

# Okabe-Ito (colour-blind safe). One colour per action, used identically in every figure.
ACT = {
    "A0": "#7f7f7f",  # none
    "A1": "#0072B2",  # readout mitigation
    "A2": "#D55E00",  # ZNE
    "A3": "#CC79A7",  # combined
    "A4": "#E69F00",  # extra shots
}
ACT_NAME = {
    "A0": "A0 none",
    "A1": "A1 readout mitigation",
    "A2": "A2 ZNE",
    "A3": "A3 combined",
    "A4": "A4 3x shots",
}
FIXED, RULE, RULE_MAIN, LEARN, ORACLE = "#9a9a9a", "#56B4E9", "#0b3d6b", "#D55E00", "#222222"
INK, MUTED = "#1f1f1f", "#5a5a5a"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "axes.edgecolor": "#444444",
        "axes.labelcolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#e6e6e6",
        "grid.linewidth": 0.6,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
        "axes.axisbelow": True,
    }
)


def save(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=220)
    plt.close(fig)


def policy_color(p: str) -> str:
    if p == "R_thr":
        return RULE_MAIN
    if p.startswith("always"):
        return FIXED
    if p.startswith("R_"):
        return RULE
    if p.startswith("L_"):
        return LEARN
    return ORACLE


LABEL = {
    "always_A0": "Never (A0)",
    "always_A1": "Always A1",
    "always_A2": "Always A2",
    "always_A3": "Always A3",
    "always_A4": "Always A4",
    "R_cat": "5B category rule",
    "R_thr": "Probe rule R_thr",
    "R_obs": "R_thr + readout type",
    "L_logistic": "Logistic (learned)",
    "L_tree3": "Tree d=3 (learned)",
    "L_gbt": "Grad. boosting (learned)",
    "L_gbt_benefit": "GBT benefit (learned)",
    "oracle": "Oracle",
}


# ------------------------------------------------------------------ diagrams


def _box(ax, x, y, w, h, text, fc, ec="#333333", fs=8.5, color=INK, bold=False):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02", fc=fc, ec=ec, lw=0.9
        )
    )
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        color=color,
        fontweight="bold" if bold else "normal",
        wrap=True,
    )


def _arrow(ax, a, b, color="#333333", style="-|>", lw=1.0, ls="-"):
    ax.add_patch(
        FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=10, color=color, lw=lw, ls=ls)
    )


def fig_architecture() -> None:
    fig, ax = plt.subplots(figsize=(8.0, 3.9))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    bw, bh = 1.9, 1.15
    top, bot = 3.35, 1.25
    boxes = {
        "batch": (0.15, top, "Transaction batch\n(N rows)", "#eef3f8"),
        "vqc": (2.45, top, "Frozen 4-qubit VQC\nZZ map + ansatz", "#eef3f8"),
        "noise": (4.75, top, "Noisy execution\n(readout, gate,\nthermal noise)", "#fdf0e6"),
        "probe": (
            4.55,
            bot,
            ("Label-free probes:\nreadout calibration\n+ fixed gate probe\n(66·S shots / batch)"),
            "#e8f4ea",
        ),
        "policy": (
            7.05,
            2.3,
            "Selective policy\nprobe rule R_thr\nor learned controller",
            "#dfe9f5",
        ),
        "action": (
            7.05,
            3.85,
            "Action: A0 none · A1 readout\nA2 ZNE · A3 both · A4 3× shots",
            "#f6eef4",
        ),
        "out": (7.05, 0.75, "Mitigated probabilities\n→ calibrated fraud decision", "#eef3f8"),
    }
    for key, (x, y, text, fc) in boxes.items():
        w = 2.7 if key in ("policy", "action", "out") else (2.3 if key == "probe" else bw)
        h = 0.95 if key in ("action", "out") else (1.45 if key == "probe" else bh)
        _box(ax, x, y, w, h, text, fc, fs=7.6, bold=(key == "policy"))
    _arrow(ax, (0.15 + bw, top + bh / 2), (2.45, top + bh / 2))
    _arrow(ax, (2.45 + bw, top + bh / 2), (4.75, top + bh / 2))
    _arrow(ax, (4.75 + bw / 2, top), (4.75 + bw / 2, bot + 1.45))
    _arrow(ax, (4.55 + 2.3, bot + 0.9), (7.05, 2.3 + 0.35))
    _arrow(ax, (8.4, 2.3 + bh), (8.4, 3.85))
    _arrow(ax, (8.4, 2.3), (8.4, 0.75 + 0.95))
    ax.text(
        8.55,
        2.0,
        "inputs: probes + 16 static\nmodel descriptors",
        ha="left",
        va="center",
        fontsize=6.8,
        color=MUTED,
    )
    ax.add_patch(
        FancyBboxPatch(
            (0.15, 0.55),
            3.95,
            1.95,
            boxstyle="round,pad=0.05",
            fc="#fff7f7",
            ec="#b30000",
            lw=0.9,
            ls="--",
        )
    )
    ax.text(
        2.12,
        2.15,
        "Offline only: never a policy input",
        ha="center",
        fontsize=7.8,
        color="#b30000",
        fontweight="bold",
    )
    ax.text(
        2.12,
        1.35,
        "true noise parameters · noise labels\nmodel / structure identifiers\n"
        "transaction labels · post-action outcomes\nOracle choice · sealed test lockbox",
        ha="center",
        va="center",
        fontsize=7.2,
        color="#7a1f1f",
    )
    ax.set_title(
        "Q-TRACE decision layer: what the policy sees and what it may choose",
        loc="left",
        fontsize=10,
    )
    save(fig, "fig1_architecture")


def fig_workflow() -> None:
    fig, ax = plt.subplots(figsize=(8.0, 3.7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    steps = [
        ("P1–P2", "Data, leakage-safe\npartitions,\nclassical baselines", "#eef3f8"),
        ("P3A / P3A-R", "First VQC;\npre-registered\nencoding repair", "#eef3f8"),
        ("P3B  (G1 conditional)", "Noise\ncharacterization", "#fdf0e6"),
        ("P4  (G2 conditional)", "Mitigation vs\nshot-matched baseline", "#fdf0e6"),
        ("P5A  (G3A pass)", "64-model pool,\nfrozen + hashed", "#e8f4ea"),
        ("P5B  (G3B FAIL)", "Categorical noise\ncounterfactuals", "#f6eef4"),
        ("P5C  (G3C FAIL)", "Continuous joint\nnoise counterfactuals", "#f6eef4"),
        ("P7 + Final  (H1–H4 ✓)", "Frozen policies;\nsealed test\nopened once", "#dfe9f5"),
    ]
    w, h, gap = 2.15, 1.15, 0.33
    for i, (tag, text, fc) in enumerate(steps):
        row, col = divmod(i, 4)
        col = col if row == 0 else 3 - col  # snake layout
        x = 0.1 + col * (w + gap)
        y = 3.2 if row == 0 else 1.15
        _box(ax, x, y, w, h, text, fc, fs=7.6)
        ax.text(
            x + w / 2, y + h + 0.15, tag, ha="center", fontsize=7.4, fontweight="bold", color=INK
        )
        if i in (0, 1, 2):
            _arrow(ax, (x + w, y + h / 2), (x + w + gap, y + h / 2))
        if i in (4, 5, 6):
            _arrow(ax, (x, y + h / 2), (x - gap, y + h / 2))
        if i == 3:
            _arrow(ax, (x + w / 2, y), (x + w / 2, 1.15 + h + 0.42))
    ax.text(
        5.0,
        0.62,
        "Every phase: pre-register (config + code) → push → clean-tree reported run "
        "→ validate → commit and push.",
        ha="center",
        fontsize=7.6,
        color=MUTED,
    )
    ax.text(
        5.0,
        0.22,
        "Gates decide whether to continue; controller-test outcomes stay sealed "
        "until the final protocol is pushed.",
        ha="center",
        fontsize=7.6,
        color=MUTED,
    )
    save(fig, "fig2_workflow")


# ------------------------------------------------------------------ quantitative


def fig_noise_effects() -> None:
    d = pd.read_csv(T / "p3b_exact_metrics.csv")
    d = d[(d.model == "p3a_r") & (d.condition != "clean")]
    order = [
        f"{fam}-{sev}"
        for fam in ("dep", "th", "ro-sym", "comb")
        for sev in ("low", "medium", "high")
    ] + ["ar-005", "ar-020", "ar-050"]
    d = d.set_index("condition").loc[order]
    clean = pd.read_csv(T / "p3b_exact_metrics.csv")
    clean = clean[(clean.model == "p3a_r") & (clean.condition == "clean")].iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    x = np.arange(len(d))
    ax = axes[0]
    err = [d.delta_auprc - d.delta_auprc_ci_low, d.delta_auprc_ci_high - d.delta_auprc]
    ax.bar(x, d.delta_auprc, color="#0072B2", width=0.7)
    ax.errorbar(x, d.delta_auprc, yerr=err, fmt="none", color=INK, lw=0.7, capsize=1.5)
    ax.axhline(0, color=INK, lw=0.7)
    ax.set_ylim(-0.05, 0.05)
    ax.set_ylabel("ΔAUPRC vs clean (95% CI)")
    ax.set_title(
        f"Discrimination: essentially unchanged\n(clean AUPRC {clean.auprc:.3f})", fontsize=9
    )
    ax = axes[1]
    ax.bar(x, d.brier, color="#D55E00", width=0.7)
    ax.axhline(clean.brier, color=INK, lw=0.8, ls="--")
    ax.text(-0.4, clean.brier + 0.004, f"clean {clean.brier:.4f}", ha="left", fontsize=7.5)
    ax.set_ylabel("Brier score (exact)")
    ax.set_title("Calibration: up to 13× worse", fontsize=9)
    for a in axes:
        a.set_xticks(x, d.index, rotation=70, ha="right", fontsize=7)
    fig.suptitle(
        "Noise reshapes calibration, not discrimination (P3A-R on vqc_val; Phase 3B)",
        x=0.02,
        ha="left",
        fontsize=10,
    )
    fig.tight_layout()
    save(fig, "fig3_noise_effects")


def fig_mitigation() -> None:
    d = pd.read_csv(T / "p4_summary.csv")
    d = d[(d.arm == "s1024") & d.vector.isin(["A0", "A1", "A2", "A3", "RM3"])]
    conds = [
        "clean",
        "ro-sym-high",
        "ar-020",
        "ar-050",
        "dep-high",
        "th-high",
        "comb-medium",
        "comb-high",
    ]
    piv = d.pivot_table(index="condition", columns="vector", values="brier").loc[conds]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    vecs = ["A0", "A1", "A2", "A3", "RM3"]
    cols = {"A0": ACT["A0"], "A1": ACT["A1"], "A2": ACT["A2"], "A3": ACT["A3"], "RM3": ACT["A4"]}
    names = {
        "A0": "A0 none",
        "A1": "A1 readout mit.",
        "A2": "A2 ZNE",
        "A3": "A3 combined",
        "RM3": "3× shots (shot-matched)",
    }
    w = 0.16
    for k, v in enumerate(vecs):
        ax.bar(np.arange(len(conds)) + (k - 2) * w, piv[v], width=w, color=cols[v], label=names[v])
    ax.set_xticks(np.arange(len(conds)), conds, fontsize=7.5, rotation=15)
    ax.set_ylabel("Brier score (mean of 20 replicates)")
    ax.legend(ncol=5, fontsize=7.5, loc="upper left")
    ax.set_ylim(0, piv.values.max() * 1.25)
    ax.set_title(
        "Mitigation repairs calibration; extra shots do not (P3A-R, 1,024 shots; Phase 4)",
        loc="left",
    )
    fig.tight_layout()
    save(fig, "fig4_mitigation")


def fig_preferred_actions() -> None:
    m5b = json.loads((T / "p5b_metadata.json").read_text())
    m5c = json.loads((T / "p5c_metadata.json").read_text())
    fin = json.loads((T / "final_metadata.json").read_text())["preferred_shares"]
    rows = [
        ("5B val\n(categorical)", m5b["preferred_shares_val"]),
        ("5B test\n(categorical)", fin["5b_test"]),
        ("5C val\n(continuous)", m5c["preferred_shares"]["val"]),
        ("5C test\n(continuous)", fin["5c_test"]),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    left = np.zeros(len(rows))
    for a in ["A0", "A1", "A2", "A3", "A4"]:
        v = np.array([r[1].get(a, 0.0) for r in rows])
        ax.barh(np.arange(len(rows)), v, left=left, color=ACT[a], label=ACT_NAME[a], height=0.6)
        for i, (vi, li) in enumerate(zip(v, left, strict=True)):
            if vi >= 0.06:
                ax.text(
                    li + vi / 2,
                    i,
                    f"{vi:.0%}",
                    ha="center",
                    va="center",
                    fontsize=7.5,
                    color="white",
                )
        left += v
    ax.set_yticks(np.arange(len(rows)), [r[0] for r in rows], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_xlabel("share of contexts where the action is the cost-aware Oracle choice p*")
    ax.legend(ncol=5, fontsize=7.2, loc="upper center", bbox_to_anchor=(0.5, -0.32))
    ax.grid(axis="y", visible=False)
    ax.set_title(
        "Which action is worth paying for? (Oracle: cheapest within 10% of best Brier)", loc="left"
    )
    save(fig, "fig5_preferred_actions")


def _final(env: str) -> pd.DataFrame:
    p = pd.read_csv(T / f"final_policies_{env}.csv")
    return p[p.arm == "all"].set_index("policy")


def fig_cost_reliability() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3))
    spec = {
        "5c_test": (
            "5C test: continuous joint noise",
            (0.93, 1.07, -0.006, 0.11),
            {
                "always_A3": ("Always A3", (-6, 6), "right"),
                "R_cat": ("5B category rule", (-6, 4), "right"),
                "L_logistic": ("Logistic (learned)", (6, -2), "left"),
                "oracle": ("Oracle", (6, 2), "left"),
                "R_thr": (
                    "Probe rule R_thr  (R_obs, tree, GBT,\nGBT-benefit ≈ same point)",
                    (16, -2),
                    "left",
                ),
            },
        ),
        "5b_test": (
            "5B test: categorical noise",
            (0.97, 1.2, -0.01, 0.33),
            {
                "R_cat": ("5B category rule", (6, -3), "left"),
                "R_thr": ("Probe rule R_thr", (9, 6), "left"),
                "R_obs": ("R_thr + readout type", (6, 4), "left"),
                "L_tree3": ("Tree d=3 (learned)", (-8, 7), "right"),
                "L_logistic": ("Logistic (learned)", (-6, 4), "right"),
                "oracle": ("Oracle", (6, 2), "left"),
            },
        ),
    }
    for ax, (env, (title, (x0, x1, y0, y1), labels)) in zip(axes, spec.items(), strict=True):
        p = _final(env)
        rel = p.mean_total_shots_per_inference / p.loc["oracle"].mean_total_shots_per_inference
        off = []
        for pol, r in p.iterrows():
            if x0 <= rel[pol] <= x1 and y0 <= r.material_failure <= y1:
                ax.scatter(
                    rel[pol],
                    r.material_failure,
                    s=60 if pol == "R_thr" else 28,
                    color=policy_color(pol),
                    zorder=3 if pol != "R_thr" else 4,
                    edgecolor="white",
                    lw=0.6,
                )
            else:
                off.append(f"{LABEL[pol]} ({r.material_failure:.2f}, {rel[pol]:.2f}×)")
        for pol, (text, (dx, dy), ha) in labels.items():
            ax.annotate(
                text,
                (rel[pol], p.loc[pol].material_failure),
                xytext=(dx, dy),
                textcoords="offset points",
                fontsize=6.8,
                ha=ha,
                va="center",
                color=INK,
            )
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_xlabel("total shots per inference ÷ Oracle (incl. probes)")
        ax.set_title(title, fontsize=9)
        top_note = True
        ax.text(
            0.98,
            0.97 if top_note else 0.03,
            "off scale (material, shots):\n" + "\n".join(off),
            transform=ax.transAxes,
            ha="right",
            va="top" if top_note else "bottom",
            fontsize=5.8,
            color=MUTED,
            linespacing=1.15,
        )
    axes[0].set_ylabel("material failure rate")
    fig.suptitle(
        "Cost–reliability trade-off on sealed held-out models (one-time test)",
        x=0.02,
        ha="left",
        fontsize=10,
    )
    fig.tight_layout()
    save(fig, "fig6_cost_reliability")


def fig_learned_vs_rule() -> None:
    comps = ["L_logistic", "L_tree3", "L_gbt", "L_gbt_benefit", "R_obs", "R_cat", "always_A3"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, env, title in ((axes[0], "5c_test", "5C test"), (axes[1], "5b_test", "5B test")):
        q = pd.read_csv(T / f"final_paired_vs_rthr_{env}.csv").set_index("comparator").loc[comps]
        y = np.arange(len(comps))
        # diff = R_thr - comparator; show comparator - R_thr so right = comparator worse
        est = -q.diff_material
        lo, hi = -q.diff_material_ci_hi, -q.diff_material_ci_lo
        ax.errorbar(est, y, xerr=[est - lo, hi - est], fmt="o", color=INK, ms=4, lw=1, capsize=2)
        for i, c in enumerate(comps):
            ax.scatter(est.iloc[i], i, color=policy_color(c), s=36, zorder=3)
        ax.axvline(0, color=INK, lw=0.8)
        ax.axvspan(-0.02, 0.02, color="#cfe3f3", alpha=0.6, lw=0)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("material failure: comparator − R_thr\n(95% two-stage cluster CI)")
    axes[0].set_yticks(np.arange(len(comps)), [LABEL[c] for c in comps], fontsize=7.8)
    axes[0].invert_yaxis()
    fig.suptitle(
        "No learned comparator beats the probe rule on material failure (shaded: ±0.02 margin)",
        x=0.02,
        ha="left",
        fontsize=10,
    )
    fig.tight_layout()
    save(fig, "fig7_learned_vs_rule")


def fig_final_heldout() -> None:
    order = [
        "always_A0",
        "always_A1",
        "always_A2",
        "always_A3",
        "always_A4",
        "R_cat",
        "R_thr",
        "R_obs",
        "L_logistic",
        "L_tree3",
        "L_gbt",
        "L_gbt_benefit",
        "oracle",
    ]
    p = _final("5c_test").loc[order]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), sharey=True)
    for ax, col, lo, hi, title in (
        (axes[0], "failure", "fail_ci_lo", "fail_ci_hi", "Any deviation from Oracle"),
        (axes[1], "material_failure", "material_ci_lo", "material_ci_hi", "Material failure"),
    ):
        y = np.arange(len(p))
        ax.barh(y, p[col], color=[policy_color(o) for o in order], height=0.7)
        ax.errorbar(
            p[col],
            y,
            xerr=[p[col] - p[lo], p[hi] - p[col]],
            fmt="none",
            color=INK,
            lw=0.7,
            capsize=1.5,
        )
        for i, (v, h) in enumerate(zip(p[col], p[hi], strict=True)):
            if v > 0.75:
                ax.text(
                    v - 0.03, i, f"{v:.3f}", va="center", ha="right", fontsize=6.8, color="white"
                )
            else:
                ax.text(h + 0.02, i, f"{v:.3f}", va="center", fontsize=6.8, color=INK)
        ax.set_xlim(0, 1.05)
        ax.set_title(title, fontsize=9)
    axes[0].set_yticks(np.arange(len(p)), [LABEL[o] for o in order], fontsize=7.8)
    axes[0].invert_yaxis()
    fig.suptitle(
        "Final held-out evaluation, 5C test (16 unseen models, 4 unseen structures; 95% CIs)",
        x=0.02,
        ha="left",
        fontsize=10,
    )
    fig.tight_layout()
    save(fig, "fig8_final_heldout")


def fig_ablation() -> None:
    a = pd.read_csv(T / "ablation_probes.csv")
    variants = [
        "R_thr (both probes)",
        "gate probe only",
        "readout probe only",
        "no probe (fixed per budget)",
    ]
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    w = 0.38
    for k, (env, col) in enumerate((("5c_val", "#0b3d6b"), ("5b_val", "#56B4E9"))):
        v = a[a.environment == env].set_index("variant").loc[variants, "material_failure"]
        ax.bar(
            np.arange(4) + (k - 0.5) * w,
            v,
            width=w,
            color=col,
            label={"5c_val": "5C val (continuous)", "5b_val": "5B val (categorical)"}[env],
        )
        for i, x in enumerate(v):
            ax.text(i + (k - 0.5) * w, x + 0.01, f"{x:.3f}", ha="center", fontsize=7)
    ax.set_xticks(np.arange(4), variants, fontsize=8)
    ax.set_ylabel("material failure (validation)")
    ax.legend(fontsize=7.5)
    ax.set_title(
        "Probe ablation: the gate probe carries the material decision (validation only)", loc="left"
    )
    save(fig, "fig9_probe_ablation")


def main() -> int:
    fig_architecture()
    fig_workflow()
    fig_noise_effects()
    fig_mitigation()
    fig_preferred_actions()
    fig_cost_reliability()
    fig_learned_vs_rule()
    fig_final_heldout()
    fig_ablation()
    print("figures written to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
