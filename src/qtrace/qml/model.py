"""Clean VQC: probability readout, BCE objective, COBYLA training, freezing and replay.

Readout (O01, fixed before evaluation): z = <Z^n> in [-1, 1] and
``p_fraud = (1 - z) / 2``. Loss: binary cross-entropy with p clipped to
[eps, 1 - eps] before the logarithms (eps from the config).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, ConfigDict
from scipy.optimize import minimize

from qtrace.config.schemas import OptimizerConfig
from qtrace.qml.simulate import ansatz_unitary, parity_diagonal, parity_expectations
from qtrace.utils.hashing import stable_hash


def fraud_probability(z: np.ndarray) -> np.ndarray:
    return (1.0 - z) / 2.0


def bce(y: np.ndarray, p: np.ndarray, eps: float) -> float:
    q = np.clip(p, eps, 1.0 - eps)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))


def initial_parameters(n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).uniform(-np.pi, np.pi, size=n)


@dataclass
class TrainingResult:
    theta: np.ndarray
    theta0: np.ndarray
    trace: list[float]  # loss at every objective evaluation, in order
    final_loss: float  # loss at the returned parameters (scipy ``res.fun``)
    nfev: int
    status: int
    message: str
    seconds: float

    @property
    def initial_loss(self) -> float:
        return self.trace[0]


def train(
    ans,
    states: np.ndarray,
    y: np.ndarray,
    opt: OptimizerConfig,
    eps: float,
    seed: int,
    diagonal: np.ndarray | None = None,
) -> TrainingResult:
    """``diagonal``: Z-type observable eigenvalues per basis state (default: n-qubit parity)."""
    parity = parity_diagonal(ans.num_qubits) if diagonal is None else diagonal
    trace: list[float] = []

    def objective(theta: np.ndarray) -> float:
        z = parity_expectations(states, ansatz_unitary(ans, theta), parity)
        loss = bce(y, fraud_probability(z), eps)
        trace.append(loss)
        return loss

    theta0 = initial_parameters(ans.num_parameters, seed)
    start = time.perf_counter()
    res = minimize(
        objective,
        theta0.copy(),
        method="COBYLA",
        options={"maxiter": opt.max_evaluations, "rhobeg": opt.rhobeg, "tol": opt.tol},
    )
    seconds = time.perf_counter() - start
    return TrainingResult(
        theta=np.asarray(res.x, dtype=np.float64),
        theta0=theta0,
        trace=trace,
        final_loss=float(res.fun),
        nfev=int(res.nfev),
        status=int(res.status),
        message=str(res.message),
        seconds=seconds,
    )


class FrozenVQC(BaseModel):
    """Everything needed to replay the trained VQC; committed under artifacts/."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    vqc_id: str
    theta: tuple[float, ...]
    theta_sha256: str
    vqc_config_sha256: str
    dataset_sha256: str
    split_vqc_train_sha256: str
    preprocessing_sha256: str
    features: tuple[str, ...]
    encoder: dict
    encoder_sha256: str
    subset_rows_sha256: str
    init_seed: int
    readout: str
    software: dict[str, str]

    def artifact_sha256(self) -> str:
        return stable_hash(self)


def theta_sha256(theta: np.ndarray) -> str:
    return stable_hash([float(v) for v in theta])


def predict(
    ans, states: np.ndarray, theta: np.ndarray, diagonal: np.ndarray | None = None
) -> np.ndarray:
    diag = parity_diagonal(ans.num_qubits) if diagonal is None else diagonal
    return fraud_probability(parity_expectations(states, ansatz_unitary(ans, theta), diag))
