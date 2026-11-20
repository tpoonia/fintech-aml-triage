import json
import re

import pandas as pd

from src.dashboard import visuals
from src.triage_config import SCORE_THRESHOLDS


def _alerts(n=300):
    tiers = (["P1"] * 5 + ["P2"] * 25 + ["P3"] * 250 + ["P4"] * 20)[:n]
    return pd.DataFrame({
        "alert_id": [f"A{i:05d}" for i in range(n)],
        "customer_id": [f"C{i % 40:04d}" for i in range(n)],
        "priority": tiers,
        "risk_score": [90 - i * 0.2 for i in range(n)],
        "ml_probability": [0.9 - i * 0.002 for i in range(n)],
        "behavioral_risk": [0.5] * n,
        "transaction_amount": [100.0 + i for i in range(n)],
        "alert_type": ["NEW_COUNTERPARTY"] * n,
    })


def _embedded_data(doc):
    match = re.search(r"var (?:DATA|D)=(\{.*?\});\n", doc)
    assert match, "payload not embedded"
    return json.loads(match.group(1))


def test_sampling_keeps_every_urgent_alert():
    df = _alerts()
    payload = visuals.galaxy_payload(df, limit=60)
    assert payload["shown"] == 60
    assert payload["tier"].count(0) == 5 and payload["tier"].count(1) == 25
    assert len(payload["pos"]) == 3 * 60


def test_galaxy_places_higher_risk_closer_to_core():
    payload = visuals.galaxy_payload(_alerts())
    pos = payload["pos"]
    radius = [(pos[i * 3] ** 2 + pos[i * 3 + 2] ** 2) ** 0.5 for i in range(payload["shown"])]
    p1 = [r for r, t in zip(radius, payload["tier"]) if t == 0]
    p3 = [r for r, t in zip(radius, payload["tier"]) if t == 2]
    assert sum(p1) / len(p1) < sum(p3) / len(p3)


def test_components_embed_valid_payloads_and_no_ground_truth():
    df = _alerts()
    hero = visuals.galaxy_hero(visuals.galaxy_payload(df), [{"label": "Alerts", "value": 300}], {"P1": 5}, 300)
    explorer = visuals.risk_explorer(visuals.explorer_payload(df, visuals.explorer_bounds(df)))
    for doc in (hero, explorer):
        assert doc.startswith("<!doctype html>")
        assert "app/static/vendor/three.min.js" in doc
        assert "is_suspicious" not in doc
        _embedded_data(doc)
    data = _embedded_data(explorer)
    assert data["total"] == 300 and len(data["id"]) == data["shown"]


def test_gauge_uses_shared_thresholds_and_escapes_text():
    doc = visuals.risk_gauge("<A1>", 80, "P1", SCORE_THRESHOLDS, [("ML <prob>", 50, "50%")])
    assert "&lt;A1&gt;" in doc and "ML &lt;prob&gt;" in doc
    assert "var score=80.0" in doc


def test_learn_story_uses_real_numbers_and_scroll_libs():
    facts = {
        "total": 1000, "tiers": {"P1": 10, "P2": 90, "P3": 850, "P4": 50},
        "thresholds": dict(SCORE_THRESHOLDS), "action_share": 0.15, "p1_share": 0.01, "p1_hit": 1.0,
        "example": {"id": "A<1>", "score": 88, "type": "New counterparty", "amount": "$10.00", "reasons": ["Burst <x>"]},
    }
    doc = visuals.learn_story(facts)
    assert "ScrollTrigger.min.js" in doc and "three.min.js" in doc
    assert "1 in 7" in doc and "1,000 alerts" in doc
    assert "A&lt;1&gt;" in doc and "Burst &lt;x&gt;" in doc
    assert doc.count('class="step"') == 7
