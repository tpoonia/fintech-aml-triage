"""Shared score tiers and investigator priority definitions."""

SCORE_THRESHOLDS = {
    "CRITICAL": 73,
    "HIGH": 47,
    "MEDIUM": 25,
}
LEVEL_TO_PRIORITY = {
    "CRITICAL": "P1",
    "HIGH": "P2",
    "MEDIUM": "P3",
    "LOW": "P4",
}
PRIORITY_ORDER = {priority: i for i, priority in enumerate(LEVEL_TO_PRIORITY.values(), start=1)}
PRIORITY_DEFINITIONS = {
    "P1": "Critical score tier; prompt human review.",
    "P2": "High score tier; elevated review queue.",
    "P3": "Medium score tier; standard review queue.",
    "P4": "Low score tier; lower review urgency.",
}


def risk_level_for_score(score: float) -> str:
    """Map a 0–100 risk score to the shared operational risk level."""
    if score >= SCORE_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    if score >= SCORE_THRESHOLDS["HIGH"]:
        return "HIGH"
    if score >= SCORE_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


def priority_for_level(level: str) -> str:
    """Map a risk level to its investigator queue priority."""
    return LEVEL_TO_PRIORITY[level]
