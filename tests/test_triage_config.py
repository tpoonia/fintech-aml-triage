import pytest

from src.triage_config import priority_for_level, risk_level_for_score


@pytest.mark.parametrize(
    ("score", "level", "priority"),
    [
        (73, "CRITICAL", "P1"),
        (47, "HIGH", "P2"),
        (46, "MEDIUM", "P3"),
        (25, "MEDIUM", "P3"),
        (24, "LOW", "P4"),
    ],
)
def test_shared_score_tiers(score, level, priority):
    assert risk_level_for_score(score) == level
    assert priority_for_level(level) == priority
