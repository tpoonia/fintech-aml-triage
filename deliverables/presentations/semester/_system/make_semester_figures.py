"""Additional figures for the semester presentation series (PNG 300 dpi + vector PDF).

Usage (repository root):
    uv run python deliverables/presentations/semester/_system/make_semester_figures.py

Data figures read committed tables in results/tables/ only. Schematics are drawn from the frozen
configurations (configs/vqc, configs/repair, configs/model_pool) or are explicitly labelled
"illustrative" (no project data). Provenance: deliverables/presentations/semester/FIGURES.md.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[4]
T = ROOT / "results" / "tables"
OUT = Path(__file__).resolve().parent / "figures"

INK, MUTED, GRID = "#1f1f1f", "#5a5a5a", "#e6e6e6"
NAVY, TEAL, AMBER, RED, SKY, GREY = "#1B2A49", "#0F8B8D", "#E8A33D", "#C0392B", "#56B4E9", "#9a9a9a"
ACT = {"A0": "#7f7f7f", "A1": "#0072B2", "A2": "#D55E00", "A3": "#CC79A7", "A4": "#E69F00"}

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 12,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "axes.edgecolor": "#444444",
        "axes.labelcolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
        "axes.axisbelow": True,
    }
)


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf", metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(OUT / f"{name}.png", dpi=300)
    plt.close(fig)


def _gate(ax, x, y, text, w=0.62, h=0.5, fc="#ffffff", ec=NAVY, fs=11, color=INK):
    ax.add_patch(
        FancyBboxPatch(
            (x - w / 2, y - h / 2),
            w,
            h,
            boxstyle="round,pad=0.0,rounding_size=0.06",
            fc=fc,
            ec=ec,
            lw=1.1,
            zorder=3,
        )
    )
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=color, zorder=4)


def _cx(ax, x, yc, yt, color=NAVY):
    ax.plot([x, x], [yc, yt], color=color, lw=1.4, zorder=2)
    ax.add_patch(plt.Circle((x, yc), 0.08, color=color, zorder=4))
    ax.add_patch(plt.Circle((x, yt), 0.17, fc="white", ec=color, lw=1.4, zorder=4))
    ax.plot([x - 0.17, x + 0.17], [yt, yt], color=color, lw=1.4, zorder=5)
    ax.plot([x, x], [yt - 0.17, yt + 0.17], color=color, lw=1.4, zorder=5)


def _meter(ax, x, y):
    _gate(ax, x, y, "", w=0.55, h=0.46, fc="#f3f5f9")
    t = np.linspace(np.pi * 0.15, np.pi * 0.85, 30)
    ax.plot(x + 0.17 * np.cos(t), y - 0.1 + 0.17 * np.sin(t), color=INK, lw=1, zorder=5)
    ax.plot([x, x + 0.13], [y - 0.1, y + 0.12], color=INK, lw=1, zorder=5)


def fig_circuit_p3ar() -> None:
    """The frozen P3A-R classifier (configs/repair/p3ar_v1.yaml, candidate e3-r2-par)."""
    fig, ax = plt.subplots(figsize=(13.0, 4.6))
    ax.set_xlim(-1.6, 17.6)
    ax.set_ylim(-1.55, 4.15)
    ax.axis("off")
    ys = [3.0, 2.0, 1.0, 0.0]
    feats = ["V17", "V14", "V12", "V10"]
    for i, y in enumerate(ys):
        ax.plot([0.0, 16.3], [y, y], color="#8a94a6", lw=1.1, zorder=1)
        ax.text(
            -0.15, y, f"$q_{i}$:  $x_{i + 1}$={feats[i]}", ha="right", va="center", fontsize=11.5
        )
    # feature-map region
    ax.add_patch(Rectangle((0.25, -0.55), 6.1, 4.1, fc="#eaf4f4", ec="none", zorder=0))
    ax.text(
        3.3,
        3.85,
        "ZZ feature map (reps 1, full entanglement)",
        ha="center",
        fontsize=12,
        color=TEAL,
        fontweight="bold",
    )
    for y in ys:
        _gate(ax, 0.85, y, "H")
        _gate(ax, 1.95, y, r"P$(2x_i)$", w=1.0)
    ax.add_patch(
        FancyBboxPatch(
            (2.9, -0.32),
            3.2,
            3.64,
            boxstyle="round,pad=0.0,rounding_size=0.1",
            fc="#ffffff",
            ec=TEAL,
            lw=1.4,
            zorder=3,
        )
    )
    ax.text(4.5, 1.95, "pairwise ZZ terms", ha="center", va="center", fontsize=12, zorder=4)
    ax.text(4.5, 1.45, "6 pairs: CX · P · CX", ha="center", va="center", fontsize=10.5, zorder=4)
    ax.text(
        4.5,
        0.85,
        r"$\phi_{ij}=(\pi-x_i)(\pi-x_j)$",
        ha="center",
        va="center",
        fontsize=12,
        zorder=4,
    )
    ax.text(4.5, 0.3, "12 CX", ha="center", va="center", fontsize=11, color=MUTED, zorder=4)
    # ansatz region
    ax.add_patch(Rectangle((6.65, -0.55), 8.3, 4.1, fc="#eef1f8", ec="none", zorder=0))
    ax.text(
        10.8,
        3.85,
        "RealAmplitudes ansatz (reps 2, linear)",
        ha="center",
        fontsize=12,
        color=NAVY,
        fontweight="bold",
    )
    xs = 7.2
    for layer in range(3):
        for i, y in enumerate(ys):
            _gate(ax, xs, y, rf"R$_Y(\theta_{{{4 * layer + i}}})$", w=1.18, fs=10)
        if layer < 2:
            for k in range(3):
                _cx(ax, xs + 1.0 + 0.55 * k, ys[k], ys[k + 1])
            xs += 3.05
    # measurement
    for y in ys:
        _meter(ax, 15.75, y)
    ax.text(
        16.5,
        1.5,
        "parity\n" + r"$\langle Z^{\otimes 4}\rangle$",
        ha="left",
        va="center",
        fontsize=12,
    )
    ax.text(
        8.0,
        -1.2,
        r"$p(\mathrm{fraud})=(1-\langle Z^{\otimes 4}\rangle)/2$     ·     "
        r"encoding e3: clip ±15 IQR → $x_i\in[-\pi/4,\pi/4]$     ·     "
        "12 trainable parameters  ·  18 CX after transpilation",
        ha="center",
        va="center",
        fontsize=11,
        color=MUTED,
    )
    save(fig, "circuit_p3ar")


def fig_circuit_generic() -> None:
    """Generic variational-classifier template (no project-specific choices)."""
    fig, ax = plt.subplots(figsize=(11.0, 4.0))
    ax.set_xlim(-1.2, 12.2)
    ax.set_ylim(-1.7, 3.9)
    ax.axis("off")
    ys = [3.0, 2.0, 1.0, 0.0]
    for y in ys:
        ax.plot([0.0, 9.6], [y, y], color="#8a94a6", lw=1.1, zorder=1)
        ax.text(-0.2, y, r"$|0\rangle$", ha="right", va="center", fontsize=12)
    for x0, w, label, sub, ec, fc in (
        (0.5, 2.6, r"$U(\mathbf{x})$", "data encoding", TEAL, "#eaf4f4"),
        (3.8, 3.6, r"$V(\boldsymbol{\theta})$", "trainable ansatz (L layers)", NAVY, "#eef1f8"),
    ):
        ax.add_patch(
            FancyBboxPatch(
                (x0, -0.35),
                w,
                3.7,
                boxstyle="round,pad=0.0,rounding_size=0.12",
                fc=fc,
                ec=ec,
                lw=1.5,
                zorder=3,
            )
        )
        ax.text(x0 + w / 2, 1.75, label, ha="center", va="center", fontsize=20, zorder=4)
        ax.text(x0 + w / 2, 0.95, sub, ha="center", va="center", fontsize=11, color=MUTED, zorder=4)
    for y in ys:
        _meter(ax, 8.4, y)
    ax.text(9.9, 1.5, "measured\nexpectation\n→ class score", ha="left", va="center", fontsize=11.5)
    ax.annotate(
        "",
        xy=(5.6, -0.55),
        xytext=(9.1, -0.9),
        arrowprops=dict(arrowstyle="-|>", color=AMBER, lw=1.6, connectionstyle="arc3,rad=-0.25"),
    )
    ax.text(
        7.4,
        -1.45,
        "classical optimizer updates θ from the training loss",
        ha="center",
        fontsize=11,
        color="#8a5a00",
    )
    ax.text(
        0.5,
        3.65,
        "Generic template; project-specific circuit choices were not recorded before Oct 6, 2026",
        fontsize=10.5,
        color=MUTED,
        ha="left",
    )
    save(fig, "circuit_generic")


def fig_noise_concept() -> None:
    """Illustrative: noise contracts expectation values (global-depolarizing model; no data)."""
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.0))
    d = np.arange(0, 41)
    ax = axes[0]
    ax.plot(d, np.full_like(d, 0.6, dtype=float), color=NAVY, lw=2.2, label="ideal")
    for p, c, ls in ((0.01, AMBER, "-"), (0.03, RED, "--")):
        ax.plot(
            d, 0.6 * (1 - p) ** d, color=c, lw=2.2, ls=ls, label=f"noisy (error {p:.0%} per layer)"
        )
    ax.set_xlabel("circuit depth (layers)")
    ax.set_ylabel(r"expectation value $\langle O\rangle$")
    ax.set_ylim(0, 0.7)
    ax.set_title("Noise shrinks measured signals toward zero", loc="left", fontsize=12.5)
    ax.legend(fontsize=10.5, loc="lower left")
    ax = axes[1]
    z = np.linspace(-1, 1, 200)
    for s, c, lab in ((1.0, NAVY, "ideal"), (0.4, RED, "strong noise (×0.4)")):
        ax.plot(z, (1 - s * z) / 2, color=c, lw=2.2, label=lab)
    ax.axhline(0.5, color=GREY, lw=1, ls=":")
    ax.set_xlabel(r"ideal $\langle O\rangle$")
    ax.set_ylabel("predicted probability")
    ax.set_title("Probabilities are pulled toward 0.5", loc="left", fontsize=12.5)
    ax.legend(fontsize=10.5, loc="upper right")
    fig.text(
        0.01,
        -0.03,
        "Illustrative global-depolarizing model, not project data.",
        fontsize=10,
        color=MUTED,
    )
    fig.tight_layout()
    save(fig, "noise_concept")


def fig_zne_schematic() -> None:
    """Illustrative ZNE: fold the circuit to amplify noise, then extrapolate to zero noise."""
    fig, ax = plt.subplots(figsize=(5.6, 3.7))
    lam = np.array([1.0, 3.0, 5.0])
    val = 0.62 * np.exp(-0.18 * lam)
    w = np.polyfit(lam, val, 1)
    xs = np.linspace(0, 5.3, 50)
    ax.plot(xs, np.polyval(w, xs), color=AMBER, lw=2, ls="--", label="linear fit")
    ax.scatter(lam, val, s=70, color=ACT["A2"], zorder=3, label="measured at λ = 1, 3, 5")
    ax.scatter(
        [0],
        [np.polyval(w, 0)],
        s=110,
        marker="*",
        color=TEAL,
        zorder=4,
        label="extrapolated (λ = 0)",
    )
    ax.axhline(0.62, color=NAVY, lw=1.2, ls=":", label="noise-free value")
    ax.set_xlabel(r"noise scale $\lambda$ (fold $U\to U(U^\dagger U)^k$, $\lambda=2k+1$)")
    ax.set_ylabel(r"$\langle O\rangle$")
    ax.set_xlim(-0.3, 5.6)
    ax.set_ylim(0, 0.72)
    ax.set_xticks([0, 1, 3, 5])
    ax.legend(fontsize=10, loc="lower left")
    ax.text(
        0.0,
        -0.32,
        "Illustrative values (not project data).",
        transform=ax.transAxes,
        fontsize=10,
        color=MUTED,
    )
    save(fig, "zne_schematic")


def fig_baselines() -> None:
    p2 = pd.read_csv(T / "phase2_classical_metrics.csv")
    p2 = p2[(p2.regime == "a-full") & (p2.draw == 0) & (p2.representation == "full")].set_index(
        "model"
    )
    cmp_ = pd.read_csv(T / "p3ar_validation_comparison.csv").set_index("model")
    rows = [
        ("Random forest · 30 feat.", p2.loc["rf"], GREY),
        ("Grad. boosting · 30 feat.", p2.loc["hgb"], GREY),
        ("Logistic reg. · 30 feat.", p2.loc["logreg"], GREY),
        ("Logistic reg. · VQC inputs", cmp_.loc["logreg"], SKY),
        ("Random forest · VQC inputs", cmp_.loc["rf"], SKY),
        ("Grad. boosting · VQC inputs", cmp_.loc["hgb"], SKY),
        ("VQC, repaired (P3A-R)", cmp_.loc["p3a_r"], TEAL),
        ("VQC, first (P3A)", cmp_.loc["p3a_original"], RED),
    ]
    fig, ax = plt.subplots(figsize=(6.2, 3.7))
    y = np.arange(len(rows))[::-1]
    for yi, (_lab, r, c) in zip(y, rows, strict=True):
        ax.barh(yi, r.auprc, color=c, height=0.62)
        ax.errorbar(
            r.auprc,
            yi,
            xerr=[[r.auprc - r.auprc_ci_low], [r.auprc_ci_high - r.auprc]],
            fmt="none",
            ecolor=INK,
            lw=1,
            capsize=3,
        )
        ax.text(r.auprc_ci_high + 0.015, yi, f"{r.auprc:.3f}", va="center", fontsize=11)
    ax.set_yticks(y, [r[0] for r in rows], fontsize=11)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("validation AUPRC, 95% CI (chance ≈ 0.0017)")
    ax.grid(axis="y", visible=False)
    save(fig, "baselines_auprc")


def fig_encoding_repair() -> None:
    e = pd.read_csv(T / "p3ar_encoding_diagnostics.csv").set_index("enc_id")
    cmp_ = pd.read_csv(T / "p3ar_validation_comparison.csv").set_index("model")
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.9))
    labs = ["first\nclip ±3 IQR\n[−π, π]", "repaired\nclip ±15 IQR\n[−π/4, π/4]"]
    cols = [RED, TEAL]
    panels = [
        (
            "distinct fraud inputs\n(of 213 training frauds)",
            [e.loc["e0", "distinct_fraud_vectors"], e.loc["e3", "distinct_fraud_vectors"]],
            213,
        ),
        (
            "frauds clipped on\nall four features",
            [
                e.loc["e0", "frauds_all_features_clipped"],
                e.loc["e3", "frauds_all_features_clipped"],
            ],
            213,
        ),
    ]
    for ax, (title, vals, top) in zip(axes[:2], panels, strict=True):
        ax.bar([0, 1], vals, color=cols, width=0.6)
        for i, v in enumerate(vals):
            ax.text(i, v + top * 0.02, f"{int(v)}", ha="center", fontsize=13, fontweight="bold")
        ax.set_ylim(0, top * 1.12)
        ax.set_xticks([0, 1], labs, fontsize=10.5)
        ax.set_title(title, fontsize=12)
        ax.grid(axis="x", visible=False)
    ax = axes[2]
    for i, m in enumerate(["p3a_original", "p3a_r"]):
        r = cmp_.loc[m]
        ax.bar(i, r.auprc, color=cols[i], width=0.6)
        ax.errorbar(
            i,
            r.auprc,
            yerr=[[r.auprc - r.auprc_ci_low], [r.auprc_ci_high - r.auprc]],
            fmt="none",
            ecolor=INK,
            lw=1,
            capsize=4,
        )
        ax.text(i + 0.36, r.auprc, f"{r.auprc:.3f}", va="center", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 0.8)
    ax.set_xlim(-0.5, 1.9)
    ax.set_xticks([0, 1], labs, fontsize=10.5)
    ax.set_title("validation AUPRC (95% CI)", fontsize=12)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    save(fig, "encoding_repair")


def fig_pool() -> None:
    m = pd.read_csv(T / "p5a_pool_metrics.csv")
    m = m[m.role == "candidate"].copy()
    split = pd.read_csv(T / "p5b_split.csv").set_index("struct_id")["split"]
    m["split"] = m.struct_id.map(split)
    order = m.groupby("struct_id").auprc.median().sort_values().index
    color = {"train": NAVY, "val": SKY, "test": AMBER}
    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    for i, s in enumerate(order):
        d = m[m.struct_id == s]
        ax.scatter(
            d.auprc,
            np.full(len(d), i),
            s=34,
            color=color[d.split.iloc[0]],
            zorder=3,
            edgecolor="white",
            lw=0.6,
        )
    for k, c in color.items():
        ax.scatter(
            [],
            [],
            color=c,
            s=40,
            label={
                "train": "training (8 structures)",
                "val": "validation (4)",
                "test": "sealed test (4)",
            }[k],
        )
    ax.axvline(0.507, color=TEAL, lw=1.2, ls="--", label="P3A-R anchor (0.507)")
    ax.set_yticks(range(len(order)), [s.replace("-", " · ") for s in order], fontsize=10.5)
    ax.set_xlabel("clean validation AUPRC (each dot = one of 64 models)")
    ax.set_xlim(0, 0.6)
    ax.set_ylim(-0.6, len(order) - 0.4)
    ax.legend(loc="upper center", bbox_to_anchor=(0.42, -0.13), ncol=2, fontsize=10.5)
    ax.grid(axis="y", visible=False)
    save(fig, "pool_auprc")


def fig_cost_slide() -> None:
    """Slide-legible cost–reliability view of the 5C sealed test (all budgets pooled)."""
    p = pd.read_csv(T / "final_policies_5c_test.csv")
    p = p[p.arm == "all"].set_index("policy")
    rel = p.mean_total_shots_per_inference / p.loc["oracle", "mean_total_shots_per_inference"]
    names = {
        "R_thr": ("Probe rule R_thr", NAVY, 150),
        "R_obs": ("R_thr + readout type", SKY, 60),
        "R_cat": ("5B category rule", SKY, 60),
        "always_A3": ("Always combined (A3)", ACT["A3"], 70),
        "L_logistic": ("Logistic (learned)", ACT["A2"], 60),
        "L_tree3": ("Tree d=3 (learned)", ACT["A2"], 60),
        "L_gbt": ("Grad. boosting (learned)", ACT["A2"], 60),
        "L_gbt_benefit": ("GBT benefit (learned)", ACT["A2"], 60),
        "oracle": ("Oracle", INK, 70),
    }
    # label positions in data coordinates (leader lines for the crowded cluster near the Oracle)
    pos = {
        "R_thr": (0.958, 0.010, "left"),
        "R_obs": (0.958, 0.031, "left"),
        "R_cat": (0.962, 0.052, "left"),
        "always_A3": (1.017, 0.068, "left"),
        "L_logistic": (0.954, 0.094, "left"),
        "L_tree3": (1.022, 0.044, "left"),
        "L_gbt_benefit": (1.027, 0.032, "left"),
        "L_gbt": (1.022, 0.010, "left"),
        "oracle": (1.004, -0.001, "left"),
    }
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for k, (lab, c, sz) in names.items():
        x, y = rel[k], p.loc[k, "material_failure"]
        ax.scatter(x, y, s=sz, color=c, zorder=3, edgecolor="white", lw=0.8)
        tx, ty, ha = pos[k]
        ax.annotate(
            lab,
            (x, y),
            xytext=(tx, ty),
            textcoords="data",
            fontsize=10.5,
            ha=ha,
            va="center",
            fontweight="bold" if k == "R_thr" else "normal",
            arrowprops=dict(arrowstyle="-", color="#9aa3b2", lw=0.8, shrinkA=2, shrinkB=4),
        )
    off = [
        f"Never mitigate: {p.loc['always_A0', 'material_failure']:.2f} at {rel['always_A0']:.2f}×",
        f"Always readout: {p.loc['always_A1', 'material_failure']:.2f} at {rel['always_A1']:.2f}×",
        f"Always ZNE: {p.loc['always_A2', 'material_failure']:.2f} at {rel['always_A2']:.2f}×",
        f"Always 3× shots: {p.loc['always_A4', 'material_failure']:.2f} at {rel['always_A4']:.2f}×",
    ]
    ax.text(
        0.985,
        0.97,
        "Off scale (material failure, shots):\n" + "\n".join(off),
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10,
        color=MUTED,
        linespacing=1.3,
        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=GRID),
    )
    ax.set_xlim(0.935, 1.065)
    ax.set_ylim(-0.005, 0.11)
    ax.set_xlabel("total shots per inference ÷ Oracle (including probes)")
    ax.set_ylabel("material failure rate")
    save(fig, "cost_reliability_slide")


def fig_workflow_slide() -> None:
    """Pre-registered workflow (slide variant of fig2_workflow with an exact registration note)."""
    from matplotlib.patches import FancyArrowPatch

    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.15, 5)
    ax.axis("off")
    steps = [
        ("P1–P2", "Data, leakage-safe\npartitions,\nclassical baselines", "#eef3f8"),
        ("P3A / P3A-R", "First VQC;\npre-registered\nencoding repair", "#eef3f8"),
        ("P3B  (G1 conditional)", "Noise\ncharacterization", "#fdf0e6"),
        ("P4  (G2 conditional)", "Mitigation vs\nshot-matched\nbaseline", "#fdf0e6"),
        ("P5A  (G3A pass)", "64-model pool,\nfrozen + hashed", "#e8f4ea"),
        ("P5B  (G3B FAIL)", "Categorical noise\ncounterfactuals", "#f6eef4"),
        ("P5C  (G3C FAIL)", "Continuous joint\nnoise counterfactuals", "#f6eef4"),
        ("P7 + Final  (H1–H4 ✓)", "Frozen policies;\nsealed test\nopened once", "#dfe9f5"),
    ]
    w, h, gap = 2.15, 1.15, 0.33

    def arrow(a, b):
        ax.add_patch(
            FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11, color="#333333", lw=1.0)
        )

    for i, (tag, text, fc) in enumerate(steps):
        row, col = divmod(i, 4)
        col = col if row == 0 else 3 - col  # snake layout
        x = 0.1 + col * (w + gap)
        y = 3.2 if row == 0 else 1.15
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.012,rounding_size=0.02",
                fc=fc,
                ec="#333333",
                lw=0.9,
            )
        )
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9, color=INK)
        ax.text(
            x + w / 2, y + h + 0.15, tag, ha="center", fontsize=8.8, fontweight="bold", color=INK
        )
        if i in (0, 1, 2):
            arrow((x + w, y + h / 2), (x + w + gap, y + h / 2))
        if i in (4, 5, 6):
            arrow((x, y + h / 2), (x - gap, y + h / 2))
        if i == 3:
            arrow((x + w / 2, y), (x + w / 2, 1.15 + h + 0.42))
    ax.text(
        5.0,
        0.6,
        "From Phase 3A-R on, each phase was registered and committed before its own "
        "outcomes; reported runs used a clean tree.",
        ha="center",
        fontsize=9,
        color=MUTED,
    )
    ax.text(
        5.0,
        0.15,
        "Gates decided whether to continue; controller-test outcomes stayed sealed "
        "until the final protocol was pushed.",
        ha="center",
        fontsize=9,
        color=MUTED,
    )
    save(fig, "workflow_slide")


def main() -> int:
    fig_circuit_p3ar()
    fig_circuit_generic()
    fig_noise_concept()
    fig_zne_schematic()
    fig_baselines()
    fig_encoding_repair()
    fig_pool()
    fig_cost_slide()
    fig_workflow_slide()
    print(f"semester figures written to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
