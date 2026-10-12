"""Phase 4 study mechanics on synthetic inputs: paired/nested draws, determinism, no oracle
leak, one frozen threshold, the RRB rule, Table D and the G2 verdict. No transaction data."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from qtrace.config import load_component, repo_root
from qtrace.mitigation import readout as RO
from qtrace.mitigation import study as ST
from qtrace.noise.models import apply_readout
from qtrace.utils.seeds import make_rng

ROOT = repo_root()


@pytest.fixture(scope="module")
def study():
    s = load_component("mitigation_study", "p4_v1")
    return s.model_copy(update={"replicates": 3, "bootstrap_resamples": 100})


@pytest.fixture(scope="module")
def synth():
    rng = np.random.default_rng(21)
    n = 400
    y = np.zeros(n, dtype=np.int64)
    y[:40] = 1
    base = rng.dirichlet(np.ones(16) * 0.5, size=n)
    odd = np.array([bin(i).count("1") % 2 for i in range(16)], bool)
    base[y == 1] = 0.5 * base[y == 1] + 0.5 * odd / odd.sum()  # frauds lean odd parity
    probs = {f: apply_readout(base**1, 0.02 * f / 5, 0.04 * f / 5) for f in (1, 3, 5)}
    e0, e1 = np.zeros(16), np.zeros(16)
    e0[0], e1[15] = 1.0, 1.0
    cal = (apply_readout(e0[None], 0.02, 0.04)[0], apply_readout(e1[None], 0.02, 0.04)[0])
    clean_s = ((1 - (base @ np.where(odd, -1.0, 1.0))) / 2).clip(0, 1)
    return y, probs, cal, clean_s


def _run(study, synth, oracle):
    y, probs, cal, clean_s = synth
    draws = make_rng(8123, "bootstrap", "test-draw").integers(0, study.replicates, 100)
    return ST.run_context(
        "ar-020", "s1024", 1024, probs, cal, oracle, y, clean_s, 0.4, study, 9011, 77, draws
    )


def test_draws_are_paired_and_nested(synth, study):
    _, probs, cal, _ = synth

    def rng(component):
        return make_rng(9011, "shots", "t", component)

    d = ST.draw_context(probs, cal, 1024, (1, 3, 5), rng)
    assert (d["lam1"].sum(axis=1) == 1024).all() and (d["lam5"].sum(axis=1) == 1024).all()
    assert (d["rm3"].sum(axis=1) == 3 * 1024).all() and (d["rm9"].sum(axis=1) == 9 * 1024).all()
    assert (d["rm3"] >= d["lam1"]).all() and (d["rm9"] >= d["rm3"]).all()  # nested baselines
    assert d["cal0"].sum() == 1024 and d["cal1"].sum() == 1024
    again = ST.draw_context(probs, cal, 1024, (1, 3, 5), rng)
    assert all(np.array_equal(d[k], again[k]) for k in d)


def test_context_is_deterministic_and_oracle_never_reaches_main_actions(synth, study):
    oracle_a = RO.ReadoutCalibration(np.full(4, 0.02), np.full(4, 0.04))
    oracle_b = RO.ReadoutCalibration(np.full(4, 0.2), np.full(4, 0.1))
    a = _run(study, synth, oracle_a)
    b = _run(study, synth, oracle_a)
    c = _run(study, synth, oracle_b)
    assert a["rows"] == b["rows"] and a["intervals"] == b["intervals"]
    main = [r for r in a["rows"] if r["vector"] != "A1-oracle"]
    main_c = [r for r in c["rows"] if r["vector"] != "A1-oracle"]
    assert main == main_c and a["intervals"] == c["intervals"]
    oa = [r for r in a["rows"] if r["vector"] == "A1-oracle"]
    oc = [r for r in c["rows"] if r["vector"] == "A1-oracle"]
    assert oa != oc
    assert len(a["rows"]) == study.replicates * len(ST.VECTORS)
    assert {(x, y) for x, y in a["intervals"]} == set(ST.BOOT_COMPARISONS)


def test_readout_mitigation_recovers_clean_scores_from_observable_calibration():
    from qtrace.noise.diagnostics import parity_z
    from qtrace.noise.shots import sample_counts

    rng = np.random.default_rng(31)
    base = rng.dirichlet(np.ones(16), size=300)
    noisy = apply_readout(base, 0.025, 0.075)
    e0, e1 = np.zeros((1, 16)), np.zeros((1, 16))
    e0[0, 0], e1[0, 15] = 1.0, 1.0
    cal_exact = RO.estimate_calibration(
        apply_readout(e0, 0.025, 0.075)[0], apply_readout(e1, 0.025, 0.075)[0]
    )
    rec, _ = RO.mitigate(noisy, cal_exact)
    assert (
        np.max(np.abs(parity_z(rec) - parity_z(base))) <= 1e-12
    )  # exact calibration: exact recovery
    errs_a0, errs_a1 = [], []
    for seed in range(5):
        g = np.random.default_rng(seed)
        counts = sample_counts(noisy, 4096, g) / 4096
        c0 = sample_counts(apply_readout(e0, 0.025, 0.075), 4096, g)[0]
        c1 = sample_counts(apply_readout(e1, 0.025, 0.075), 4096, g)[0]
        mit, _ = RO.mitigate(counts, RO.estimate_calibration(c0, c1))
        errs_a0.append(np.mean(np.abs(parity_z(counts) - parity_z(base))))
        errs_a1.append(np.mean(np.abs(parity_z(mit) - parity_z(base))))
    assert np.mean(errs_a1) < np.mean(errs_a0)


def test_exact_actions_without_noise_are_identity(synth, study):
    y, probs, _, clean_s = synth
    base = {f: probs[1] for f in (1, 3, 5)}
    ident = RO.ReadoutCalibration(np.zeros(4), np.zeros(4))
    from qtrace.mitigation.zne import extrapolation_weights

    w = extrapolation_weights((1, 3, 5), "linear_least_squares")
    r = extrapolation_weights((1, 3, 5), "richardson")
    vecs, _ = ST.action_scores(base, ident, ident, w, r, 0.5)
    for v in ("A1", "A2", "A3", "A1-oracle", "A2-rich", "A3-rich"):
        assert np.max(np.abs(vecs[v] - vecs["A0"])) <= 1e-12


def test_single_frozen_threshold_in_code():
    """max_f1_threshold is called exactly once in Phase 4 code: to reproduce the frozen tau."""
    calls = []
    for path in sorted((ROOT / "src" / "qtrace" / "mitigation").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Attribute) and node.attr == "max_f1_threshold":
                calls.append(path.name)
    assert calls == ["study.py"]
    text = (ROOT / "src" / "qtrace" / "mitigation" / "study.py").read_text()
    assert "tau = study.frozen_tau" in text


def _row(metric, d, lo, hi, comp=0.05):
    return {"metric": metric, "mean_delta": d, "ci_low": lo, "ci_high": hi, "comparator_mean": comp}


def test_rrb_rule(study):
    g2 = study.g2
    assert ST._rrb(_row("auprc", 0.012, 0.001, 0.02), g2) == (True, False)
    assert ST._rrb(_row("auprc", 0.009, 0.001, 0.02), g2) == (False, False)
    assert ST._rrb(_row("auprc", 0.02, -0.001, 0.04), g2) == (False, False)
    assert ST._rrb(_row("auprc", -0.02, -0.04, -0.001), g2) == (False, True)
    assert ST._rrb(_row("brier", -0.006, -0.008, -0.004, 0.05), g2) == (True, False)
    assert ST._rrb(_row("brier", -0.004, -0.006, -0.002, 0.05), g2) == (False, False)
    assert ST._rrb(_row("brier", 0.006, 0.004, 0.008, 0.05), g2) == (False, True)
    assert ST._rrb(_row("f1", 0.06, 0.01, 0.1), g2) == (True, False)


def _cells(benefits):
    rows = []
    for cond, arm, action, endpoint, qual, ben in benefits:
        rows.append(
            {
                "condition": cond,
                "arm": arm,
                "action": action,
                "endpoint": endpoint,
                "qualifying": qual,
                "rrb_benefit": ben,
                "rrb_harm": False,
            }
        )
    return pd.DataFrame(rows)


def _best(actions_by_endpoint):
    rows = []
    for e, acts in actions_by_endpoint.items():
        for i, a in enumerate(acts):
            rows.append({"condition": f"c{i}", "arm": "s1024", "endpoint": e, "best_action": a})
    return pd.DataFrame(rows)


def test_g2_verdicts(study):
    g2 = study.g2
    varied = _best({"auprc": ["A0", "A0"], "brier": ["A0", "A1"], "f1": ["A0", "A0"]})
    const = _best({"auprc": ["A0", "A0"], "brier": ["A1", "A1"], "f1": ["A0", "A0"]})
    none = _cells([("ar-050", "s1024", "A1", "brier", True, False)])
    calib = _cells([("ar-050", "s1024", "A1", "brier", True, True)])
    one_auprc = _cells(
        [
            ("ar-050", "s1024", "A1", "brier", True, True),
            ("comb-high", "s1024", "A3", "auprc", True, True),
        ]
    )
    two_auprc = _cells(
        [
            ("comb-high", "s1024", "A3", "auprc", True, True),
            ("comb-high", "s4096", "A3", "auprc", True, True),
        ]
    )
    nc_only = _cells(
        [
            ("dep-high", "s1024", "A1", "auprc", False, True),
            ("dep-high", "s4096", "A1", "auprc", False, True),
        ]
    )
    assert ST.g2_verdict(none, varied, g2)["verdict"] == "FAIL"
    assert ST.g2_verdict(calib, const, g2)["verdict"] == "FAIL"  # universal dominance
    assert ST.g2_verdict(calib, varied, g2)["verdict"] == "CONDITIONAL PASS"
    assert ST.g2_verdict(one_auprc, varied, g2)["verdict"] == "CONDITIONAL PASS"
    assert ST.g2_verdict(two_auprc, varied, g2)["verdict"] == "PASS"
    assert ST.g2_verdict(nc_only, varied, g2)["verdict"] == "FAIL"  # negative controls never count
    flagged = _cells(
        [
            ("clean", "s1024", "A2", "auprc", False, True),
            ("comb-high", "s1024", "A3", "auprc", True, True),
            ("comb-high", "s4096", "A3", "auprc", True, True),
        ]
    )
    out = ST.g2_verdict(flagged, varied, g2)
    assert out["computed_verdict"] == "PASS" and out["verdict"].startswith("NOT ISSUED")


def test_best_action_prefers_cheapest_within_minimum_effect(study):
    rows = []
    vals = {
        "A0": (0.50, 0.050, 0.60),
        "A1": (0.505, 0.010, 0.70),
        "A2": (0.52, 0.0095, 0.62),
        "A3": (0.509, 0.0105, 0.71),
    }
    for cond in study.conditions:
        for b in study.shot_budgets:
            for v in ST.COST_ORDER:
                a, br, f = vals[v]
                rows.append(
                    {
                        "condition": cond,
                        "arm": b.arm_id,
                        "vector": v,
                        "replicate": 0,
                        "auprc": a,
                        "brier": br,
                        "f1": f,
                    }
                )
    best = ST.best_actions(pd.DataFrame(rows), study).set_index("endpoint")
    first = best.groupby(level=0).first()
    assert first.loc["auprc", "best_action"] == "A2"  # 0.52 vs A0 0.50: beyond 0.01
    assert first.loc["brier", "best_action"] == "A1"  # within 10% of the best (0.0095)
    assert first.loc["f1", "best_action"] == "A1"  # 0.70 within 0.05 of 0.71


def test_phase4_static_guard_and_access():
    from qtrace.data.access import PartitionAccessError, check_access

    assert check_access("phase4", ["vqc_val"]) == ("vqc_val",)
    for bad in ("vqc_train", "ctrl_train", "ctrl_val", "ctrl_test"):
        with pytest.raises(PartitionAccessError):
            check_access("phase4", [bad])
    sources = sorted((ROOT / "src" / "qtrace" / "mitigation").rglob("*.py"))
    sources += sorted((ROOT / "scripts").glob("*mitigation*.py")) + sorted(
        (ROOT / "scripts").glob("*p4*.py")
    )
    for path in sources:
        consts = {
            n.value
            for n in ast.walk(ast.parse(Path(path).read_text()))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        }
        assert not any("ctrl_" in c for c in consts), path
