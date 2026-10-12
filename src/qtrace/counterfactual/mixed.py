"""Phase 5C continuous mixed-noise design (PREREG_P5C §4): deterministic, registered first.

Each noise source is placed on an *anchor-severity* scale s in [0, 3]: 0 = absent and
1/2/3 = the [RR] low/medium/high anchors of Phase 3B. Physical parameters are piecewise
linear in s between anchors, so no point exceeds the validated "high" anchor.

- readout mean error r(s_ro): 0, 0.005, 0.020, 0.050 with asymmetry alpha in [0, 0.5]:
  p01 = r(1 - alpha), p10 = r(1 + alpha). alpha = 0.5 is the Phase 3B synthetic split
  (0.5p / 1.5p); the asymmetric component is a SYNTHETIC stress-test assumption.
- depolarizing (p1, p2)(s_dep): (0, 0), (0.0005, 0.005), (0.001, 0.010), (0.003, 0.020).
- thermal relaxation rates (1/T1, 1/T2)(s_th): 0, (1/200, 1/250), (1/100, 1/150),
  (1/50, 1/70) per microsecond. Linear interpolation of rates preserves T2 <= 2 T1.

Split-plot structure. Gate noise (expensive: exact density-matrix simulation per setting)
varies across *gate plots*: one gate-free plot plus a maximin Latin hypercube in
(s_dep, s_th). Readout noise (cheap: applied classically) varies within plots by a sliced
Latin hypercube in (s_ro, alpha): every plot gets one point in each quarter of both ranges.
"""

from __future__ import annotations

import hashlib
import io

import numpy as np
import pandas as pd

from qtrace.config.schemas import MixedNoiseDesignConfig, NoiseProfile, ThermalConfig
from qtrace.utils.seeds import make_rng

DESIGN_COLUMNS = (
    "point_id",
    "gate_plot",
    "s_ro",
    "alpha",
    "s_dep",
    "s_th",
    "readout_mean",
    "readout_p01",
    "readout_p10",
    "p1",
    "p2",
    "t1_us",
    "t2_us",
    "region",
)
REGIONS = ("near_clean", "readout_dominated", "gate_dominated", "mixed")


def _interp(s: float, values: tuple[float, ...]) -> float:
    return float(np.interp(s, np.arange(len(values)), values))


def _lhs(rng: np.random.Generator, n: int, dims: int) -> np.ndarray:
    """One Latin hypercube sample in [0, 1)^dims (one point per stratum and dimension)."""
    u = (rng.random((n, dims)) + np.arange(n)[:, None]) / n
    for j in range(dims):
        u[:, j] = u[rng.permutation(n), j]
    return u


def _min_distance(u: np.ndarray) -> float:
    d = np.sqrt(((u[:, None, :] - u[None, :, :]) ** 2).sum(-1))
    return float(d[np.triu_indices(len(u), 1)].min())


def maximin_lhs(rng: np.random.Generator, n: int, dims: int, candidates: int) -> np.ndarray:
    """The candidate LHS with the largest minimum pairwise distance (first wins ties)."""
    best, best_d = None, -1.0
    for _ in range(candidates):
        u = _lhs(rng, n, dims)
        d = _min_distance(u)
        if d > best_d:
            best, best_d = u, d
    return best


def sliced_lhs(rng: np.random.Generator, slices: int, per_slice: int) -> np.ndarray:
    """Sliced LHS in one dimension: ``slices x per_slice`` values in [0, 1).

    The whole set is an LHS with ``slices * per_slice`` strata, and within each slice the
    values fall in distinct coarse strata (one per 1/per_slice of the range).
    """
    n = slices * per_slice
    out = np.empty((slices, per_slice))
    for k in range(per_slice):  # coarse stratum k holds fine strata k*slices .. (k+1)*slices-1
        fine = k * slices + rng.permutation(slices)
        out[:, k] = (fine + rng.random(slices)) / n
    for j in range(slices):  # which point of the slice sits in which coarse stratum
        out[j] = out[j, rng.permutation(per_slice)]
    return out


def region(s_ro: float, s_dep: float, s_th: float, cut: float) -> str:
    gate, ro = max(s_dep, s_th) >= cut, s_ro >= cut
    if gate and ro:
        return "mixed"
    if gate:
        return "gate_dominated"
    if ro:
        return "readout_dominated"
    return "near_clean"


def build_design(cfg: MixedNoiseDesignConfig, master_seed: int) -> pd.DataFrame:
    """The registered design table (one row per noise point), fully determined by the config."""
    rng = make_rng(master_seed, "noise", cfg.seed_key)
    smax = cfg.severity_max
    gate = maximin_lhs(rng, cfg.gate_plots, 2, cfg.lhs_candidates) * smax
    plots = [(0.0, 0.0)] if cfg.gate_free_plot else []
    plots += [(float(a), float(b)) for a, b in gate]
    n_plots, k = len(plots), cfg.readout_points_per_plot
    s_ro = sliced_lhs(rng, n_plots, k) * smax
    alpha = sliced_lhs(rng, n_plots, k) * cfg.asymmetry_max
    a = cfg.anchors
    rows = []
    for g, (s_dep, s_th) in enumerate(plots):
        for j in range(k):
            sr, al = float(s_ro[g, j]), float(alpha[g, j])
            r = _interp(sr, a.readout_mean)
            g1, g2 = _interp(s_th, a.thermal_rate1_per_us), _interp(s_th, a.thermal_rate2_per_us)
            rows.append(
                {
                    "point_id": f"g{g:02d}-r{j}",
                    "gate_plot": f"g{g:02d}",
                    "s_ro": sr,
                    "alpha": al,
                    "s_dep": s_dep,
                    "s_th": s_th,
                    "readout_mean": r,
                    "readout_p01": r * (1 - al),
                    "readout_p10": r * (1 + al),
                    "p1": _interp(s_dep, a.depolarizing_p1),
                    "p2": _interp(s_dep, a.depolarizing_p2),
                    "t1_us": 1.0 / g1 if g1 > 0 else np.inf,
                    "t2_us": 1.0 / g2 if g2 > 0 else np.inf,
                    "region": region(sr, s_dep, s_th, cfg.region_cut),
                }
            )
    return pd.DataFrame(rows, columns=list(DESIGN_COLUMNS))


def design_csv(design: pd.DataFrame) -> str:
    buffer = io.StringIO()
    design.round(12).to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def design_sha256(design: pd.DataFrame) -> str:
    return hashlib.sha256(design_csv(design).encode()).hexdigest()


def profile_of(row: pd.Series | dict) -> NoiseProfile:
    """The NoiseProfile of one design point (offline metadata; never a controller input)."""
    r = dict(row)
    thermal = None
    if np.isfinite(r["t1_us"]):
        thermal = ThermalConfig(t1_us=float(r["t1_us"]), t2_us=float(r["t2_us"]))
    gate = r["p1"] > 0 or r["p2"] > 0 or thermal is not None
    return NoiseProfile(
        profile_id=r["point_id"],
        family="combined" if gate else "readout",
        role="synthetic_stress",
        p1=float(r["p1"]),
        p2=float(r["p2"]),
        readout_p01=float(r["readout_p01"]),
        readout_p10=float(r["readout_p10"]),
        thermal=thermal,
    )
