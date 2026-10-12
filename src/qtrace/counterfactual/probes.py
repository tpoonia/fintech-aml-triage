"""Pre-action probes (A01, O19, A15): label-free, cheap, executed before action selection.

Readout probe: the two calibration circuits (|0...0>, |1...1>), S shots each. Its counts
are the calibration that A1/A3 reuse, so the readout probe adds no cost for them.

Gate probe: a FIXED set of synthetic parameter bindings (data-free: angles drawn once
from U(-hw, hw), the model's own frozen θ) run through the model's transpiled circuit
at global-fold scales 1 and 3, S shots each. Features summarize how much the model's
own observable contracts when gate noise is amplified. No transaction, label or
post-action output is used.
"""

from __future__ import annotations

import numpy as np

from qtrace.mitigation import readout as RO


def probe_angles(n_bindings: int, half_width: float, rng: np.random.Generator) -> np.ndarray:
    return rng.uniform(-half_width, half_width, size=(n_bindings, 4))


def readout_features(cal0: np.ndarray, cal1: np.ndarray, shots: int) -> dict[str, float]:
    est = RO.estimate_calibration(cal0, cal1)
    p01, p10 = float(np.mean(est.p01)), float(np.mean(est.p10))
    err = (p01 + p10) / 2
    n = len(est.p01)
    return {
        "probe_readout_p01_mean": p01,
        "probe_readout_p10_mean": p10,
        "probe_readout_error_mean": err,
        "probe_readout_asymmetry": p10 - p01,
        "probe_readout_se": float(np.sqrt(max(err * (1 - err), 0.0) / (2 * n * shots))),
    }


def gate_features(
    counts1: np.ndarray, counts3: np.ndarray, diagonal: np.ndarray, shots: int
) -> dict[str, float]:
    z1 = (counts1 @ diagonal) / shots
    z3 = (counts3 @ diagonal) / shots
    a1, a3 = float(np.mean(np.abs(z1))), float(np.mean(np.abs(z3)))
    return {
        "probe_gate_abs_z_lambda1": a1,
        "probe_gate_abs_z_lambda3": a3,
        "probe_gate_contraction": a3 / a1 if a1 > 0 else 1.0,
        "probe_gate_slope": float(np.mean((z3 - z1) / 2)),
        "probe_gate_abs_slope": float(np.mean(np.abs(z3 - z1) / 2)),
        "probe_gate_shot_variance": float(np.mean((1 - z1**2) / shots)),
    }


def probe_costs(
    shots: int,
    n_bindings: int,
    folded: dict[int, dict],
    calibration: tuple[dict, dict],
    n_inferences: int,
) -> dict:
    """Batch-level probe cost (charged to any probing policy; Phase 7 total = probe + action)."""
    gate_circ = 2 * n_bindings
    gate_shots = gate_circ * shots
    cal_circ, cal_shots = 2, 2 * shots
    cx = n_bindings * shots * (folded[1]["cx"] + folded[3]["cx"])
    q1 = n_bindings * shots * (folded[1]["noisy_1q"] + folded[3]["noisy_1q"])
    q1 += shots * sum(c["noisy_1q"] for c in calibration)
    depth = n_bindings * shots * (folded[1]["depth"] + folded[3]["depth"])
    depth += shots * sum(c["depth"] for c in calibration)
    total_shots = gate_shots + cal_shots
    return {
        "probe_gate_circuit_executions": gate_circ,
        "probe_gate_shots": gate_shots,
        "probe_readout_circuit_executions": cal_circ,
        "probe_readout_shots": cal_shots,
        "probe_total_circuit_executions": gate_circ + cal_circ,
        "probe_total_shots": total_shots,
        "probe_cx_shots": cx,
        "probe_noisy_1q_shots": q1,
        "probe_depth_weighted_shots": depth,
        "probe_shots_per_inference": total_shots / n_inferences,
        "probe_readout_reused_by": "A1|A3",
    }
