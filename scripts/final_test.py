"""The ONE-TIME final evaluation on the sealed controller-test outcomes (docs/PREREG_FINAL.md).

Usage:
    uv run python scripts/final_test.py               # the single registered evaluation
    uv run python scripts/final_test.py --reproduce   # later byte-for-byte reproduction (logged)

Refuses unless the protocol and the Phase 7 freeze record are committed, pushed and clean. The
first run records the unlock (results/lockbox/UNLOCK_RECORD.json); a second unlock is refused.
Before any test row is used, the sealed files are checked against their committed content hashes
and the refitted learned comparators must reproduce their frozen validation fingerprints.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

import pandas as pd

from qtrace.config import repo_root
from qtrace.controller import final_eval as FE
from qtrace.controller import lockbox as LB
from qtrace.counterfactual import generate as G
from qtrace.counterfactual import mixed_analysis as AN
from qtrace.counterfactual.study import _csv, _json
from qtrace.utils.seeds import make_rng

sys.path.insert(0, str(repo_root() / "scripts"))
from phase7_validate import fit_frozen, load_inputs  # noqa: E402

T = "results/tables/"


def _tracked_clean(root, rel: str) -> bool:
    tracked = subprocess.run(["git", "ls-files", rel], cwd=root, capture_output=True, text=True)
    dirty = subprocess.run(
        ["git", "status", "--porcelain", rel], cwd=root, capture_output=True, text=True
    )
    return bool(tracked.stdout.strip()) and not dirty.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reproduce", action="store_true")
    args = parser.parse_args(argv)
    root = repo_root()
    resolved, study, base, cfg, rules, statics = load_inputs(root)
    for rel in (cfg["protocol"], cfg["frozen_record"], "configs/final_test/final_v1.yaml"):
        if not _tracked_clean(root, rel):
            print(f"refusing: {rel} must be committed and unchanged", file=sys.stderr)
            return 2
    if args.reproduce:
        record = json.loads((root / LB.RECORD).read_text())
    else:
        record = LB.unlock(root, cfg["protocol"], "single registered final evaluation")
    frozen = json.loads((root / cfg["frozen_record"]).read_text())
    learned, seed = fit_frozen(root, resolved, study, base, statics)
    assert seed == frozen["learned_seed"]
    val5c = AN.load_split(root / study.processed_dir, "val")
    smap = FE.static_map(statics, base)
    dec_val = AN.decisions_frame(val5c)
    for name, pol in learned.items():
        fp = FE.fingerprint(FE.choose(pol, dec_val, smap, base, study))
        if fp != frozen["fingerprints_5c_val"][name]:
            raise RuntimeError(f"{name} does not reproduce its frozen validation fingerprint")
    envs = {}
    for key in ("primary", "secondary"):
        e = cfg["environments"][key]
        df = LB.read_sealed(
            root, e["sealed_file"], pd.read_parquet, "final evaluation " + e["name"]
        )
        expected = json.loads((root / e["manifest"]).read_text())["content_sha256"]
        if G.content_sha256(df) != expected:
            raise RuntimeError(f"{e['sealed_file']} differs from its committed content hash")
        if set(df.split) != {"test"}:
            raise RuntimeError("sealed file content is not the test split")
        envs[e["name"]] = (
            FE.from_5b(df) if key == "secondary" else df,
            pd.read_csv(root / e["costs"]),
        )
    rng = make_rng(resolved.spec.seeds.bootstrap, "bootstrap", cfg["bootstrap_seed_key"])
    res = {
        name: FE.evaluate_environment(
            df, costs, statics, rules, learned, base, study, rng, cfg["cluster_bootstrap"]
        )
        for name, (df, costs) in envs.items()
    }
    hyp = FE.hypotheses(res["5c_test"], res["5b_test"], cfg["hypotheses"])
    out = {}
    for tag, r in res.items():
        out[T + f"final_policies_{tag}.csv"] = _csv(r["policies"])
        out[T + f"final_paired_vs_rthr_{tag}.csv"] = _csv(r["paired_vs_rthr"])
        out[T + f"final_by_structure_{tag}.csv"] = _csv(r["by_structure"])
    out[T + "final_metadata.json"] = _json(
        {
            "protocol": cfg["protocol"],
            "unlock_record": record,
            "hypotheses": hyp,
            "preferred_shares": {k: r["preferred_shares"] for k, r in res.items()},
            "learned_fingerprints_verified_on_5c_val": True,
            "sealed_content_verified": True,
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
    for tag, r in res.items():
        p = r["policies"]
        print(tag)
        print(p[p.arm == "all"][cols].round(4).to_string(index=False))
    print(json.dumps(hyp, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
