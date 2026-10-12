"""Decision-time feature extraction (registry-driven).

Must not import qtrace.counterfactual or qtrace.evaluation (PROJECT_SPEC rule R1).
"""

from qtrace.features.registry import (
    FeatureRegistry,
    FeatureSpec,
    LeakageError,
    assert_deployable,
    load_registry,
)

__all__ = ["FeatureRegistry", "FeatureSpec", "LeakageError", "assert_deployable", "load_registry"]
