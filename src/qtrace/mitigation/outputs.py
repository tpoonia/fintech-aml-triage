"""Phase 4 committed outputs: aggregate, deterministic tables (no transaction-level data)."""

from __future__ import annotations

import io
import json
from importlib import metadata as importlib_metadata

import numpy as np
import pandas as pd

from qtrace.evaluation import metrics as M
from qtrace.mitigation.costs import resource_matched_comparator
from qtrace.mitigation.study import (
    DIAGNOSTIC_VECTORS,
    EXPERIMENT_ID,
    G2_ENDPOINTS,
    VECTORS,
    MitigationRun,
    replicate_frame,
)
from qtrace.utils.hashing import stable_hash

T = "results/tables/"
DIGITS = 9
REPLICATE_DIGITS = 6
HIST_BINS = 50
EXPECTED = {
    "applicable": "targets a noise source that is present",
    "partial": "one component targets a present source (ablation)",
    "negative_control": "no targeted source present: expect no benefit; variance and cost only",
}
SUMMARY_METRICS = (
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
    "top47_overlap",
    "top100_overlap",
    "top284_overlap",
    "clip_fraction",
    "rows_projected",
)


def _csv(frame: pd.DataFrame, digits: int = DIGITS) -> str:
    buffer = io.StringIO()
    frame.round(digits).to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def _json(obj) -> str:
    def default(o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))

    return json.dumps(obj, indent=2, default=default) + "\n"


def _software() -> dict[str, str]:
    names = ("qiskit", "qiskit-aer", "numpy", "scipy", "scikit-learn")
    return {n: importlib_metadata.version(n) for n in names}


def _label(run: MitigationRun, cond: str, vector: str) -> str:
    if vector in ("A0", "RM3", "RM9"):
        return "baseline" if vector == "A0" else "resource_matched_baseline"
    if vector in DIAGNOSTIC_VECTORS:
        return "diagnostic"
    return run.study.applicability[cond][vector]


def render_mitigation(run: MitigationRun) -> dict[str, str]:
    study, y = run.study, run.y
    out: dict[str, str] = {}
    matrix = []
    for cond, p in run.conditions.items():
        row = {
            "condition": cond,
            "family": p.family,
            "severity": p.severity or "",
            "p1": p.p1,
            "p2": p.p2,
            "readout_p01": p.readout_p01,
            "readout_p10": p.readout_p10,
            "t1_us": p.thermal.t1_us if p.thermal else None,
            "t2_us": p.thermal.t2_us if p.thermal else None,
            "note": (
                "synthetic asymmetric readout stress-test profile (not device calibration)"
                if p.role == "synthetic_stress"
                else ("negative control (Phase 3B)" if p.role == "negative_control" else "")
            ),
        }
        for a in ("A1", "A2", "A3"):
            lab = study.applicability[cond][a]
            row[f"{a}_label"] = lab
            row[f"{a}_expected"] = EXPECTED[lab]
        row["PEC"] = "not applicable (not implemented; deferred)"
        matrix.append(row)
    out[T + "p4_noise_action_matrix.csv"] = _csv(pd.DataFrame(matrix))
    circ = [
        {
            "circuit": name,
            **{k: v for k, v in s.items() if k != "operation_counts"},
            "operation_counts": json.dumps(s["operation_counts"], sort_keys=True),
        }
        for name, s in run.circuits.items()
    ]
    out[T + "p4_circuits.csv"] = _csv(pd.DataFrame(circ))
    costs = pd.DataFrame(run.costs)
    out[T + "p4_costs.csv"] = _csv(costs)
    out[T + "p4_validation.json"] = _json(run.validation)

    exact_rows = []
    for cond, e in run.exact.items():
        for v, m in e["metrics"].items():
            row = {"condition": cond, "vector": v, "label": _label(run, cond, v), **m}
            if v != "A0":
                for name, (lo, hi) in e["intervals"][v].items():
                    if name.startswith("delta_"):
                        row[f"{name}_vs_A0_ci_low"], row[f"{name}_vs_A0_ci_high"] = lo, hi
                for k in ("auprc", "auroc", "brier", "ece"):
                    row[f"delta_{k}_vs_A0"] = m[k] - e["metrics"]["A0"][k]
            exact_rows.append(row)
    exact = pd.DataFrame(exact_rows)
    exact = exact.drop(columns=[c for c in exact.columns if c == "diag_unstable"], errors="ignore")
    out[T + "p4_exact_diagnostics.csv"] = _csv(exact)

    rep_conditions = ["clean", *study.representative_conditions]
    edges = np.linspace(0, 1, HIST_BINS + 1)
    hist, cal = [], []
    for cond in rep_conditions:
        vectors = ("A0",) if cond == "clean" else ("A0", "A1", "A2", "A3")
        for v in vectors:
            s = run.exact[cond]["scores"][v]
            legit, _ = np.histogram(s[y == 0], bins=edges)
            fraud, _ = np.histogram(s[y == 1], bins=edges)
            hist += [
                {
                    "condition": cond,
                    "vector": v,
                    "bin_lower": edges[i],
                    "bin_upper": edges[i + 1],
                    "legit_count": int(legit[i]),
                    "fraud_count": int(fraud[i]),
                }
                for i in range(HIST_BINS)
            ]
            cal += [
                {"condition": cond, "vector": v, **b}
                for b in M.calibration_bins(y, s, study.ece_bins, "uniform")
            ]
    out[T + "p4_score_histogram.csv"] = _csv(pd.DataFrame(hist))
    out[T + "p4_calibration_bins.csv"] = _csv(pd.DataFrame(cal))

    if run.replicate_rows:
        rep = replicate_frame(run)
        rep_out = rep.drop(columns=["unstable"]).assign(unstable=rep["unstable"].astype(int))
        for b in study.shot_budgets:  # one file per arm: repo hygiene caps tables at 2,000 rows
            out[T + f"p4_replicates_{b.arm_id}.csv"] = _csv(
                rep_out[rep_out.arm == b.arm_id].reset_index(drop=True), REPLICATE_DIGITS
            )
        out[T + "p4_calibration_estimates.csv"] = _csv(pd.DataFrame(run.calibration_rows))
        cost_idx = costs.set_index(["arm", "vector"])
        summary = []
        groups = dict(tuple(rep.groupby(["condition", "arm", "vector"])))
        for cond in study.conditions:
            for b in study.shot_budgets:
                for v in VECTORS:
                    g = groups[(cond, b.arm_id, v)]
                    row = {
                        "condition": cond,
                        "arm": b.arm_id,
                        "vector": v,
                        "label": _label(run, cond, v),
                    }
                    for m in SUMMARY_METRICS:
                        row[m] = g[m].mean()
                    for m in ("auprc", "brier", "f1"):
                        row[f"{m}_sd"] = g[m].std(ddof=1)
                    c = cost_idx.loc[(b.arm_id, v)]
                    for k in (
                        "shots_per_inference",
                        "circuits_per_inference",
                        "cx_shots_per_inference",
                    ):
                        row[k] = c[k]
                    summary.append(row)
        summary = pd.DataFrame(summary)
        out[T + "p4_summary.csv"] = _csv(summary)
        dl = run.analysis["deltas"].copy()
        spi = costs.set_index(["arm", "vector"])["shots_per_inference"]
        dl["delta_shots_per_inference"] = [
            spi[(a, v)] - spi[(a, r)]
            for a, v, r in zip(dl.arm, dl.action, dl.comparator, strict=True)
        ]
        vs_none = dl[dl.comparator == "A0"]
        for b in study.shot_budgets:
            out[T + f"p4_deltas_vs_none_{b.arm_id}.csv"] = _csv(
                vs_none[vs_none.arm == b.arm_id].reset_index(drop=True)
            )
        rm = dl[
            dl.apply(
                lambda r: (
                    (
                        r.action in ("A1", "A2", "A3")
                        and r.comparator == resource_matched_comparator(r.action)
                    )
                    or r.comparator == "RM9"
                ),
                axis=1,
            )
        ].reset_index(drop=True)
        cells = run.analysis["cells"].set_index(["condition", "arm", "action", "endpoint"])
        flags_b, flags_h, labels = [], [], []
        for r in rm.itertuples():
            key = (r.condition, r.arm, r.action, r.metric)
            primary = r.comparator != "RM9" and r.metric in G2_ENDPOINTS and key in cells.index
            flags_b.append(bool(cells.loc[key, "rrb_benefit"]) if primary else None)
            flags_h.append(bool(cells.loc[key, "rrb_harm"]) if primary else None)
            labels.append(run.study.applicability[r.condition].get(r.action, ""))
        rm["applicability"] = labels
        rm["g2_rrb_benefit"] = flags_b
        rm["g2_rrb_harm"] = flags_h
        rm["comparison_role"] = np.where(rm.comparator == "RM9", "diagnostic", "primary")
        out[T + "p4_resource_matched.csv"] = _csv(rm)
        out[T + "p4_best_action.csv"] = _csv(run.analysis["best"])
    out[T + "p4_metadata.json"] = _json(_metadata(run))
    return out


