"""Phase 7 validation comparison and the one-time final test (PREREG_FINAL.md).

The deployable policy is the frozen Phase 5C rule R_thr (parameters in p5c_metadata.json,
fitted on 5C train). Comparators are fixed in advance: universal policies, R_cat, R_obs, four
learned comparators with fixed hyper-parameters fitted on 5C TRAIN replicates only, and the
Oracle. Every policy is evaluated per replicate with the registered failure / material-failure /
regret definitions (``qtrace.counterfactual.mixed_analysis``); uncertainty is a two-stage
cluster bootstrap (structures, then models). The same frozen policies are applied unchanged to
the Phase 5B environment (categorical noise; ``condition`` plays the role of ``point_id``).
"""

from __future__ import annotations

import hashlib

import pandas as pd

from qtrace.controller.learned import ACTIONS, FittedPolicy, Spec, benefit_targets, fit_policy
from qtrace.counterfactual import mixed_analysis as AN
from qtrace.counterfactual.features import mixed_controller_table
from qtrace.features import load_registry

LEARNED_SPECS: dict[str, Spec] = {
    "L_logistic": Spec("logistic", "classify", (("C", 1.0),)),
    "L_tree3": Spec("tree", "classify", (("max_depth", 3), ("min_leaf", 50))),
    "L_gbt": Spec("gbt", "classify", (("max_depth", 4), ("learning_rate", 0.1), ("max_iter", 200))),
    "L_gbt_benefit": Spec(
        "gbt", "benefit", (("max_depth", 4), ("learning_rate", 0.1), ("max_iter", 200))
    ),
}
RULES = ("R_cat", "R_thr", "R_obs")
PRIMARY = "R_thr"
ENDPOINTS = ("fail", "material", "rel_brier_regret", "cost_regret_S", "total_shots_per_inference")


def rules_from_json(rules: dict) -> dict:
    """Frozen rules as stored in JSON (cell keys become strings) -> the in-memory form."""
    return {
        name: {
            key: {**p, "cells": {int(c): a for c, a in p["cells"].items()}}
            for key, p in params.items()
        }
        for name, params in rules.items()
    }


def from_5b(df: pd.DataFrame) -> pd.DataFrame:
    """Phase 5B replicate rows in the Phase 5C layout (condition -> point; RM9 dropped)."""
    out = df[df.action.isin(ACTIONS)].copy()
    out["point_id"] = out["condition"]
    out["gate_plot"] = out["condition"]
    return out


def static_map(statics: pd.DataFrame, base) -> dict[str, dict]:
    cols = [c for c in base.static_features if c != "shots_per_circuit"]
    return statics.set_index("model_id")[cols].to_dict("index")


def features(dec: pd.DataFrame, smap: dict, base, study) -> tuple[pd.DataFrame, pd.DataFrame]:
    return mixed_controller_table(dec, smap, base, study, load_registry())


def fit_learned(
    dec: pd.DataFrame, orc: pd.DataFrame, smap: dict, base, study, eps: float, seed: int
) -> dict[str, FittedPolicy]:
    """The pre-specified learned comparators, fitted on TRAIN replicates only."""
    keys, feats = features(dec, smap, base, study)
    lab = keys.merge(orc, on=list(AN.CONTEXT), how="left")
    target = lab["preferred"].reset_index(drop=True)
    benefit = benefit_targets(lab).reset_index(drop=True)
    return {
        name: fit_policy(spec, feats, target, benefit, eps, tuple(base.cost_order), seed)
        for name, spec in LEARNED_SPECS.items()
    }


def choose(policy: FittedPolicy, dec: pd.DataFrame, smap: dict, base, study) -> pd.DataFrame:
    keys, feats = features(dec, smap, base, study)
    out = keys[list(AN.DECISION)].copy()
    out["choice"] = policy.choose(feats)
    return out


def fingerprint(choices: pd.DataFrame) -> str:
    """Order-independent SHA-256 of a policy's decisions."""
    c = choices.sort_values(list(AN.DECISION), kind="stable")
    text = "\n".join(
        "|".join(map(str, r))
        for r in c[[*AN.DECISION, "choice"]].itertuples(index=False, name=None)
    )
    return hashlib.sha256(text.encode()).hexdigest()


def all_choices(dec, orc, smap, statics, rules, learned, base, study) -> dict[str, pd.DataFrame]:
    out = {f"always_{a}": AN.universal(dec, a) for a in ACTIONS}
    for name in RULES:
        out[name] = AN.apply_rule(name, rules[name], dec, statics, study)
    for name, pol in learned.items():
        out[name] = choose(pol, dec, smap, base, study)
    oracle = dec[list(AN.DECISION)].merge(orc[[*AN.CONTEXT, "preferred"]], on=list(AN.CONTEXT))
    out["oracle"] = oracle.rename(columns={"preferred": "choice"})
    return out


def _secondary(choice: pd.DataFrame, ctx: pd.DataFrame) -> pd.DataFrame:
    """ECE, F1@tau and AUPRC of the chosen action (context means)."""
    m = ctx[[*AN.CONTEXT, "action", "ece", "f1", "auprc"]].rename(columns={"action": "choice"})
    return choice.merge(m, on=[*AN.CONTEXT, "choice"], how="left")


