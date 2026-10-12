"""Phase 7: fit the pre-specified learned comparators on 5C TRAIN, compare every frozen policy on
VALIDATION (5C val; 5B val as a second environment), and freeze the comparators (fingerprints).

Usage: uv run python scripts/phase7_validate.py
Reads only train/val data (the sealed test splits are refused by the loaders). Writes
results/tables/p7_*.csv, p7_frozen_policies.json and p7_metadata.json. Deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from qtrace.config import repo_root
from qtrace.controller import final_eval as FE
from qtrace.counterfactual import analysis as AN5B
from qtrace.counterfactual import mixed_analysis as AN
from qtrace.counterfactual.mixed_study import load_mixed_study
from qtrace.counterfactual.study import _csv, _json
from qtrace.utils.seeds import make_rng

T = "results/tables/"


def load_inputs(root: Path):
    resolved, study, base, _, _, _ = load_mixed_study()
    cfg = yaml.safe_load((root / "configs/final_test/final_v1.yaml").read_text())
    assert cfg["tolerance"] == study.preferred_relative_tolerance
    rules = FE.rules_from_json(json.loads((root / cfg["rules_source"]).read_text())["rules"])
    statics = pd.read_csv(root / T / "p5b_static_features.csv")
    return resolved, study, base, cfg, rules, statics


def fit_frozen(root: Path, resolved, study, base, statics):
    """The learned comparators exactly as frozen (deterministic refit from 5C train)."""
    train = AN.load_split(root / study.processed_dir, "train")
    orc = AN.oracle(AN.context_means(train), study.preferred_relative_tolerance, base.cost_order)
    seed = FE.learned_seed(resolved.spec.seeds.policy)
    smap = FE.static_map(statics, base)
    return FE.fit_learned(
        AN.decisions_frame(train), orc, smap, base, study, study.preferred_relative_tolerance, seed
    ), seed


def main() -> int:
    root = repo_root()
    resolved, study, base, cfg, rules, statics = load_inputs(root)
    learned, seed = fit_frozen(root, resolved, study, base, statics)
    rng = make_rng(resolved.spec.seeds.bootstrap, "bootstrap", "p7-" + cfg["bootstrap_seed_key"])
    val5c = AN.load_split(root / study.processed_dir, "val")
    val5b = FE.from_5b(AN5B.load_split(root / base.processed_dir, "val"))
    costs5c = pd.read_csv(root / cfg["environments"]["primary"]["costs"])
    costs5b = pd.read_csv(root / cfg["environments"]["secondary"]["costs"])
    n = cfg["cluster_bootstrap"]
    r5c = FE.evaluate_environment(val5c, costs5c, statics, rules, learned, base, study, rng, n)
    r5b = FE.evaluate_environment(val5b, costs5b, statics, rules, learned, base, study, rng, n)
    out = {}
    for tag, res in (("5c_val", r5c), ("5b_val", r5b)):
        out[T + f"p7_policies_{tag}.csv"] = _csv(res["policies"])
        out[T + f"p7_paired_vs_rthr_{tag}.csv"] = _csv(res["paired_vs_rthr"])
        out[T + f"p7_by_structure_{tag}.csv"] = _csv(res["by_structure"])
    build = json.loads((root / T / "p5c_build.json").read_text())
    out[T + "p7_frozen_policies.json"] = _json(
        {
            "primary_policy": cfg["primary_policy"],
            "rules": rules,
            "learned_specs": {k: v.name for k, v in FE.LEARNED_SPECS.items()},
            "learned_seed": seed,
            "learned_training_data_sha256": build["dataset_content_sha256"]["train"],
            "fingerprints_5c_val": r5c["fingerprints"],
            "fingerprints_5b_val": r5b["fingerprints"],
        }
    )
    hyp = FE.hypotheses(r5c, r5b, cfg["hypotheses"])
    out[T + "p7_metadata.json"] = _json(
        {
            "stage": "Phase 7 validation comparison (NOT confirmatory; the sealed test decides)",
            "validation_hypothesis_preview": hyp,
            "preferred_shares": {
                "5c_val": r5c["preferred_shares"],
                "5b_val": r5b["preferred_shares"],
            },
        }
    )
    for rel, text in out.items():
        (root / rel).write_text(text, encoding="utf-8")
    cols = [
        "policy",
        "failure",
        "material_failure",
        "mean_rel_brier_regret",
        "mean_total_shots_per_inference",
    ]
    for tag, res in (("5C val", r5c), ("5B val", r5b)):
        p = res["policies"]
        print(tag)
        print(p[p.arm == "all"][cols].round(4).to_string(index=False))
    print(json.dumps(hyp, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
