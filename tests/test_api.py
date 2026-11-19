import pandas as pd
from fastapi.testclient import TestClient

from src.api import app as api


def test_api_health_stats_filters_pagination_and_alert_not_found(tmp_path, monkeypatch):
    data_path = tmp_path / "alerts.csv"
    pd.DataFrame(
        {
            "alert_id": ["A1", "A2", "A3"],
            "queue_position": [1, 2, 3],
            "priority": ["P1", "P2", "P2"],
            "risk_level": ["CRITICAL", "HIGH", "HIGH"],
            "risk_score": [90, 60, 55],
            "priority_score": [88, 70, 65],
            "alert_type": ["WIRE", "CASH", "WIRE"],
            "alert_timestamp": ["2025-01-01", "2025-01-02", "2025-01-03"],
        }
    ).to_csv(data_path, index=False)
    monkeypatch.setattr(api, "DATA_PATH", data_path)
    read_count = 0
    original_reader = api.read_alerts

    def count_reads(path):
        nonlocal read_count
        read_count += 1
        return original_reader(path)

    monkeypatch.setattr(api, "read_alerts", count_reads)

    with TestClient(api.app) as client:
        assert read_count == 1
        assert client.get("/").status_code == 200
        health = client.get("/health").json()
        assert health["status"] == "healthy"
        assert health["total_alerts"] == 3
        assert client.get("/stats").json()["total_alerts"] == 3

        page = client.get("/alerts", params={"priority": "P2", "page": 1, "page_size": 1})
        assert page.status_code == 200
        assert page.json()["total_matching_alerts"] == 2
        assert page.json()["returned"] == 1
        assert client.get("/alerts", params={"page_size": 201}).status_code == 422

        filtered = client.get(
            "/alerts",
            params={"risk_level": "HIGH", "alert_type": "WIRE", "date_from": "2025-01-03"},
        )
        assert [row["alert_id"] for row in filtered.json()["alerts"]] == ["A3"]
        assert client.get("/alerts/A1").json()["priority"] == "P1"
        assert client.get("/alerts/UNKNOWN").status_code == 404
        assert client.get("/alerts/UNKNOWN/explanation").status_code == 404
        model = client.get("/model")
        assert model.status_code == 200
        assert model.json()["level_to_priority"]["CRITICAL"] == "P1"
        assert read_count == 1