def evaluate_environment(
    df: pd.DataFrame,
    costs: pd.DataFrame,
    statics: pd.DataFrame,
    rules: dict,
    learned: dict,
    base,
    study,
    rng,
    n_boot: int,
) -> dict:
    """All frozen policies on one environment/split; tables + paired differences vs R_thr."""
    eps = study.preferred_relative_tolerance
    order = tuple(base.cost_order)
    ctx = AN.context_means(df)
    orc = AN.oracle(ctx, eps, order)
    dec = AN.decisions_frame(df)
    smap = static_map(statics, base)
    shots = AN.shots_table(costs)
    struct_of = dict(df[["model_id", "struct_id"]].drop_duplicates().itertuples(index=False))
    choices = all_choices(dec, orc, smap, statics, rules, learned, base, study)
    evs = {}
    for name, ch in choices.items():
        probing = name in RULES or name in learned
        ev = AN.evaluate(ch, orc, shots, study, eps, probing)
        sec = _secondary(ch, ctx)
        evs[name] = ev.merge(sec[[*AN.DECISION, "ece", "f1", "auprc"]], on=list(AN.DECISION))
    rows = []
    for name, ev in evs.items():
        for arm, sub in [("all", ev), *sorted(ev.groupby("arm"))]:
            row = {"policy": name, "arm": arm, **AN.summarize(sub)}
            row |= {f"mean_{k}": float(sub[k].mean()) for k in ("ece", "f1", "auprc")}
            if arm == "all":
                ci = AN.cluster_ci(
                    sub, struct_of, ("fail", "material", "rel_brier_regret"), rng, n_boot
                )
                for k, (lo, hi) in ci.items():
                    row[f"{k}_ci_lo"], row[f"{k}_ci_hi"] = lo, hi
            rows.append(row)
    paired = []
    ref = evs[PRIMARY].set_index(list(AN.DECISION))
    for name, ev in evs.items():
        if name == PRIMARY:
            continue
        other = ev.set_index(list(AN.DECISION)).loc[ref.index]
        d = pd.DataFrame(
            {
                "model_id": ref.index.get_level_values("model_id"),
                **{
                    k: ref[k].to_numpy(dtype=float) - other[k].to_numpy(dtype=float)
                    for k in ENDPOINTS
                },
            }
        )
        ci = AN.cluster_ci(d, struct_of, ENDPOINTS, rng, n_boot)
        paired.append(
            {
                "comparator": name,
                **{f"diff_{k}": float(d[k].mean()) for k in ENDPOINTS},
                **{f"diff_{k}_ci_lo": ci[k][0] for k in ENDPOINTS},
                **{f"diff_{k}_ci_hi": ci[k][1] for k in ENDPOINTS},
            }
        )
    by_struct = []
    for name, ev in evs.items():
        e = ev.assign(struct_id=ev.model_id.map(struct_of))
        for s, g in e.groupby("struct_id"):
            by_struct.append(
                {
                    "policy": name,
                    "struct_id": s,
                    "failure": float(g.fail.mean()),
                    "material_failure": float(g.material.mean()),
                    "mean_rel_brier_regret": float(g.rel_brier_regret.mean()),
                }
            )
    return {
        "policies": pd.DataFrame(rows),
        "paired_vs_rthr": pd.DataFrame(paired),
        "by_structure": pd.DataFrame(by_struct),
        "fingerprints": {n: fingerprint(choices[n]) for n in learned},
        "preferred_shares": {
            a: float(v) for a, v in orc.preferred.value_counts(normalize=True).items()
        },
    }


def hypotheses(res5c: dict, res5b: dict | None, h) -> dict:
    """The pre-specified final hypotheses (PREREG_FINAL.md §6) from the evaluated tables."""
    p = res5c["policies"].set_index(["policy", "arm"])
    r = p.loc[(PRIMARY, "all")]
    h1 = bool(
        r.material_failure <= h["h1_max_material"]
        and r.mean_rel_brier_regret <= h["h1_max_rel_brier_regret"]
    )
    paired = res5c["paired_vs_rthr"].set_index("comparator")
    # Paired differences are R_thr minus comparator (per decision, then averaged):
    # diff_material > 0 means the comparator fails materially LESS; diff_total_shots > 0
    # means the comparator spends FEWER shots per inference.
    meaningful = {}
    for name in LEARNED_SPECS:
        q = paired.loc[name]
        more_reliable = bool(
            q.diff_material >= h["h2_min_material_gain"] and q.diff_material_ci_lo > 0
        )
        cheaper = bool(
            q.diff_total_shots_per_inference
            >= h["h2_min_shot_saving"] * r.mean_total_shots_per_inference
            and q.diff_material >= -h["h2_material_slack"]
        )
        meaningful[name] = more_reliable or cheaper
    universal = [f"always_{a}" for a in ACTIONS]
    h3 = bool(
        r.material_failure < min(p.loc[(u, "all")].material_failure for u in universal)
        and r.mean_total_shots_per_inference
        <= p.loc[("always_A3", "all")].mean_total_shots_per_inference
    )
    out = {
        "H1_simple_rule_near_oracle": h1,
        "H2_learning_adds_no_meaningful_value": not any(meaningful.values()),
        "H2_meaningful_by_comparator": meaningful,
        "H3_rule_beats_fixed_policies": h3,
        "rthr_material_failure": float(r.material_failure),
        "rthr_rel_brier_regret": float(r.mean_rel_brier_regret),
    }
    if res5b is not None:
        b = res5b["policies"].set_index(["policy", "arm"]).loc[(PRIMARY, "all")]
        out["H4_rule_transfers_to_categorical_noise"] = bool(
            b.material_failure <= h["h4_max_material"]
        )
        out["rthr_material_failure_5b"] = float(b.material_failure)
    return out


def learned_seed(master: int) -> int:
    from qtrace.utils.seeds import derive_seed

    return int(derive_seed(master, "policy", "p7-learned-comparators") % (2**31 - 1))
