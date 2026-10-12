"""A13 noise diagnostics, pre-registered labels, negative control, G1 (PREREG_P3B §6-12).

Scores are p_fraud = (1 - z)/2 with z the parity expectation of the measured
distribution. Every noisy condition is paired with the clean reference on the
identical ordered rows; Delta = noisy - clean.
"""

from __future__ import annotations

import numpy as np
from joblib import Parallel, delayed

from qtrace.config.schemas import A13RulesConfig
from qtrace.evaluation import metrics as M
from qtrace.evaluation.bootstrap import percentile_interval, stratified_weights
from qtrace.qml.simulate import parity_diagonal

LABELS = (
    "ranking_preserving",
    "ranking_distortion",
    "calibration_distortion",
    "threshold_distortion",
    "discrimination_degradation",
)
BOOT_METRICS = ("auprc", "auroc", "brier", "ece")
TREND_TOL = 1e-9


def parity_z(probs: np.ndarray) -> np.ndarray:
    return np.atleast_2d(probs) @ parity_diagonal(int(np.log2(np.shape(probs)[-1])))


def fraud_score(probs: np.ndarray) -> np.ndarray:
    """p_fraud = (1 - z)/2, clipped to [0, 1] against ~1e-16 simulator round-off."""
    return np.clip((1.0 - parity_z(probs)) / 2.0, 0.0, 1.0)


def condition_metrics(
    y: np.ndarray, clean: np.ndarray, noisy: np.ndarray, tau: float, top_k, n_bins: int
) -> dict[str, float]:
    """Point diagnostics of one condition against the clean reference (A13 measures)."""
    shift = noisy - clean
    clean_flag, noisy_flag = clean >= tau, noisy >= tau
    crossed = clean_flag != noisy_flag
    out = {
        "auprc": M.average_precision(y, noisy),
        "auroc": M.roc_auc(y, noisy),
        "brier": M.brier(y, noisy),
        "ece": M.expected_calibration_error(y, noisy, n_bins, "uniform"),
    }
    ref = {
        "auprc": M.average_precision(y, clean),
        "auroc": M.roc_auc(y, clean),
        "brier": M.brier(y, clean),
        "ece": M.expected_calibration_error(y, clean, n_bins, "uniform"),
    }
    for name in BOOT_METRICS:
        out[f"delta_{name}"] = out[name] - ref[name]
    out |= {
        "spearman": M.spearman(clean, noisy),
        "kendall": M.kendall(clean, noisy),
        **{f"top{k}_overlap": M.top_k_overlap(clean, noisy, k) for k in top_k},
        "mean_shift": float(np.mean(shift)),
        "median_shift": float(np.median(shift)),
        "mean_abs_shift": float(np.mean(np.abs(shift))),
        "max_abs_shift": float(np.max(np.abs(shift))),
        "variance_clean": float(np.var(clean)),
        "variance_noisy": float(np.var(noisy)),
        "variance_ratio": float(np.var(noisy) / np.var(clean)),
        "crossing_fraction": float(crossed.mean()),
        "fraud_crossing_rate": float(crossed[y == 1].mean()),
        "legit_crossing_rate": float(crossed[y == 0].mean()),
        "flagged_clean": int(clean_flag.sum()),
        "flagged_noisy": int(noisy_flag.sum()),
        **{f"{k}_at_tau": v for k, v in M.threshold_metrics(y, noisy, tau).items()},
    }
    return out


def _boot_samples(y, scores, n_resamples, seed, n_bins) -> dict[str, np.ndarray]:
    out = {m: np.empty(n_resamples) for m in BOOT_METRICS}
    for b, w in enumerate(stratified_weights(y, n_resamples, seed)):
        out["auprc"][b] = M.average_precision(y, scores, w)
        out["auroc"][b] = M.roc_auc(y, scores, w)
        out["brier"][b] = M.brier(y, scores, w)
        out["ece"][b] = M.expected_calibration_error_weighted(y, scores, w, n_bins)
    return out


def paired_bootstrap(
    y: np.ndarray,
    clean: np.ndarray,
    noisy: dict[str, np.ndarray],
    n_resamples: int,
    seed: int,
    n_bins: int,
    confidence: float = 0.95,
    n_jobs: int = -1,
) -> dict[str, dict[str, tuple[float, float]]]:
    """Percentile CIs of each condition's metrics and of noisy - clean on the SAME resamples.

    Every call regenerates the identical resample sequence from ``seed`` (the shared
    Phase 2 vqc_val bootstrap), so clean and noisy are paired resample by resample.
    """
    keys = list(noisy)
    samples = Parallel(n_jobs=n_jobs)(
        delayed(_boot_samples)(y, s, n_resamples, seed, n_bins) for s in [clean, *noisy.values()]
    )
    ref = samples[0]
    out = {}
    for key, smp in zip(keys, samples[1:], strict=True):
        out[key] = {}
        for m in BOOT_METRICS:
            out[key][m] = percentile_interval(smp[m], confidence)
            out[key][f"delta_{m}"] = percentile_interval(smp[m] - ref[m], confidence)
    out["clean"] = {m: percentile_interval(ref[m], confidence) for m in BOOT_METRICS}
    return out


