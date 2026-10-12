"""Raw quantum-resource accounting per action (PREREG_P4 §10; F25, O08).

Totals are per batch of ``n_inferences`` logical inferences (one transaction scored
once). Field names mirror ``qtrace.records.ResourceUsage``; nothing is collapsed
into one number. Wall-clock time is recorded elsewhere and is never a decision cost.
"""

from __future__ import annotations

ACTIONS = ("A0", "A1", "A2", "A3", "RM3", "RM9")
DIAGNOSTICS = {"A1-oracle": "A1", "A2-rich": "A2", "A3-rich": "A3"}


def _gate_shots(stats: dict, shots: int) -> dict[str, int]:
    return {
        "cx_shots": shots * stats["cx"],
        "noisy_1q_shots": shots * stats["noisy_1q"],
        "depth_weighted_shots": shots * stats["depth"],
    }


def _add(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}


def action_costs(
    action: str,
    shots: int,
    n_inferences: int,
    folded: dict[int, dict],
    calibration: tuple[dict, dict],
) -> dict:
    """``folded``: noise factor -> circuit statistics; ``calibration``: (all-zeros, all-ones)."""
    if action in DIAGNOSTICS:
        action = DIAGNOSTICS[action]
    n, base = n_inferences, folded[1]
    task_mult = {"RM3": 3, "RM9": 9}.get(action, 1)
    task_shots = n * shots * task_mult
    gates = _gate_shots(base, task_shots)
    mitigation_circuits = mitigation_shots = 0
    if action in ("A2", "A3"):
        for factor, stats in folded.items():
            if factor == 1:
                continue
            mitigation_circuits += n
            mitigation_shots += n * shots
            gates = _add(gates, _gate_shots(stats, n * shots))
    calibration_circuits = calibration_shots = 0
    if action in ("A1", "A3"):
        calibration_circuits, calibration_shots = len(calibration), len(calibration) * shots
        for stats in calibration:
            gates = _add(gates, _gate_shots(stats, shots))
    out = {
        "logical_inferences": n,
        "task_circuit_executions": n,
        "task_shots": task_shots,
        "mitigation_circuit_executions": mitigation_circuits,
        "mitigation_shots": mitigation_shots,
        "calibration_circuit_executions": calibration_circuits,
        "calibration_shots": calibration_shots,
        **gates,
    }
    out["total_circuit_executions"] = n + mitigation_circuits + calibration_circuits
    out["total_shots"] = task_shots + mitigation_shots + calibration_shots
    out["shots_per_inference"] = out["total_shots"] / n
    out["circuits_per_inference"] = out["total_circuit_executions"] / n
    out["cx_shots_per_inference"] = out["cx_shots"] / n
    return out


def resource_matched_comparator(action: str) -> str:
    """Shot-matched no-mitigation comparator (primary cost; PREREG_P4 §5)."""
    return {"A1": "A0", "A2": "RM3", "A3": "RM3"}[action]
