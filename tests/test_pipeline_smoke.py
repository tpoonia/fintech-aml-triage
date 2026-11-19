import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def test_demo_pipeline_outputs_and_all_dashboard_tabs(monkeypatch):
    result = subprocess.run(
        [sys.executable, "run_pipeline.py", "--demo", "--n-customers", "200"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Pipeline completed" in result.stdout

    processed = ROOT / "data" / "processed"
    expected = [
        processed / "alerts.csv",
        processed / "ml_alert_dataset.csv",
        processed / "aml_risk_scored_alerts.csv",
        processed / "aml_explained_alerts.csv",
        processed / "aml_prioritized_alerts.csv",
        ROOT / "models" / "metrics.json",
        ROOT / "models" / "risk_scoring_summary.json",
        ROOT / "models" / "prioritization_summary.json",
        ROOT / "models" / "xai_summary.json",
        ROOT / "models" / "aml_random_forest.joblib",
    ]
    assert all(path.exists() for path in expected)

    metrics = json.loads((ROOT / "models" / "metrics.json").read_text())
    risk_summary = json.loads((ROOT / "models" / "risk_scoring_summary.json").read_text())
    queue_summary = json.loads((ROOT / "models" / "prioritization_summary.json").read_text())
    assert metrics["customer_overlap"] == 0
    assert "is_suspicious" not in metrics["numeric_features"]
    assert "investigation_outcome" not in metrics["categorical_features"]
    assert risk_summary["priority_distribution"] == queue_summary["priority_distribution"]
    assert risk_summary["risk_level_distribution"] == queue_summary["risk_level_distribution"]
    queue = processed / "aml_prioritized_alerts.csv"
    queue_columns = set(pd.read_csv(queue, nrows=1).columns)
    assert "is_suspicious" not in queue_columns
    assert "target" not in queue_columns

    monkeypatch.setenv("AML_ALERTS_DATA_PATH", str(queue))
    dashboard = AppTest.from_file(str(ROOT / "src" / "dashboard" / "app.py"), default_timeout=30).run()
    assert not dashboard.exception
    assert len(dashboard.get("tab")) >= 6
