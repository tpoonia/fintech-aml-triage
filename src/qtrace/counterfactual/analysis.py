"""Phase 5B registered analysis (PREREG_P5B §11-13): TRAIN and VAL contexts only.

The test split's outcomes are sealed in the lockbox and are refused here. A context is
model x condition x shot budget; replicates give uncertainty (no pseudo-replication: every
statistic is computed on context means or on replicate deltas within a context).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from qtrace.config.schemas import CounterfactualStudyConfig
from qtrace.utils.seeds import make_rng

ACTIONS = ("A0", "A1", "A2", "A3", "A4")
OUTCOMES = (
    "auprc",
    "auroc",
    "brier",
    "ece",
    "precision",
    "recall",
    "f1",
    "f2",
    "crossing_all",
    "crossing_fraud",
    "crossing_legit",
    "spearman",
    "kendall",
)
CONTEXT = ("model_id", "condition", "arm")
AXES = ("feature_set", "encoding_family", "ansatz", "ansatz_reps", "readout_observable")


class LockboxError(RuntimeError):
    """Test-split outcomes may not be read by the Phase 5B analysis."""


def load_split(processed_dir: Path, split: str) -> pd.DataFrame:
    if split not in ("train", "val"):
        raise LockboxError(f"split {split!r} is sealed or unknown; only train/val are analysed")
    frame = pd.read_parquet(processed_dir / f"counterfactual_{split}.parquet")
    if set(frame["split"]) != {split}:
        raise LockboxError("file content does not match its split")
    return frame


def context_means(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby([*CONTEXT, "action"], sort=True)
    out = g[list(OUTCOMES)].mean()
    for m in ("brier", "f1", "auprc"):
        out[f"{m}_sd"] = g[m].std(ddof=1)
    return out.reset_index()


def _cost_rank(study: CounterfactualStudyConfig) -> dict[str, int]:
    return {a: i for i, a in enumerate(study.cost_order)}


def preferred(ctx: pd.DataFrame, study: CounterfactualStudyConfig) -> pd.DataFrame:
    """Cost-aware preferred action per context (Oracle; descriptive; never a feature)."""
    rank = _cost_rank(study)
    tol, ftol = study.preferred_relative_tolerance, study.secondary_tolerance
    b = ctx[ctx.action.isin(ACTIONS)].pivot_table(
        index=list(CONTEXT), columns="action", values="brier"
    )
    f = ctx[ctx.action.isin(ACTIONS)].pivot_table(
        index=list(CONTEXT), columns="action", values="f1"
    )
    order = list(study.cost_order)
    rows = []
    for idx in b.index:
        br, f1 = b.loc[idx], f.loc[idx]
        mn = br.min()
        p_star = next(a for a in order if br[a] <= (1 + tol) * mn)
        best = min(ACTIONS, key=lambda a: (br[a], rank[a]))
        f_pref = next(a for a in order if f1[a] >= f1.max() - ftol)
        rows.append(
            {
                **dict(zip(CONTEXT, idx, strict=True)),
                "preferred": p_star,
                "reliability_best": best,
                "f1_preferred": f_pref,
                "min_brier": mn,
                **{f"brier_{a}": br[a] for a in ACTIONS},
                **{f"f1_{a}": f1[a] for a in ACTIONS},
                "improvable": bool(mn <= (1 - study.g3b.improvable_relative_brier) * br["A0"]),
            }
        )
    return pd.DataFrame(rows)


def fails(row: pd.Series, action: str, study: CounterfactualStudyConfig) -> bool:
    """Reliability failure (Brier beyond tolerance) or overspend relative to the Oracle."""
    rank = _cost_rank(study)
    too_bad = row[f"brier_{action}"] > (1 + study.preferred_relative_tolerance) * row["min_brier"]
    return bool(too_bad or rank[action] > rank[row["preferred"]])


def split_half_agreement(df: pd.DataFrame, study: CounterfactualStudyConfig) -> float:
    reps = sorted(df.replicate.unique())
    first = set(reps[: len(reps) // 2])
    in_first = df.replicate.isin(first)
    a = preferred(context_means(df[in_first]), study).set_index(list(CONTEXT))
    b = preferred(context_means(df[~in_first]), study).set_index(list(CONTEXT))
    return float((a.preferred == b.preferred.loc[a.index]).mean())


def probe_category(rep: pd.DataFrame, study: CounterfactualStudyConfig) -> pd.Series:
    cfg = study.probe_categories
    ro = rep["probe_readout_error_mean"] >= cfg.readout_error_min
    ga = rep["probe_gate_contraction"] <= cfg.gate_contraction_max
    return pd.Series(
        np.select([ro & ga, ro, ga], ["both", "readout", "gate"], default="none"), index=rep.index
    )


def replicate_probes(df: pd.DataFrame, study: CounterfactualStudyConfig) -> pd.DataFrame:
    """One row per context replicate (probe features are identical across action rows)."""
    rep = df[df.action == "A0"].copy()
    rep["category"] = probe_category(rep, study)
    return rep


def fit_category_rule(rep_train: pd.DataFrame, pstar: pd.DataFrame, study) -> dict:
    """Majority Oracle action per (probe category, arm) over TRAIN replicates (descriptive)."""
    rank = _cost_rank(study)
    m = rep_train.merge(pstar[[*CONTEXT, "preferred"]], on=list(CONTEXT))
    rule = {}
    for (cat, arm), g in m.groupby(["category", "arm"]):
        counts = g.preferred.value_counts()
        top = counts.max()
        rule[(cat, arm)] = min((a for a in counts.index if counts[a] == top), key=rank.get)
    counts = m.preferred.value_counts()
    rule["__fallback__"] = min((a for a in counts.index if counts[a] == counts.max()), key=rank.get)
    return rule


def failure_rate_rule(rep: pd.DataFrame, pstar: pd.DataFrame, rule: dict, study) -> float:
    p = pstar.set_index(list(CONTEXT))
    out = []
    for r in rep.itertuples():
        act = rule.get((r.category, r.arm), rule["__fallback__"])
        out.append(fails(p.loc[(r.model_id, r.condition, r.arm)], act, study))
    return float(np.mean(out))


def failure_rate_universal(pstar: pd.DataFrame, study) -> dict[str, float]:
    return {a: float(np.mean([fails(r, a, study) for _, r in pstar.iterrows()])) for a in ACTIONS}


def heterogeneity(df: pd.DataFrame, study: CounterfactualStudyConfig) -> pd.DataFrame:
    """One-way random effects across models of replicate-paired ΔBrier (action - A0)."""
    piv = df.pivot_table(index=[*CONTEXT, "replicate"], columns="action", values="brier")
    rows = []
    for a in ACTIONS[1:]:
        d = (piv[a] - piv["A0"]).rename("d").reset_index()
        for (cond, arm), g in d.groupby(["condition", "arm"]):
            mat = g.pivot_table(index="model_id", columns="replicate", values="d").to_numpy()
            k, r = mat.shape
            means = mat.mean(axis=1)
            ms_b = r * np.sum((means - means.mean()) ** 2) / (k - 1)
            ms_w = np.sum((mat - means[:, None]) ** 2) / (k * (r - 1))
            if ms_w == 0 and ms_b == 0:
                fstat, p = np.nan, np.nan
            else:
                fstat = ms_b / ms_w if ms_w > 0 else np.inf
                p = float(stats.f.sf(fstat, k - 1, k * (r - 1))) if np.isfinite(fstat) else 0.0
            sb2 = max((ms_b - ms_w) / r, 0.0)
            rows.append(
                {
                    "action": a,
                    "condition": cond,
                    "arm": arm,
                    "models": k,
                    "replicates": r,
                    "mean_delta_brier": float(mat.mean()),
                    "ms_between": ms_b,
                    "ms_within": ms_w,
                    "f": fstat,
                    "p": p,
                    "sigma_between": float(np.sqrt(sb2)),
                    "sigma_within": float(np.sqrt(ms_w)),
                    "icc": sb2 / (sb2 + ms_w) if (sb2 + ms_w) > 0 else np.nan,
                }
            )
    out = pd.DataFrame(rows)
    ok = out.p.notna()
    out["p_holm"] = np.nan
    if ok.any():
        pv = out.loc[ok, "p"].to_numpy()
        order = np.argsort(pv, kind="stable")
        adj = np.empty_like(pv)
        running = 0.0
        for i, j in enumerate(order):
            running = max(running, min(1.0, (len(pv) - i) * pv[j]))
            adj[j] = running
        out.loc[ok, "p_holm"] = adj
    out["heterogeneous"] = (out.p_holm < study.heterogeneity.alpha) & (
        out.icc >= study.heterogeneity.icc_min
    )
    return out


def variance_decomposition(ctx: pd.DataFrame) -> pd.DataFrame:
    """Two-way (model x context) decomposition of context-mean ΔBrier per action."""
    b = ctx.pivot_table(index=list(CONTEXT), columns="action", values="brier")
    rows = []
    for a in ACTIONS[1:]:
        d = (b[a] - b["A0"]).rename("d").reset_index()
        d["ctx"] = d.condition + "|" + d.arm
        x = d.pivot_table(index="model_id", columns="ctx", values="d").to_numpy()
        gm = x.mean()
        ss_t = np.sum((x - gm) ** 2)
        ss_c = x.shape[0] * np.sum((x.mean(axis=0) - gm) ** 2)
        ss_m = x.shape[1] * np.sum((x.mean(axis=1) - gm) ** 2)
        rows.append(
            {
                "action": a,
                "eta2_noise_context": ss_c / ss_t if ss_t > 0 else np.nan,
                "eta2_model": ss_m / ss_t if ss_t > 0 else np.nan,
                "eta2_model_x_context": (ss_t - ss_c - ss_m) / ss_t if ss_t > 0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _mi(a: np.ndarray, b: np.ndarray) -> float:
    ta = pd.crosstab(a, b).to_numpy().astype(float)
    p = ta / ta.sum()
    pa, pb = p.sum(axis=1, keepdims=True), p.sum(axis=0, keepdims=True)
    nz = p > 0
    return float(np.sum(p[nz] * np.log(p[nz] / (pa @ pb)[nz])))


def conditional_mi(target, label, strata) -> float:
    df = pd.DataFrame({"t": target, "l": label, "s": strata})
    return float(
        sum(len(g) / len(df) * _mi(g.t.to_numpy(), g.l.to_numpy()) for _, g in df.groupby("s"))
    )


def structure_association(ctx_pref: pd.DataFrame, study, shots_master: int) -> dict:
    """I(preferred action; structure | probe category, arm) with a model-label permutation test."""
    obs = conditional_mi(ctx_pref.preferred, ctx_pref.struct_id, ctx_pref.stratum)
    models = ctx_pref[["model_id", "struct_id"]].drop_duplicates().sort_values("model_id")
    rng = make_rng(shots_master, "bootstrap", study.heterogeneity.permutation_seed_key)
    count = 0
    for _ in range(study.heterogeneity.permutations):
        perm = dict(zip(models.model_id, rng.permutation(models.struct_id.to_numpy()), strict=True))
        val = conditional_mi(ctx_pref.preferred, ctx_pref.model_id.map(perm), ctx_pref.stratum)
        count += val >= obs - 1e-12
    return {"conditional_mi": obs, "p": (1 + count) / (1 + study.heterogeneity.permutations)}


def g3b_rule(m: dict, g) -> dict:
    """Registered G3B rule (PREREG_P5B §13) on the computed metrics."""
    fail = {
        "dominance": m["max_action_share"] >= g.fail_dominance_share,
        "negligible_differences": m["improvable_fraction"] < g.fail_min_improvable_fraction,
        "replicate_noise": m["split_half_agreement"] < g.fail_min_split_half_agreement,
        "no_observable_signal": m["rule_gain_val"] < g.fail_min_rule_gain,
        "fixed_rule_sufficient": m["rule_failure_val"] < g.fail_max_rule_failure,
    }
    passed = {
        "multiple_useful_actions": m["actions_with_share"] >= g.pass_min_actions_useful,
        "universal_suboptimal": m["best_universal_failure_val"] >= g.pass_min_universal_failure,
        "observable_signal": m["rule_gain_val"] >= g.pass_min_rule_gain,
        "residual_complexity": m["rule_failure_val"] >= g.pass_min_rule_failure
        and m["structure_association_p"] < g.pass_max_structure_association_p,
        "model_heterogeneity": m["heterogeneous_cell_fraction"]
        >= g.pass_min_heterogeneous_cell_fraction,
    }
    verdict = (
        "FAIL" if any(fail.values()) else ("PASS" if all(passed.values()) else "CONDITIONAL PASS")
    )
    return {"verdict": verdict, "fail_conditions": fail, "pass_criteria": passed, "metrics": m}


def analyse(train: pd.DataFrame, val: pd.DataFrame, study, shots_master: int) -> dict:
    """Every registered quantity; the G3B inputs come from TRAIN (rule fit) and VAL (check)."""
    out: dict = {}
    for name, df in (("train", train), ("val", val)):
        ctx = context_means(df)
        pst = preferred(ctx, study)
        rep = replicate_probes(df, study)
        out[name] = {"ctx": ctx, "pref": pst, "rep": rep, "df": df}
    rule = fit_category_rule(out["train"]["rep"], out["train"]["pref"], study)
    for name in ("train", "val"):
        o = out[name]
        o["rule_failure"] = failure_rate_rule(o["rep"], o["pref"], rule, study)
        o["universal_failure"] = failure_rate_universal(o["pref"], study)
        o["shares"] = o["pref"].preferred.value_counts(normalize=True).reindex(ACTIONS).fillna(0)
    tr = out["train"]
    modal = tr["rep"].groupby(list(CONTEXT)).category.agg(lambda s: s.value_counts().index[0])
    cp = tr["pref"].merge(modal.rename("category").reset_index(), on=list(CONTEXT))
    cp = cp.merge(tr["df"][["model_id", "struct_id"]].drop_duplicates(), on="model_id")
    cp["stratum"] = cp.category + "|" + cp.arm
    assoc = structure_association(cp, study, shots_master)
    het = heterogeneity(train, study)
    best_u_val = min(out["val"]["universal_failure"].values())
    metrics = {
        "max_action_share": float(tr["shares"].max()),
        "actions_with_share": int((tr["shares"] >= study.g3b.pass_min_action_share).sum()),
        "improvable_fraction": float(tr["pref"].improvable.mean()),
        "split_half_agreement": split_half_agreement(train, study),
        "best_universal_failure_train": min(tr["universal_failure"].values()),
        "best_universal_failure_val": best_u_val,
        "rule_failure_train": tr["rule_failure"],
        "rule_failure_val": out["val"]["rule_failure"],
        "rule_gain_val": best_u_val - out["val"]["rule_failure"],
        "structure_association_mi": assoc["conditional_mi"],
        "structure_association_p": assoc["p"],
        "heterogeneous_cell_fraction": float(het.heterogeneous[het.p.notna()].mean()),
    }
    out["rule"] = {f"{k[0]}|{k[1]}" if isinstance(k, tuple) else k: v for k, v in rule.items()}
    out["heterogeneity"] = het
    out["variance"] = variance_decomposition(tr["ctx"])
    out["association"] = assoc
    out["g3b"] = g3b_rule(metrics, study.g3b)
    return out
