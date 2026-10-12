"""Phase 5B report: registered analysis tables, Q1-Q6 answers and G3B (train/val only)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from qtrace.counterfactual import analysis as AN
from qtrace.counterfactual.features import controller_table
from qtrace.counterfactual.study import T, _csv, _json, load_counterfactual_study
from qtrace.features import load_registry

METRICS_D = ("brier", "f1", "auprc", "ece")


def run_report(root: Path) -> dict:
    resolved, study, pool, mit, profiles = load_counterfactual_study()
    processed = root / study.processed_dir
    train, val = AN.load_split(processed, "train"), AN.load_split(processed, "val")
    an = AN.analyse(train, val, study, resolved.spec.seeds.shots)
    static = pd.read_csv(root / T / "p5b_static_features.csv")
    costs = pd.read_csv(root / T / "p5b_costs.csv")
    return {"study": study, "an": an, "static": static, "costs": costs}


def _context_features(rep: pd.DataFrame, static: pd.DataFrame, study) -> pd.DataFrame:
    reg = load_registry()
    cols = [c for c in study.static_features if c != "shots_per_circuit"]
    st = static.set_index("model_id")[cols].to_dict("index")
    keys, feats = controller_table(rep, st, study, reg)
    both = pd.concat([keys, feats], axis=1)
    agg = both.groupby(["model_id", "condition", "arm"], sort=True)
    means = agg[list(study.probe_features)].mean().add_suffix("_mean")
    sds = agg[["probe_readout_error_mean", "probe_gate_contraction"]].std(ddof=1).add_suffix("_sd")
    first = agg[[c for c in feats.columns if c not in study.probe_features]].first()
    return pd.concat([first, means, sds], axis=1).reset_index()


def render_report(rep: dict) -> dict[str, str]:
    study, an, static, costs = rep["study"], rep["an"], rep["static"], rep["costs"]
    out: dict[str, str] = {}
    spi = costs.set_index(["model_id", "arm", "action"])
    axes = static.set_index("model_id")

    # ---- context-level outcomes, preferences and features (train / val)
    for split in ("train", "val"):
        o = an[split]
        ctx = o["ctx"].copy()
        ctx["shots_per_inference"] = [
            spi.loc[(m, a, v), "shots_per_inference"]
            for m, a, v in zip(ctx.model_id, ctx.arm, ctx.action, strict=True)
        ]
        if split == "train":
            for arm in ("s1024", "s4096"):
                out[T + f"p5b_context_outcomes_train_{arm}.csv"] = _csv(ctx[ctx.arm == arm])
        else:
            out[T + "p5b_context_outcomes_val.csv"] = _csv(ctx)
        modal = (
            o["rep"]
            .groupby(list(AN.CONTEXT))
            .category.agg(lambda s: s.value_counts().index[0])
            .rename("probe_category")
        )
        stab = (
            o["rep"]
            .groupby(list(AN.CONTEXT))
            .category.agg(lambda s: s.value_counts(normalize=True).iloc[0])
            .rename("probe_category_stability")
        )
        pref = (
            o["pref"]
            .merge(modal.reset_index(), on=list(AN.CONTEXT))
            .merge(stab.reset_index(), on=list(AN.CONTEXT))
        )
        out[T + f"p5b_preferred_actions_{split}.csv"] = _csv(pref)
        o["features"] = _context_features(o["rep"], static, study)
        out[T + f"p5b_context_features_{split}.csv"] = _csv(o["features"])
        o["pref_full"] = pref

    # ---- Table C: outcome summary by action
    rows = []
    for split in ("train", "val"):
        ctx = an[split]["ctx"]
        for (cond, arm, act), g in ctx.groupby(["condition", "arm", "action"]):
            c = [spi.loc[(m, arm, act)] for m in g.model_id]
            rows.append(
                {
                    "split": split,
                    "condition": cond,
                    "arm": arm,
                    "action": act,
                    "contexts": len(g),
                    **{
                        m: g[m].mean()
                        for m in (
                            "brier",
                            "ece",
                            "f1",
                            "precision",
                            "recall",
                            "auprc",
                            "auroc",
                            "spearman",
                            "kendall",
                        )
                    },
                    "shots_per_inference": float(np.mean([x["shots_per_inference"] for x in c])),
                    "cx_shots_per_inference": float(
                        np.mean([x["cx_shots_per_inference"] for x in c])
                    ),
                }
            )
    table_c = pd.DataFrame(rows)
    out[T + "p5b_action_summary.csv"] = _csv(table_c)

    # ---- Table D: benefit distributions across models (context-mean deltas vs A0)
    rows = []
    for split in ("train", "val"):
        ctx = an[split]["ctx"]
        piv = {
            m: ctx.pivot_table(index=list(AN.CONTEXT), columns="action", values=m)
            for m in METRICS_D
        }
        for a in AN.ACTIONS[1:]:
            for m in METRICS_D:
                d = (piv[m][a] - piv[m]["A0"]).rename("d").reset_index()
                for (cond, arm), g in d.groupby(["condition", "arm"]):
                    v = g.d.to_numpy()
                    rows.append(
                        {
                            "split": split,
                            "action": a,
                            "metric": m,
                            "condition": cond,
                            "arm": arm,
                            "models": len(v),
                            "mean": v.mean(),
                            "sd": v.std(ddof=1),
                            "min": v.min(),
                            "q05": np.quantile(v, 0.05),
                            "q50": np.quantile(v, 0.5),
                            "q95": np.quantile(v, 0.95),
                            "max": v.max(),
                        }
                    )
    out[T + "p5b_benefit_distribution.csv"] = _csv(pd.DataFrame(rows))

    # ---- Tables E/F/G: preferred-action frequencies
    def shares(frame, by):
        rows = []
        for key, g in frame.groupby(by):
            key = key if isinstance(key, tuple) else (key,)
            cnt = g.preferred.value_counts(normalize=True)
            rel = g.reliability_best.value_counts(normalize=True)
            for a in AN.ACTIONS:
                rows.append(
                    {
                        **dict(zip(by, key, strict=True)),
                        "action": a,
                        "contexts": len(g),
                        "share_preferred": cnt.get(a, 0.0),
                        "share_reliability_best": rel.get(a, 0.0),
                    }
                )
        return rows

    e_rows, f_rows, g_rows = [], [], []
    for split in ("train", "val"):
        p = an[split]["pref_full"].copy()
        for r in shares(p, ["condition", "arm"]):
            e_rows.append({"split": split, **r})
        p = p.join(axes[list(AN.AXES)], on="model_id")
        for axis in AN.AXES:
            for r in shares(p.rename(columns={axis: "level"}), ["level"]):
                f_rows.append({"split": split, "axis": axis, **r, "level": str(r["level"])})
        for r in shares(p, ["arm"]):
            g_rows.append({"split": split, **r})
    out[T + "p5b_preferred_by_condition.csv"] = _csv(pd.DataFrame(e_rows))
    out[T + "p5b_preferred_by_family.csv"] = _csv(pd.DataFrame(f_rows))
    agree = []
    for split in ("train", "val"):
        p = an[split]["pref"]
        w = p.pivot_table(
            index=["model_id", "condition"], columns="arm", values="preferred", aggfunc="first"
        )
        agree.append(
            {
                "split": split,
                "model_condition_pairs": len(w),
                "same_preferred_both_arms": float((w.s1024 == w.s4096).mean()),
            }
        )
    out[T + "p5b_preferred_by_arm.csv"] = _csv(
        pd.concat([pd.DataFrame(g_rows), pd.DataFrame(agree)], ignore_index=True)
    )

    # ---- Table H: heterogeneity (train) + variance decomposition
    out[T + "p5b_heterogeneity.csv"] = _csv(an["heterogeneity"])
    out[T + "p5b_variance_decomposition.csv"] = _csv(an["variance"])

    # ---- Table I: Pareto (mean over models; brier vs shots per inference)
    rows = []
    for _, g in table_c.groupby(["split", "condition", "arm"]):
        for r in g.itertuples():
            dominated = any(
                (
                    o.brier <= r.brier
                    and o.shots_per_inference <= r.shots_per_inference
                    and (o.brier < r.brier or o.shots_per_inference < r.shots_per_inference)
                )
                for o in g.itertuples()
            )
            rows.append(
                {
                    "split": r.split,
                    "condition": r.condition,
                    "arm": r.arm,
                    "action": r.action,
                    "brier": r.brier,
                    "f1": r.f1,
                    "shots_per_inference": r.shots_per_inference,
                    "cx_shots_per_inference": r.cx_shots_per_inference,
                    "pareto_optimal": not dominated,
                }
            )
    out[T + "p5b_pareto.csv"] = _csv(pd.DataFrame(rows))

    # ---- predictability: feature-benefit association, rule, universal failures
    rows = []
    tr = an["train"]
    feats = an["train"]["features"]
    pv = tr["ctx"].pivot_table(index=list(AN.CONTEXT), columns="action", values="brier")
    merged = feats.set_index(list(AN.CONTEXT))
    numeric = [c for c in merged.columns if merged[c].dtype.kind in "fi"]
    for a in AN.ACTIONS[1:]:
        d = (pv[a] - pv["A0"]).loc[merged.index]
        for c in numeric:
            if merged[c].nunique() > 1:
                rho = stats.spearmanr(merged[c], d).statistic
                rows.append(
                    {
                        "kind": "spearman_feature_vs_delta_brier",
                        "action": a,
                        "feature": c,
                        "value": float(rho),
                    }
                )
    for split in ("train", "val"):
        for a, f in an[split]["universal_failure"].items():
            rows.append(
                {"kind": f"universal_failure_{split}", "action": a, "feature": "", "value": f}
            )
        rows.append(
            {
                "kind": f"category_rule_failure_{split}",
                "action": "",
                "feature": "",
                "value": an[split]["rule_failure"],
            }
        )
    for k, v in an["rule"].items():
        rows.append(
            {"kind": "category_rule_mapping_train", "action": v, "feature": k, "value": np.nan}
        )
    out[T + "p5b_predictability.csv"] = _csv(pd.DataFrame(rows))

    # ---- metadata, Q1-Q6, G3B
    g = an["g3b"]
    m = g["metrics"]
    het = an["heterogeneity"]
    var = an["variance"].set_index("action")
    tr_sh = an["train"]["shares"]
    pref_tr = an["train"]["pref"]
    w = pref_tr.pivot_table(
        index=["model_id", "condition"], columns="arm", values="preferred", aggfunc="first"
    )
    intervene = pref_tr[pref_tr.preferred != "A0"]
    answers = {
        "Q1_benefit_varies_across_models": {
            "heterogeneous_cell_fraction": m["heterogeneous_cell_fraction"],
            "median_icc": float(het.icc.median()),
            "eta2_model_by_action": var.eta2_model.to_dict(),
        },
        "Q2_context_vs_structure": var.to_dict("index"),
        "Q3_shot_budget_changes_preferred_action": {
            "fraction_model_condition_pairs_changed": float((w.s1024 != w.s4096).mean())
        },
        "Q4_extra_shots_preferred": {
            "share_all_contexts": float(tr_sh.get("A4", 0.0)),
            "share_among_intervention_contexts": float((intervene.preferred == "A4").mean())
            if len(intervene)
            else 0.0,
        },
        "Q5_no_intervention_preferred": {"share": float(tr_sh.get("A0", 0.0))},
        "Q6_residual_after_probes": {
            "category_rule_failure_val": m["rule_failure_val"],
            "best_universal_failure_val": m["best_universal_failure_val"],
            "rule_gain_val": m["rule_gain_val"],
            "structure_association_p": m["structure_association_p"],
            "structure_association_mi": m["structure_association_mi"],
        },
    }
    out[T + "p5b_metadata.json"] = _json(
        {
            "study_id": study.study_id,
            "g3b": g,
            "answers": answers,
            "preferred_shares_train": tr_sh.to_dict(),
            "preferred_shares_val": an["val"]["shares"].to_dict(),
            "category_rule_train": an["rule"],
            "notes": {
                "test_split": "sealed in the lockbox; not analysed in Phase 5B",
                "preferred_action": "cost-aware Oracle (descriptive): cheapest action within "
                "10% of the minimum context-mean Brier; never a controller feature",
                "thresholds": "per-model tau frozen in Phase 5A on vqc_val (optimistic there); "
                "never tuned on ctrl_*, under noise or by action",
                "synthetic_profiles": "ar-020/ar-050 are synthetic asymmetric readout stress-test "
                "profiles, not device calibration data (O20 open)",
            },
        }
    )
    return out
