"""Phase 5C registered analysis (PREREG_P5C §8-12): TRAIN and VAL only; the test split is sealed.

A *context* is model x noise point x shot budget. Replicates give uncertainty; no statistic
treats replicates, transactions or action rows as independent model-level observations.

Oracle (as Phase 5B): p*(c) is the cheapest action (registered cost order) whose context-
mean Brier is <= (1 + eps) x the minimum over A0-A4. Because p* is the *cheapest* action
within tolerance, any other choice either breaks the tolerance (cheaper) or overspends
(costlier): a decision fails exactly when it differs from p*. A failure is *material* when
the Brier exceeds (1 + 2 eps) x min or the choice costs >= 1 x S more shots per inference.

Simple probe rules are fitted on TRAIN replicates and evaluated per replicate:
- R_cat: the Phase 5B a-priori categories (readout error >= 0.005; contraction <= 0.90);
- R_thr: the same decision-list form with per-budget thresholds chosen on train;
- R_obs: R_thr fitted separately per readout observable (a legitimate static descriptor).
Each cell takes the majority train p* (ties to the cheaper action), which minimises train
failure; thresholds minimise train failure over a registered quantile grid.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from qtrace.config.schemas import CounterfactualStudyConfig, MixedNoiseStudyConfig
from qtrace.counterfactual.analysis import conditional_mi
from qtrace.counterfactual.mixed_generate import ACTIONS, METRICS
from qtrace.utils.seeds import make_rng

CONTEXT = ("model_id", "point_id", "arm")
DECISION = (*CONTEXT, "replicate")


class LockboxError(RuntimeError):
    """Test-split outcomes may not be read before the frozen final evaluation."""


def load_split(processed_dir: Path, split: str) -> pd.DataFrame:
    if split not in ("train", "val"):
        raise LockboxError(f"split {split!r} is sealed or unknown; only train/val are analysed")
    frame = pd.read_parquet(processed_dir / f"mixed_{split}.parquet")
    if set(frame["split"]) != {split}:
        raise LockboxError("file content does not match its split")
    return frame


# ------------------------------------------------------------------ oracle and costs


def context_means(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby([*CONTEXT, "action"], sort=True)
    out = g[list(METRICS)].mean()
    out["brier_sd"] = g["brier"].std(ddof=1)
    return out.reset_index()


def oracle(ctx: pd.DataFrame, eps: float, cost_order: tuple[str, ...]) -> pd.DataFrame:
    """Wide per-context Brier, minimum, p* and the reliability-best action."""
    b = ctx.pivot_table(index=list(CONTEXT), columns="action", values="brier")[list(ACTIONS)]
    mn = b.min(axis=1)
    ok = b.le((1 + eps) * mn, axis=0)
    p_star = ok[list(cost_order)].idxmax(axis=1)  # first action in cost order within tolerance
    rank = {a: i for i, a in enumerate(cost_order)}
    best = b.apply(lambda r: min(ACTIONS, key=lambda a: (r[a], rank[a])), axis=1)
    out = b.add_prefix("brier_")
    out["min_brier"], out["preferred"], out["reliability_best"] = mn, p_star, best
    return out.reset_index()


def shots_table(costs: pd.DataFrame) -> pd.DataFrame:
    """Per (model, arm): shots and CX-shots per inference of every action, probe shots, S."""
    piv = costs.pivot_table(
        index=["model_id", "arm"], columns="action", values="shots_per_inference"
    )[list(ACTIONS)].add_prefix("shots_")
    cx = costs.pivot_table(
        index=["model_id", "arm"], columns="action", values="cx_shots_per_inference"
    )[list(ACTIONS)].add_prefix("cx_")
    probe = costs.groupby(["model_id", "arm"])["probe_shots_per_inference"].first()
    s = costs.groupby(["model_id", "arm"])["shots_per_inference"].min()  # A0 = S
    out = piv.join(cx)
    out["probe_shots"], out["S"] = probe, s
    return out.reset_index()


# ------------------------------------------------------------------ decisions and failure


def decisions_frame(df: pd.DataFrame) -> pd.DataFrame:
    """One row per context replicate with its probe features (identical across actions)."""
    return df[df.action == "A0"].drop(columns=["action"]).reset_index(drop=True)


def evaluate(
    chosen: pd.DataFrame,
    orc: pd.DataFrame,
    shots: pd.DataFrame,
    study: MixedNoiseStudyConfig,
    eps: float,
    uses_probes: bool,
) -> pd.DataFrame:
    """Per-decision failure, material failure and regrets (chosen: DECISION keys + 'choice')."""
    m = chosen.merge(orc, on=list(CONTEXT), how="left").merge(
        shots, on=["model_id", "arm"], how="left"
    )
    idx = np.arange(len(m))

    def pick(prefix: str, col: str) -> np.ndarray:
        mat = m[[f"{prefix}{a}" for a in ACTIONS]].to_numpy()
        return mat[idx, m[col].map(ACTIONS.index).to_numpy()]

    b_a, b_p = pick("brier_", "choice"), pick("brier_", "preferred")
    s_a, s_p = pick("shots_", "choice"), pick("shots_", "preferred")
    cx_a = pick("cx_", "choice")
    mn, S = m.min_brier.to_numpy(), m.S.to_numpy()
    out = m[[*DECISION, "choice", "preferred"]].copy()
    out["fail"] = m.choice.to_numpy() != m.preferred.to_numpy()
    out["material"] = (b_a > (1 + study.material_reliability_multiple * eps) * mn) | (
        s_a - s_p >= study.material_overspend_shots_fraction * S - 1e-9
    )
    out["reliability_fail"] = b_a > (1 + eps) * mn
    out["brier"] = b_a
    out["rel_brier_regret"] = (b_a - b_p) / mn
    out["cost_regret_S"] = (s_a - s_p) / S
    out["action_shots_per_inference"] = s_a
    out["total_shots_per_inference"] = s_a + (m.probe_shots.to_numpy() if uses_probes else 0.0)
    out["cx_shots_per_inference"] = cx_a
    return out


def summarize(ev: pd.DataFrame) -> dict:
    return {
        "decisions": int(len(ev)),
        "failure": float(ev.fail.mean()),
        "material_failure": float(ev.material.mean()),
        "reliability_failure": float(ev.reliability_fail.mean()),
        "mean_brier": float(ev.brier.mean()),
        "mean_rel_brier_regret": float(ev.rel_brier_regret.mean()),
        "mean_cost_regret_S": float(ev.cost_regret_S.mean()),
        "mean_total_shots_per_inference": float(ev.total_shots_per_inference.mean()),
        "mean_cx_shots_per_inference": float(ev.cx_shots_per_inference.mean()),
    }


def cluster_ci(ev: pd.DataFrame, struct_of: dict, cols: tuple[str, ...], rng, n_boot: int) -> dict:
    """Two-stage (structure, then model within structure) bootstrap 95% CIs of decision means."""
    per = ev.groupby("model_id")[list(cols)].agg(["sum", "count"])
    models = per.index.to_numpy()
    structs = np.array([struct_of[m] for m in models])
    keys = sorted(set(structs))
    groups = [np.flatnonzero(structs == s) for s in keys]
    sums = np.column_stack([per[(c, "sum")].to_numpy(dtype=float) for c in cols])
    cnt = per[(cols[0], "count")].to_numpy(dtype=float)
    draws = np.empty((n_boot, len(cols)))
    for b in range(n_boot):
        chosen = np.concatenate(
            [
                rng.choice(groups[s], size=len(groups[s]), replace=True)
                for s in rng.choice(len(keys), size=len(keys), replace=True)
            ]
        )
        draws[b] = sums[chosen].sum(axis=0) / cnt[chosen].sum()
    draws = {c: draws[:, j] for j, c in enumerate(cols)}
    return {
        c: (float(np.quantile(draws[c], 0.025)), float(np.quantile(draws[c], 0.975))) for c in cols
    }


# ------------------------------------------------------------------ simple rules


def _majority(codes: np.ndarray, rank: np.ndarray) -> int:
    counts = np.bincount(codes, minlength=len(ACTIONS))
    top = counts.max()
    return int(min(np.flatnonzero(counts == top), key=lambda a: rank[a]))


def _cells(ro: np.ndarray, ga: np.ndarray, t_r: float, t_g: float) -> np.ndarray:
    return 2 * (ro >= t_r).astype(int) + (ga <= t_g).astype(int)  # 0 none, 1 gate, 2 ro, 3 both


def fit_decision_list(
    ro: np.ndarray,
    ga: np.ndarray,
    target: np.ndarray,
    rank: np.ndarray,
    grid_r: np.ndarray,
    grid_g: np.ndarray,
) -> dict:
    """Thresholds (from the grids) and cell actions maximising train agreement with p*."""
    best = None
    k = len(ACTIONS)
    for t_r in grid_r:
        rbit = 2 * (ro >= t_r).astype(int)
        for t_g in grid_g:
            cell = rbit + (ga <= t_g).astype(int)
            counts = np.bincount(cell * k + target, minlength=4 * k).reshape(4, k)
            acc = counts.max(axis=1).sum()
            if best is None or acc > best[0]:
                best = (acc, float(t_r), float(t_g))
    _, t_r, t_g = best
    cell = _cells(ro, ga, t_r, t_g)
    fallback = _majority(target, rank)
    actions = {
        int(c): (_majority(target[cell == c], rank) if (cell == c).any() else fallback)
        for c in range(4)
    }
    return {"t_r": t_r, "t_g": t_g, "cells": {c: ACTIONS[a] for c, a in actions.items()}}


def fit_rules(
    dec: pd.DataFrame,
    orc: pd.DataFrame,
    statics: pd.DataFrame,
    study: MixedNoiseStudyConfig,
    base: CounterfactualStudyConfig,
    cost_order: tuple[str, ...],
) -> dict:
    """R_cat, R_thr and R_obs fitted on TRAIN decisions (replicate level)."""
    rank = np.array([list(cost_order).index(a) for a in ACTIONS])
    d = dec.merge(orc[[*CONTEXT, "preferred"]], on=list(CONTEXT)).merge(
        statics[["model_id", study.rules.group_descriptor]], on="model_id"
    )
    target = d.preferred.map(ACTIONS.index).to_numpy()
    rf, gf = study.rules.readout_feature, study.rules.gate_feature
    q = np.array(study.rules.threshold_quantiles)
    cat = base.probe_categories
    rules: dict = {"R_cat": {}, "R_thr": {}, "R_obs": {}}
    for arm in sorted(d.arm.unique()):
        a = (d.arm == arm).to_numpy()
        ro, ga = d.loc[a, rf].to_numpy(), d.loc[a, gf].to_numpy()
        rules["R_cat"][arm] = fit_decision_list(
            ro,
            ga,
            target[a],
            rank,
            np.array([cat.readout_error_min]),
            np.array([cat.gate_contraction_max]),
        )
        gr, gg = np.unique(np.quantile(ro, q)), np.unique(np.quantile(ga, q))
        rules["R_thr"][arm] = fit_decision_list(ro, ga, target[a], rank, gr, gg)
        for grp in sorted(d[study.rules.group_descriptor].unique()):
            b = a & (d[study.rules.group_descriptor] == grp).to_numpy()
            ro_b, ga_b = d.loc[b, rf].to_numpy(), d.loc[b, gf].to_numpy()
            gr_b, gg_b = np.unique(np.quantile(ro_b, q)), np.unique(np.quantile(ga_b, q))
            rules["R_obs"][f"{grp}|{arm}"] = fit_decision_list(
                ro_b, ga_b, target[b], rank, gr_b, gg_b
            )
    return rules


def apply_rule(
    name: str, rule: dict, dec: pd.DataFrame, statics: pd.DataFrame, study
) -> pd.DataFrame:
    rf, gf = study.rules.readout_feature, study.rules.gate_feature
    grp_col = study.rules.group_descriptor
    d = dec.merge(statics[["model_id", grp_col]], on="model_id", how="left")
    key = d[grp_col].astype(str) + "|" + d.arm if name == "R_obs" else d.arm
    choice = np.empty(len(d), dtype=object)
    for k, idx in key.groupby(key).groups.items():
        if k not in rule:  # every descriptor group of the pool occurs in train (registered)
            raise KeyError(f"no {name} parameters for {k}")
        p = rule[k]
        sub = d.loc[idx]
        cells = _cells(sub[rf].to_numpy(), sub[gf].to_numpy(), p["t_r"], p["t_g"])
        choice[d.index.get_indexer(idx)] = [p["cells"][int(c)] for c in cells]
    out = d[list(DECISION)].copy()
    out["choice"] = choice
    return out


def universal(dec: pd.DataFrame, action: str) -> pd.DataFrame:
    out = dec[list(DECISION)].copy()
    out["choice"] = action
    return out


# ------------------------------------------------------------------ residual structure


def noise_only_ceiling(orc: pd.DataFrame, struct_of: dict, cost_order) -> dict:
    """Best model-agnostic action per (noise point, arm), chosen ON the split (upper bound)."""
    rank = np.array([list(cost_order).index(a) for a in ACTIONS])
    o = orc.copy()
    o["code"] = o.preferred.map(ACTIONS.index)
    maj = o.groupby(["point_id", "arm"]).code.apply(lambda c: _majority(c.to_numpy(), rank))
    o["noise_only"] = [maj.loc[(p, a)] for p, a in zip(o.point_id, o.arm, strict=True)]
    o["miss"] = o.code != o.noise_only
    o["struct_id"] = o.model_id.map(struct_of)
    per_struct = o.groupby("struct_id").miss.mean()
    return {"overall": float(o.miss.mean()), "per_structure": per_struct.to_dict()}


def split_half_agreement(df: pd.DataFrame, eps: float, cost_order) -> float:
    reps = sorted(df.replicate.unique())
    first = df.replicate.isin(reps[: len(reps) // 2])
    a = oracle(context_means(df[first]), eps, cost_order).set_index(list(CONTEXT))
    b = oracle(context_means(df[~first]), eps, cost_order).set_index(list(CONTEXT))
    return float((a.preferred == b.preferred.loc[a.index]).mean())


def label_instability(df: pd.DataFrame, eps: float, cost_order, rng, n_boot: int) -> float:
    """Mean P(p* changes) when each context's replicates are resampled (paired across actions)."""
    piv = df.pivot_table(index=[*CONTEXT, "replicate"], columns="action", values="brier")[
        list(ACTIONS)
    ]
    reps = piv.index.get_level_values("replicate").nunique()
    x = piv.to_numpy().reshape(-1, reps, len(ACTIONS))  # contexts x replicates x actions
    order = [ACTIONS.index(a) for a in cost_order]

    def pref(mean: np.ndarray) -> np.ndarray:
        ok = mean <= (1 + eps) * mean.min(axis=1, keepdims=True)
        return np.array(order)[np.argmax(ok[:, order], axis=1)]

    full = pref(x.mean(axis=1))
    changed = np.zeros(len(x))
    for _ in range(n_boot):
        idx = rng.integers(0, reps, size=reps)
        changed += pref(x[:, idx, :].mean(axis=1)) != full
    return float((changed / n_boot).mean())


