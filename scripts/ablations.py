"""Robustness and ablations on VALIDATION only (the sealed test was spent once; never reused).

Usage: uv run python scripts/ablations.py

1. Probe ablation: rules refitted on 5C train exactly like R_thr, but with
   - readout probe only (gate noise always assumed present),
   - gate probe only (readout noise always assumed present),
   - no probe (one cell per budget = the best fixed action).
2. Probe-cost break-even: the batch size N below which the probes (66*S shots per batch)
   cost more than R_thr saves over always-combined mitigation.
Writes results/tables/ablation_*.csv. Deterministic. Exploratory (not pre-registered).
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from qtrace.config import repo_root
from qtrace.controller import final_eval as FE
from qtrace.counterfactual import analysis as AN5B
from qtrace.counterfactual import mixed_analysis as AN
from qtrace.counterfactual.mixed_study import load_mixed_study
from qtrace.counterfactual.study import _csv

T = "results/tables/"
PROBE_SHOTS_PER_BATCH = 66  # x S (32 bindings x 2 folds + 2 calibration circuits)


def fit_variant(dec, orc, study, base, readout: bool, gate: bool) -> dict:
    rank = np.array([list(base.cost_order).index(a) for a in AN.ACTIONS])
    d = dec.merge(orc[[*AN.CONTEXT, "preferred"]], on=list(AN.CONTEXT))
    target = d.preferred.map(AN.ACTIONS.index).to_numpy()
    q = np.array(study.rules.threshold_quantiles)
    rf, gf = study.rules.readout_feature, study.rules.gate_feature
    out = {}
    for arm in sorted(d.arm.unique()):
        a = (d.arm == arm).to_numpy()
        ro, ga = d.loc[a, rf].to_numpy(), d.loc[a, gf].to_numpy()
        gr = np.unique(np.quantile(ro, q)) if readout else np.array([-np.inf])  # always "readout"
        gg = np.unique(np.quantile(ga, q)) if gate else np.array([np.inf])  # always "gate"
        out[arm] = AN.fit_decision_list(ro, ga, target[a], rank, gr, gg)
    return out


def main() -> int:
    root = repo_root()
    _, study, base, _, _, _ = load_mixed_study()
    eps = study.preferred_relative_tolerance
    statics = pd.read_csv(root / T / "p5b_static_features.csv")
    rules = FE.rules_from_json(json.loads((root / T / "p5c_metadata.json").read_text())["rules"])
    train = AN.load_split(root / study.processed_dir, "train")
    orc_tr = AN.oracle(AN.context_means(train), eps, base.cost_order)
    dec_tr = AN.decisions_frame(train)
    variants = {
        "R_thr (both probes)": rules["R_thr"],
        "readout probe only": fit_variant(dec_tr, orc_tr, study, base, True, False),
        "gate probe only": fit_variant(dec_tr, orc_tr, study, base, False, True),
        "no probe (fixed per budget)": fit_variant(dec_tr, orc_tr, study, base, False, False),
    }
    envs = {
        "5c_val": (
            AN.load_split(root / study.processed_dir, "val"),
            pd.read_csv(root / T / "p5c_costs.csv"),
        ),
        "5b_val": (
            FE.from_5b(AN5B.load_split(root / base.processed_dir, "val")),
            pd.read_csv(root / T / "p5b_costs.csv"),
        ),
    }
    rows, cost_rows = [], []
    for env, (df, costs) in envs.items():
        orc = AN.oracle(AN.context_means(df), eps, base.cost_order)
        dec = AN.decisions_frame(df)
        shots = AN.shots_table(costs)
        evs = {}
        for name, rule in variants.items():
            ch = AN.apply_rule("R_thr", rule, dec, statics, study)
            probing = name != "no probe (fixed per budget)"
            evs[name] = AN.evaluate(ch, orc, shots, study, eps, probing)
            rows.append({"environment": env, "variant": name, **AN.summarize(evs[name])})
        a3 = AN.evaluate(AN.universal(dec, "A3"), orc, shots, study, eps, False)
        r = evs["R_thr (both probes)"]
        for arm, g in r.groupby("arm"):
            S = float(g.merge(shots, on=["model_id", "arm"]).S.mean())
            saving = float(
                a3[a3.arm == arm].action_shots_per_inference.mean()
                - g.action_shots_per_inference.mean()
            )
            cost_rows.append(
                {
                    "environment": env,
                    "arm": arm,
                    "shots_per_circuit": S,
                    "action_shot_saving_vs_always_A3_per_inference": saving,
                    "probe_shots_per_batch": PROBE_SHOTS_PER_BATCH * S,
                    "break_even_batch_size": PROBE_SHOTS_PER_BATCH * S / saving
                    if saving > 0
                    else float("inf"),
                    "material_failure_R_thr": float(g.material.mean()),
                    "material_failure_always_A3": float(a3[a3.arm == arm].material.mean()),
                }
            )
    out = {
        T + "ablation_probes.csv": _csv(pd.DataFrame(rows)),
        T + "ablation_probe_cost.csv": _csv(pd.DataFrame(cost_rows)),
    }
    for rel, text in out.items():
        (root / rel).write_text(text, encoding="utf-8")
    cols = [
        "environment",
        "variant",
        "failure",
        "material_failure",
        "mean_rel_brier_regret",
        "mean_total_shots_per_inference",
    ]
    print(pd.DataFrame(rows)[cols].round(4).to_string(index=False))
    print(pd.DataFrame(cost_rows).round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
