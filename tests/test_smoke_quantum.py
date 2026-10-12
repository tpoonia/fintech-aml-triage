"""Phase 0 environment/noise smoke test (fast: one 4-qubit density-matrix circuit family)."""

from __future__ import annotations

import numpy as np

from qtrace.config import load_component
from qtrace.utils.smoke import apply_readout_confusion, run_smoke_test


def test_smoke_profile_passes_all_checks():
    profile = load_component("noise", "smoke").profiles[0]
    result = run_smoke_test(profile, shots=4096, seed=9011)
    assert result["passed"], result["checks"]


def test_readout_confusion_matches_closed_form():
    # |0000> with p01 on every qubit: P(all zero) = (1 - p01)^4.
    probs = np.zeros(16)
    probs[0] = 1.0
    out = apply_readout_confusion(probs, p01=0.02, p10=0.05)
    assert np.isclose(out.sum(), 1.0)
    assert np.isclose(out[0], 0.98**4)
    # |1111> with p10 on every qubit: P(all one) = (1 - p10)^4.
    probs = np.zeros(16)
    probs[15] = 1.0
    assert np.isclose(apply_readout_confusion(probs, 0.02, 0.05)[15], 0.95**4)