def _metadata(run: MitigationRun) -> dict:
    study = run.study
    meta = {
        "experiment_id": EXPERIMENT_ID,
        "study_id": study.study_id,
        "preregistration": "docs/PREREG_P4.md (committed 9d377d0 before the experiment)",
        "status": run.status,
        "g2": run.analysis.get("g2", "not issued"),
        "hypotheses": run.analysis.get("hypotheses", {}),
        "context": run.context,
        "model": {
            "model_id": study.model.model_id,
            "artifact": study.model.artifact,
            "artifact_content_sha256": study.model.artifact_sha256,
            "transpile_seed": study.model.transpile_seed,
        },
        "frozen_tau": run.tau,
        "conditions": list(study.conditions),
        "shot_budgets": [b.model_dump() for b in study.shot_budgets],
        "replicates": study.replicates,
        "circuits": {
            k: {kk: vv for kk, vv in v.items() if kk != "operation_counts"}
            for k, v in run.circuits.items()
        },
        "exact_calibration_estimates": {c: e["calibration"] for c, e in run.exact.items()},
        "seeds": {
            "finite_shot": (
                f"shots stream, key ({study.seed_key}, condition, arm, replicate, component)"
            ),
            "bootstrap": "shared Phase 2 vqc_val resamples + bootstrap key p4-replicate-draw",
            "e08": f"shots stream, key ({study.e08.seed_key}, profile, factor, aer|multinomial)",
        },
        "notes": {
            "synthetic_profiles": (
                "ar-020/ar-050 are synthetic asymmetric readout stress-test profiles, "
                "not IBM or device calibration data (O20 open)"
            ),
            "oracle": "A1-oracle uses the true confusion matrix: diagnostic upper bound only",
            "exclusions": "no Q-TRACE, no pool, no PEC, no retraining; one frozen threshold",
        },
        "config_hashes": {
            "experiment": run.context["experiment_config_hash"],
            "study": stable_hash(study),
        },
        "software": _software(),
    }
    return meta