def structure_association(orc: pd.DataFrame, stratum: pd.Series, struct_of, rng, perms) -> dict:
    labels = orc.model_id.map(struct_of)
    obs = conditional_mi(orc.preferred, labels, stratum)
    models = sorted(orc.model_id.unique())
    s = np.array([struct_of[m] for m in models])
    count = 0
    for _ in range(perms):
        perm = dict(zip(models, rng.permutation(s), strict=True))
        count += conditional_mi(orc.preferred, orc.model_id.map(perm), stratum) >= obs - 1e-12
    return {"conditional_mi": float(obs), "p": (1 + count) / (1 + perms)}


def variance_decomposition(ctx: pd.DataFrame) -> pd.DataFrame:
    """Two-way (model x noise point) decomposition of context-mean dBrier, per action and arm."""
    b = ctx.pivot_table(index=list(CONTEXT), columns="action", values="brier")
    rows = []
    for a in ACTIONS[1:]:
        d = (b[a] - b["A0"]).rename("d").reset_index()
        for arm, g in d.groupby("arm"):
            x = g.pivot_table(index="model_id", columns="point_id", values="d").to_numpy()
            gm = x.mean()
            ss_t = np.sum((x - gm) ** 2)
            ss_c = x.shape[0] * np.sum((x.mean(axis=0) - gm) ** 2)
            ss_m = x.shape[1] * np.sum((x.mean(axis=1) - gm) ** 2)
            rows.append(
                {
                    "action": a,
                    "arm": arm,
                    "eta2_noise_point": ss_c / ss_t if ss_t > 0 else np.nan,
                    "eta2_model": ss_m / ss_t if ss_t > 0 else np.nan,
                    "eta2_model_x_point": (ss_t - ss_c - ss_m) / ss_t if ss_t > 0 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def spearman(a, b) -> float:
    return float(stats.spearmanr(a, b).statistic)


# ------------------------------------------------------------------ gate


def g3c_rule(m: dict, g) -> dict:
    """The registered G3C decision from the computed metrics (PREREG_P5C §12)."""
    fail = {
        "dominance": max(m["max_share_train"], m["max_share_val"]) >= g.fail_dominance_share,
        "rule_sufficient": m["best_rule_failure_val"] < g.fail_max_rule_failure,
        "negligible_regret": m["best_rule_material_failure_val"] < g.fail_max_rule_material_failure,
        "replicate_noise": m["split_half_agreement_train"] < g.fail_min_split_half_agreement,
    }
    passed = {
        "P1_multiple_actions": m["actions_useful_both"] >= g.pass_min_actions_useful,
        "P2_rule_not_near_perfect": m["best_rule_failure_val"] >= g.pass_min_rule_failure,
        "P3_model_noise_interaction": (
            m["noise_only_failure_val"] >= g.pass_min_noise_only_failure
            and m["noise_only_structures_val"] >= g.pass_min_structures_val
            and m["noise_only_structures_train"] >= g.pass_min_structures_train
        ),
        "P4_beyond_replicate_noise": m["best_rule_failure_val"] - m["label_instability_val"]
        >= g.pass_min_failure_above_label_noise,
        "P5_meaningful_gap": m["best_rule_material_failure_val"] >= g.pass_min_material_failure,
        "P6_sample_support": m["action_support_ok"]
        and m["best_rule_max_structure_failure_share_val"]
        <= g.pass_max_single_structure_failure_share,
    }
    if any(fail.values()):
        verdict = "FAIL"
    elif all(passed.values()):
        verdict = "PASS"
    else:
        verdict = "CONDITIONAL"
    return {"verdict": verdict, "fail_conditions": fail, "pass_criteria": passed, "metrics": m}


def analyse(
    train: pd.DataFrame,
    val: pd.DataFrame,
    design: pd.DataFrame,
    costs: pd.DataFrame,
    statics: pd.DataFrame,
    study: MixedNoiseStudyConfig,
    base: CounterfactualStudyConfig,
    master_seed: int,
) -> dict:
    """The registered Phase 5C analysis on train and val (everything the report renders)."""
    order = tuple(base.cost_order)
    eps = study.preferred_relative_tolerance
    g = study.g3c
    struct_of = dict(
        pd.concat([train, val])[["model_id", "struct_id"]].drop_duplicates().itertuples(index=False)
    )
    shots = shots_table(costs)
    out: dict = {"splits": {}}
    ctx = {s: context_means(d) for s, d in (("train", train), ("val", val))}
    orc = {s: oracle(c, eps, order) for s, c in ctx.items()}
    dec = {s: decisions_frame(d) for s, d in (("train", train), ("val", val))}
    rules = fit_rules(dec["train"], orc["train"], statics, study, base, order)
    out["rules"] = rules

    # policies (rules fitted on train; universal policies need no fitting)
    policies: dict[str, dict] = {}
    for split in ("train", "val"):
        evs = {}
        for a in ACTIONS:
            evs[f"always_{a}"] = evaluate(
                universal(dec[split], a), orc[split], shots, study, eps, False
            )
        for name in ("R_cat", "R_thr", "R_obs"):
            evs[name] = evaluate(
                apply_rule(name, rules[name], dec[split], statics, study),
                orc[split],
                shots,
                study,
                eps,
                True,
            )
        oracle_choice = dec[split][list(DECISION)].merge(
            orc[split][[*CONTEXT, "preferred"]], on=list(CONTEXT)
        )
        evs["oracle"] = evaluate(
            oracle_choice.rename(columns={"preferred": "choice"}),
            orc[split],
            shots,
            study,
            eps,
            False,
        )
        policies[split] = evs
    best_universal = min(
        ACTIONS, key=lambda a: (policies["train"][f"always_{a}"].fail.mean(), order.index(a))
    )
    best_rule = min(("R_cat", "R_thr", "R_obs"), key=lambda r: (policies["val"][r].fail.mean(), r))
    out["best_universal_train"], out["best_rule_val"] = best_universal, best_rule

    rng = make_rng(master_seed, "bootstrap", study.bootstrap_seed_key)
    table = []
    for split, evs in policies.items():
        for name, ev in evs.items():
            for arm, sub in [("all", ev), *sorted(ev.groupby("arm"))]:
                row = {"split": split, "policy": name, "arm": arm, **summarize(sub)}
                if (
                    split == "val"
                    and arm == "all"
                    and name
                    in (
                        "R_cat",
                        "R_thr",
                        "R_obs",
                        f"always_{best_universal}",
                    )
                ):
                    ci = cluster_ci(
                        sub,
                        struct_of,
                        ("fail", "material", "rel_brier_regret", "cost_regret_S"),
                        rng,
                        study.cluster_bootstrap,
                    )
                    for k, (lo, hi) in ci.items():
                        row[f"{k}_ci_lo"], row[f"{k}_ci_hi"] = lo, hi
                table.append(row)
    out["policy_eval"] = pd.DataFrame(table)

    # tolerance sensitivity: p* shares and rule failures re-derived at each eps
    sens = []
    for e in (*study.tolerance_sensitivity, eps):
        o_tr = oracle(ctx["train"], e, order)
        o_va = oracle(ctx["val"], e, order)
        r_e = rules if e == eps else fit_rules(dec["train"], o_tr, statics, study, base, order)
        for split, o in (("train", o_tr), ("val", o_va)):
            shares = o.preferred.value_counts(normalize=True)
            row = {"eps": e, "split": split}
            row |= {f"share_{a}": float(shares.get(a, 0.0)) for a in ACTIONS}
            for name in ("R_cat", "R_thr", "R_obs"):
                ev = evaluate(
                    apply_rule(name, r_e[name], dec[split], statics, study),
                    o,
                    shots,
                    study,
                    e,
                    True,
                )
                row[f"{name}_failure"] = float(ev.fail.mean())
                row[f"{name}_material_failure"] = float(ev.material.mean())
            sens.append(row)
    out["eps_sensitivity"] = pd.DataFrame(sens)

    # residual structure
    noise_only = {s: noise_only_ceiling(orc[s], struct_of, order) for s in orc}
    out["noise_only"] = noise_only
    stab = {}
    for split, d in (("train", train), ("val", val)):
        stab[split] = {
            "split_half_agreement": split_half_agreement(d, eps, order),
            "label_instability": label_instability(d, eps, order, rng, study.label_bootstrap),
        }
    out["stability"] = stab
    assoc = {}
    for split in ("train", "val"):
        ev = policies[split][best_rule]
        modal = ev.groupby(list(CONTEXT)).choice.agg(lambda c: c.value_counts().idxmax())
        o = orc[split].set_index(list(CONTEXT))
        stratum = (modal.loc[o.index] + "|" + o.index.get_level_values("arm")).reset_index(
            drop=True
        )
        assoc[split] = structure_association(
            o.reset_index(), stratum, struct_of, rng, study.permutations
        )
    out["structure_association"] = assoc

    # descriptives
    pts = design.set_index("point_id")
    out["context"] = {s: o.assign(region=o.point_id.map(pts.region)) for s, o in orc.items()}
    out["context_means"] = ctx
    out["variance_decomposition"] = pd.concat(
        [variance_decomposition(c).assign(split=s) for s, c in ctx.items()], ignore_index=True
    )
    budget = []
    for split, o in orc.items():
        w = o.pivot_table(
            index=["model_id", "point_id"], columns="arm", values="preferred", aggfunc="first"
        )
        arms = list(w.columns)
        for i, a in enumerate(arms):
            for b in arms[i + 1 :]:
                budget.append(
                    {
                        "split": split,
                        "arm_a": a,
                        "arm_b": b,
                        "disagreement": float((w[a] != w[b]).mean()),
                    }
                )
        all_same = w.nunique(axis=1) == 1
        budget.append(
            {
                "split": split,
                "arm_a": "any",
                "arm_b": "any",
                "disagreement": float(1 - all_same.mean()),
            }
        )
    out["budget_effect"] = pd.DataFrame(budget)
    validity = []
    for split, d in (("train", train), ("val", val)):
        r = (
            decisions_frame(d)
            .groupby(list(CONTEXT))[[study.rules.readout_feature, study.rules.gate_feature]]
            .mean()
            .reset_index()
        )
        r = r.merge(design, on="point_id")
        for arm, sub in [("all", r), *sorted(r.groupby("arm"))]:
            validity.append(
                {
                    "split": split,
                    "arm": arm,
                    "rho_readout_probe_vs_true_mean": spearman(
                        sub[study.rules.readout_feature], sub.readout_mean
                    ),
                    "rho_contraction_vs_s_dep": spearman(sub[study.rules.gate_feature], sub.s_dep),
                    "rho_contraction_vs_s_th": spearman(sub[study.rules.gate_feature], sub.s_th),
                    "rho_contraction_vs_gate_max": spearman(
                        sub[study.rules.gate_feature], np.maximum(sub.s_dep, sub.s_th)
                    ),
                }
            )
    out["probe_validity"] = pd.DataFrame(validity)

    # gate metrics
    shares = {s: o.preferred.value_counts(normalize=True) for s, o in orc.items()}
    useful = [
        a
        for a in ACTIONS
        if shares["train"].get(a, 0) >= g.pass_min_action_share
        and shares["val"].get(a, 0) >= g.pass_min_action_share
    ]
    support = True
    for a in [a for a in ACTIONS if shares["train"].get(a, 0) >= g.pass_min_action_share]:
        for split, need in (
            ("train", g.pass_min_action_structures_train),
            ("val", g.pass_min_action_structures_val),
        ):
            o = orc[split].assign(struct_id=orc[split].model_id.map(struct_of))
            used = (o.preferred == a).groupby(o.struct_id).mean()
            support &= int((used >= 0.05).sum()) >= need
    ev_best = policies["val"][best_rule]
    fails_by_struct = ev_best[ev_best.fail].model_id.map(struct_of).value_counts()
    thr = g.pass_min_structure_noise_only_failure
    metrics = {
        "max_share_train": float(shares["train"].max()),
        "max_share_val": float(shares["val"].max()),
        "actions_useful_both": len(useful),
        "useful_actions": "|".join(useful),
        "best_rule": best_rule,
        "best_rule_failure_val": float(ev_best.fail.mean()),
        "best_rule_material_failure_val": float(ev_best.material.mean()),
        "best_rule_failure_train": float(policies["train"][best_rule].fail.mean()),
        "best_universal": best_universal,
        "best_universal_failure_val": float(
            policies["val"][f"always_{best_universal}"].fail.mean()
        ),
        "noise_only_failure_val": noise_only["val"]["overall"],
        "noise_only_failure_train": noise_only["train"]["overall"],
        "noise_only_structures_val": int(
            sum(v >= thr for v in noise_only["val"]["per_structure"].values())
        ),
        "noise_only_structures_train": int(
            sum(v >= thr for v in noise_only["train"]["per_structure"].values())
        ),
        "split_half_agreement_train": stab["train"]["split_half_agreement"],
        "split_half_agreement_val": stab["val"]["split_half_agreement"],
        "label_instability_val": stab["val"]["label_instability"],
        "label_instability_train": stab["train"]["label_instability"],
        "action_support_ok": bool(support),
        "best_rule_max_structure_failure_share_val": float(
            fails_by_struct.max() / fails_by_struct.sum() if len(fails_by_struct) else 0.0
        ),
    }
    out["g3c"] = g3c_rule(metrics, g)
    out["shares"] = {s: {a: float(v.get(a, 0.0)) for a in ACTIONS} for s, v in shares.items()}
    out["struct_of"] = struct_of
    return out
