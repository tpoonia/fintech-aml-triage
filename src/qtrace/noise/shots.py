"""Finite-shot sampling of cached exact distributions, and its E08 validation (PREREG_P3B §9-10).

The cached-distribution sampler draws multinomial counts from the exact
(readout-included) distribution of each transaction. E08 compares it with direct
Aer shot execution (density matrix, full noise model with ``ReadoutError``,
``measure_all``) on the same rows.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from scipy import stats

from qtrace.config.schemas import E08ValidationConfig
from qtrace.noise.diagnostics import parity_z
from qtrace.qml.simulate import parity_diagonal


def sample_counts(probs: np.ndarray, shots: int, rng: np.random.Generator) -> np.ndarray:
    """Multinomial counts per row (negative round-off clipped, rows renormalized)."""
    p = np.clip(probs, 0.0, None)
    return rng.multinomial(shots, p / p.sum(axis=1, keepdims=True))


def counts_score(counts: np.ndarray, shots: int) -> np.ndarray:
    """Finite-shot p_fraud = (1 - z_shot)/2 = fraction of odd-parity outcomes."""
    return (1.0 - (counts @ parity_diagonal(int(np.log2(counts.shape[1])))) / shots) / 2.0


def direct_aer_counts(
    transpiled: QuantumCircuit,
    values: np.ndarray,
    noise_model: NoiseModel | None,
    shots: int,
    seed: int,
) -> np.ndarray:
    circuit = transpiled.copy()
    circuit.measure_all()
    sim = AerSimulator(method="density_matrix", noise_model=noise_model, seed_simulator=seed)
    params = list(circuit.parameters)
    binds = [{p: values[:, j].tolist() for j, p in enumerate(params)}]
    result = sim.run(circuit, parameter_binds=binds, shots=shots).result()
    out = np.zeros((len(values), 2**transpiled.num_qubits), dtype=np.int64)
    for i in range(len(values)):
        for key, count in result.get_counts(i).items():
            out[i, int(key.replace(" ", ""), 2)] = count
    return out


def merged_chi2(counts: np.ndarray, probs: np.ndarray, shots: int, min_expected: float):
    """Pooled Pearson chi-square; per row, the smallest bins are merged until >= min_expected.

    Merging rule: bins are sorted by expected count; all bins below ``min_expected``
    form one group, which absorbs the next-smallest bins while its expectation is
    still below ``min_expected``. A row reduced to one group contributes nothing.
    """
    stat, dof = 0.0, 0
    for c, p in zip(counts, np.clip(probs, 0.0, None), strict=True):
        e = p * shots
        order = np.argsort(e, kind="stable")
        e, c = e[order], c[order]
        k = int(np.sum(e < min_expected))
        while 0 < k < len(e) and e[:k].sum() < min_expected:
            k += 1
        exp_groups = np.concatenate([[e[:k].sum()], e[k:]]) if k else e
        obs_groups = np.concatenate([[c[:k].sum()], c[k:]]) if k else c
        if len(exp_groups) < 2:
            continue
        stat += float(np.sum((obs_groups - exp_groups) ** 2 / exp_groups))
        dof += len(exp_groups) - 1
    return stat, dof, float(stats.chi2.sf(stat, dof)) if dof else 1.0


def e08_tests(
    exact_probs: np.ndarray,
    aer_counts: np.ndarray,
    mult_counts: np.ndarray,
    shots: int,
    cfg: E08ValidationConfig,
) -> dict:
    z = parity_z(exact_probs)
    var = 1.0 - z**2
    keep = var > 1e-12  # residuals undefined where the exact parity is deterministic
    z_aer = (aer_counts @ parity_diagonal(int(np.log2(aer_counts.shape[1])))) / shots
    z_mult = (mult_counts @ parity_diagonal(int(np.log2(mult_counts.shape[1])))) / shots
    se = np.sqrt(var[keep] / shots)
    u_aer, u_mult = (z_aer[keep] - z[keep]) / se, (z_mult[keep] - z[keep]) / se
    chi2, dof, chi2_p = merged_chi2(aer_counts, exact_probs, shots, cfg.min_expected_count)
    p_exact = (1 - z) / 2
    mean_diff = float(np.mean((1 - z_aer) / 2) - np.mean(p_exact))
    mean_se = float(np.sqrt(np.sum(p_exact * (1 - p_exact) / shots)) / len(z))
    tvd_aer = 0.5 * np.abs(aer_counts / shots - exact_probs).sum(axis=1)
    tvd_mult = 0.5 * np.abs(mult_counts / shots - exact_probs).sum(axis=1)
    tvd_ratio = float(tvd_aer.mean() / tvd_mult.mean())
    ks = stats.ks_2samp(u_aer, u_mult)
    out = {
        "n_rows": len(z),
        "n_rows_residual": int(keep.sum()),
        "residual_mean_aer": float(u_aer.mean()),
        "residual_var_aer": float(u_aer.var(ddof=1)),
        "residual_mean_multinomial": float(u_mult.mean()),
        "residual_var_multinomial": float(u_mult.var(ddof=1)),
        "chi2": chi2,
        "chi2_dof": dof,
        "chi2_p": chi2_p,
        "mean_score_diff": mean_diff,
        "mean_score_se": mean_se,
        "mean_score_diff_in_se": abs(mean_diff) / mean_se,
        "tvd_mean_aer": float(tvd_aer.mean()),
        "tvd_mean_multinomial": float(tvd_mult.mean()),
        "tvd_ratio": tvd_ratio,
        "ks_statistic": float(ks.statistic),
        "ks_p": float(ks.pvalue),
    }
    lo, hi = cfg.residual_var_range
    out["pass_residual"] = bool(
        abs(out["residual_mean_aer"]) <= cfg.residual_mean_abs_max
        and lo <= out["residual_var_aer"] <= hi
    )
    out["pass_chi2"] = bool(chi2_p >= cfg.chi2_p_min)
    out["pass_mean_score"] = bool(out["mean_score_diff_in_se"] <= cfg.mean_score_se_multiple)
    out["pass_tvd_ratio"] = bool(cfg.tvd_ratio_range[0] <= tvd_ratio <= cfg.tvd_ratio_range[1])
    out["pass_ks"] = bool(out["ks_p"] >= cfg.ks_p_min)
    out["passed"] = all(out[k] for k in out if k.startswith("pass_"))
    return out
