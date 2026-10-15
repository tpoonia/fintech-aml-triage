"""
Stage 5 - AML Investigator API

FastAPI service for the AML Alert Triage Engine.

Reads:
    data/processed/aml_prioritized_alerts.csv

Provides:
    GET /                 -> API information
    GET /health           -> health check
    GET /stats            -> queue/risk statistics
    GET /alerts           -> paginated investigator queue
    GET /alerts/{alert_id}-> one alert with explanation/details
    GET /alerts/{alert_id}/explanation -> concise explanation

Run from project root:
    uvicorn src.api.app:app --reload
"""

from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "aml_prioritized_alerts.csv"

app = FastAPI(
    title="AML Alert Triage Engine API",
    description="Investigator-facing API for prioritized AML alerts.",
    version="1.0.0",
)


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Prioritized dataset not found: {DATA_PATH}. "
            "Run Stage 4 first."
        )
    return pd.read_csv(DATA_PATH)


def clean_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def row_to_dict(row: pd.Series) -> dict:
    return {key: clean_value(value) for key, value in row.to_dict().items()}


@app.get("/")
def root():
    return {
        "service": "AML Alert Triage Engine API",
        "stage": "Stage 5 - Investigator API",
        "status": "running",
        "docs": "/docs",
        "data_source": str(DATA_PATH),
    }


@app.get("/health")
def health():
    exists = DATA_PATH.exists()
    return {
        "status": "healthy" if exists else "degraded",
        "dataset_available": exists,
        "dataset_path": str(DATA_PATH),
    }


@app.get("/stats")
def stats():
    try:
        df = load_data()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    result = {"total_alerts": int(len(df))}

    for column in ["priority", "risk_level", "alert_type", "investigation_outcome"]:
        if column in df.columns:
            counts = df[column].fillna("UNKNOWN").astype(str).value_counts()
            result[f"{column}_distribution"] = {
                str(k): int(v) for k, v in counts.items()
            }

    for column in ["risk_score", "priority_score"]:
        if column in df.columns:
            values = pd.to_numeric(df[column], errors="coerce")
            result[f"average_{column}"] = round(float(values.mean()), 2)

    return result


@app.get("/alerts")
def get_alerts(
    priority: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    alert_type: Optional[str] = Query(default=None),
    investigation_outcome: Optional[str] = Query(default=None),
    min_risk_score: Optional[float] = Query(default=None, ge=0, le=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
):
    try:
        df = load_data()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    filtered = df.copy()

    filters = {
        "priority": priority,
        "risk_level": risk_level,
        "alert_type": alert_type,
        "investigation_outcome": investigation_outcome,
    }

    for column, value in filters.items():
        if value is not None and column in filtered.columns:
            filtered = filtered[
                filtered[column].fillna("").astype(str).str.upper() == value.upper()
            ]

    if min_risk_score is not None and "risk_score" in filtered.columns:
        scores = pd.to_numeric(filtered["risk_score"], errors="coerce")
        filtered = filtered[scores >= min_risk_score]

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    page_df = filtered.iloc[start:end]

    return {
        "page": page,
        "page_size": page_size,
        "total_matching_alerts": int(total),
        "returned": int(len(page_df)),
        "alerts": [row_to_dict(row) for _, row in page_df.iterrows()],
    }


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: str):
    try:
        df = load_data()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if "alert_id" not in df.columns:
        raise HTTPException(status_code=500, detail="alert_id column is missing")

    matches = df[df["alert_id"].astype(str) == str(alert_id)]

    if matches.empty:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    return row_to_dict(matches.iloc[0])


@app.get("/alerts/{alert_id}/explanation")
def get_explanation(alert_id: str):
    try:
        df = load_data()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if "alert_id" not in df.columns:
        raise HTTPException(status_code=500, detail="alert_id column is missing")

    matches = df[df["alert_id"].astype(str) == str(alert_id)]

    if matches.empty:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    row = matches.iloc[0]

    return {
        "alert_id": clean_value(row.get("alert_id")),
        "risk_score": clean_value(row.get("risk_score")),
        "risk_level": clean_value(row.get("risk_level")),
        "priority_score": clean_value(row.get("priority_score")),
        "priority": clean_value(row.get("priority")),
        "priority_reason": clean_value(row.get("priority_reason")),
        "investigator_explanation": clean_value(
            row.get("investigator_explanation")
        ),
    }
