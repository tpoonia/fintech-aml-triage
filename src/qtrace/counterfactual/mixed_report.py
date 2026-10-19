"""Phase 5C registered report: committed aggregate tables and the G3C metadata (train/val only)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from qtrace.counterfactual import mixed_analysis as AN
from qtrace.counterfactual.mixed_generate import ACTIONS
from qtrace.counterfactual.mixed_study import T, load_mixed_study
from qtrace.counterfactual.study import _csv, _json


def run_report(root: Path) -> dict:
    resolved, study, base, _, _, design = load_mixed_study()
    processed = root / study.processed_dir
    train, val = AN.load_split(processed, "train"), AN.load_split(processed, "val")
    costs = pd.read_csv(root / T / "p5c_costs.csv")
    statics = pd.read_csv(root / T / "p5b_static_features.csv")  # deployable descriptors (5B)
    an = AN.analyse(train, val, design, costs, statics, study, base, resolved.spec.seeds.bootstrap)
    return {"study": study, "base": base, "design": design, "an": an}


def _point_summary(ctx: pd.DataFrame, orc: pd.DataFrame, design: pd.DataFrame) -> pd.DataFrame:
    b = ctx.pivot_table(index=list(AN.CONTEXT), columns="action", values="brier")
    d = b.sub(b["A0"], axis=0).stack().rename("delta_brier_vs_A0").reset_index()
    m = ctx.merge(d, on=[*AN.CONTEXT, "action"])
    g = m.groupby(["point_id", "arm", "action"], sort=True)
    out = g.agg(
        models=("model_id", "nunique"),
        brier_mean=("brier", "mean"),
        brier_sd_across_models=("brier", "std"),
        delta_brier_mean=("delta_brier_vs_A0", "mean"),
        delta_brier_sd=("delta_brier_vs_A0", "std"),
        ece_mean=("ece", "mean"),
        auprc_mean=("auprc", "mean"),
        f1_mean=("f1", "mean"),
    ).reset_index()
    share = (
        orc.groupby(["point_id", "arm"])
        .preferred.value_counts(normalize=True)
        .rename("preferred_share")
        .reset_index()
        .rename(columns={"preferred": "action"})
    )
    out = out.merge(share, on=["point_id", "arm", "action"], how="left").fillna(
        {"preferred_share": 0.0}
    )
    return out.merge(design[["point_id", "gate_plot", "region"]], on="point_id")


def _preferred_by_point(orc: pd.DataFrame, design: pd.DataFrame) -> pd.DataFrame:
    counts = orc.pivot_table(
        index=["point_id", "arm"], columns="preferred", values="model_id", aggfunc="count"
    ).reindex(columns=list(ACTIONS), fill_value=0)
    counts = counts.fillna(0).astype(int).add_prefix("n_")
    counts["distinct_actions"] = (counts > 0).sum(axis=1)
    counts["majority"] = counts[[f"n_{a}" for a in ACTIONS]].idxmax(axis=1).str[2:]
    counts["majority_share"] = counts[[f"n_{a}" for a in ACTIONS]].max(axis=1) / counts[
        [f"n_{a}" for a in ACTIONS]
    ].sum(axis=1)
    return (
        counts.reset_index()
        .merge(design, on="point_id")
        .sort_values(["point_id", "arm"])
        .reset_index(drop=True)
    )


def _structure_summary(an: dict) -> pd.DataFrame:
    rows = []
    for split, o in an["context"].items():
        o = o.assign(struct_id=o.model_id.map(an["struct_of"]))
        for (s, arm), g in [
            *o.groupby(["struct_id", "arm"]),
            *(((s, "all"), g) for s, g in o.groupby("struct_id")),
        ]:
            shares = g.preferred.value_counts(normalize=True)
            rows.append(
                {
                    "split": split,
                    "struct_id": s,
                    "arm": arm,
                    "contexts": len(g),
                    **{f"share_{a}": float(shares.get(a, 0.0)) for a in ACTIONS},
                }
            )
    out = pd.DataFrame(rows)
    miss = pd.DataFrame(
        [
            {"split": split, "struct_id": s, "arm": "all", "noise_only_miss": v}
            for split, d in an["noise_only"].items()
            for s, v in d["per_structure"].items()
        ]
    )
    return out.merge(miss, on=["split", "struct_id", "arm"], how="left")


def _region_summary(an: dict) -> pd.DataFrame:
    rows = []
    for split, o in an["context"].items():
        for (reg, arm), g in o.groupby(["region", "arm"]):
            shares = g.preferred.value_counts(normalize=True)
            rows.append(
                {
                    "split": split,
                    "region": reg,
                    "arm": arm,
                    "contexts": len(g),
                    **{f"share_{a}": float(shares.get(a, 0.0)) for a in ACTIONS},
                    "improvable_share": float((g.min_brier <= 0.9 * g.brier_A0).mean()),
                }
            )
    return pd.DataFrame(rows)


def render_report(rep: dict) -> dict[str, str]:
    an, design, study = rep["an"], rep["design"], rep["study"]
    out: dict[str, str] = {}
    for split in ("train", "val"):
        out[T + f"p5c_point_summary_{split}.csv"] = _csv(
            _point_summary(an["context_means"][split], an["context"][split], design)
        )
        out[T + f"p5c_preferred_by_point_{split}.csv"] = _csv(
            _preferred_by_point(an["context"][split], design)
        )
    out[T + "p5c_policy_eval.csv"] = _csv(an["policy_eval"])
    out[T + "p5c_eps_sensitivity.csv"] = _csv(an["eps_sensitivity"])
    out[T + "p5c_structure_summary.csv"] = _csv(_structure_summary(an))
    out[T + "p5c_region_summary.csv"] = _csv(_region_summary(an))
    out[T + "p5c_budget_effect.csv"] = _csv(an["budget_effect"])
    out[T + "p5c_variance_decomposition.csv"] = _csv(an["variance_decomposition"])
    out[T + "p5c_probe_validity.csv"] = _csv(an["probe_validity"])
    g = an["g3c"]
    out[T + "p5c_metadata.json"] = _json(
        {
            "study_id": study.study_id,
            "g3c": {
                "verdict": g["verdict"],
                "fail_conditions": g["fail_conditions"],
                "pass_criteria": g["pass_criteria"],
                "metrics": g["metrics"],
            },
            "rules": an["rules"],
            "best_rule_val": an["best_rule_val"],
            "best_universal_train": an["best_universal_train"],
            "preferred_shares": an["shares"],
            "noise_only": an["noise_only"],
            "stability": an["stability"],
            "structure_association": an["structure_association"],
            "notes": {
                "test_split": "sealed in the lockbox; not analysed in Phase 5C",
                "preferred_action": "cost-aware Oracle (descriptive): cheapest action within "
                f"{study.preferred_relative_tolerance:.0%} of the minimum context-mean Brier",
                "noise_only": "offline upper bound using the TRUE noise point; never a policy",
                "design": "anchor-severity interpolation of the Phase 3B [RR] anchors; the "
                "readout asymmetry component is a synthetic stress-test assumption (O20)",
            },
        }
    )
    return out
