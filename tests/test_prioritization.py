import json

import pandas as pd

from src.prioritization import prioritize_alerts


def test_prioritization_preserves_shared_score_tiers_and_creates_p1(tmp_path, monkeypatch):
    source = tmp_path / "risk.csv"
    pd.DataFrame(
        {
            "alert_id": ["A1", "A2", "A3", "A4"],
            "customer_id": ["C1", "C2", "C3", "C4"],
            "risk_score": [90, 60, 47, 46],
            "transaction_amount": [5_000, 4_000, 3_000, 2_000],
            "amount_deviation_ratio": [2, 1, 0.5, 0.2],
            "transactions_last_7_days": [5, 4, 3, 2],
            "unique_counterparties": [5, 4, 3, 2],
            "is_cross_border": [1, 0, 0, 0],
            "target": [1, 1, 0, 0],
        }
    ).to_csv(source, index=False)
    output = tmp_path / "queue.csv"
    summary = tmp_path / "summary.json"
    monkeypatch.setattr(prioritize_alerts, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(prioritize_alerts, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(prioritize_alerts, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(prioritize_alerts, "EXPLAINED_PATH", tmp_path / "missing.csv")
    monkeypatch.setattr(prioritize_alerts, "RISK_SCORED_PATH", source)
    monkeypatch.setattr(prioritize_alerts, "OUTPUT_PATH", output)
    monkeypatch.setattr(prioritize_alerts, "SUMMARY_PATH", summary)

    prioritize_alerts.main()

    queue = pd.read_csv(output)
    assert queue.loc[queue.alert_id == "A1", "priority"].item() == "P1"
    assert queue.set_index("alert_id").loc["A2", "priority"] == "P2"
    assert queue.set_index("alert_id").loc["A3", "priority"] == "P2"
    assert queue.set_index("alert_id").loc["A4", "priority"] == "P3"
    assert queue["risk_level"].tolist()[0] == "CRITICAL"
    assert "target" not in queue.columns
    summary_data = json.loads(summary.read_text())
    assert summary_data["input_file"] == "risk.csv"
    assert summary_data["output_file"] == "queue.csv"
    assert summary_data["priority_distribution"]["P1"] > 0
    assert summary_data["risk_level_distribution"]["CRITICAL"] == summary_data["priority_distribution"]["P1"]