def _excludes_zero(ci: tuple[float, float]) -> bool:
    return ci[0] > 0 or ci[1] < 0


def _contains_zero(ci: tuple[float, float]) -> bool:
    return ci[0] <= 0 <= ci[1]


def a13_labels(m: dict, ci: dict, clean_brier: float, rules: A13RulesConfig) -> dict[str, bool]:
    """Pre-registered, multi-label, pilot-indicative A13 rules (PREREG_P3B §8)."""
    rho, tau_k = m["spearman"], m["kendall"]
    top = m[f"top{rules.topk_for_overlap_rule}_overlap"]
    monotone = rho >= rules.spearman_monotonic and tau_k >= rules.kendall_monotonic
    calib = rho >= rules.calibration_spearman_min and (
        (
            abs(m["delta_brier"]) >= rules.brier_relative_change * clean_brier
            and _excludes_zero(ci["delta_brier"])
        )
        or (abs(m["delta_ece"]) >= rules.ece_abs_change and _excludes_zero(ci["delta_ece"]))
    )
    return {
        "ranking_preserving": monotone
        and _contains_zero(ci["delta_auprc"])
        and _contains_zero(ci["delta_auroc"]),
        "ranking_distortion": not monotone or top < rules.topk_overlap_min,
        "calibration_distortion": calib,
        "threshold_distortion": rho >= rules.calibration_spearman_min
        and (
            m["crossing_fraction"] >= rules.threshold_crossing_fraction
            or m["fraud_crossing_rate"] >= rules.fraud_crossing_rate
        ),
        "discrimination_degradation": (ci["delta_auprc"][1] < 0 or ci["delta_auroc"][1] < 0)
        and rho < rules.spearman_monotonic,
    }


def negative_control(
    y: np.ndarray, z_clean: np.ndarray, z_noisy: np.ndarray, p: float, n_qubits: int
) -> dict:
    """Exact symmetric readout must be the affine contraction z -> (1 - 2p)^n z (PREREG §11)."""
    factor = (1 - 2 * p) ** n_qubits
    s_clean, s_noisy = (1 - z_clean) / 2, (1 - z_noisy) / 2
    out = {
        "readout_p": p,
        "contraction_factor": factor,
        "max_abs_affine_residual": float(np.max(np.abs(z_noisy - factor * z_clean))),
        "abs_delta_auprc": abs(M.average_precision(y, s_noisy) - M.average_precision(y, s_clean)),
        "abs_delta_auroc": abs(M.roc_auc(y, s_noisy) - M.roc_auc(y, s_clean)),
        "spearman": M.spearman(s_clean, s_noisy),
    }
    out["passed"] = bool(
        out["max_abs_affine_residual"] <= 1e-10
        and out["abs_delta_auprc"] <= 1e-9
        and out["abs_delta_auroc"] <= 1e-9
        and out["spearman"] >= 1 - 1e-9
    )
    return out


def non_increasing(values) -> bool:
    return all(b <= a + TREND_TOL for a, b in zip(values, values[1:], strict=False))


def severity_trend(rows_low_to_high: list[dict]) -> dict[str, bool]:
    d = [r["delta_auprc"] for r in rows_low_to_high]
    s = [r["spearman"] for r in rows_low_to_high]
    return {
        "delta_auprc_non_increasing": non_increasing(d),
        "spearman_non_increasing": non_increasing(s),
        "trend": non_increasing(d) or non_increasing(s),
    }


def g1_verdict(conditions: list[dict], rules: A13RulesConfig) -> dict:
    """G1 on the primary model's exact Stage 1 (PREREG_P3B §12).

    ``conditions``: dicts with ``condition``, ``g1_family``, ``severity``, ``role``,
    the A13 ``labels`` and the point metrics. Negative controls are excluded.
    """
    order = {"low": 0, "medium": 1, "high": 2}
    eligible = [c for c in conditions if c["role"] != "negative_control"]
    families: dict[str, list[dict]] = {}
    for c in sorted(eligible, key=lambda c: (c["g1_family"], order[c["severity"]])):
        families.setdefault(c["g1_family"], []).append(c)
    trends = {f: severity_trend(rows) for f, rows in families.items()}
    top = f"top{rules.topk_for_overlap_rule}_overlap"
    qualifying = [
        c["condition"]
        for c in eligible
        if (
            c["labels"]["discrimination_degradation"]
            or (c["labels"]["ranking_distortion"] and c[top] < rules.topk_overlap_min)
        )
        and trends[c["g1_family"]]["trend"]
    ]
    conditional = [
        c["condition"]
        for c in eligible
        if c["labels"]["calibration_distortion"]
        or c["labels"]["threshold_distortion"]
        or c["labels"]["ranking_distortion"]
    ]
    verdict = "PASS" if qualifying else ("CONDITIONAL PASS" if conditional else "FAIL")
    return {
        "verdict": verdict,
        "pass_qualifying_conditions": qualifying,
        "conditional_conditions": conditional,
        "family_trends": trends,
        "excluded_negative_controls": [
            c["condition"] for c in conditions if c["role"] == "negative_control"
        ],
    }
